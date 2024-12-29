<script>
    import { onMount } from "svelte";
    import { modelSettings } from "./stores.js";
    import { fade } from "svelte/transition";

    let models = [];
    let error = null;
    export let show = false;
    const MAX_TOKENS = 128000;
    const TOKEN_STEP = 128;
    let loading = false;
    let localSettings;
    $: localSettings = { ...$modelSettings };

    async function loadModels() {
        try {
            const response = await fetch("http://localhost:8000/models");
            if (!response.ok) throw new Error("Failed to fetch models");
            const data = await response.json();
            models = data.available_models || [];
        } catch (e) {
            error = "Failed to load models list";
        }
    }
    async function loadModel(modelId) {
        loading = true;
        error = null;
        try {
            const response = await fetch(
                `http://localhost:8000/models/${modelId}/load`,
                {
                    method: "POST",
                },
            );

            if (!response.ok) throw new Error("Failed to load model");

            localSettings.model = modelId;
            await updateSettings();
        } catch (e) {
            error = `Failed to load model: ${e.message}`;
        } finally {
            loading = false;
        }
    }

    async function stopModel() {
        try {
            await fetch("http://localhost:8000/models/stop", {
                method: "POST",
            });
            localSettings.model = null;
            await updateSettings();
        } catch (e) {
            error = "Failed to stop model";
        }
    }

    function updateSettings() {
        modelSettings.set(localSettings);
        show = false;
    }

    function handleTemperature(event) {
        const value = parseFloat(event.target.value);
        localSettings.temperature = Math.max(0, Math.min(2, value));
    }

    function handleMaxTokens(event) {
        const value = parseInt(event.target.value);
        localSettings.max_tokens = Math.max(1, Math.min(MAX_TOKENS, value));
    }

    function handleModalClick(event) {
        if (event.target.classList.contains("settings-modal")) {
            show = false;
        }
    }

    function formatTokens(value) {
        if (value >= 1000) {
            return `${(value / 1000).toFixed(1)}k`;
        }
        return value.toString();
    }

    onMount(() => {
        loadModels();
    });
</script>

<div
    class="settings-modal"
    class:show
    transition:fade
    on:click={handleModalClick}
