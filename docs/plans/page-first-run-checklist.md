# page-first-run-checklist.md — First-run checklist (D-045) build plan

**Status: SIGNED OFF (owner 2026-07-11). Phase 0 DONE; Phase 0a IN PROGRESS → PAUSE for
ratification before Phase 1.** §9 fully resolved (F-1..F-12); F-4 timezone source =
`Intl.supportedValuesOf` client-side + backend-validated (F-3), searchable picker scoped
into the Phase-0a amendment; F-10 `PUT /settings` canonical (assert side effects in
Phase 2); F-12 EXCLUDE demo data. Derived from PRODUCT-SPEC §7, D-045, SECURITY-BASELINE
§3, D-069, chrome C-4.

**This is a gate/overlay, not a content page — it adapts the template** (per the
`TEMPLATE-page-build.md` shell-adaptation note). Like the chrome, it deviates from the
page shape: **no route, no nav entry, no H1-owned figures.** It is a first-run **overlay
in the app shell** that runs five skippable settings steps. §1/§2 describe UI-state
ownership + settings mutation, not figure ownership; acceptance is behavioural
(skippable, links out, honest), not a single-page happy path.

---

## 1. IDENTITY (adapted — overlay, not a page)

| Field | Value | Spec ref |
|-------|-------|----------|
| Name | First-run checklist | PRODUCT-SPEC §7, D-045 |
| Route | **none** — an overlay mounted in the app shell (the chrome's reserved first-run gate slot) | page-chrome C-4; IA "Global chrome (D-045)" |
| Nav group | **n/a** — never in the sidebar (it is a one-time setup overlay) | D-043 (not a nav page) |
| Page template | **n/a** — a **gate/overlay** in the shell, like the LockScreen; the four page templates render *behind* it | DESIGN-SYSTEM §5.5; page-chrome §12 (shell-adaptation) |
| Rotation eligibility | **n/a** — not a rotatable page (D-044) | IA §3 |
| One-line purpose | A minimal, **skippable** first-run checklist run against **real settings** (no personas, no profiling): base currency · timezone · PIN · data provider · no-egress | PRODUCT-SPEC §7, D-045 |

**Replaces PersonaOnboarding, which is KILLED (D-045).** No personas, no profiling —
each step is a real setting, skippable, and links to its Settings home.

---

## 2. OWNERSHIP TABLE (adapted — UI state + settings mutation, no figures)

**Owns (UI state only):** the checklist's own **step state** (which of the five steps
are done / skipped / outstanding) and the one-time **first-run dismissal/completion**
state. **Owns no figures.**

**Writes (mutates settings via the canonical settings/auth endpoints — never a second
code path):** it does not *summarise* readers; it **sets** real configuration through
the same endpoints the (future) Settings page uses. Each step's canonical home is
**Settings**, and D-045 requires each step to **link to its Settings home**.

| Step (D-045 order) | Canonical Settings home | Real setting it writes | Endpoint (frozen contract) |
|--------------------|-------------------------|------------------------|----------------------------|
| 1. Base currency | Settings · General | `base_currency` | **`PUT /settings`** — canonical (F-10, verified: it also applies to `.env` + reloads + resets FX + restarts the worker); `/system/data-source.base_currency` stays a provider-bundle convenience |
| 2. Timezone | Settings · General | device `timezone` (D-013) | **`PUT /settings`** after the **F-3 delta** (timezone added to the write surface) |
| 3. PIN | Settings · Security | first PIN (access lock, D-002) | `POST /auth/set-pin` (first PIN from loopback, no auth) |
| 4. Data provider | Settings · Prices | `market_provider` (+ optional API key) | `PUT /system/data-source` |
| 5. No-egress toggle | Settings · Privacy | `privacy_mode` (D-069/D-075) | `PUT /settings` |

**Density is NOT a step** — it is a plain Settings → Appearance option (D-045),
explicitly excluded from the checklist.

**Enforcement corollary (P-1):** the checklist shows **no figures** — it only writes
settings and links to Settings. Nothing here duplicates a canonical page's numbers.

---

## 3. API SURFACE

### 3a. Consumed (already in the frozen contract)

