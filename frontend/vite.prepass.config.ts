// THROWAWAY isolated pre-pass config — not committed, deleted after the run.
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5199,
    strictPort: true,
    proxy: {
      "/api": { target: "http://127.0.0.1:8399", changeOrigin: true },
      "/health": { target: "http://127.0.0.1:8399", changeOrigin: true },
    },
  },
});
