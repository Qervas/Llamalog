<script>
    import { onMount } from "svelte";
    import { fade } from "svelte/transition";
    import Markdown from "./lib/Markdown.svelte";
    import { modelSettings } from "./lib/stores";
    import ModelSettings from "./lib/ModelSettings.svelte";

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

    async function sendMessage() {
        if (!message.trim()) return;

        const userMessage = message;
        message = "";
        loading = true;
        shouldAutoScroll = true;

        // Ensure a session exists
        if (!currentSessionId) {
            const newSession = await createNewSession();
            currentSessionId = newSession.id;

            // Auto-rename the session based on first message
            const title =
                userMessage.slice(0, 30) +
                (userMessage.length > 30 ? "..." : "");
            await updateSessionTitle(currentSessionId, title);
        }

        chatHistory = [
            ...chatHistory,
            {
                user_input: userMessage,
                ai_response: "",
                isStreaming: true,
            },
        ];
        scrollToBottom();

        try {
            const response = await fetch("http://localhost:8000/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    message: userMessage,
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
                (msg) => msg.user_input !== userMessage,
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
    });

    $: mainContentClass = showSidebar ? "" : "sidebar-collapsed";
</script>

<div class="app-container">
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
            <!-- svelte-ignore a11y_consider_explicit_label -->
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
            <!-- svelte-ignore a11y_consider_explicit_label -->
            <button
                class="settings-button"
                on:click={() => (showSettings = true)}
            >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                    />
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                    />
                </svg>
            </button>
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
                                    <Markdown content={chat.ai_response} />
                                {/if}
                            </div>
                        </div>
                    </div>
                {/each}
            </div>

            <div class="input-container">
                <div class="input-wrapper">
                    <textarea
                        bind:this={textareaElement}
                        bind:value={message}
                        on:keydown={(e) => {
                            if (e.key === "Enter" && !e.shiftKey) {
                                e.preventDefault();
                                sendMessage();
                            }
                        }}
                        placeholder="Type your message... (Press Enter to send, Shift+Enter for new line)"
                        disabled={loading}
                        rows="1"
                    ></textarea>
                    <button
                        on:click={sendMessage}
                        disabled={loading || !message.trim()}
                        class:active={message.trim()}
                        aria-label="Send message"
                    >
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            viewBox="0 0 24 24"
                            fill="currentColor"
                            aria-hidden="true"
                        >
                            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
                        </svg>
                        <span class="sr-only">Send</span>
                    </button>
                </div>
            </div>
        </main>
    </div>
    <ModelSettings bind:show={showSettings} />
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
    }

    .sidebar {
        width: 260px;
        background: #202123;
        color: white;
        padding: 1rem;
        display: flex;
        flex-direction: column;
        transition: width 0.3s ease;
        overflow-y: auto;
        height: 100vh;
        position: fixed;
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
        background: #fff;
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
        color: #333;
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
        color: #666;
        margin: 2rem 0;
    }

    .message-group {
        margin-bottom: 1.5rem;
    }

    .message {
        display: flex;
        gap: 1rem;
        margin-bottom: 1rem;
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

    .content {
        flex: 1;
        padding: 1rem;
        background: white;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        max-width: calc(100% - 60px);
    }

    .content p {
        margin: 0;
        line-height: 1.5;
        white-space: pre-wrap;
    }

    .input-container {
        background: white;
        padding: 1rem;
        border-radius: 12px;
        box-shadow: 0 -2px 4px rgba(0, 0, 0, 0.1);
    }

    .input-wrapper {
        display: flex;
        gap: 0.5rem;
        align-items: flex-end;
    }

    textarea {
        flex: 1;
        padding: 0.8rem;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        font-size: 1rem;
        resize: none;
        min-height: 20px;
        max-height: 200px;
        font-family: inherit;
    }

    textarea:focus {
        outline: none;
        border-color: #2196f3;
    }

    button {
        padding: 0.8rem;
        background: #e0e0e0;
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
        color: #666;
    }

    button.active {
        background: #2196f3;
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
</style>
