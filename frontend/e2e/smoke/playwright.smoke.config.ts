import { defineConfig } from "@playwright/test";
import { BASE } from "./smoke-target.mjs";

// ⚠ DEV-ONLY SMOKE HARNESS — NOT a test suite, NEVER wired into `npm run check` or CI.
// It drives the FIRST-RUN CHECKLIST against the dev backend + frontend named by the
// isolated-instance config (smoke-target.mjs, fail-closed) and assumes a DESTRUCTIVE reset
// has been applied to that dev
// DB (settings cleared, pin_hash NULL). Telemetry/observation only; run manually:
//   npx playwright test --config e2e/smoke/playwright.smoke.config.ts
export default defineConfig({
  testDir: ".",
  reporter: [["list"]],
  workers: 1,
  // SMOKE_BASE lets an isolated pre-pass point at a spare-port frontend (§14dr-28 / rule #6).
  use: { baseURL: BASE },
  // No webServer — the dev servers must already be running (dev tool).
});
