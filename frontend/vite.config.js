import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    strictPort: true,
    // Avoid the browser caching pre-bundled dep URLs across Vite restarts (504 Outdated Optimize Dep).
    headers: {
      "Cache-Control": "no-store",
    },
  },
  optimizeDeps: {
    include: [
      "react",
      "react-dom",
      "react-dom/client",
      "react/jsx-runtime",
      "react-router-dom",
      "framer-motion",
      "chart.js",
      "react-chartjs-2",
    ],
    holdUntilCrawlEnd: true,
  },
});
