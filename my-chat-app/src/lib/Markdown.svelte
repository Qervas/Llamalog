<script lang="ts">
    import { onMount, afterUpdate, onDestroy } from "svelte";
    import MarkdownIt from "markdown-it";
    import katex from "katex";
    import "katex/dist/katex.min.css";
    import Prism from "prismjs";
    // Import necessary Prism languages
    import "prismjs/components/prism-c";
    import "prismjs/components/prism-cpp";
    import "prismjs/components/prism-csharp";
    import "prismjs/components/prism-java";
    import "prismjs/components/prism-kotlin";
    import "prismjs/components/prism-swift";
    import "prismjs/components/prism-go";
    import "prismjs/components/prism-php";
    import "prismjs/components/prism-python";
    import "prismjs/components/prism-ruby";
    import "prismjs/components/prism-rust";
    import "prismjs/components/prism-dart";
    import "prismjs/components/prism-perl";
    import "prismjs/components/prism-scala";
    import "prismjs/components/prism-sql";
    import "prismjs/components/prism-r";
    import "prismjs/components/prism-lua";
    import "prismjs/components/prism-haskell";
    import "prismjs/components/prism-bash";
    import "prismjs/components/prism-yaml";
    import "prismjs/components/prism-toml";
    import "prismjs/components/prism-json";
    import "prismjs/components/prism-css";
    import "prismjs/components/prism-scss";
    import "prismjs/components/prism-jsx";
    import "prismjs/components/prism-tsx";
    import "prismjs/components/prism-typescript";
    import "prismjs/components/prism-graphql";
    import "prismjs/components/prism-mongodb";
    import "prismjs/components/prism-nginx";
    import "prismjs/components/prism-shell-session";
    import "prismjs/components/prism-vim";
    import "prismjs/components/prism-regex";
    import "prismjs/components/prism-makefile";
    import "prismjs/components/prism-cmake";
    import ClipboardJS from "clipboard";
    import DOMPurify from "dompurify";
    import { artifacts } from "./stores";

    export let content = "";
    let renderedContent = "";
    let mounted = false;
    const codeBlocksMap = new Map();

    // Language detection and normalization
    function normalizeLanguage(lang) {
        if (!lang) return "text";

        const languageMap = {
            // JavaScript and TypeScript
            js: "javascript",
            javascript: "javascript",
            ts: "typescript",
            typescript: "typescript",
            jsx: "jsx",
            tsx: "tsx",

            // Python
            py: "python",
            python: "python",
            python3: "python",
            py3: "python",

            // Ruby
            rb: "ruby",
            ruby: "ruby",
            rails: "ruby",

            // Shell scripting
            sh: "bash",
            shell: "bash",
            bash: "bash",
            zsh: "bash",
            "shell-session": "shell-session",

            // C-family
            c: "c",
            cpp: "cpp",
            "c++": "cpp",
            h: "c",
            hpp: "cpp",
            cs: "csharp",
            csharp: "csharp",

            // Java and JVM
            java: "java",
            kotlin: "kotlin",
            kt: "kotlin",
            scala: "scala",
            groovy: "groovy",

            // Web
            html: "html",
            xml: "xml",
            css: "css",
            scss: "scss",
            sass: "scss",
            less: "less",
            graphql: "graphql",
            gql: "graphql",

            // Go
            go: "go",
            golang: "go",

            // Rust
            rust: "rust",
            rs: "rust",

            // PHP
            php: "php",

            // Swift
            swift: "swift",

            // Dart
            dart: "dart",
            flutter: "dart",

            // Database
            sql: "sql",
            mysql: "sql",
            postgresql: "sql",
            mongo: "mongodb",
            mongodb: "mongodb",

            // Configuration
            yaml: "yaml",
            yml: "yaml",
            toml: "toml",
            json: "json",
            ini: "ini",
            nginx: "nginx",
            apache: "apache",

            // Build tools
            makefile: "makefile",
            cmake: "cmake",
            docker: "dockerfile",

            // Other languages
            r: "r",
            perl: "perl",
            pl: "perl",
            lua: "lua",
            haskell: "haskell",
            hs: "haskell",
            vim: "vim",

            // Regular expressions
            regex: "regex",
            regexp: "regex",
        };

        const normalized = languageMap[lang.toLowerCase()];

        // If we have a mapping and Prism supports it, use it
        if (normalized && Prism.languages[normalized]) {
            return normalized;
        }

        // If Prism directly supports the input language
        if (Prism.languages[lang.toLowerCase()]) {
            return lang.toLowerCase();
        }

        // Default fallback
        return "text";
    }

    function updateArtifact(id, content, lang) {
        artifacts.update((state) => {
            // Create a more unique title
            const timestamp = new Date().toLocaleTimeString();
            const title = `${lang || "text"} snippet - ${timestamp}`;

            const items = state.items.map((item) =>
                item.id === id
                    ? {
                          ...item,
                          content,
                          title,
                          language: lang || "text",
                          size: `${content.split("\n").length} lines`,
                      }
                    : item,
            );

            if (!items.find((item) => item.id === id)) {
                items.push({
                    id,
                    type: "code",
                    title,
                    content,
                    language: lang || "text",
                    size: `${content.split("\n").length} lines`,
                });
            }

            const currentArtifact =
                state.currentArtifact?.id === id
                    ? items.find((item) => item.id === id)
                    : state.currentArtifact;

            return {
                ...state,
                items,
                currentArtifact,
            };
        });
    }

    // Initialize markdown-it with necessary configurations
    const md = new MarkdownIt({
        html: true,
        linkify: true,
        breaks: true,
        highlight: function (str, lang) {
            const normalizedLang = normalizeLanguage(lang);

            if (str.split("\n").length > 5) {
                const hash = btoa(str.slice(0, 50) + normalizedLang).slice(
                    0,
                    32,
                );
                let id = codeBlocksMap.get(hash) || crypto.randomUUID();
                codeBlocksMap.set(hash, id);
                updateArtifact(id, str, normalizedLang);

                return `<div class="code-preview" data-artifact-id="${id}">
                    <span class="language">${normalizedLang}</span>
                    <span class="line-count">${str.split("\n").length} lines</span>
                    <button class="expand-button" title="View full code">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                            <path d="M15 3h6v6M21 3l-7 7"/>
                        </svg>
                    </button>
                </div>`;
            }

            if (normalizedLang !== "text") {
                try {
                    return `<pre class="line-numbers language-${normalizedLang}"><code class="language-${normalizedLang}">${Prism.highlight(
                        str,
                        Prism.languages[normalizedLang],
                        normalizedLang,
                    )}</code></pre>`;
                } catch (e) {
                    console.error("Highlighting error:", e);
                }
            }
            return `<pre class="line-numbers language-text"><code>${md.utils.escapeHtml(str)}</code></pre>`;
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
        document.addEventListener("showArtifact", (e) => {
            artifacts.update((state) => {
                const artifact = state.items.find(
                    (item) => item.id === e.detail,
                );
                return artifact
                    ? {
                          ...state,
                          visible: true,
                          currentArtifact: artifact,
                      }
                    : state;
            });
        });
    });

    afterUpdate(() => {
        const codeBlocks = document.querySelectorAll(".code-preview");
        codeBlocks.forEach((block) => {
            if (!block.hasAttribute("data-handler-attached")) {
                block.setAttribute("data-handler-attached", "true");
                block.addEventListener("click", () => {
                    const artifactId = block.getAttribute("data-artifact-id");
                    artifacts.update((state) => ({
                        ...state,
                        visible: true,
                        currentArtifact: state.items.find(
                            (item) => item.id === artifactId,
                        ),
                    }));
                });
            }
        });
    });

    onDestroy(() => {
        codeBlocksMap.clear();
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
    /* Base markdown content styles */
    .markdown-content {
        font-size: 1rem;
        line-height: 1.6;
        color: var(--text-primary);
        overflow-wrap: break-word;
        min-height: 2rem;
        contain: content;
    }

    /* Typography */
    .markdown-content :global(p) {
        margin: 1.25em 0;
        white-space: pre-wrap;
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
        color: var(--text-primary);
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

    .markdown-content :global(strong) {
        font-weight: 600;
        color: var(--text-primary);
    }

    .markdown-content :global(em) {
        font-style: italic;
    }

    /* Lists */
    .markdown-content :global(ul),
    .markdown-content :global(ol) {
        margin: 1em 0;
        padding-left: 2em;
    }

    .markdown-content :global(li) {
        margin: 0.5em 0;
    }

    /* Links */
    .markdown-content :global(a) {
        color: var(--accent-primary);
        text-decoration: none;
    }

    .markdown-content :global(a:hover) {
        text-decoration: underline;
    }

    /* Block elements */
    .markdown-content :global(blockquote) {
        margin: 1.25em 0;
        padding: 0.5em 1em;
        border-left: 4px solid var(--markdown-blockquote-border);
        background: var(--markdown-blockquote-background);
    }

    .markdown-content :global(hr) {
        margin: 2em 0;
        border: none;
        border-top: 1px solid var(--message-border);
    }

    .markdown-content :global(img) {
        max-width: 100%;
        height: auto;
        border-radius: 6px;
    }

    /* Tables */
    .markdown-content :global(table) {
        width: 100%;
        margin: 1.25em 0;
        border-collapse: collapse;
    }

    .markdown-content :global(th),
    .markdown-content :global(td) {
        padding: 0.5em;
        border: 1px solid var(--input-border);
    }

    .markdown-content :global(th) {
        background: var(--code-background);
        font-weight: 600;
    }

    /* Code blocks */
    .markdown-content :global(pre[class*="language-"]),
    .markdown-content :global(pre) {
        margin: 0;
        padding: 1rem;
        background: var(--code-background);
        border-radius: 6px;
        overflow-x: auto;
    }

    .markdown-content :global(code[class*="language-"]),
    .markdown-content :global(pre code),
    .markdown-content :global(.inline-code) {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
            monospace;
        font-size: 0.875rem;
        line-height: 1.5;
        background: transparent;
        color: var(--code-text);
    }

    .markdown-content :global(.inline-code) {
        padding: 0.2em 0.4em;
        background: var(--code-background);
        border-radius: 4px;
    }

    /* Code preview box */
    :global(.code-preview) {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.875rem;
        padding: 0.25rem 0.5rem;
        margin: 0 0.5rem;
        border-radius: 4px;
        background: var(--background-tertiary);
        color: var(--text-primary);
        cursor: pointer;
        transition: all 0.2s ease;
        vertical-align: middle;
        border: 1px solid var(--input-border);
    }

    :global(.code-preview:hover) {
        border-color: var(--accent-primary);
        background: var(--background-secondary);
    }

    :global(.code-preview .preview-header) {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.5rem 0.75rem;
        border-bottom: 1px solid var(--input-border);
        background: var(--background-tertiary);
        color: var(--text-primary);
    }

    :global(.code-preview .language) {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
            monospace;
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--text-primary);
        text-transform: uppercase;
    }

    :global(.code-preview .header-left) {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    :global(.code-preview .file-icon) {
        width: 16px;
        height: 16px;
        stroke: var(--text-secondary);
        opacity: 0.8;
    }

    :global(.code-preview .file-info) {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
    }

    :global(.code-preview .line-count) {
        font-size: 0.5rem;
        color: var(--text-secondary);
    }

    :global(.code-preview .preview-info) {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        color: var(--accent-primary);
        font-size: 0.875rem;
    }

    :global(.code-preview .preview-info svg) {
        width: 16px;
        height: 16px;
        stroke: currentColor;
    }

    :global(.code-preview .expand-button) {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 0.125rem;
        color: var(--text-secondary);
        background: transparent;
        border: none;
        border-radius: 3px;
        transition: all 0.2s ease;
    }

    :global(.code-preview .expand-button:hover) {
        color: var(--accent-primary);
    }

    :global(.code-preview .expand-button svg) {
        width: 12px;
        height: 12px;
        stroke: currentColor;
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

    /* Syntax highlighting */
    .markdown-content :global(.token.comment),
    .markdown-content :global(.token.prolog),
    .markdown-content :global(.token.doctype),
    .markdown-content :global(.token.cdata) {
        color: var(--code-comment, #6272a4);
    }

    .markdown-content :global(.token.punctuation) {
        color: var(--code-punctuation, #f8f8f2);
    }

    .markdown-content :global(.token.namespace) {
        opacity: 0.7;
    }

    .markdown-content :global(.token.property),
    .markdown-content :global(.token.tag),
    .markdown-content :global(.token.constant),
    .markdown-content :global(.token.symbol),
    .markdown-content :global(.token.deleted) {
        color: var(--code-keyword, #ff79c6);
    }

    .markdown-content :global(.token.boolean),
    .markdown-content :global(.token.number) {
        color: var(--code-number, #bd93f9);
    }

    .markdown-content :global(.token.selector),
    .markdown-content :global(.token.attr-name),
    .markdown-content :global(.token.string),
    .markdown-content :global(.token.char),
    .markdown-content :global(.token.builtin),
    .markdown-content :global(.token.inserted) {
        color: var(--code-string, #50fa7b);
    }

    .markdown-content :global(.token.operator),
    .markdown-content :global(.token.entity),
    .markdown-content :global(.token.url),
    .markdown-content :global(.language-css .token.string),
    .markdown-content :global(.style .token.string) {
        color: var(--code-operator, #f8f8f2);
    }

    .markdown-content :global(.token.atrule),
    .markdown-content :global(.token.attr-value),
    .markdown-content :global(.token.keyword) {
        color: var(--code-keyword, #ff79c6);
    }

    .markdown-content :global(.token.function),
    .markdown-content :global(.token.class-name) {
        color: var(--code-function, #ffb86c);
    }

    .markdown-content :global(.token.regex),
    .markdown-content :global(.token.important),
    .markdown-content :global(.token.variable) {
        color: var(--code-variable, #f1fa8c);
    }
</style>
