// SMOKE TARGET RESOLVER — the ONE place a smoke spec learns where to send traffic.
//
// WHY THIS EXISTS (the near-miss, 2026-07-19, page-help §9-bis-11 Step F):
// 20 smoke specs hardcoded the owner's LIVE instance (127.0.0.1:8321 / :5173). `SMOKE_BASE`
// redirects only the BROWSER; every `page.request.*` call talks to the API DIRECTLY, bypassing
// the frontend proxy. So an "isolated" pre-pass drove the spare-port frontend while sending its
// PUTs at the OWNER'S LIVE BACKEND. Nothing was written only because that instance happened to be
// PIN-locked and answered 401 to everything — and one Settings spec would have SET A PIN on an
// unlocked live install. The isolation held by LUCK, not by design.
//
// THE RULE (architect under delegation, 2026-07-19, owner-unvetoed; release-train blocking):
// specs NEVER name a port. They import from here. This module is FAIL-CLOSED: with no isolated
// target configured it REFUSES to run rather than silently defaulting to the owner's live stack.
//
// Run isolated (the normal path):
//   SMOKE_BASE=http://127.0.0.1:5199 SMOKE_API=http://127.0.0.1:8399 \
//     npx playwright test --config e2e/smoke/playwright.smoke.config.ts
//
// Run against the owner's LIVE instance (the acceptance walk ONLY — deliberate, never default):
//   SMOKE_ALLOW_LIVE=1 npx playwright test --config e2e/smoke/playwright.smoke.config.ts

/** The owner's live dev stack. Traffic here is refused unless the owner-walk flag is set. */
const LIVE_PORTS = { ui: "5173", api: "8321" };

/** Deliberate opt-in for the owner-driven acceptance walk (pre-release-walk.md). */
export const OWNER_WALK = process.env.SMOKE_ALLOW_LIVE === "1";

const HOW_TO_ISOLATE =
  "Run isolated:  SMOKE_BASE=http://127.0.0.1:5199 SMOKE_API=http://127.0.0.1:8399 npx playwright test …\n" +
  "Or, for the owner-driven acceptance walk against the LIVE stack, set SMOKE_ALLOW_LIVE=1 deliberately.";

/** @param {string} reason @returns {never} */
function refuse(reason) {
  throw new Error(`SMOKE ISOLATION REFUSED — ${reason}\n${HOW_TO_ISOLATE}`);
}

/**
 * Resolve one target origin from the isolated-instance config.
 * Fail-closed twice over: unset env refuses, and an explicitly-configured LIVE port refuses.
 *
 * @param {string} envName @param {string} livePort @param {string} what @returns {string}
 */
function resolveOrigin(envName, livePort, what) {
  const configured = process.env[envName];

  if (!configured) {
    if (!OWNER_WALK) {
      refuse(`${envName} is not set, so the ${what} target is unknown. Smoke specs never default to the owner's live instance (port ${livePort}).`);
    }
    return `http://127.0.0.1:${livePort}`;
  }

  let port;
  try {
    port = new URL(configured).port;
  } catch {
    refuse(`${envName}="${configured}" is not a valid origin URL.`);
  }

  if (port === livePort && !OWNER_WALK) {
    refuse(`${envName}="${configured}" points at the owner's LIVE ${what} port ${livePort}. A pre-pass must never drive the live stack.`);
  }

  return configured.replace(/\/+$/, "");
}

/** Frontend origin the browser drives. */
export const BASE = resolveOrigin("SMOKE_BASE", LIVE_PORTS.ui, "frontend");

/** Backend origin `page.request.*` talks to directly (bypasses the frontend proxy). */
export const API_ORIGIN = resolveOrigin("SMOKE_API", LIVE_PORTS.api, "backend");

/** Versioned API root — what specs actually use. */
export const API = `${API_ORIGIN}/api/v1`;
