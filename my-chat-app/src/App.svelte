<script>
    import { onDestroy, onMount } from "svelte";
    import { fade } from "svelte/transition";
    import Markdown from "./lib/Markdown.svelte";
    import { modelSettings, artifacts, currentTheme } from "./lib/stores";
    import ModelSettings from "./lib/ModelSettings.svelte";
    import FileUpload from "./lib/FileUpload.svelte";
    import Artifact from "./lib/Artifact.svelte";
    import ThemeToggle from "./lib/ThemeToggle.svelte";
    import { themes } from "./lib/theme";

    let message = "";
    let chatHistory = [];
    let loading = false;
    let chatContainer;
    let sessions = [];
    let currentSessionId = null;
    let showSidebar = true;
    let textareaElement;
    let editingSessionId = null;
    let editingTitle = "";
    let shouldAutoScroll = true;
    let showSettings = false;
    export let show = false;
    let fileUploadComponent;
    let isDragging = false;
    let dragCounter = 0;
    let selectedFiles = [];

    let localSettings;
    $: localSettings = { ...$modelSettings };
    async function createNewSession() {
        try {
            const response = await fetch("http://localhost:8000/sessions", {
                method: "POST",
            });
            const newSession = await response.json();
            sessions = [newSession, ...sessions];
            // Automatically set this session as current
            currentSessionId = newSession.id;
            return newSession;
        } catch (error) {
            console.error("Failed to create new session:", error);
        }
    }

    async function loadSession(sessionId) {
        try {
            const response = await fetch(
                `http://localhost:8000/sessions/${sessionId}`,
            );
            const data = await response.json();
            currentSessionId = sessionId;
            chatHistory = data.conversations;
            shouldAutoScroll = true;
            scrollToBottom();
        } catch (error) {
            console.error("Failed to load session:", error);
        }
    }

    async function deleteSession(sessionId) {
        if (!confirm("Are you sure you want to delete this chat?")) return;

        try {
            await fetch(`http://localhost:8000/sessions/${sessionId}`, {
                method: "DELETE",
            });
            sessions = sessions.filter((s) => s.id !== sessionId);
            if (currentSessionId === sessionId) {
                currentSessionId = null;
                chatHistory = [];
            }
        } catch (error) {
            console.error("Failed to delete session:", error);
        }
    }

    async function updateSessionTitle(sessionId, newTitle) {
        try {
            await fetch(`http://localhost:8000/sessions/${sessionId}`, {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ title: newTitle }),
            });
            sessions = sessions.map((s) =>
                s.id === sessionId ? { ...s, title: newTitle } : s,
            );
        } catch (error) {
            console.error("Failed to update session title:", error);
        }
    }

    function formatSize(bytes) {
        const units = ["B", "KB", "MB", "GB"];
        let size = bytes;
        let unitIndex = 0;

        while (size >= 1024 && unitIndex < units.length - 1) {
            size /= 1024;
            unitIndex++;
        }

        return `${size.toFixed(1)} ${units[unitIndex]}`;
    }

    async function handleFileContent(content, filename) {
        const id = crypto.randomUUID();
        const artifact = {
            id,
            type: "file",
            title: filename,
            content,
            size: formatSize(content.length),
        };

        artifacts.update((state) => ({
            ...state,
            items: [...state.items, artifact],
            visible: true,
            currentArtifact: artifact,
        }));

        return `[File: ${filename}] (Click to view content)`;
    }

    async function sendMessage() {
        if (!message.trim() && !selectedFiles.length) return;

        loading = true;
        shouldAutoScroll = true;
        try {
            // Process files first if any
            const fileContent =
                selectedFiles.length > 0 ? await processFiles() : "";

            // Combine user message with file content
            let finalMessage = "";
            if (fileContent && message.trim()) {
                finalMessage = `${message}\n\nAttached files:\n${fileContent}`;
            } else if (fileContent) {
                finalMessage = `Please analyze these files:\n\n${fileContent}`;
            } else {
                finalMessage = message;
            }

            // Clear the input and files
            message = "";
            selectedFiles = [];

            // Ensure a session exists
            if (!currentSessionId) {
                const newSession = await createNewSession();
                currentSessionId = newSession.id;
                await updateSessionTitle(
                    currentSessionId,
                    finalMessage.slice(0, 30) + "...",
                );
            }

            // Add message to chat history
            chatHistory = [
                ...chatHistory,
                {
                    user_input: finalMessage,
                    ai_response: "",
                    isStreaming: true,
                },
            ];
            scrollToBottom();

            const response = await fetch("http://localhost:8000/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    message: finalMessage,
                    session_id: currentSessionId,
                    settings: $modelSettings,
                }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let currentResponse = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split("\n");

                for (const line of lines) {
                    if (line.startsWith("data: ") && line.length > 6) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            if (data.content) {
                                currentResponse += data.content;
                                chatHistory = chatHistory.map((msg, index) => {
                                    if (index === chatHistory.length - 1) {
                                        const updatedMsg = {
                                            ...msg,
                                            ai_response: currentResponse,
                                            isStreaming: false,
                                        };
                                        scrollToBottom();
                                        return updatedMsg;
                                    }
                                    return msg;
                                });
                            }
                        } catch (e) {
                            console.error("Error parsing SSE data:", e);
                        }
                    }
                }
            }
        } catch (error) {
            console.error("Error:", error);
            chatHistory = chatHistory.filter(
                (msg) => msg.user_input !== message,
            );
            alert("Failed to send message. Please try again.");
        } finally {
            loading = false;
            textareaElement?.focus();
        }
    }

    function startEditing(session) {
        editingSessionId = session.id;
        editingTitle = session.title;
    }

    function updateSettings() {
        modelSettings.set({
            ...localSettings,
            stream: true,
        });
        show = false;
    }

    async function saveTitle(session) {
        if (!editingTitle.trim()) {
            editingTitle = session.title;
            editingSessionId = null;
            return;
        }

        try {
            const response = await fetch(
                `http://localhost:8000/sessions/${session.id}`,
                {
                    method: "PUT",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({ title: editingTitle.trim() }),
                },
            );

            if (!response.ok) {
                throw new Error("Failed to update title");
            }

            // Update local state
            sessions = sessions.map((s) =>
                s.id === session.id ? { ...s, title: editingTitle.trim() } : s,
            );
        } catch (error) {
            console.error("Failed to update session title:", error);
            alert("Failed to update session title");
        } finally {
            editingSessionId = null;
        }
    }
    async function processFiles() {
        if (!selectedFiles.length) return "";
        let fileContents = [];

        try {
            for (const fileData of selectedFiles) {
                const formData = new FormData();
                formData.append("file", fileData.file);

                const response = await fetch("http://localhost:8000/upload", {
                    method: "POST",
                    body: formData,
                });

                if (!response.ok) {
                    throw new Error(`Failed to upload file: ${fileData.name}`);
                }

                const result = await response.json();
                fileContents.push({
                    content: result.content,
                    filename: fileData.name,
                });
            }

            // Format the file contents section
            return fileContents
                .map((f) => `[File: ${f.filename}]\n${f.content}`)
                .join("\n\n");
        } catch (error) {
            console.error("Error processing files:", error);
            alert("Failed to process files. Please try again.");
            return "";
        }
    }

    function handleTitleKeydown(event, session) {
        if (event.key === "Enter") {
            event.preventDefault();
            saveTitle(session);
        } else if (event.key === "Escape") {
            editingSessionId = null;
            editingTitle = session.title;
        }
    }

    function handleScroll(event) {
        const target = event.target;
        const isAtBottom =
            Math.abs(
                target.scrollHeight - target.scrollTop - target.clientHeight,
            ) < 1;
        shouldAutoScroll = isAtBottom;
    }

    function scrollToBottom() {
        if (chatContainer && shouldAutoScroll) {
            setTimeout(() => {
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }, 0);
        }
    }
    function handleDragOver(e) {
        e.preventDefault();
        e.stopPropagation();
        if (!isDragging) {
            isDragging = true;
        }
    }

    function handleDragLeave(e) {
        e.preventDefault();
        e.stopPropagation();
        // Check if we're leaving the window
        const rect = e.currentTarget.getBoundingClientRect();
        const x = e.clientX;
        const y = e.clientY;

        if (
            x <= rect.left ||
            x >= rect.right ||
            y <= rect.top ||
            y >= rect.bottom
        ) {
            isDragging = false;
        }
    }

    function handleDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            fileUploadComponent?.handleFiles(files);
        }
        isDragging = false;
    }

    function handleDragEnter(e) {
        e.preventDefault();
        e.stopPropagation();
        if (!isDragging) {
            isDragging = true;
        }
    }

    function applyTheme(themeName) {
        const theme = themes[themeName];
        Object.entries(theme).forEach(([property, value]) => {
            document.documentElement.style.setProperty(property, value);
        });
    }

    onMount(async () => {
        try {
            const response = await fetch("http://localhost:8000/sessions");
            sessions = await response.json();
        } catch (error) {
            console.error("Failed to load sessions:", error);
        }
    });
    onMount(() => {
        textareaElement?.focus();
        const savedTheme = localStorage.getItem("theme") || "light";
        currentTheme.set(savedTheme);
        applyTheme(savedTheme);
    });

    onDestroy(() => {
        isDragging = false;
        dragCounter = 0;
    });

    $: mainContentClass = showSidebar ? "" : "sidebar-collapsed";
    $: if ($currentTheme) {
        applyTheme($currentTheme);
    }
