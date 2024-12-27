<script lang="ts">
    import { onMount } from "svelte";
    import MarkdownIt from "markdown-it";
    import katex from "katex";
    import "katex/dist/katex.min.css";
    import Prism from "prismjs";
    import "prismjs/themes/prism-tomorrow.css";
    // Import necessary Prism languages
    import "prismjs/components/prism-rust";
    import "prismjs/components/prism-python";
    import "prismjs/components/prism-bash";
    import "prismjs/components/prism-javascript";
    import "prismjs/components/prism-typescript";
    import "prismjs/components/prism-json";
    import "prismjs/components/prism-markdown";
    import "prismjs/components/prism-yaml";
    import "prismjs/components/prism-sql";
    import ClipboardJS from "clipboard";
    import DOMPurify from "dompurify";

    export let content = "";
    let renderedContent = "";
    let mounted = false;

    // Initialize markdown-it with necessary configurations
    const md = new MarkdownIt({
        html: true,
        linkify: true,
        breaks: true,
        highlight: function (str, lang) {
            if (lang && Prism.languages[lang]) {
                try {
                    return `<pre class="language-${lang}"><code>${Prism.highlight(str, Prism.languages[lang], lang)}</code></pre>`;
                } catch (__) {}
            }
            return `<pre class="language-text"><code>${md.utils.escapeHtml(str)}</code></pre>`;
        },
    });

    // Plugin for KaTeX
    const katexPlugin = (md) => {
        const inlineMath = /\$([^$]+)\$/g;
        const blockMath = /\$\$([^$]+)\$\$/g;

        // Inline math
        md.inline.ruler.after("escape", "math_inline", (state, silent) => {
            let match = inlineMath.exec(state.src);
            if (!match) return false;
            if (silent) return false;

            const token = state.push("math_inline", "", 0);
            token.content = match[1];
            state.pos += match[0].length;
            return true;
        });

        // Block math
        md.block.ruler.after(
            "blockquote",
            "math_block",
            (state, startLine, endLine, silent) => {
                let pos = state.bMarks[startLine] + state.tShift[startLine];
                const max = state.eMarks[startLine];
                if (state.src.slice(pos, pos + 2) !== "$$") return false;
                let nextLine = startLine + 1;
                let found = false;

                while (nextLine < endLine) {
                    pos = state.bMarks[nextLine] + state.tShift[nextLine];
                    if (state.src.slice(pos, pos + 2) === "$$") {
                        found = true;
                        break;
                    }
                    nextLine++;
                }

                if (!found) return false;
                if (silent) return false;

                const token = state.push("math_block", "math", 0);
                token.block = true;
                token.content = state.getLines(
                    startLine + 1,
                    nextLine,
                    0,
                    false,
                );
                token.info = "";
                token.map = [startLine, nextLine + 1];
                state.line = nextLine + 1;
                return true;
            },
        );

        // Render math
        md.renderer.rules.math_inline = (tokens, idx) => {
            try {
                return katex.renderToString(tokens[idx].content, {
                    displayMode: false,
                });
            } catch (e) {
                console.error("KaTeX error:", e);
                return tokens[idx].content;
            }
        };

        md.renderer.rules.math_block = (tokens, idx) => {
            try {
                return katex.renderToString(tokens[idx].content, {
                    displayMode: true,
                });
            } catch (e) {
                console.error("KaTeX error:", e);
                return tokens[idx].content;
            }
        };
    };

    md.use(katexPlugin);

    onMount(() => {
        mounted = true;
        const clipboard = new ClipboardJS(".copy-button");
        clipboard.on("success", (e) => {
            const button = e.trigger as HTMLButtonElement;
            button.innerHTML = "Copied!";
            setTimeout(() => (button.innerHTML = "Copy"), 2000);
        });
        return () => clipboard.destroy();
    });

    $: {
        try {
            const dirty = md.render(content);
            console.log("Rendered Content:", dirty); // For debugging
            renderedContent = DOMPurify.sanitize(dirty);
            if (mounted) {
                setTimeout(() => {
                    Prism.highlightAll();
                }, 0);
            }
        } catch (e) {
            console.error("Markdown parsing error:", e);
            renderedContent = content;
        }
    }