| Method + path | Purpose in the checklist | Shape pinned? |
|---------------|--------------------------|---------------|
| `GET /settings` | read current `base_currency`, `timezone` (default), `demo_mode`, stored `privacy_mode` to show step state | `{stored, defaults}` (typed loosely) |
| `PUT /settings` | write `base_currency`, `privacy_mode` (no-egress) | `{values}` allow-listed keys |
| `POST /auth/set-pin` | set the first PIN (loopback; `PinPayload{pin}`, 4–32 chars — policy min 6, SECURITY-BASELINE §3) | pinned |
| `GET /auth/state` | know whether a PIN is already set (step-3 done-state) | `{pin_set}` |
| `GET /system/data-source` | read the **served provider list** (`providers`) + current provider (frontend zero-copy, D-005) | `{providers, ...}` |
| `PUT /system/data-source` | write `market_provider` (+ optional `api_key`, never returned) | `DataSourceIn` |

### 3b. Contract deltas — **DONE (Phase 0)**

| kind | Endpoint | Decision | Shipped |
|------|----------|----------|---------|
| reshape | **timezone settable** via `PUT /settings` | D-013 / D-045 step 2 / **F-3/F-4** | ✅ `timezone` added to the settings allow-list; **backend-validated against `zoneinfo.available_timezones()`** (invalid → honest 400, never a silent default); applied to `.env` + `reload_settings()` so `GET /settings.defaults.timezone` reflects it. |
| add | **first-run flag** via `PUT /settings` | D-045 / **F-5** | ✅ `first_run_complete` added to the allow-list — a **server-persisted settings key** (survives a browser wipe), set on complete OR dismiss; read from `GET /settings.stored`. |

**Contract note:** both deltas go through the **existing `PUT /settings` allow-list** — no
new endpoint and **no OpenAPI shape change** (the shape is `{values: dict}`), so
`API-CONTRACT.json`/`openapi.json` are **unchanged** (drift check run + current). Base
currency needs **no** delta — `PUT /settings` is canonical (§2/F-10). Provider API keys
stay in Settings (F-8), not first-run. **Tests:** `tests/integration/test_first_run_settings.py`.

---

## 4. COMPONENTS

*Only ratified `src/components/ui/` components may be composed. A needed affordance
the inventory lacks is a DESIGN-SYSTEM amendment (also listed in §9).*

| Ratified component | Role in the checklist | Data source (real / mock) | Notes |
|--------------------|-----------------------|---------------------------|-------|
| **LockScreen pattern** (reference, §5.5) | the closest existing full-shell gate/overlay — the checklist overlay may reuse its scrim/centering approach | — | reuse the *pattern*, not the component (it is a PIN gate) |
| **MoneyInput / MasterSelect** | base-currency choice (currency master, D-005) | `GET /refdata` (currency master) or `/system/data-source.providers` | currency is a MASTER-DATA vocab (§5) |
| **Select** | timezone choice; provider choice (served lists, not MASTER-DATA masters) | `/system/data-source.providers`; timezone source **§9** | see §5 |
| **LockScreen PIN input pattern / ConfirmDialog PIN** | the PIN step's masked numeric entry (min 6) | `POST /auth/set-pin` | reuse the masked-PIN pattern (no new input primitive) |
| **Toggle/`.lf-iconbtn` or a Settings-style switch** | the no-egress toggle | `PUT /settings{privacy_mode}` | **§9**: is there a ratified toggle/switch, or is it a §5.5 amendment? |
| **PageHeader / EmptyState / Toast** | overlay heading, per-step "skipped/reason" honesty, save confirmation | — | ratified |

**Affordances the ratified inventory LACKS (amendment — APPROVED, ratify at kitchen sink):**
- **A checklist / stepper overlay (+ the no-egress toggle/switch + a searchable picker).**
  No ratified checklist/stepper/first-run-overlay, no settings toggle, and **no searchable
  picker** (InstrumentPicker is instrument-bound) exist → **APPROVED (F-6):** author all
  as **PROPOSED, DESIGN-SYSTEM §5.5 amendment**, ratified at `/kitchen-sink` in **Phase 0a
  before assembly**. Dismissible card form (F-1). The **searchable picker** (F-4) backs the
  timezone step's ~400 `Intl.supportedValuesOf('timeZone')` options — **no silent new
  primitive**; it is part of this amendment.
