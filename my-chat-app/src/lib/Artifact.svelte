<script>
    import { artifacts } from "./stores.js";
    import { fade, slide } from "svelte/transition";
    import ClipboardJS from "clipboard";
    import { onMount, afterUpdate } from "svelte";

    let clipboard;

    // @ts-ignore
    onMount(async () => {
        // Load saved artifacts
        try {
            const response = await fetch("http://localhost:8000/artifacts");
            if (response.ok) {
                const savedArtifacts = await response.json();
                artifacts.update((state) => ({
                    ...state,
                    items: savedArtifacts,
                }));
            }
        } catch (error) {
            console.error("Failed to load artifacts:", error);
        }

        // Initialize clipboard
        clipboard = new ClipboardJS(".copy-button", {
            text: function (trigger) {
                // Get the content from the current artifact
                const artifactId = trigger.getAttribute("data-artifact-id");
                const artifact = $artifacts.items.find(
                    (item) => item.id === artifactId,
                );
                return artifact ? artifact.content : "";
            },
        });

        clipboard.on("success", (e) => {
            const button = e.trigger;
            button.classList.add("copied");
            const span = button.querySelector(".copy-text");
            const originalText = span.textContent;
            span.textContent = "Copied!";

            setTimeout(() => {
                button.classList.remove("copied");
                span.textContent = originalText;
            }, 2000);
        });

        return () => {
            if (clipboard) clipboard.destroy();
        };
    });

    function closeArtifacts() {
        artifacts.update((state) => ({
            ...state,
            visible: false,
            currentArtifact: null,
        }));
    }

    function selectArtifact(id) {
        artifacts.update((state) => ({
            ...state,
            currentArtifact: state.items.find((item) => item.id === id),
        }));
    }

    afterUpdate(() => {
        if ($artifacts.currentArtifact) {
            setTimeout(() => {
                Prism.highlightAll();
            }, 0);
        }
    });
</script>

