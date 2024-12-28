<script>
    import { modelSettings } from "./stores.js";
    import { fade } from "svelte/transition";

    export let show = false;

    let localSettings;
    $: localSettings = { ...$modelSettings };

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
        localSettings.max_tokens = Math.max(1, Math.min(4096, value));
    }

    function handleModalClick(event) {
        if (event.target.classList.contains("settings-modal")) {
            show = false;
        }
    }
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

        <div class="setting-group">
            <label for="model">Model</label>
            <select id="model" bind:value={localSettings.model}>
                <option value="llama-3.2-3b-instruct"
                    >Llama 3.2B Instruct</option
                >
                <!-- Add other models as needed -->
            </select>
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
                Max Tokens: {localSettings.max_tokens}
                <span class="hint">Maximum length of response</span>
            </label>
            <input
                type="range"
                id="max_tokens"
                min="1"
                max="4096"
                step="1"
                value={localSettings.max_tokens}
                on:input={handleMaxTokens}
            />
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
</style>
