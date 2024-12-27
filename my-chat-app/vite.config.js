import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

// https://vite.dev/config/
export default defineConfig({
  plugins: [svelte()],
  optimizeDeps: {
    include: ["mathjax/es5/tex-svg.js"], // Include the MathJax file explicitly
  },
  build: {
    commonjsOptions: {
      transformMixedEsModules: true,
    },
  },
});