- **The shell first-run slot — mounts AFTER the lock gate (F-7).** `AppShell` mounts only
  the LockScreen today; this milestone **adds the first-run overlay to `AppShell` after
  the lock gate** — unlock precedes onboarding (restored-DB-with-PIN: lock first, then the
  checklist). No leak behind either.

**Step-specific rules (resolved):**
- **Provider step = selection only (F-8/D-069).** It writes `market_provider` inline and
  **links out** for the API key — it **never renders a key field** (secrets stay in
  Settings).
- **Honest interplay copy (F-9, all PROPOSED — ratify at kitchen sink):** the no-egress
  step states **prices won't refresh**; the provider step **notes when no-egress is
  already enabled**. No decision IDs in the copy (copy hygiene).

**Component usage rules the build must honour (from the template + chrome):**
- **Every input is a ratified `ui/` component** — no raw `<input>`/`<select>` (DESIGN-SYSTEM §6).
- **Copy hygiene (template governing rule):** no decision IDs / implementation notes in
  any user-facing string; every shown term matches GLOSSARY (e.g. "No egress").
- **Overflow:** the overlay must show **zero horizontal overflow at 320/375/900/1366px**
  — extend the Playwright suite (ADR-0004), jsdom cannot measure it.

---

## 5. VOCABULARIES

| Field in the checklist | Vocabulary / master | Fixed / extensible | Source |
|------------------------|---------------------|--------------------|--------|
| Base currency | currency master | fixed (base-eligible subset) | MASTER-DATA §3 via `/refdata` — **MasterSelect** |
| Data provider | market-provider list `{mock, csv, alphavantage, yahoo, eodhd, kite}` | **served system list, NOT a MASTER-DATA master** | `GET /system/data-source.providers` (frontend zero-copy, D-005) — a `Select` over a served list |
| Timezone | IANA timezone id | **NOT a LedgerFrame vocabulary** (IANA is a public standard — no `/refdata`) | **`Intl.supportedValuesOf('timeZone')` client-side** (F-4); backend-validated on write (F-3 delta, `zoneinfo` truth). Uses the **PROPOSED searchable picker** (Phase-0a amendment), not `MasterSelect`/`Select`. |
| No-egress | boolean toggle | n/a | `privacy_mode` |

**Provider choice is user/system config, not a MASTER-DATA categorical** → it uses a
`Select` over the served `providers` list, not a `MasterSelect`. **Timezone has no
vocabulary source pinned** — §9.

---

## 6. DECISIONS IN FORCE

| Decision | What it forbids / requires here |
|----------|----------------------------------|
| **D-045** | The five steps + order; each **skippable**; each **links to its Settings home**; no personas/profiling; density is **not** a step. |
| **D-002** | PIN is an **access lock**, not encryption; min 6 digits (SECURITY-BASELINE §3). The PIN step must surface the **disk-encryption guidance** (SECURITY-BASELINE §3 makes this normative for first-run) and honour the **first-PIN-from-loopback guard** (a LAN-reachable instance can only set its first PIN from the device). |
| **D-103** | Unrelated but adjacent: unlocking never authorises purge — not a checklist concern, noted so the PIN step copy makes no such promise. |
| **D-069** | No-egress step: the Privacy posture is an **explicit first-run choice**; when enabled the state is **shown as a plain statement**, not merely offered. |
| **D-075 / D-060** | If no-egress is enabled at first run, the device makes **zero outbound calls** — the provider step (and any version check) must respect it. |
| **D-004** | No-PIN-open-local: with no PIN set, first-run writes are permitted from loopback; the checklist must not itself demand auth it cannot yet have. |
| **D-066** | The overlay is **chrome, composed once** in the shell — never re-implemented per page. |
| **D-065 / P-7** | Scope principle: keep the checklist **minimal** — exactly the five steps, nothing added. |
| **D-005** | The provider list (and any vocab) is **backend-served, frontend zero-copy** — no hardcoded lists. |

