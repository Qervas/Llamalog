<script>
    import { artifacts } from "./stores.js";
    import { fade, slide } from "svelte/transition";
    import ClipboardJS from "clipboard";
    import { onMount } from "svelte";

    let clipboard;

    onMount(() => {
        clipboard = new ClipboardJS(".copy-button");
        clipboard.on("success", (e) => {
            const button = e.trigger;
            button.textContent = "Copied!";
            setTimeout(() => {
                button.textContent = "Copy";
            }, 2000);
        });

        return () => {
            clipboard.destroy();
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
                                <div class="artifact-title">{item.title}</div>
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
                        <h4>{$artifacts.currentArtifact.title}</h4>
                        <button
                            class="copy-button"
                            data-clipboard-text={$artifacts.currentArtifact
                                .content}
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
                            Copy
                        </button>
                    </div>
                    <pre><code>{$artifacts.currentArtifact.content}</code></pre>
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
        background: rgba(0, 0, 0, 0.3);
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
        background: white;
        box-shadow: -2px 0 8px rgba(0, 0, 0, 0.1);
        display: grid;
        grid-template-columns: 300px 1fr;
    }

    .artifacts-list {
        border-right: 1px solid #eee;
        display: flex;
        flex-direction: column;
    }

    header {
        padding: 1rem;
        border-bottom: 1px solid #eee;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    h3 {
        margin: 0;
        font-size: 1.2rem;
        color: #333;
    }

    .close-button {
        background: none;
        border: none;
        cursor: pointer;
        padding: 0.5rem;
        color: #666;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .close-button svg {
        width: 20px;
        height: 20px;
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
        gap: 0.75rem;
    }

    .artifact-item:hover {
        background: #f5f5f5;
    }

    .artifact-item.active {
        background: #e3f2fd;
    }

    .artifact-icon svg {
        width: 24px;
        height: 24px;
        color: #666;
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
    }

    .artifact-meta {
        font-size: 0.875rem;
        color: #666;
    }

    .artifact-content {
        padding: 1.5rem;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
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
        color: #333;
    }

    .copy-button {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 1rem;
        background: #e3f2fd;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        color: #1976d2;
        font-size: 0.875rem;
    }

    .copy-button svg {
        width: 16px;
        height: 16px;
    }

    .copy-button:hover {
        background: #bbdefb;
    }

    pre {
        margin: 0;
        padding: 1rem;
        background: #282c34;
        border-radius: 6px;
        overflow-x: auto;
        flex: 1;
    }

    code {
        font-family: "Fira Code", monospace;
        font-size: 0.875rem;
        color: #abb2bf;
    }

    .no-selection {
        display: flex;
        align-items: center;
        justify-content: center;
        height: 100%;
        color: #666;
    }
</style>
