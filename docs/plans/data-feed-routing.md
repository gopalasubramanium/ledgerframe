# data-feed-routing — Provider routing matrix (ROADMAP R-38) build plan

> **STATUS: PLAN-ONLY KICKOFF (owner activation 2026-07-18, page-settings
> milestone close).** R-38 is **ACTIVATED as the NEXT milestone** — the
> R-35-activation precedent (plan-file-first, verify-first). **Nothing is built
> yet.** This file is the kickoff stub: it records the verified KEPT machinery,
> the MISSING scope, the canonical UI home, and the verify-first mandate. The
> full plan (ownership table · API surface · components · acceptance criteria ·
> NEEDS DECISION) is authored **before** any code, per `TEMPLATE-page-build.md`
> and the CLAUDE.md session protocol.

---

## 0. WHAT R-38 IS

A **provider routing matrix**: a **per asset-class × listing-country** mapping
that says *which provider prices this kind of instrument in this market*. Today
routing is resolved by a fixed lane policy + the active provider + a per-instrument
override; R-38 adds a **user-editable mapping table** as a precedence layer, with a
canonical editor in **Settings → Data feeds** (§14st-1) and per-cell provenance on
**Pricing Health**.

The platform still **never fabricates a price** and **never advises**; this is a
routing-configuration surface, not a pricing change.

---

## 1. THE KEPT MACHINERY (verify-first, confirmed 2026-07-18)

Recorded so the milestone does not rebuild what exists. Each claim is grepped, not
recalled.

| Kept | Where (verified) |
|------|------------------|
| `CAPABILITIES` registry declares `asset_classes` + `regions` **per provider** | `docs/audit/05-PROVIDERS-AND-ROUTING.md` §A.2; `app/providers/market/router.py:53` (dataclass `ProviderCapabilities`, `:44-45`: `asset_classes: frozenset`, `regions: frozenset` — ISO-3166 alpha-2 or `"*"`) |
| The pure resolver takes `asset_class` / `asset_subclass` / `listing_country` and validates coverage | §A.7; `router.py:195` `route(...)` → `lane_for(...)` `:128`; coverage/auth-gap checks `:161` |
| A **per-instrument `source_override`** precedence slot already exists | `router.py:237` (`if source_override in CAPABILITIES:`) |
| `capabilities_for(name)` lookup helper | `router.py:93` |

> The capability model that a validated matrix needs — *"which providers cover
> which class×region"* — **already exists**. R-38 is the mapping layer + its
> editing + its provenance, not the capability engine.

---

## 2. THE MISSING SCOPE (what this milestone builds)

1. **The mapping table (data model).** A new persisted model keyed by
   **asset-class × listing-country → provider**. Migration + defaults; the
   defaults must not silently change any instrument's current provider (the
   PARAM-WINS honesty precedent, Amendment A).
2. **Its precedence slot.** Where the matrix sits in resolution — **between the
   per-instrument `source_override` and the active provider** (override still
   wins; the matrix is the next-most-specific signal; the active provider is the
   fallback). Encoded in `route()`, verify-first with fail-first tests.
3. **Capability-validated editing.** A cell may pick **only** a provider whose
   `CAPABILITIES` cover that class×country (`asset_classes` ∋ class AND `regions`
   ∋ country or `"*"`); an invalid pick is an **honest 400**, never a silent
   accept — the write-only-key/unknown-key precedent.
4. **The matrix editor UI.** Canonical home **Settings → Data feeds** (§14st-1;
   the tab already exists). Ratified components only — a new component needs a §5
   amendment. No frontend routing logic (the resolver stays backend, D-105/P-1).
5. **Per-cell provenance on Pricing Health.** How Pricing Health surfaces **which
   provider actually priced each class×country** — provenance-first
   (DESIGN-SYSTEM), the existing StalenessChip/ProvenanceBadge vocabulary.

---

## 3. CANONICAL HOMES & DECISIONS IN FORCE

- **Editor home:** Settings → **Data feeds** (D-069 amendment #1, §14st-1). One
  canonical home (P-1) — Pricing Health *reads* provenance, it does not own the
  matrix.
- **D-005** — the matrix vocabularies (asset classes, listing countries,
  providers) are **served**, not copied to the frontend.
- **D-105 / P-1** — no money math and no routing math in the frontend; the
  resolver stays in the backend.
- **API-CONTRACT** — new endpoints ship **backend-first**, contract regenerated
  in the same commit; allow-list changes (if any) pinned by served-value tests.

---

## 4. NEEDS DECISION (surfaced at plan-authoring, not assumed here)

- The **default matrix** content (or an empty matrix that falls through to the
  active provider) — must not silently repoint any instrument.
- **Granularity** — class × country only, or also asset-subclass? (The resolver
  already reads subclass; the matrix key breadth is an owner call.)
- **Country vocabulary** — the six-bucket region model (D-083) vs raw ISO-3166
  listing country (the resolver uses alpha-2). One must be canonical for the
  matrix rows.
- **Pricing Health surface** — a new per-cell column/section vs an annotation on
  the existing provenance display.

*(New ideas during authoring → ROADMAP, never silent scope — CLAUDE.md.)*

---

**Kickoff only.** The next session authors the full plan against the specs, gets
owner confirmation, then builds verify-first. Nothing here is a commitment to a UI
or a data shape — those are decided in the full plan.
