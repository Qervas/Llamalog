import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

// https://vite.dev/config/
export default defineConfig({
  plugins: [svelte()],
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
      "/llm": {
        target: "http://localhost:8080",
        rewrite: (path) => path.replace(/^\/llm/, ""),
      },
    },
  },
  optimizeDeps: {
    include: ["mathjax/es5/tex-svg.js"], // Include the MathJax file explicitly
  },
  build: {
    commonjsOptions: {
      transformMixedEsModules: true,
    },
  },
});