{#if $artifacts.visible}
    <div class="artifacts-overlay" on:click={closeArtifacts} transition:fade>
        <div
            class="artifacts-sidebar"
            on:click|stopPropagation
            transition:slide={{ duration: 300 }}
        >
            <div class="artifacts-list">
                <header>
                    <h3>Artifacts</h3>
                    <button class="close-button" on:click={closeArtifacts}>
                        <svg
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="2"
                        >
                            <path d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </header>

                <div class="items-list">
                    {#each $artifacts.items as item}
                        <div
                            class="artifact-item"
                            class:active={$artifacts.currentArtifact?.id ===
                                item.id}
                            on:click={() => selectArtifact(item.id)}
                        >
                            <div class="artifact-icon">
                                {#if item.type === "file"}
                                    <svg
                                        viewBox="0 0 24 24"
                                        fill="none"
                                        stroke="currentColor"
                                    >
                                        <path
                                            d="M13 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V9z"
                                        />
                                        <polyline points="13 2 13 9 20 9" />
                                    </svg>
                                {:else if item.type === "code"}
                                    <svg
                                        viewBox="0 0 24 24"
                                        fill="none"
                                        stroke="currentColor"
                                    >
                                        <polyline points="16 18 22 12 16 6" />
                                        <polyline points="8 6 2 12 8 18" />
                                    </svg>
                                {:else}
                                    <svg
                                        viewBox="0 0 24 24"
                                        fill="none"
                                        stroke="currentColor"
                                    >
                                        <path
                                            d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"
                                        />
                                    </svg>
                                {/if}
                            </div>
                            <div class="artifact-info">
                                <div class="artifact-title">
                                    {item.title}
                                    <span class="artifact-type"
                                        >{item.type_desc}</span
                                    >
                                </div>
                                <div class="artifact-meta">
                                    {item.type} • {item.size}
                                </div>
                            </div>
                        </div>
                    {/each}
                </div>
            </div>

            <div class="artifact-content">
                {#if $artifacts.currentArtifact}
                    <div class="content-header">
                        <div class="content-info">
                            <h4>{$artifacts.currentArtifact.title}</h4>
                            {#if $artifacts.currentArtifact.language}
                                <span class="language-tag"
                                    >{$artifacts.currentArtifact.language}</span
                                >
                            {/if}
                        </div>
                        <button
                            class="copy-button"
                            data-artifact-id={$artifacts.currentArtifact.id}
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
                            <span class="copy-text">Copy</span>
                        </button>
                    </div>
                    <div class="code-container">
                        <div class="line-numbers">
                            {#each $artifacts.currentArtifact.content.split("\n") as _, i}
                                <span class="line-number">{i + 1}</span>
                            {/each}
                        </div>
                        <pre class="code-content"><code
                                >{$artifacts.currentArtifact.content}</code
                            ></pre>
                    </div>
                {:else}
                    <div class="no-selection">
                        <p>Select an artifact to view its content</p>
                    </div>
                {/if}
            </div>
        </div>
    </div>
{/if}

<style>
    .artifacts-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: var(--modal-overlay);
        z-index: 1000;
        backdrop-filter: blur(2px);
    }

    .artifacts-sidebar {
        position: absolute;
        top: 0;
        right: 0;
        bottom: 0;
        width: 80%;
        max-width: 1200px;
        background: var(--modal-background);
        border-left: 1px solid var(--input-border);
        box-shadow: -2px 0 8px rgba(0, 0, 0, 0.1);
        display: grid;
        grid-template-columns: 300px 1fr;
        color: var(--text-primary);
    }

    .artifacts-list {
        border-right: 1px solid var(--input-border);
        display: flex;
        flex-direction: column;
    }

    header {
        padding: 1rem;
        border-bottom: 1px solid var(--input-border);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    h3 {
        margin: 0;
        font-size: 1.2rem;
        color: var(--text-primary);
    }

    .close-button {
        background: none;
        border: none;
        cursor: pointer;
        padding: 0.5rem;
        color: var(--text-primary);
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .close-button svg {
        width: 20px;
        height: 20px;
    }

    .close-button:hover {
        color: var(--text-primary);
    }

    .items-list {
        flex: 1;
        overflow-y: auto;
        padding: 1rem;
    }

    .artifact-item {
        display: flex;
        align-items: center;
        padding: 0.75rem;
        border-radius: 6px;
        cursor: pointer;
        transition: background 0.2s;
        background: var(--background-primary);
        gap: 0.75rem;
    }

    .artifact-item:hover {
        background: var(--hover-background);
    }

    .artifact-item.active {
        background: var(--active-item-background);
    }

    .artifact-icon svg {
        width: 24px;
        height: 24px;
        color: var(--text-primary);
    }

    .artifact-info {
        flex: 1;
        min-width: 0;
    }

    .artifact-title {
        font-weight: 500;
        margin-bottom: 0.25rem;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        color: var(--text-primary);
    }

    .artifact-meta {
        font-size: 0.875rem;
        color: var(--text-primary);
    }

    .artifact-content {
        padding: 1.5rem;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        height: 100%;
    }

    .content-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
    }

    .content-header h4 {
        margin: 0;
        font-size: 1.1rem;
        color: var(--text-primary);
    }

    .copy-button {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 1rem;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        background: var(--button-background);
        color: var(--text-primary);
        font-size: 0.875rem;
        transition: all 0.2s ease;
    }

    .copy-button svg {
        width: 16px;
        height: 16px;
    }

    .copy-button:hover {
        background: var(--background-secondary);
        border-color: var(--accent-primary);
    }

    .copy-button.copied {
        background: var(--accent-primary);
        color: white;
    }

    .code-container {
        display: flex;
        background: var(--code-background);
        border-radius: 6px;
        overflow: hidden;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
            monospace;
        font-size: 0.875rem;
        line-height: 1.5;
        flex: 1;
        min-height: 0;
    }

    .line-numbers {
        padding: 1rem 0.5rem;
        border-right: 1px solid var(--input-border);
        background: var(--background-secondary);
        user-select: none;
        text-align: right;
        color: var(--text-secondary);
    }

    .line-number {
        display: block;
        padding: 0 0.5rem;
        opacity: 0.5;
        font-size: 0.75rem;
    }

    .code-content {
        margin: 0;
        padding: 1rem;
        background: transparent;
        color: var(--text-primary);
        overflow: auto;
        flex: 1;
        min-width: 0;
    }

    pre,
    code {
        font-family: inherit;
        background: transparent;
        color: inherit;
    }

    .no-selection {
        display: flex;
        align-items: center;
        justify-content: center;
        height: 100%;
        color: var(--text-secondary);
    }

    .content-info {
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }

    .language-tag {
        padding: 0.25rem 0.5rem;
        background: #e2e8f0;
        border-radius: 4px;
        font-size: 0.75rem;
        background: var(--background-tertiary);
        color: var(--text-secondary);
        font-family: monospace;
    }

    :global(pre .token.comment),
    :global(pre .token.prolog),
    :global(pre .token.doctype),
    :global(pre .token.cdata) {
        color: #8292a2 !important;
    }

    :global(pre .token.punctuation) {
        color: #f8f8f2 !important;
    }

    :global(pre .token.namespace) {
        opacity: 0.7 !important;
    }

    :global(pre .token.property),
    :global(pre .token.tag),
    :global(pre .token.constant),
    :global(pre .token.symbol),
    :global(pre .token.deleted) {
        color: #ff79c6 !important;
    }

    :global(pre .token.boolean),
    :global(pre .token.number) {
        color: #bd93f9 !important;
    }

    :global(pre .token.selector),
    :global(pre .token.attr-name),
    :global(pre .token.string),
    :global(pre .token.char),
    :global(pre .token.builtin),
    :global(pre .token.inserted) {
        color: #50fa7b !important;
    }

    :global(pre .token.operator),
    :global(pre .token.entity),
    :global(pre .token.url),
    :global(pre .language-css .token.string),
    :global(pre .style .token.string) {
        color: #f8f8f2 !important;
    }

    :global(pre .token.atrule),
    :global(pre .token.attr-value),
    :global(pre .token.keyword) {
        color: #ff79c6 !important;
    }

    :global(pre .token.function),
    :global(pre .token.class-name) {
        color: #ffb86c !important;
    }

    :global(pre .token.regex),
    :global(pre .token.important),
    :global(pre .token.variable) {
        color: #f1fa8c !important;
    }

    :global(pre .token.important),
    :global(pre .token.bold) {
        font-weight: bold !important;
    }

    :global(pre .token.italic) {
        font-style: italic !important;
    }

    :global(pre .token.entity) {
        cursor: help !important;
    }
</style>