---

## 7. ACCEPTANCE CRITERIA (adapted — overlay behaviour, not a page)

- [ ] **Five steps, D-045 order:** base currency · timezone · PIN · data provider · no-egress. **Density is not a step.**
- [ ] **Every step is skippable** — skipping is honest (the step shows as skipped, not failed) and never blocks reaching the app.
- [ ] **Each step links to its Settings home** (General/Security/Prices/Privacy) — behaviour when Settings is **not yet built** is per §9 (links vs inline set).
- [ ] **PIN step:** masked numeric, **min 6 digits**; surfaces **disk-encryption guidance**; handles the **first-PIN-from-loopback** case honestly (if reachable over LAN and not on the device, it explains the PIN must be set from the device — never a silent failure).
- [ ] **No-egress step:** enabling it shows the **plain-statement** privacy state (D-069); with it on, the checklist itself makes **zero outbound calls** (extend the C-3 network-trace test).
- [ ] **First-run detection + dismissal:** the overlay appears only when first-run state says so and does **not reappear** once completed/dismissed (mechanism per §3b/§9).
- [ ] **Honesty (Guarantee 3):** every empty/unset field and every skipped step shows a **reason**, never a fabricated default presented as chosen.
- [ ] **Terms** match GLOSSARY; **copy hygiene** — no decision IDs / impl notes in any user string.
- [ ] **No frontend money math**; base currency is a served master value.
- [ ] **Base-currency side effects (F-10):** a Phase-2 test asserts `PUT /settings` with `base_currency` applies to `.env`, resets the FX cache, and restarts the worker (its response reports `restarted_worker`).
- [ ] **Both themes + both densities**; interactive OPEN states (Select/PIN) verified in both themes.
- [ ] **Rendered layout + overflow:** the overlay is verified **rendering at 320/375/900/1366px in both themes** with **zero horizontal overflow**, via the **Playwright suite (ADR-0004)** extended to the first-run overlay — not unit tests alone.
- [ ] **Composes with the lock gate:** the interaction order of first-run overlay ↔ LockScreen is correct (per §9) and neither leaks behind the other.

---

## 8. BUILD PHASES

*One commit per phase. Backend deltas FIRST. Nothing built until §9 clears.*

- **Phase 0 — Contract deltas (§3b): ✅ DONE.** `timezone` + `first_run_complete` settable via `PUT /settings` (timezone backend-validated); no OpenAPI change (allow-list), contract current; `test_first_run_settings.py` green.
- **Phase 0a — §5.5 component amendment (IN PROGRESS → PAUSE):** author the checklist/stepper overlay + no-egress toggle + searchable timezone picker + the F-9 interplay copy as **PROPOSED**, with `/kitchen-sink` specimens; **PAUSE for owner ratification before Phase 1** (new components forbidden without an amendment).
- **Phase 1 — Overlay assembly:** mount the ratified dismissible overlay into `AppShell` **after the lock gate** (F-7); wire the five steps to their endpoints with **inline-minimal controls** (F-2), each also **linking to its Settings home**; provider = selection-only + link-out for keys (F-8); honest interplay copy (F-9); skip/skip-all set the first-run flag = completion (F-1/F-11); no-egress respected.
- **Phase 2 — Tests:** render/behaviour tests (skippable steps, first-run detection, PIN min-6 + loopback case, no-egress zero-call); **extend the Playwright overflow suite** for the overlay; drift/typecheck/lint green.
- **Phase 3 — Owner acceptance walk (LIVE):** drive the real app on a **fresh no-PIN, no-settings instance** (both themes + a narrow width): the overlay appears, each step sets/skips, links behave, PIN + no-egress work, it does not reappear after completion. Each finding → numbered §-entry, re-verified live. Done only after this walk.

---

## 9. NEEDS DECISION — RESOLVED (owner, 2026-07-11)

