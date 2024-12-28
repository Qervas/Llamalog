<script>
    // @ts-nocheck

    import { createEventDispatcher } from "svelte";
    import { fade } from "svelte/transition";
    const dispatch = createEventDispatcher();

    export let onFileProcess;
    export let loading = false;
    let error = "";
    let fileInput;

    export function handleFiles(files) {
        if (!files || !files.length) return;
        const validFiles = Array.from(files).filter((file) => {
            // Check file size (10MB limit)
            if (file.size > 10 * 1024 * 1024) {
                error = "Files must be less than 10MB";
                return false;
            }
            return true;
        });

        if (validFiles.length > 0) {
            dispatch("filesSelected", {
                files: validFiles.map((file) => ({
                    file,
                    name: file.name,
                    size: file.size,
                    status: "pending",
                })),
            });
        }
    }
</script>

<div class="file-upload">
    <input
        bind:this={fileInput}
        type="file"
        id="file-input"
        on:change={(e) => handleFiles(e.target.files)}
        multiple
        class="hidden"
    />
    {#if error}
        <div class="error" transition:fade>{error}</div>
    {/if}
</div>

<style>
    .file-upload {
        display: inline-block;
    }

    .hidden {
        display: none;
    }

    .error {
        color: #ef4444;
        font-size: 0.75rem;
        margin-top: 0.25rem;
    }
</style>
