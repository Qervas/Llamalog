<script>
    import { fade, slide } from "svelte/transition";
    import { modelSettings, serverStatus } from "./stores.js";
    import { onMount, onDestroy } from "svelte";
    import { api } from "./api.js";

    let models = [];
    let loading = false;
    let error = null;
    let currentModel = null;
    let statusCheckInterval;

    async function loadModels() {
        try {
            const data = await api.getModels();
            models = data.available_models || [];
            if (data.current_model) {
                // Update model settings if a model is currently loaded
                modelSettings.update((settings) => ({
                    ...settings,
                    model: data.current_model,
                }));
            }
        } catch (e) {
            error = "Failed to load models list";
            console.error("Error loading models:", e);
        }
    }

    $: if (!$serverStatus.healthy) {
        error = "Server is not responding";
    }

    $: canLoadModel = $serverStatus.healthy && !loading;

    async function checkServerStatus() {
        try {
            const response = await fetch("http://localhost:8000/health");
            if (!response.ok) throw new Error("Server health check failed");

            const data = await response.json();
            serverStatus.set({
                healthy: data.status === "healthy",
                modelServer: data.model_server,
                apiServer: data.api_server,
                lastCheck: new Date(),
                error: null,
            });
        } catch (e) {
            serverStatus.set({
                healthy: false,
                modelServer: null,
                apiServer: null,
                lastCheck: new Date(),
                error: e.message,
            });
        }
    }

    async function loadModel(modelId) {
        loading = true;
        error = null;
        try {
            await api.loadModel(modelId);
            await loadModels();
            await checkServerStatus();
        } catch (e) {
            error = `Failed to load model: ${e.message}`;
        } finally {
            loading = false;
        }
    }

    async function stopModel() {
        try {
            await api.stopModel();
            currentModel = null;
        } catch (e) {
            error = "Failed to stop model";
        }
    }

    onMount(() => {
        loadModels();
        checkServerStatus();
        statusCheckInterval = setInterval(() => {
            checkServerStatus();
            loadModels();
        }, 5000); // Check every 5 seconds
    });
    onDestroy(() => {
        if (statusCheckInterval) clearInterval(statusCheckInterval);
    });
</script>

<div class="model-selector">
    <h3>Available Models</h3>

    {#if loading}
        <div class="loading">Loading model...</div>
    {/if}

    {#if error}
        <div class="error" transition:fade>{error}</div>
    {/if}

    <div class="models-list">
        {#each models as model}
            <div
                class="model-card"
                class:active={model.name === $modelSettings.model}
            >
                <div class="model-info">
                    <h4>{model.name}</h4>
                    <span class="model-size">{model.size}</span>
                    {#if model.description}
                        <p class="model-description">{model.description}</p>
                    {/if}
                    <div class="model-details">
                        <span>Parameters: {model.parameters}</span>
                        <span>Context: {model.context_length} tokens</span>
                    </div>
                </div>

                <div class="model-actions">
                    {#if model.name === $modelSettings.model}
                        <button
                            class="stop"
                            on:click={stopModel}
                            disabled={!canLoadModel}
                        >
                            <svg
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                            >
                                <rect x="6" y="6" width="12" height="12" />
                            </svg>
                            Stop
                        </button>
                    {:else}
                        <button
                            class="load"
                            on:click={() => loadModel(model.name)}
                            disabled={!canLoadModel}
                        >
                            <svg
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                            >
                                <path d="M5 12h14M12 5l7 7-7 7" />
                            </svg>
                            Load
                        </button>
                    {/if}
                </div>
            </div>
        {/each}
    </div>
</div>

<style>
    .model-selector {
        padding: 1rem;
        background: var(--background-secondary);
        border-radius: 8px;
        margin-bottom: 1rem;
    }

    h3 {
        margin: 0 0 1rem;
        color: var(--text-primary);
    }

    .models-list {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .model-card {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1rem;
        background: var(--background-primary);
        border: 1px solid var(--input-border);
        border-radius: 6px;
        transition: all 0.2s ease;
    }

    .model-card:hover {
        border-color: var(--accent-primary);
    }

    .model-card.active {
        background: var(--active-item-background);
        border-color: var(--accent-primary);
    }

    .model-info h4 {
        margin: 0 0 0.25rem;
        color: var(--text-primary);
    }

    .model-size {
        font-size: 0.875rem;
        color: var(--text-secondary);
    }

    .model-actions {
        display: flex;
        gap: 0.5rem;
    }

    button {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 1rem;
        border-radius: 4px;
        border: none;
        cursor: pointer;
        font-size: 0.875rem;
        transition: all 0.2s ease;
    }

    button svg {
        width: 16px;
        height: 16px;
    }

    button.load {
        background: var(--accent-primary);
        color: white;
    }

    button.stop {
        background: var(--button-background);
        color: var(--text-primary);
    }

    button:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .loading {
        padding: 1rem;
        text-align: center;
        color: var(--text-secondary);
    }

    .error {
        padding: 1rem;
        background: #fee2e2;
        color: #dc2626;
        border-radius: 4px;
        margin-bottom: 1rem;
    }
</style>