</script>

<div class="markdown-content">
    {@html renderedContent}
</div>

<style>
    .markdown-content {
        font-size: 1rem;
        line-height: 1.6;
        color: #374151;
        overflow-wrap: break-word;
        min-height: 2rem;
        contain: content;
    }

    .markdown-content :global(p) {
        margin: 1.25em 0;
        white-space: pre-wrap;
    }

    .markdown-content :global(.code-block) {
        margin: 1.25em 0;
        background: #1e1e1e;
        border-radius: 8px;
        overflow: hidden;
    }

    .markdown-content :global(.code-header) {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.5rem 1rem;
        background: #2d2d2d;
        border-bottom: 1px solid #404040;
    }

    .markdown-content :global(.code-language) {
        color: #9ca3af;
        font-size: 0.875rem;
        text-transform: uppercase;
    }

    .markdown-content :global(.copy-button) {
        padding: 0.25rem 0.75rem;
        font-size: 0.875rem;
        color: #e5e7eb;
        background: #404040;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        transition: all 0.2s;
    }

    .markdown-content :global(.copy-button:hover) {
        background: #4a4a4a;
    }

    .markdown-content :global(pre) {
        margin: 0;
        padding: 1rem;
        overflow-x: auto;
    }

    .markdown-content :global(pre code) {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
            monospace;
        font-size: 0.875rem;
        line-height: 1.5;
        display: block;
        padding: 0;
        background: transparent;
    }

    .markdown-content :global(.inline-code) {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
            monospace;
        font-size: 0.875em;
        color: #ef4444;
        padding: 0.2em 0.4em;
        background: #f3f4f6;
        border-radius: 4px;
    }

    .markdown-content :global(h1),
    .markdown-content :global(h2),
    .markdown-content :global(h3),
    .markdown-content :global(h4),
    .markdown-content :global(h5),
    .markdown-content :global(h6) {
        margin: 1.5em 0 0.5em;
        font-weight: 600;
        line-height: 1.25;
        color: #111827;
    }

    .markdown-content :global(h1) {
        font-size: 2em;
    }
    .markdown-content :global(h2) {
        font-size: 1.5em;
    }
    .markdown-content :global(h3) {
        font-size: 1.25em;
    }
    .markdown-content :global(h4) {
        font-size: 1em;
    }

    .markdown-content :global(ul),
    .markdown-content :global(ol) {
        margin: 1em 0;
        padding-left: 2em;
    }

    .markdown-content :global(li) {
        margin: 0.5em 0;
    }

    .markdown-content :global(blockquote) {
        margin: 1.25em 0;
        padding: 0.5em 1em;
        border-left: 4px solid #e5e7eb;
        background: #f9fafb;
        color: #4b5563;
    }

    .markdown-content :global(img) {
        max-width: 100%;
        height: auto;
        border-radius: 6px;
    }

    .markdown-content :global(table) {
        width: 100%;
        margin: 1.25em 0;
        border-collapse: collapse;
    }

    .markdown-content :global(th),
    .markdown-content :global(td) {
        padding: 0.5em;
        border: 1px solid #e5e7eb;
    }

    .markdown-content :global(th) {
        background: #f9fafb;
        font-weight: 600;
    }

    .markdown-content :global(a) {
        color: #2563eb;
        text-decoration: none;
    }

    .markdown-content :global(a:hover) {
        text-decoration: underline;
    }

    .markdown-content :global(strong) {
        font-weight: 600;
        color: #111827;
    }

    .markdown-content :global(em) {
        font-style: italic;
    }

    .markdown-content :global(hr) {
        margin: 2em 0;
        border: none;
        border-top: 1px solid #e5e7eb;
    }

    /* KaTeX styles */
    .markdown-content :global(.katex) {
        font-size: 1.1em;
    }

    .markdown-content :global(.katex-display) {
        margin: 1em 0;
        overflow-x: auto;
        overflow-y: hidden;
    }

    /* Fix layout jumping */
    .markdown-content {
        min-height: 2rem;
        contain: content;
    }
</style>
