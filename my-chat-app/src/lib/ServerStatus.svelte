<script>
    import { serverStatus } from "./stores.js";
    import { onMount, onDestroy } from "svelte";
    import { fade } from "svelte/transition";
    import { api } from "./api.js";
    import { config } from "./config.js";

    let checkInterval;

    async function checkStatus() {
        try {
            const data = await api.checkHealth();
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

    onMount(() => {
        checkStatus();
        checkInterval = setInterval(checkStatus, config.HEALTH_CHECK_INTERVAL);
    });

    onDestroy(() => {
        if (checkInterval) clearInterval(checkInterval);
    });
</script>

<div class="server-status" transition:fade>
    {#if $serverStatus.error}
        <div class="status-indicator error">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <circle cx="12" cy="12" r="10" />
                <line x1="15" y1="9" x2="9" y2="15" />
                <line x1="9" y1="9" x2="15" y2="15" />
            </svg>
            <span>Server Error: {$serverStatus.error}</span>
        </div>
    {:else if $serverStatus.healthy}
        {#if $serverStatus.modelServer?.status === "running"}
            <div class="status-indicator success">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path d="M20 6L9 17l-5-5" />
                </svg>
                <span>
                    Server Active
                    {#if $serverStatus.modelServer?.current_model?.name}
                        - Model: {$serverStatus.modelServer.current_model.name}
                    {:else}
                        - No model loaded
                    {/if}
                </span>
            </div>
        {:else}
            <div class="status-indicator warning">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="8" x2="12" y2="12" />
                    <line x1="12" y1="16" x2="12" y2="16" />
                </svg>
                <span>Model Server Not Running</span>
            </div>
        {/if}
    {:else}
        <div class="status-indicator error">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <circle cx="12" cy="12" r="10" />
                <line x1="15" y1="9" x2="9" y2="15" />
                <line x1="9" y1="9" x2="15" y2="15" />
            </svg>
            <span>Server Offline</span>
        </div>
    {/if}
</div>

<style>
    .server-status {
        padding: 0.5rem;
        margin-bottom: 1rem;
        border-radius: 6px;
        font-size: 0.875rem;
    }

    .status-indicator {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem;
        border-radius: 4px;
    }

    .status-indicator svg {
        width: 16px;
        height: 16px;
    }

    .success {
        background: var(--success-background, #dcfce7);
        color: var(--success-text, #166534);
    }

    .warning {
        background: var(--warning-background, #fef9c3);
        color: var(--warning-text, #854d0e);
    }

    .error {
        background: var(--error-background, #fee2e2);
        color: var(--error-text, #991b1b);
    }
</style>
