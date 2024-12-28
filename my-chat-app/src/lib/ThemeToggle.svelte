<script>
    // @ts-nocheck

    import { currentTheme } from "./stores.js";
    import { themes } from "./theme.js";

    function toggleTheme() {
        $currentTheme = $currentTheme === "light" ? "dark" : "light";
        applyTheme($currentTheme);
    }

    function applyTheme(themeName) {
        const theme = themes[themeName];
        Object.entries(theme).forEach(([property, value]) => {
            document.documentElement.style.setProperty(property, value);
        });
        localStorage.setItem("theme", themeName);
    }
</script>

<button class="theme-toggle" on:click={toggleTheme}>
    {#if $currentTheme === "light"}
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" />
        </svg>
    {:else}
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <circle cx="12" cy="12" r="5" />
            <line x1="12" y1="1" x2="12" y2="3" />
            <line x1="12" y1="21" x2="12" y2="23" />
            <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
            <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
            <line x1="1" y1="12" x2="3" y2="12" />
            <line x1="21" y1="12" x2="23" y2="12" />
            <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
            <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
        </svg>
    {/if}
</button>

<style>
    .theme-toggle {
        padding: 0.5rem;
        background: transparent;
        border: none;
        color: var(--text-primary);
        cursor: pointer;
        transition: color 0.2s;
    }

    .theme-toggle:hover {
        color: var(--accent-primary);
    }

    .theme-toggle svg {
        width: 24px;
        height: 24px;
    }
</style>
