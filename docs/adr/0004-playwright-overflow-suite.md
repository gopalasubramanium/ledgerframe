# ADR-0004 — Playwright for the breakpoint overflow suite

**Status:** Accepted (owner, 2026-07-11 — page-chrome §11-14 / batch-3 follow-up).
**Context:** ADR-0002 forbids new frontend dependencies without an ADR.

## Decision

Add **`@playwright/test`** (dev dependency) and a real-browser **breakpoint
overflow suite** (`frontend/e2e/overflow.spec.ts`).

**Why:** jsdom (Vitest) has **no layout engine** — `scrollWidth`/`clientWidth` are
always 0 — so horizontal-overflow regressions (like §11-14) cannot be caught there;
such a test passes vacuously. Only a real browser measures layout.

**What it asserts:** zero horizontal overflow (`scrollWidth <= clientWidth + 1px`) on
**both** the document and `.lf-shell__content`, across:
- widths **320 · 375 · 900 · 1366 px**,
- the shell + both built pages (`/`, `/holdings`, `/instrument/:symbol`),
- **both themes** (light/dark, driven by `emulateMedia` since the default choice is
  "system").

The suite runs the app with **no backend** (API calls fail gracefully); layout is what
we measure, and the chrome + page headers render regardless.

## Consequences

- **Browser binary at install:** CI (and any fresh checkout) must run
  `npx playwright install chromium` before the suite — the browser is **not** bundled in
  `node_modules`. Documented here and in the §-entry.
- **Wired into `npm run check`** as `test:overflow` (after Vitest). Playwright's
  `webServer` builds the app and serves it via `vite preview` on `127.0.0.1:4173`.
- **Vitest excludes `e2e/**`** (Playwright specs are not jsdom tests).
- Version pinned in `package.json` (installed `@playwright/test` 1.61.x). Upgrades are
  deliberate.
- Artifacts (`test-results/`, `playwright-report/`, `playwright/.cache/`) are gitignored.