</script>

<div
    class="app-container"
    on:dragenter|preventDefault
    on:dragover={handleDragOver}
    on:dragleave={handleDragLeave}
    on:drop={handleDrop}
>
    {#if isDragging}
        <div
            class="drag-overlay"
            on:dragover|preventDefault
            on:dragleave={handleDragLeave}
            on:drop={handleDrop}
        >
            <div class="drag-content">
                {#if fileUploadComponent?.loading}
                    <div class="loading-spinner" />
                    <span>Processing file...</span>
                {:else}
                    <svg
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                    >
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                        <polyline points="17 8 12 3 7 8" />
                        <line x1="12" y1="3" x2="12" y2="15" />
                    </svg>
                    <span>Drop files here</span>
                    <span class="supported-formats"
                        >Any file type supported</span
                    >
                {/if}
            </div>
        </div>
    {/if}
    <!-- Sidebar -->
    <aside class="sidebar" class:collapsed={!showSidebar}>
        <button class="new-chat" on:click={createNewSession}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M12 4v16m8-8H4"
                />
            </svg>
            New Chat
        </button>

        <div class="sessions-list">
            {#each sessions as session}
                <div
                    class="session-item"
                    class:active={currentSessionId === session.id}
                    on:click={() => loadSession(session.id)}
                >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-4l-4 4z"
                        />
                    </svg>

                    {#if editingSessionId === session.id}
                        <input
                            type="text"
                            bind:value={editingTitle}
                            on:blur={() => saveTitle(session)}
                            on:keydown={(e) => handleTitleKeydown(e, session)}
                            class="session-title-input"
                            autofocus
                        />
                    {:else}
                        <span
                            class="session-title"
                            on:dblclick={() => startEditing(session)}
                            title={session.title}
                        >
                            {session.title}
                        </span>
                    {/if}

                    <button
                        class="delete-session"
                        on:click|stopPropagation={() =>
                            deleteSession(session.id)}
                        title="Delete chat"
                    >
                        <svg
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                stroke-width="2"
                                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                            />
                        </svg>
                    </button>
                </div>
            {/each}
        </div>
    </aside>

    <div class="main-content" class:sidebar-collapsed={!showSidebar}>
        <header>
            <button
                class="toggle-sidebar"
                on:click={() => (showSidebar = !showSidebar)}
            >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M4 6h16M4 12h16M4 18h16"
                    />
                </svg>
            </button>
            <h1>AI Assistant</h1>
            <div class="header-actions">
                <ThemeToggle />
                <button
                    class="artifacts-button"
                    on:click={() =>
                        artifacts.update((state) => ({
                            ...state,
                            visible: !state.visible,
                        }))}
                    title="View Artifacts"
                >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <path
                            d="M20 11.08V8l-6-6H6a2 2 0 00-2 2v16c0 1.1.9 2 2 2h12a2 2 0 002-2v-3.08"
                        />
                        <path d="M18 14v4" />
                        <path d="M18 22v.01" />
                    </svg>
                </button>
                <button
                    class="settings-button"
                    on:click={() => (showSettings = true)}
                >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <path d="M12 15a3 3 0 100-6 3 3 0 000 6z" />
                        <path
                            d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"
                        />
                    </svg>
                </button>
            </div>
        </header>
        <main>
            <div
                class="chat-container"
                bind:this={chatContainer}
                on:scroll={handleScroll}
            >
                {#if chatHistory.length === 0}
                    <div class="welcome-message">
                        <h2>Welcome! 👋</h2>
                        <p>How can I help you today?</p>
                        <FileUpload onFileProcess={handleFileContent} />
                    </div>
                {/if}

                {#each chatHistory as chat, i (i)}
                    <div class="message-group" transition:fade>
                        <div class="message user">
                            <div class="avatar">You</div>
                            <div class="content">
                                <p>{chat.user_input}</p>
                            </div>
                        </div>

                        <div class="message ai">
                            <div class="avatar">AI</div>
                            <div class="content">
                                {#if chat.isStreaming && chat.ai_response === ""}
                                    <div class="loading-dots">
                                        <span>.</span><span>.</span><span
                                            >.</span
                                        >
                                    </div>
                                {:else}
                                    <div class="response-container">
                                        <div class="response-actions">
                                            <button
                                                class="copy-response"
                                                on:click={() => {
                                                    navigator.clipboard.writeText(
                                                        chat.ai_response,
                                                    );
                                                    const button =
                                                        document.activeElement;
                                                    if (button) {
                                                        const originalText =
                                                            button.innerHTML;
                                                        button.innerHTML =
                                                            "Copied!";
                                                        setTimeout(() => {
                                                            button.innerHTML =
                                                                originalText;
                                                        }, 2000);
                                                    }
                                                }}
                                                title="Copy response"
                                            >
                                                <svg
                                                    viewBox="0 0 24 24"
                                                    fill="none"
                                                    stroke="currentColor"
                                                >
                                                    <path
                                                        d="M8 4v12a2 2 0 002 2h8a2 2 0 002-2V7.242a2 2 0 00-.602-1.43L16.083 2.57A2 2 0 0014.685 2H10a2 2 0 00-2 2z"
                                                    />
                                                    <path
                                                        d="M16 18v2a2 2 0 01-2 2H6a2 2 0 01-2-2V9a2 2 0 012-2h2"
                                                    />
                                                </svg>
                                            </button>
                                        </div>
                                        <Markdown content={chat.ai_response} />
                                    </div>
                                {/if}
                            </div>
                        </div>
                    </div>
                {/each}
            </div>

            <div class="input-container">
                <div class="input-wrapper">
                    <button
                        class="upload-button"
                        title="Upload file"
                        on:click={() => {
                            const fileInput = document.querySelector(
                                '.file-upload input[type="file"]',
                            );
                            if (fileInput) fileInput.click();
                        }}
                    >
                        <svg
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                        >
                            <path d="M12 5v13M5 12l7-7 7 7" />
                        </svg>
                    </button>

                    {#if selectedFiles.length > 0}
                        <div class="selected-files">
                            {#each selectedFiles as file}
                                <div class="file-chip">
                                    <span>{file.name}</span>
                                    <button
                                        class="remove-file"
                                        on:click={() => {
                                            selectedFiles =
                                                selectedFiles.filter(
                                                    (f) => f !== file,
                                                );
                                        }}>×</button
                                    >
                                </div>
                            {/each}
                        </div>
                    {/if}

                    <FileUpload
                        bind:this={fileUploadComponent}
                        on:filesSelected={({ detail }) => {
                            selectedFiles = [...selectedFiles, ...detail.files];
                        }}
                    />

                    <textarea
                        bind:this={textareaElement}
                        bind:value={message}
                        on:keydown={(e) => {
                            if (e.key === "Enter" && !e.shiftKey) {
                                e.preventDefault();
                                sendMessage();
                            }
                        }}
                        placeholder="Type your message..."
                        disabled={loading}
                        rows="1"
                    />
                    <button
                        on:click={sendMessage}
                        disabled={loading ||
                            (!message.trim() && !selectedFiles.length)}
                        class:active={message.trim() ||
                            selectedFiles.length > 0}
                    >
                        <svg viewBox="0 0 24 24" fill="currentColor">
                            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
                        </svg>
                    </button>
                </div>
            </div>
        </main>
    </div>
    <ModelSettings bind:show={showSettings} />
    <Artifact />
</div>

<style>
    .app-container {
        display: flex;
        height: 100vh;
        width: 100vw;
        overflow: hidden;
        position: fixed;
        top: 0;
        left: 0;
        background-color: var(--background-primary);
        color: var(--text-primary);
    }

    .sidebar {
        width: 260px;
        background: var(--sidebar-background);
        color: var(--sidebar-text);
        padding: 1rem;
        display: flex;
        flex-direction: column;
        transition: width 0.3s ease;
        overflow-y: auto;
        height: 100vh;
        flex-shrink: 0;
        position: relative;
        left: 0;
        top: 0;
    }

    .sidebar.collapsed {
        width: 0;
        padding: 0;
        overflow: hidden;
    }

    .main-content {
        flex: 1;
        display: flex;
        transition: margin-left 0.3s ease;
        margin-left: 260px;
        flex-direction: column;
        overflow: hidden;
        height: 100vh;
        margin-left: 0;
    }

    .main-content.sidebar-collapsed {
        margin-left: 0;
    }

    .new-chat {
        width: 100%;
        padding: 0.8rem;
        background: #343541;
        color: white;
        border: 1px solid #565869;
        border-radius: 8px;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        cursor: pointer;
        margin-bottom: 1rem;
    }

    .new-chat svg {
        width: 20px;
        height: 20px;
    }

    .sessions-list {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .session-item {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.8rem;
        border-radius: 8px;
        cursor: pointer;
        transition: background-color 0.2s;
    }

    .session-item:hover {
        background: #2a2b32;
    }

    .session-item.active {
        background: #343541;
    }

    .session-item svg {
        width: 20px;
        height: 20px;
    }

    .session-title {
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .delete-session {
        padding: 4px;
        background: transparent;
        color: #565869;
        opacity: 0;
        transition: opacity 0.2s;
    }

    .session-item:hover .delete-session {
        opacity: 1;
    }

    .toggle-sidebar {
        padding: 0.5rem;
        background: transparent;
        color: #333;
    }

    .toggle-sidebar svg {
        width: 24px;
        height: 24px;
    }
    .chat-app {
        height: 100vh;
        display: flex;
        flex-direction: column;
        background-color: #f5f5f5;
    }

    header {
        background: var(--background-secondary);
        color: var(--text-primary);
        display: flex;
        padding: 1rem;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        z-index: 1;
    }

    header h1 {
        margin: 0;
        font-size: 1.5rem;
        color: var(--text-primary);
    }

    main {
        flex: 1;
        display: flex;
        flex-direction: column;
        max-width: 1000px;
        margin: 0 auto;
        width: 100%;
        padding: 1rem;
        overflow: hidden;
        height: calc(100vh - 60px);
    }

    .chat-container {
        flex: 1;
        overflow-y: auto;
        padding: 1rem;
        margin-bottom: 1rem;
        scrollbar-width: thin;
        scrollbar-color: #888 #f1f1f1;
        scroll-behavior: smooth;
        contain: strict;
        height: calc(100vh - 120px);
    }

    .welcome-message {
        text-align: center;
        color: var(--text-primary);
        margin: 2rem 0;
    }

    .message-group {
        margin-bottom: 1.5rem;
    }

    .message .content {
        position: relative;
        flex: 1;
        padding: 1rem;
        background: var(--message-background);
        color: var(--text-primary);
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        max-width: calc(100% - 60px);
    }

    .avatar {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background: #e0e0e0;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.8rem;
        font-weight: 500;
    }

    .user .avatar {
        background: #2196f3;
        color: white;
    }

    .ai .avatar {
        background: #4caf50;
        color: white;
    }

    .content p {
        margin: 0;
        line-height: 1.5;
        white-space: pre-wrap;
    }

    .input-container {
        background: var(--background-secondary);
        padding: 1rem;
        border-radius: 12px;
        box-shadow: 0 -2px 4px var(--shadow-color);
    }

    .input-wrapper {
        display: flex;
        gap: 0.5rem;
        align-items: flex-end;
        border-radius: 8px;
        border: 1px solid;
        background: var(--background-primary);
        border-color: var(--input-border);
        padding: 0.4rem;
    }

    textarea {
        flex: 1;
        padding: 0.8rem;
        border: 1px solid;
        border-radius: 8px;
        font-size: 1rem;
        resize: none;
        min-height: 20px;
        max-height: 200px;
        font-family: inherit;
        background: var(--input-background);
        color: var(--text-primary);
        border-color: var(--input-border);
    }

    textarea:focus {
        outline: none;
        border-color: #2196f3;
    }

    textarea::placeholder {
        color: var(--text-secondary);
    }

    button {
        padding: 0.8rem;
        background: var(--button-background);
        color: var(--text-primary);
        border: none;
        border-radius: 8px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.2s;
    }

    button svg {
        width: 24px;
        height: 24px;
        color: var(--text-secondary);
    }

    button.active {
        background: var(--accent-primary);
        color: white;
    }

    button.active svg {
        color: white;
    }

    button:hover {
        opacity: 0.9;
    }

    button:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .loading-dots {
        display: flex;
        gap: 0.2rem;
    }

    .loading-dots span {
        animation: dots 1.5s infinite;
        font-size: 1.5rem;
        line-height: 0.5;
    }

    .loading-dots span:nth-child(2) {
        animation-delay: 0.5s;
    }

    .loading-dots span:nth-child(3) {
        animation-delay: 1s;
    }

    @keyframes dots {
        0%,
        100% {
            opacity: 0;
        }
        50% {
            opacity: 1;
        }
    }

    @media (max-width: 640px) {
        main {
            padding: 0.5rem;
        }

        .content {
            padding: 0.8rem;
        }
    }

    .sr-only {
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        white-space: nowrap;
        border: 0;
    }
    .session-title-input {
        flex: 1;
        background: transparent;
        border: none;
        border-bottom: 1px solid #565869;
        color: white;
        font-size: 0.9rem;
        padding: 2px 4px;
        width: 100%;
        outline: none;
    }

    .session-title-input:focus {
        border-bottom-color: #2196f3;
    }

    .session-title {
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        cursor: text;
    }

    .session-item:hover .session-title {
        color: #fff;
    }

    .session-item.active .session-title {
        color: #fff;
        font-weight: 500;
    }

    .chat-container::-webkit-scrollbar {
        width: 8px;
    }

    .chat-container::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 4px;
    }

    .chat-container::-webkit-scrollbar-thumb {
        background: #888;
        border-radius: 4px;
    }

    .chat-container::-webkit-scrollbar-thumb:hover {
        background: #555;
    }

    /* Update .sessions-list */
    .sessions-list {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        overflow-y: auto;
        flex: 1;
        scrollbar-width: thin;
        scrollbar-color: #565869 #202123;
    }

    /* styles for custom scrollbar in sessions-list */
    .sessions-list::-webkit-scrollbar {
        width: 6px;
    }

    .sessions-list::-webkit-scrollbar-track {
        background: #202123;
    }

    .sessions-list::-webkit-scrollbar-thumb {
        background: #565869;
        border-radius: 3px;
    }

    .sessions-list::-webkit-scrollbar-thumb:hover {
        background: #666;
    }

    .settings-button {
        padding: 0.5rem;
        background: transparent;
        color: #333;
    }

    .settings-button svg {
        width: 24px;
        height: 24px;
    }

    .upload-button {
        padding: 0.5rem;
        background: transparent;
        border: none;
        color: var(--text-secondary);
        cursor: pointer;
        transition: color 0.2s;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .upload-button:hover {
        color: var(--accent-primary);
    }

    .upload-button svg {
        width: 1.25rem;
        height: 1.25rem;
    }

    .input-wrapper {
        display: flex;
        gap: 0.5rem;
        align-items: flex-end;
        background: var(--background-secondary);
        border-radius: 8px;
        border: 1px solid;
        border-color: var(--input-border);
        padding: 0.4rem;
    }

    .drag-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(33, 150, 243, 0.15);
        backdrop-filter: blur(2px);
        z-index: 9999;
        display: flex;
        align-items: center;
        justify-content: center;
        pointer-events: none;
    }

    .drag-content {
        background: white;
        padding: 2rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 1rem;
        border: 3px dashed #2196f3;
        transition: all 0.2s ease;
        pointer-events: none;
    }

    .drag-content svg {
        width: 48px;
        height: 48px;
        color: #2196f3;
    }

    .drag-content span {
        font-size: 1.2rem;
        color: #2196f3;
        font-weight: 500;
    }

    .drag-content:hover {
        transform: scale(1.02);
    }

    .drag-overlay.dragging .drag-content {
        border-color: #1976d2;
        background: #e3f2fd;
    }

    .loading-spinner {
        width: 48px;
        height: 48px;
        border: 4px solid #f3f3f3;
        border-top: 4px solid #2196f3;
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }

    @keyframes spin {
        0% {
            transform: rotate(0deg);
        }
        100% {
            transform: rotate(360deg);
        }
    }

    .selected-files {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin: 0.5rem 0;
    }

    .file-chip {
        display: flex;
        align-items: center;
        gap: 0.25rem;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-size: 0.75rem;
        background: var(--file-chip-background);
        color: var(--file-chip-text);
    }

    .remove-file {
        padding: 0;
        background: transparent;
        border: none;
        color: var(--text-secondary);
        cursor: pointer;
        font-size: 1rem;
        line-height: 1;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .remove-file:hover {
        color: #ef4444;
    }

    .input-wrapper textarea {
        border: none;
        padding: 0.5rem;
        min-height: 24px;
        max-height: 200px;
        resize: none;
    }

    .code-preview {
        background: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 6px;
        cursor: pointer;
        transition: background 0.2s;
    }

    .code-preview:hover {
        background: #e9ecef;
    }

    .preview-header {
        display: flex;
        justify-content: space-between;
        padding: 0.5rem 1rem;
        background: #f1f3f5;
        border-bottom: 1px solid #e9ecef;
        font-size: 0.875rem;
        color: #495057;
    }

    .preview-content {
        margin: 0;
        padding: 1rem;
        overflow: hidden;
    }

    .header-actions {
        display: flex;
        gap: 0.5rem;
    }

    .artifacts-button {
        padding: 0.5rem;
        background: transparent;
        color: #333;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .artifacts-button svg {
        width: 24px;
        height: 24px;
    }

    .artifacts-button:hover {
        color: #2196f3;
    }

    .response-container {
        position: relative;
    }

    .response-actions {
        position: absolute;
        top: 0.5rem;
        right: 0.5rem;
        z-index: 1;
        opacity: 0;
        transition: opacity 0.2s;
    }

    .content:hover .response-actions {
        opacity: 1;
    }

    .copy-response {
        padding: 0.5rem;
        background: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 4px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #666;
        transition: all 0.2s;
    }

    .copy-response:hover {
        background: #e9ecef;
        color: #333;
    }

    .copy-response svg {
        width: 16px;
        height: 16px;
    }
</style>