All resolved by the owner except **F-4** (not addressed — see below) and **F-12**
(owner-added; recorded per the owner's stated rationale, confirm at sign-off).

| # | Item | Resolution (owner, 2026-07-11) |
|---|------|--------------------------------|
| F-1 | Overlay form + trigger | **Dismissible overlay/card, NOT a blocking gate** (D-045 skippability governs). Shown on first load when the first-run flag is unset; **dismiss = flag set, no re-nag.** |
| F-2 | Dependency on the unbuilt Settings page | **INLINE-minimal controls per step**, writing the real settings endpoints; each step **ALSO links to its Settings home** as the "more options" path. The link hits the `NotBuilt` fallback until Settings ships — **acceptable, honest.** |
| F-3 | Timezone not settable | **APPROVED — §3b delta:** timezone becomes settable **via the settings write surface**. Backend-first, contract regenerated same commit. |
| F-4 | Timezone option-list source | **RESOLVED (sign-off):** options come from **`Intl.supportedValuesOf('timeZone')` client-side**; the write is **backend-validated per the F-3 delta** (server zoneinfo is the validation truth — a rejected value surfaces the honest 400, never a silent default). **No `/refdata` vocab** — IANA is a public standard, not a LedgerFrame vocabulary. ~400 options need a **searchable picker**; **the ratified inventory has none** (InstrumentPicker is instrument-bound) → **scoped into the Phase-0a component amendment** as a PROPOSED searchable picker (no silent new primitive). |
| F-5 | First-run state storage + resumability | **APPROVED — §3b delta:** first-run flag as a **server-persisted settings key** (D-078 rotation precedent; survives a browser wipe). **Set on complete OR dismiss.** |
| F-6 | Checklist/stepper component scope | **APPROVED:** author the checklist/stepper as **PROPOSED (DESIGN-SYSTEM §5.5 amendment)**, ratified at `/kitchen-sink` in **Phase 0a before assembly.** |
| F-7 | Shell mount + order vs LockScreen | **Mounts inside the shell AFTER the lock gate** — unlock precedes onboarding (the restored-DB-with-PIN case: lock first, then the checklist). |
| F-8 | Provider step + API keys | **Provider SELECTION only, inline.** API-key entry stays **Settings territory (D-069)** — the step **links out** for keys, **never renders a key field.** |
| F-9 | No-egress ↔ provider ordering | **Keep the D-045 step order.** **Honest interplay copy required (all PROPOSED):** the no-egress step states that **prices won't refresh**; the provider step **notes when no-egress is already enabled.** |
| F-10 | Base-currency write path | **CONFIRMED (sign-off): `PUT /settings` is canonical.** Its **side effects — `.env` write, FX-cache reset, worker restart — must be asserted by Phase-2 tests** (§7). `/system/data-source.base_currency` stays a provider-bundle convenience (both write the same engine-consumed value; no divergence). |
| F-11 | Skip-all / "do this later" | **Skip-all = completion:** flag set, **defaults stand, no nag**; everything settable later in Settings. |
| F-12 | *(owner addition)* demo-data offer as a first-run step | **CONFIRMED (sign-off): EXCLUDE** — D-045's five steps only (P-7 scope). No demo-data step. |

**F-10 verification (owner asked to verify + report before Phase 0):** `base_currency`
is accepted by **two** endpoints, but there is **no divergence** — `PUT /settings`
writes the DB Setting row **and** applies `LEDGERFRAME_BASE_CURRENCY` to `.env` +
`reload_settings()` + FX-cache reset + worker restart; `PUT /system/data-source` writes
the same `.env` value as a side-effect of a provider change. The valuation engine reads
`get_settings().base_currency` (the env value) — so both ultimately set what the engine
uses. **Recommended canonical = `PUT /settings`** (the fuller path the Settings page
will use); this is a report, not a resolution — owner confirms.

---

**Open before Phase 0 (2 items):** **F-4** (timezone option-list source — not addressed)
and confirmation of the **F-10** canonical pick + **F-12** exclude reading. Everything
else is resolved; §3b deltas (timezone-settable + server-persisted first-run flag) are
approved; the Phase-0a component amendment is scoped.

**Sign-off to start build:** F-1..F-3, F-5..F-11 resolved · **F-4 stated** · F-10/F-12
confirmed · §3b deltas approved with pinned shapes · Phase-0a component amendment scoped.
**No build until the owner signs off the resolved plan.**
