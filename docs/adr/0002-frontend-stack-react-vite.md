# ADR 0002 — Frontend stack: React + TypeScript + Vite, tokens as CSS custom properties

- **Status:** Accepted
- **Date:** 2026-07-09
- **Context milestone:** Frontend foundation + design system + kitchen sink
  (`docs/plans/design-system-build.md`)

## Context

v2 needs a frontend. The v1 source (`~/Documents/github/LedgerFrame`, read-only
reference) is a **React + TypeScript + Vite** SPA served same-origin by the
FastAPI app in production, with a Vite dev server in development (the backend
already allow-lists `http://127.0.0.1:5173` / `http://localhost:5173` for CORS —
`app/main.py:159`).

This milestone is a **from-scratch build of the design system and component
library** — no legacy component code is copied in. But the runtime/tooling
choice is not a blank slate: matching v1's stack means the accumulated patterns,
the same-origin production serving model, and the existing CORS/dev-proxy seam
carry over unchanged.

DESIGN-SYSTEM §2 fixes the styling contract: tokens are semantic CSS custom
properties, and **no component may hard-code a raw hex or px** — every value
resolves to a token variable. CLAUDE.md forbids new dependencies without an ADR.

## Decision

**React + TypeScript + Vite**, from scratch (no legacy component code copied).

- **Styling:** CSS custom properties are the single source of design tokens
  (DESIGN-SYSTEM §2). A thin hand-rolled utility/class layer sits on top. **No
  CSS framework** (Tailwind, etc.) is added — that would be a separate ADR.
- **Token invariant:** every colour/size/space/radius/line-height in any
  component resolves to a token variable. Enforced mechanically by a drift check
  (`scripts/check-design-tokens.mjs`) that fails CI on any raw hex or hardcoded
  px in component source outside the token layer.
- **Baseline toolchain authorized by this ADR:** `react`, `react-dom`,
  `react-router-dom`, `vite`, `typescript`, `vitest`, `@testing-library/*`,
  `eslint` (+ its React/TS plugins). These are the from-scratch equivalents of
  v1's stack.

## Consequences

- **Pattern continuity.** Same runtime, same dev-server seam, same same-origin
  production model as v1 — no re-learning, no new CORS surface.
- **Token discipline is mechanical, not a review chore.** The drift check makes
  "no raw hex/px in components" a build failure, so the single-source-of-truth
  rule holds without relying on vigilance.
- **Fonts stay dependency-free this milestone.** DESIGN-SYSTEM §2.2 proposes
  self-hosted Inter / Source Serif 4; adding a webfont **package** is a bundle
  change that needs its own ADR. Until then the specified system fallback stacks
  ship, keeping the app deployable.
- **Charts stay dependency-free.** House-SVG only (D-053). The ECharts escape
  hatch for the treemap is available **only via a further ADR** if squarified
  parity fails within the plan-file scope.

## Alternatives rejected

- **A different framework (Svelte/Solid/Vue).** Rejected: discards v1 pattern
  continuity and the working same-origin/dev-proxy model for no offsetting
  benefit on a single-maintainer appliance.
- **A CSS framework (Tailwind or similar) for the utility layer.** Rejected here
  (not forbidden forever): it is a dependency + an ADR of its own, and it would
  compete with the CSS-custom-property token layer that DESIGN-SYSTEM §2 fixes as
  the source of truth. A thin hand-rolled layer keeps tokens unambiguously
  canonical.
- **A component/UI kit (MUI, shadcn, Radix).** Rejected: the brief explicitly
  targets an institutional-wealth visual language, "not default shadcn"
  (DESIGN-BRIEF); the component inventory is bespoke by design.