>
    <div class="settings-content">
        <h2>Model Settings</h2>

        <div class="setting-group">
            <label class="toggle-label">
                <span>Enable Web Search</span>
                <div class="toggle-switch">
                    <input
                        type="checkbox"
                        bind:checked={localSettings.useWebSearch}
                    />
                    <span class="slider"></span>
                </div>
            </label>
            <span class="hint"
                >Allow AI to search the internet for up-to-date information</span
            >
        </div>

        <!-- Model Selection Section -->
        <div class="setting-group">
            <h3>Model Selection</h3>
            <div class="models-list">
                {#each models as model}
                    <div
                        class="model-card"
                        class:active={model.name === localSettings.model}
                    >
                        <div class="model-info">
                            <h4>{model.name}</h4>
                            <span class="model-size">{model.size}</span>
                            {#if model.description}
                                <p class="model-description">
                                    {model.description}
                                </p>
                            {/if}
                        </div>
                        <div class="model-actions">
                            {#if model.name === localSettings.model}
                                <button
                                    class="stop-model"
                                    on:click={() => stopModel()}
                                    disabled={loading}
                                >
                                    Stop Model
                                </button>
                            {:else}
                                <button
                                    class="load-model"
                                    on:click={() => loadModel(model.name)}
                                    disabled={loading}
                                >
                                    Load Model
                                </button>
                            {/if}
                        </div>
                    </div>
                {/each}
            </div>
            {#if error}
                <div class="error" transition:fade>{error}</div>
            {/if}
        </div>

        <div class="setting-group">
            <label for="temperature">
                Temperature: {localSettings.temperature}
                <span class="hint"
                    >Higher values make output more random (0-2)</span
                >
            </label>
            <input
                type="range"
                id="temperature"
                min="0"
                max="2"
                step="0.1"
                value={localSettings.temperature}
                on:input={handleTemperature}
            />
        </div>

        <div class="setting-group">
            <label for="max_tokens">
                Max Output Tokens: {formatTokens(localSettings.max_tokens)}
                <span class="hint">Maximum length of response</span>
            </label>
            <input
                type="range"
                id="max_tokens"
                min="1024"
                max={MAX_TOKENS}
                step={TOKEN_STEP}
                value={localSettings.max_tokens}
                on:input={handleMaxTokens}
            />
            <div class="range-labels">
                <span>1k</span>
                <span>{formatTokens(MAX_TOKENS)}</span>
            </div>
        </div>

        <div class="setting-group">
            <label for="top_p">
                Top P: {localSettings.top_p}
                <span class="hint">Nucleus sampling threshold (0-1)</span>
            </label>
            <input
                type="range"
                id="top_p"
                min="0"
                max="1"
                step="0.05"
                bind:value={localSettings.top_p}
            />
        </div>

        <div class="buttons">
            <button class="cancel" on:click={() => (show = false)}
                >Cancel</button
            >
            <button class="save" on:click={updateSettings}>Save Settings</button
            >
        </div>
    </div>
</div>

<style>
    .settings-modal {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.5);
        display: none;
        justify-content: center;
        align-items: center;
        z-index: 1000;
    }

    .settings-modal.show {
        display: flex;
    }

    .settings-content {
        background: var(--modal-background);
        color: var(--text-primary);
        padding: 2rem;
        border-radius: 12px;
        width: 90%;
        max-width: 500px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }

    h2 {
        margin: 0 0 1.5rem;
        color: var(--text-primary);
    }

    .setting-group {
        margin-bottom: 1.5rem;
    }

    label {
        display: block;
        margin-bottom: 0.5rem;
        color: var(--text-primary);
        font-weight: 500;
    }

    .hint {
        display: block;
        font-size: 0.875rem;
        color: #666;
        font-weight: normal;
    }

    input[type="range"] {
        width: 100%;
        margin: 0.5rem 0;
    }

    select {
        width: 100%;
        padding: 0.5rem;
        border-radius: 4px;
        font-size: 1rem;
        background: var(--input-background);
        color: var(--text-primary);
        border: 1px solid var(--input-border);
    }

    .buttons {
        display: flex;
        justify-content: flex-end;
        gap: 1rem;
        margin-top: 2rem;
    }

    button {
        padding: 0.5rem 1rem;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 1rem;
    }

    .cancel {
        background: var(--button-background);
        color: var(--text-primary);
    }

    .save {
        background: #2196f3;
        color: var(--text-primary);
    }

    button:hover {
        opacity: 0.9;
    }

    .toggle-label {
        display: flex;
        justify-content: space-between;
        align-items: center;
        cursor: pointer;
    }

    .toggle-switch {
        position: relative;
        display: inline-block;
        width: 48px;
        height: 24px;
    }

    .toggle-switch input {
        opacity: 0;
        width: 0;
        height: 0;
    }

    .slider {
        position: absolute;
        cursor: pointer;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-color: var(--button-background);
        transition: 0.4s;
        border-radius: 24px;
    }

    .slider:before {
        position: absolute;
        content: "";
        height: 18px;
        width: 18px;
        left: 3px;
        bottom: 3px;
        background-color: white;
        transition: 0.4s;
        border-radius: 50%;
    }

    input:checked + .slider {
        background-color: var(--accent-primary);
    }

    input:checked + .slider:before {
        transform: translateX(24px);
    }

    .hint {
        display: block;
        font-size: 0.875rem;
        color: var(--text-secondary);
        margin-top: 0.25rem;
    }

    .models-list {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
        max-height: 300px;
        overflow-y: auto;
        padding: 0.5rem;
        background: var(--background-primary);
        border-radius: 4px;
        border: 1px solid var(--input-border);
    }

    .model-card {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.75rem;
        background: var(--background-secondary);
        border: 1px solid var(--input-border);
        border-radius: 4px;
        transition: all 0.2s ease;
    }

    .model-card.active {
        border-color: var(--accent-primary);
        background: var(--active-item-background);
    }

    .model-info h4 {
        margin: 0 0 0.25rem;
    }

    .model-size {
        font-size: 0.75rem;
        color: var(--text-secondary);
    }

    .model-description {
        font-size: 0.875rem;
        margin: 0.5rem 0 0;
        color: var(--text-secondary);
    }

    .model-actions {
        display: flex;
        gap: 0.5rem;
    }

    .load-model {
        background: var(--accent-primary);
        color: white;
    }

    .stop-model {
        background: var(--button-background);
        color: var(--text-primary);
    }

    .error {
        margin-top: 0.5rem;
        padding: 0.5rem;
        background: var(--error-background);
        color: var(--error-text);
        border-radius: 4px;
        font-size: 0.875rem;
    }

    h3 {
        margin: 0 0 1rem;
        font-size: 1.1rem;
    }
</style>
