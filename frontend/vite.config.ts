/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Backend runs on 127.0.0.1:8321 (LEDGERFRAME_API_PORT). The dev server proxies
// /health and /api to it so the frontend calls same-origin paths in dev and prod
// alike (production serves the SPA same-origin from the FastAPI app).
const BACKEND = "http://127.0.0.1:8321";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/health": BACKEND,
      "/api": BACKEND,
      // The Reports Pack (D-038) is a BACKEND-served HTML artifact, not an SPA route. In
      // production the FastAPI app serves it same-origin (registered before the SPA catch-all);
      // dev must proxy it too, or the Reports-page entry point (a real anchor to /reports/pack)
      // would hit the vite SPA fallback instead of the artifact. Dev parity with prod.
      "/reports/pack": BACKEND,
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: true,
    // e2e/ holds Playwright specs (real browser, ADR-0004) — not Vitest/jsdom.
    exclude: ["e2e/**", "node_modules/**", "dist/**"],
  },
});
