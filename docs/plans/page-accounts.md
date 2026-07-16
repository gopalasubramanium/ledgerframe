# PAGE BUILD PLAN — Accounts (`/accounts`)

> **STATUS: ✅ PAGE ACCEPTED (owner, live re-walk, 2026-07-16). MILESTONE CLOSED.**
> §9 RESOLVED one-pass (owner, 2026-07-16). PHASE 0 DONE (backend-first, 11 commits;
> evidence per commit in §11). PHASE 0a ✅ RATIFIED WITH CONDITION (§12ac). PHASE 1
> (assembly) + PHASE 2 (tests) + PHASE 3a (scripted pre-pass) ✅ DONE / GREEN — build
> record in §13. PHASE 3b OWNER WALK — batch 1 in §14 (five findings §14ac-1..5 FIXED +
> re-verified; the journey-guard RED proof stands as the §14ac-2 record). The owner
> **re-walked both journeys live and ACCEPTED (2026-07-16)** → §14 CLOSED; the two carried
> judgment items (the §9-5 restatement wording · the reworded subtitle) are **RATIFIED AS
> SHIPPED** by that acceptance (§14ac-6). No ⏸ remains. §15 retrospective closes the
> milestone; central acceptance log in `RATIFICATION.md §6`. Copied from
> `TEMPLATE-page-build.md`; every §1–§8 row cites the spec it derives from. This is the
> largest remaining page milestone — **two masters land here** (Entity CRUD, D-065;
> Institution master, D-008) — so §9 was deliberately long.
>
> *Prior status (superseded 2026-07-16, retained for the record): PLAN DRAFTED
> through §10 (verify-first) + §9 (NEEDS DECISION), §9 UNRESOLVED — no code written.*

---

## 1. IDENTITY

*Source: INFORMATION-ARCHITECTURE.md §2 (page map), §3 (navigation); DESIGN-SYSTEM.md §3 (page templates).*

| Field | Value | Spec ref |
|-------|-------|----------|
| Page name (H1 = nav label = route) | **Accounts** | IA §2 (`IA:72`), D-022 |
| Route | `/accounts` | IA §2 (`IA:72`) |
| Nav group | **Wealth** (Net worth · Portfolio · Holdings · **Accounts**) | IA §3 (`IA:105`) |
| Page template | **Worklist** (primary DataTable + row actions + CRUD editor) | DESIGN-SYSTEM §3 (`DESIGN-SYSTEM:229` — *"Holdings, **Accounts**, Review, Policy, …"*, verified — not presumed) |
| Rotation eligibility | Not a rotation surface (Wealth-group management page, not an overview) | IA §3 (D-044) |
| One-line purpose | Manage accounts (institution, kind, currency, cost-basis method, entity) and Entity CRUD; rollups are linked summaries. | IA §2 (`IA:72`) |

**Sidebar slot already reserved.** The nav-density rule sizes for the FULL 6-group/19-item
nav (Wealth = 4 items incl. Accounts), so adding `/accounts` needs no sidebar rework
(DESIGN-SYSTEM §5.5; CURRENT.md P-3 batch, `DESIGN-SYSTEM:554/565`). Flip `NavItem.built`
for Accounts at Phase 1.

---

## 2. OWNERSHIP TABLE

*Copied from INFORMATION-ARCHITECTURE.md §5 "Accounts (`/accounts`)" (`IA:243-251`). Never re-derived.*

**Owns (canonical, authoritative, fully explained on this page):**
- **Account CRUD** — name, **institution from the Institution master** (D-008), **kind from
  `/refdata`** (`account_kind`), **currency**, the **cost-basis method selector** (fifo/average,
  D-018), **entity assignment on the account form** (D-064). (`IA:245-247`)
- **Entity CRUD** — minimal: **name + kind from vocab** (`entity_kind`); **delete blocked while
  accounts reference the entity** (D-065). Card on this page. (`IA:247-249`; DECISIONS `D-065`,
  `DECISIONS:351`)
- **Institution master management** — the user-extensible master itself: create · rename · merge ·
  delete (FK-blocked). One master, FK'd from **both** `accounts.institution` **and**
  `insurance_policy.insurer` (D-008; MASTER-DATA §6/§7, `MASTER-DATA:303,372-375`).

**Summarises (other pages' info — via the named reader, linked, never recomputed):**

| Summary shown | Canonical page | Shared reader reused | Link target |
|---------------|----------------|----------------------|-------------|
| Per-account **value** rollup | Net worth / Portfolio | `value_portfolio()` (via `accounts_report()`, `app/services/accounts.py:31-91`) | → Holdings (account-scoped — see §9-11) |
| **Holdings count**, asset classes, currencies | Holdings | same `value_portfolio()` grouping | → Holdings |
| **Stale / low-confidence** counts | Pricing Health | same reader (`score_holding`) | → Pricing Health |

*(IA §5, `IA:250-251`: "account rollups … are P-1 summaries of the holdings/value reader, linked (D-064).")*

**Links to:** Holdings (account-scoped list), Pricing Health (staleness), Net worth / Portfolio (totals), Insurance (shares the Institution master — §9-1).

**Enforcement corollary (P-1/D-031):** the rollup widgets show only figures the holdings/value
reader already produces — **no account-level figure is computed on this page** (frontend renders
served strings; §9-10). The account `value` rollup is the same `value_portfolio()` total the Net
worth headline owns, grouped by `account_id` — one derivation, never a second code path.

---

## 3. API SURFACE

*Source: API-CONTRACT.json (frozen baseline, 127 paths) + API-CONTRACT.md delta table.*

### 3a. Endpoints consumed (already in the frozen contract)

| Method + path | Purpose on this page | Response shape pinned? |
|---------------|----------------------|------------------------|
| `GET /accounts` (`accounts.py:31`) | Accounts table + per-account rollup | **Untyped `-> dict`** (no `response_model`, so nothing is stripped) — shape at `services/accounts.py:73-91` |
| `GET /accounts/list` (`accounts.py:38`) | Lightweight account list + `kinds` | Untyped dict (`_account_dict`, `accounts.py:95-96`) |
| `POST /accounts` (`accounts.py:50`, `[require_auth]`) | Create account | Untyped `{ok, …}` |
| `PATCH /accounts/{aid}` (`accounts.py:57`, `[require_auth]`) | Edit account | Untyped `{ok, …}` |
| `DELETE /accounts/{aid}` (`accounts.py:67`, `[require_auth]`) | Delete account (txn-guarded) | Untyped `{ok}` |
| `GET /entities` (`accounts.py:43`) | Entity list (id · name · kind) | Untyped `{entities:[…]}` |
| `GET /refdata` (`refdata.py:124`) | `account_kind`, `cost_basis_method`, `entity_kind` vocabs | `{value,label}[]` per vocab |

### 3b. Contract deltas (needed but not in the baseline — BUILD BACKEND-FIRST)

Each row is built backend-first and regenerates `API-CONTRACT.json` + `docs/openapi.json` in the
**same commit** (freeze rule); each ships **fail-first**. Several of these are the substance of the
§9 items — they are listed here as the mechanical delta and cross-referenced to the decision that
governs them. **Nothing here is built until §9 is ruled.**

> **Verify-first divergence flags (⚠).** The premise "accounts have full CRUD" is **partly false**:
> the write model `AccountIn` (`accounts.py:24-28`) **omits `entity_id` AND `cost_basis_method`** —
> both are columns the model carries and the engine *reads* (`tax.py:257`), but **neither can be set
> through the API today**. So the two headline features of this page (D-064 entity assignment, D-018
> cost-basis selector) have **no write path** and are §3b adds, not "wire the existing endpoint".

| kind | Endpoint (current → intended) | Decision | Why this page needs it |
|------|-------------------------------|----------|------------------------|
| **reshape** | `AccountIn` gains **`entity_id`** (int\|None, FK-validated) | §9-4 / D-064 | Assign an account to an entity on the form. ⚠ absent today. |
| **reshape** | `AccountIn` gains **`cost_basis_method`** (fifo/average) + method-change rebuild | §9-5 / D-018 | The cost-basis selector. ⚠ absent today; changing it on an account with history triggers a holdings rebuild + restatement warning (D-018). |
| **behaviour** | `POST /accounts` / `PATCH` **reject** out-of-vocab `kind` (400) and out-of-vocab `currency` (400) | §9-9 | Today invalid `kind` **silently coerces** to `brokerage` (`accounts.py:114`) / silently drops (`:131`); `currency` is `upper()[:3]` with **no vocab check** (`:115,133`). The policy_status precedent = enforce, not coerce. |
| **reshape** | `accounts_report` gains served `value_display` / `total_display` + `base_currency` affix | §9-10 / D-105 | Money on this page must be **served display strings** (raw floats today, `_f` whole-unit rounding, `accounts.py:27`); frontend computes nothing. |
| **add** | `POST /entities`, `PATCH /entities/{id}`, `DELETE /entities/{id}` (delete FK-blocked) | §9-6 / D-065 | Entity CRUD. **Only `GET /entities` exists today** (API-CONTRACT.md:74); no `EntityIn`, no write route, no delete-block. |
| **add** | Institution master: `GET/POST/PATCH/DELETE` `/institutions` (or `/masters/institution`) + **`merge`** + re-pointing migration for **both** FK columns | §9-1 / §9-2 / D-008 | The master does not exist — `accounts.institution` and `insurance_policy.insurer` are **both free `String(120)`** (`models:130,525`). First user-extensible master-with-CRUD in the codebase (none exists — sector/tag are not tables). |
| **reshape** *(maybe)* | Account-scoped Holdings link — `GET /portfolio/holdings?account_id=` or `HoldingView.account_id` | §9-11 | Rollup rows link to the account's holdings, but `/portfolio/holdings` carries **no account field** (`portfolio.py:128-154`) and takes only `?symbol`/`?entity_id`. |

> **Note (typed responses):** the accounts routes are **untyped `-> dict`**, so added fields are NOT
> stripped (contrast `HoldingView`). The Entity/Institution write routes will be **typed** — declare
> every served field on the model + regenerate the contract.
>
> **Note (a ratified backend VALUE needs a same-batch code test, page-review §13):** §9-9's
> enforcement and §9-5's method-change rebuild set **behaviour**, not shape — each ships a **code test
> pinning the served behaviour in the same batch** (400-on-invalid-kind; rebuild-on-method-change),
> fail-first. Rename/removal tests discriminate by **response shape**, not status (SPA 200 fallthrough).

---

## 4. COMPONENTS

*Source: DESIGN-SYSTEM.md §5 (ratified inventory). Ratified only; any gap → §9 amendment.*

| Ratified component | Role on this page | Data source | Prop/state not exercised at kitchen-sink |
|--------------------|-------------------|-------------|------------------------------------------|
| **DataTable** (`DESIGN-SYSTEM:422`) | Accounts spine (institution · kind · currency · cost-basis · entity · rollup) + Entities table + Institution-master table | **Real** `GET /accounts` / `GET /entities` / new master reader | `rowLink`, `footer` totals (rollup Σ), `truncate` (long institution names) |
| **MasterSelect** (`DESIGN-SYSTEM:589`; `MasterSelect.tsx`) | `kind` (`account_kind`), `cost_basis_method`, entity `kind` (`entity_kind`) selectors | **Real** `/refdata` | ⚠ **`allowCreate` + `extensible` wired to a DB-backed master has NEVER shipped** — today it reads `/refdata` fixed vocabs only (§9-3, mock-backed) |
| **Select** (`DESIGN-SYSTEM:332`) | **Entity assignment** on the account form (user-record picker over `/entities`, *not* a master) | **Real** `GET /entities` | — (spec names "the account picker over `/accounts`" as the Select archetype) |
| **Dialog** (`DESIGN-SYSTEM:468`) | Account editor, Entity editor, Institution editor, Merge dialog | — | `size="lg"` (two-column account form) |
| **ConfirmDialog** (`DESIGN-SYSTEM:469`) | Delete account / entity / institution; `requirePin` per D-103 | — | delete-block **error** path (§9-6/§9-1) |
| **RowMenu** (`DESIGN-SYSTEM:470`) | Per-row actions (Edit / Delete / Merge) — keeps tables narrow | — | `disabled` (delete disabled when FK-blocked) |
| **Button** (`DESIGN-SYSTEM:534`, §5.4) | "Add account" / "Add entity" / "Add institution" — icon+label, 1em glyph | — | — |
| **StatusChip** / **StalenessChip** | Stale / low-confidence rollup chips | Real reader counts | — |
| **MetaStrip** (`DESIGN-SYSTEM:424`) | Compact account identity metadata (institution · kind · currency · entity) if a detail panel is used | Real | narrow 2-col wrap |
| **PageHeader** / **EmptyState** | Title + honest empty states (no accounts; no entities) | — | — |
| **TextInput** (`DESIGN-SYSTEM:328`) | Account name; entity name; institution name (free-text label fields) | — | — |

**Data source (Holdings retrospective).** Every component above wires to a **real endpoint** — except
the **institution add-inline affordance**, which today can only be **mock-backed** (MasterSelect's
`allowCreate` has no real extensible-master data source; §9-3). That is a **§9 NEEDS DECISION**
(mock-backed affordance) until the master endpoint is built and wired.

**Affordances the ratified inventory lacks (amendment required before build — see §9):**
- **A creatable/searchable select bound to a DB-backed extensible master** (institution) with an
  **add-inline** affordance. `MasterSelect` *has* `allowCreate` + an `extensible` flag
  (`MasterSelect.tsx:8-11`) but its data source is the `/refdata` registry (fixed vocabs);
  `Combobox` is searchable but **explicitly "NOT for MASTER-DATA categoricals"** (`DESIGN-SYSTEM:590`).
  **§9-3** decides: extend MasterSelect's data source to a DB-backed master (no new component), or a
  new control (§5 amendment). *(No new component is built without a DESIGN-SYSTEM amendment.)*

**Component usage rules the build must honour:** row actions in `RowMenu` (never wide action columns);
entity references link directly (D-098) where a canonical detail exists; popovers portal to the
viewport (§6); cards layered (D-100); scroll = content only, header outside (D-101); labels are the
**SERVED `/refdata` labels rendered verbatim** (§12es-3 lesson — see §9-13 for the `fifo → "Fifo"` bug).

**Tables — dataset-size posture (D-094):**
- **Accounts table** — **bounded** (tens of accounts). Client-side sort/filter acceptable; revisit
  threshold ~500 accounts.
- **Entities table** — **bounded** (single digits typically). Client-side.
- **Institution master table** — **bounded–growing**; client-side to start, revisit ~500 institutions
  (merge keeps it small by design). All cap at `--table-max-h` and scroll internally.

---

## 4b. PER-VARIANT FIELD & ACTION SPECS

*Accounts have a `kind` variant (brokerage / bank / retirement / wallet / property / manual / other),
but — unlike Holdings — the kind does **not** branch the form's fields or actions today: `AccountIn`
is one shape for every kind (`accounts.py:24-28`). No per-variant field matrix is required for v2.*
**Recorded N/A (CHOSEN)** unless the owner wants kind-conditional fields (that would be a §9 item and a
new backend field-spec served from `/refdata`, D-005 — not proposed here). The variant that *does*
matter is **cost-basis method** (fifo/average), which is per-account, not per-kind (D-018, §9-5).

---

## 5. VOCABULARIES

*Source: MASTER-DATA.md. Every categorical → its vocabulary/master + control.*

| Field on this page | Vocabulary / master | Fixed (/refdata) or extensible | MASTER-DATA ref |
|--------------------|---------------------|-------------------------------|-----------------|
| Account **kind** | `Account.kind` (7) | **Fixed** `/refdata` `account_kind` | §2 (`MASTER-DATA:70` table; `DEF-3`, `services/accounts.py:24`) → **MasterSelect** |
| **Cost-basis method** | `cost_basis_method` (2: fifo, average) | **Fixed** `/refdata` | §2 (`MASTER-DATA:70`; D-018) → **MasterSelect** |
| Account **currency** | `SUPPORTED_CURRENCIES` (9) | **Fixed** `/refdata` `currency` (code constant, no admin screen) | §3 AMENDMENT (`config.py:18`) → **MasterSelect** |
| **Institution** | Institution **master** | **Extensible master** (own endpoint, starts empty) | §6/§7 (`MASTER-DATA:303,372`; D-008) → **creatable master control (§9-3)** |
| Entity **kind** | `Entity.kind` (5: self/spouse/trust/company/other) | **Fixed** `/refdata` `entity_kind` | §2 (`MASTER-DATA:58`; `refdata.py:80`) → **MasterSelect** |
| **Entity assignment** (which entity) | **User record**, not a master | — | **Select** over `GET /entities` (user-record picker, `DESIGN-SYSTEM:332`) |

**User data, not a master:** the **entity assignment** field on the account form is a picker over the
user's entity *records* (`GET /entities`) — a `Select`, **not** a MasterSelect. The entity *kind* field
(inside the Entity editor) **is** a fixed vocab → MasterSelect over `entity_kind`.

---

## 6. DECISIONS IN FORCE

*Source: docs/audit/DECISIONS.md. Each decision that constrains this page.*

| Decision | What it forbids / requires on this page |
|----------|------------------------------------------|
| **D-064** (`DECISIONS:350`) | Accounts page KEEP (reshaped): institution from master · kind from `/refdata` · **cost-basis method selector here** (D-018) · **entity assignment on the account form** · rollups are P-1 linked summaries. |
| **D-065** (`DECISIONS:351`) | Entity CRUD KEEP (UI added): minimal (name + kind from vocab) as a card here; **delete blocked while accounts reference the entity**. Passes P-7. |
| **D-008** (`DECISIONS:136`) | ONE user-extensible Institution master, FK'd from `accounts.institution` **and** `insurance_policy.insurer`. Estate `related_to` stays free text (architectural invariant — do NOT normalise it). |
| **D-018** (`DECISIONS:203`) | Per-account cost-basis method (fifo/average); new accounts default `fifo`; changing method on an account **with history** → holdings rebuild + **restatement warning**. Selector on the account form. `spec` (specific-lot) → ROADMAP R-6. |
| **D-105** | Money = **backend-served display strings**; the frontend renders them (no money math here). |
| **D-103** | Writes are `[S]`-gated via the **ambient PIN session** (no second PIN prompt on save); purge-style destructive PIN stays fresh (not applicable to routine account edits). |
| **D-029** | "Institution" (not "platform"); "Household" is a valid **entity name**, not a kind and not a separate term. |
| **P-1 / D-031** | Rollups are summaries of the canonical reader — never a second figure or a recompute. |
| **P-7 / D-065** | Shipping CRUD UI for an existing capability adds no capability — Entity CRUD passes the scope test (the Policy/Cash-flow precedent). |
| **R-35 / R-33** (parked) | **No per-entity** planning / policies / scenarios this milestone; the household-scoped 400s stay honest. Entity is an account **attribute**, not a page-level scope. |

---

## 7. ACCEPTANCE CRITERIA

- [ ] **Happy path:** the accounts DataTable lists every account with institution · kind · currency ·
      cost-basis · entity · rollup (value, holdings, classes, currencies, stale/low-confidence);
      `[S]`-gated CRUD creates/edits/deletes; Entity CRUD card manages entities; Institution master
      surface lists/renames/merges/deletes.
- [ ] **Empty state:** no accounts → EmptyState with a reason + CTA; no entities → same; empty
      institution master (starts empty, D-008) → honest "no institutions yet" (Product Guarantee 3).
- [ ] **Error state:** delete blocked (account has transactions / entity has accounts / institution
      is referenced) surfaces the **honest served 400 message**, never a silent no-op; save failures toast.
- [ ] **Stale / low-confidence:** rollup counts flagged via chips, never hidden or faked; linked to
      Pricing Health.
- [ ] **Negative / large / long-name data:** long institution names truncate (not overflow); negative
      account rollups (liabilities) render tabular; multi-currency accounts render base-currency rollup
      with affix + native-currency chips.
- [ ] **Both densities + both themes** correct; **interactive OPEN states** (every Select/MasterSelect
      dropdown, the merge dialog, ConfirmDialog + PIN) verified in light AND dark; added to `/kitchen-sink`.
- [ ] **Keyboard + WCAG AA** (focus ring, `aria-sort`, labels).
- [ ] **No frontend money math** — every rollup figure is a served display string (D-105); base-currency
      affix served (`base_currency`), not client-derived.
- [ ] **Terms** match GLOSSARY; **categoricals** come from MASTER-DATA via `/refdata` — and the rendered
      label is the **SERVED `/refdata` label verbatim** (fixes `fifo → "Fifo"`, §9-13).
- [ ] **Tables (D-094):** accounts / entities / institution tables filter/sort **client-side** (bounded)
      with the recorded revisit thresholds.
- [ ] **[S] gate on every write** (D-103 ambient PIN — no second prompt); `?entity_id` **400s stay
      honest** on Policy/Scenarios/Insurance/Estate (untouched by this page).
- [ ] **Request-body assertion:** account create/edit posts exactly the intended `{name, institution,
      kind, currency, entity_id, cost_basis_method}`; entity create posts `{name, kind}`; institution
      merge posts `{survivor, duplicate}` — asserted on the actual body, not just handler-called.
- [ ] **Institution round-trip (D-008 migration):** every existing free-text `accounts.institution`
      **and** `insurance_policy.insurer` value migrates INTO the master (seeded from distinct values),
      **never destroyed** (the Amendment-B fold precedent); Insurance's typeahead superseded, its data intact.
- [ ] **Cost-basis restatement (D-018):** changing method on an account with history shows the
      restatement warning **and** the served figures actually change after the rebuild (a code test pins it).
- [ ] **Rendered layout verification:** `/accounts` added to **all three** `e2e/overflow.spec.ts`
      route arrays + the **page-inset guard (measured at 1728)** + confirmed against the reserved
      **sidebar-density** slot; zero horizontal overflow at 320/375/900/1366 × both themes; only
      `.lf-shell__content` scrolls vertically.
- [ ] **Copy hygiene:** no `D-0…`/`§…`/enum/endpoint names in user-facing strings; a changed label is
      updated **app-wide** (Insurance insurer field, any "platform"→"Institution" residue).
- [ ] **Every visual/geometry fix ships a pre-pass assertion** (fail-first, measures the owner-visible
      defect); each progressive rollup card waited out of skeleton before asserting.

---

## 8. BUILD PHASES

*One commit per phase. §3b backend deltas FIRST. Never assemble against an endpoint that does not exist.*

- **Phase 0 — Contract deltas (§3b, LARGE — the biggest Phase 0 to date):** backend-first, one delta
  per commit, each fail-first, contract regenerated same-commit (`make api-contract-check`). Order:
  (0.1) `AccountIn` + `entity_id`/`cost_basis_method` + write-validation (§9-4/5/9); (0.2) rollup
  `*_display` + affix (§9-10); (0.3) Entity CRUD + delete-block (§9-6); (0.4) **Institution master**
  table + CRUD + merge + re-pointing migration for **both** FK columns, seeded from distinct free-text
  values (§9-1/2) — the migration touches the **accepted Insurance page's data** (delta-note + re-run
  discipline). *(Skip nothing — §3b is non-empty and load-bearing.)*
- **Phase 0a — Component + geometry gate:** if §9-3 rules a **new** control (not a MasterSelect
  data-source extension), ratify it at `/kitchen-sink` **before** assembly (§5 amendment). Author the
  **geometry specimen** (worklist: accounts spine + Entity card + Institution surface; honesty frames:
  empty accounts, the default "Household" entity, an entity with delete **blocked**, long institution
  names, a **merge candidate pair** "DBS" vs "DBS Bank"). **Owner ratifies geometry before Phase 1.**
- **Phase 1 — Page assembly:** compose ratified components; wire to the endpoints; honest
  empty/error/stale states; flip `NavItem.built`; route in `AppRoutes`; extend the demo seed (accounts
  across entities; a delete-blocked entity; seeded institutions incl. a merge pair).
- **Phase 2 — Tests:** render/component tests + acceptance (§7); request-body assertions; the migration
  round-trip test; extend overflow + inset + sidebar-density guards to `/accounts`; `npm run check` **exit 0**.
- **Phase 3a — Scripted pre-pass (GREEN before the walk):** `e2e/smoke/accounts-smoke.spec.ts` on the
  reset live instance — full CRUD through the `[S]` gate, entity delete-block error surfaced,
  institution merge round-trip, rollups out of skeleton, both themes × breakpoints, 0 console errors;
  re-run `insurance-smoke` + `review-smoke` GREEN (the shared masters + any new seam).
- **Phase 3b — Owner acceptance walk (LIVE, judgment items only).** Owner closes — never self-certified.

---

## 9. NEEDS DECISION — ✅ RESOLVED one-pass (owner, 2026-07-16)

*Everything the specs under-specify. Do NOT improvise a resolution; do not start build on any open item.
**⚑ = load-bearing call.** PROPOSED resolutions are for the owner to approve/amend one-pass.*

> **RULING (owner one-pass, 2026-07-16).** ALL FOURTEEN items ACCEPTED as proposed, with three
> amendments (F/G/H) and one recording note recorded verbatim below. Each row's `Ruling` cell carries
> the accept + date; nothing in the PROPOSED column is struck. §9 flips ⛔ → ✅ RESOLVED.
>
> **AMENDMENT F (binds 9-1).** The master is seeded from the distinct free-text values of **BOTH**
> columns (`accounts.institution` **and** `insurance_policy.insurer`) using **Tag's concrete
> case+whitespace rule** for exact-collapse — trimmed, case-insensitive equality; **first-seen casing
> survives**. Anything fuzzier ("DBS" vs "DBS Bank") is **USER-DRIVEN merge only** — never
> auto-detected. The old `String` columns follow the **Amendment-E fold-then-drop pattern**: seed →
> re-point FK → **DROP both columns** in the migration. Insurance is an ACCEPTED page whose served
> shape changes: a dated delta note in `page-insurance.md` + its guards re-run.
>
> **AMENDMENT G (binds 9-11).** The drill-down lands on the Holdings **PAGE** (URL account filter →
> visible, clearable chip) — **Phase-1 work** with a dated delta note in `page-holdings.md` + its
> pre-pass re-run. **Phase 0 ships only the reader param** (`GET /portfolio/holdings?account_id=`) —
> the one derivation.
>
> **AMENDMENT H (binds 9-6).** `entity_kind` (self/spouse/trust/company/other) graduates from a code
> comment to **MASTER-DATA §2 + `/refdata`** with served labels (the `policy_status` pattern) **BEFORE**
> the CRUD ships.
>
> **RECORDING NOTE (binds 9-12).** The silent-first-account import fallback → an **08-TECH-DEBT entry**
> with the named location (`csv_import.py:428-438`), the mis-attribution risk, and the Holdings-page
> follow-up. **Recorded this session, not fixed.**

| # | Item | Why it blocks / what's needed | Proposed resolution (for owner to approve) | Ruling (owner, 2026-07-16) |
|---|------|-------------------------------|--------------------------------------------|----------------------------|
| **9-1 ⚑** | **Institution master — build + FK re-pointing (D-008).** | The master **does not exist**: `accounts.institution` (`models:130`) and `insurance_policy.insurer` (`models:525`) are **both free `String(120)`**. No institutions table, no `Institution` model, no FK — and **no user-extensible master-with-CRUD exists anywhere** in the codebase (sector = free-text column; tag = JSON list; neither is a table). This is greenfield. | **BUILD it** as the first extensible master: a `institutions` table (id · name, unique-by-name, starts empty) + typed `GET/POST/PATCH/DELETE`; migrate `accounts.institution` **and** `insurance_policy.insurer` to FK (nullable), **seeding the master from the distinct existing free-text values** (Amendment-B fold precedent — values migrate IN, never destroyed). Insurance's client-side typeahead (`Insurance.tsx:131-133`) is **superseded** by the master (delta-note on the accepted Insurance page). | **✅ ACCEPTED + AMENDMENT F** — BUILD it. Seed from **both** columns' distinct values via Tag's trimmed/case-insensitive collapse (first-seen casing wins); fuzzy is user-driven merge only. Old `String` columns dropped (fold-then-drop). Insurance served shape changes → dated delta note + guards re-run. |
| **9-2 ⚑** | **Institution merge — semantics + scope.** | MASTER-DATA specifies merge **behaviour** (fold duplicate into survivor, re-point every referencing row, delete FK-blocked, offer merge instead — `MASTER-DATA:372-375`) but **NOT how variants are detected/matched** ("DBS" vs "DBS Bank" is named as an *outcome*, no algorithm/threshold — unlike Tag's concrete case+whitespace rule). Open: ship merge now vs master-without-merge first. | **Ship merge in this milestone, USER-DRIVEN (no fuzzy auto-detect):** the admin picks survivor + duplicate explicitly; `merge` re-points both FK columns and deletes the duplicate in one transaction. **No automated similarity matching** (spec is silent → not invented). Delete is FK-blocked with "merge instead" offered. *(If the owner prefers to defer merge, the master ships with create/rename/delete-FK-blocked only and merge → a ROADMAP item — say which.)* | **✅ ACCEPTED** — merge **ships NOW**, user-driven (caller names survivor + duplicate); one transaction re-points **both** FK columns and deletes the duplicate. **No fuzzy auto-detect.** FK-blocked delete's 400 offers merge in plain language. |
| **9-3 ⚑** | **Institution selector — the add-inline component (§4 amendment).** | The account/insurance forms need to pick an institution **and add a new one inline**. `MasterSelect` has `allowCreate`+`extensible` (`MasterSelect.tsx:8-11`) but is **wired to `/refdata` fixed vocabs** — it has **never been pointed at a DB-backed master** (mock-backed affordance). `Combobox` is searchable but **"NOT for MASTER-DATA categoricals"** (`DESIGN-SYSTEM:590`). | **Extend `MasterSelect`'s data source** to accept a **DB-backed extensible master** (institution): read the master's list, `allowCreate` POSTs to the master endpoint. **No new component** — the affordance already exists in the component layer; only its data source is new (a `DESIGN-SYSTEM §5.1` clarification, not a new-component amendment). Ratify the wired-to-real-master state at `/kitchen-sink`. *(If the owner wants a searchable creatable control for hundreds of institutions, that's a Combobox-scope amendment — flag now.)* | **✅ ACCEPTED** — extend `MasterSelect`'s data source to a DB-backed master (a **DESIGN-SYSTEM §5.1 clarification**, **no new component**). Ratify the wired-to-real-master state at `/kitchen-sink`. (Phase-0a/Phase-1 work; Phase 0 is backend only.) |
| **9-4 ⚑** | **Entity assignment writable on the account form (D-064).** | ⚠ `AccountIn` **omits `entity_id`** (`accounts.py:24-28`) though the column exists (`models:134`) and 15 readers filter by it. The page **cannot assign an account to an entity today.** | **Add `entity_id` (int\|None, FK-validated) to `AccountIn`**; the form field is a **`Select` over `GET /entities`** (user records, not a master). §3b reshape, backend-first. | **✅ ACCEPTED** — add `entity_id` (int\|None, **FK-validated**, honest 400 on a nonexistent entity) to `AccountIn`. |
| **9-5 ⚑** | **Cost-basis method writable + restatement (D-018).** | ⚠ `AccountIn` **omits `cost_basis_method`** though the column exists (`models:138`) and the **realised-gains engine reads it** (`tax.py:257`). No write path → the D-064/D-018 selector is unbuildable today. D-018 also requires: changing method on an account **with history** → holdings rebuild + restatement warning. | **Add `cost_basis_method` (fifo/average, default fifo) to `AccountIn`** (MasterSelect over `cost_basis_method`). On a PATCH that **changes** the method for an account **with transactions**, trigger the holdings rebuild and surface the **restatement warning** ("realised/unrealised figures will change"). Verify whether account mutation already triggers a rebuild (likely NOT — new wiring). Code test pins rebuild-on-change, fail-first. | **✅ ACCEPTED** — add `cost_basis_method` (fifo/average, default fifo, vocab-enforced); a PATCH that **changes** the method on an account **with transactions** triggers the holdings rebuild + restatement warning. Fail-first pins rebuild-on-change (realised-gains move on the fixture). |
| **9-6 ⚑** | **Entity CRUD (D-065) — write routes + delete-block.** | Only `GET /entities` exists (API-CONTRACT.md:74); **no `POST/PATCH/DELETE`, no `EntityIn`, no `ENTITY_KINDS` constant, and no delete-block** (entity delete is unimplemented; the FK has **no `ondelete`/cascade**, `models:121/134`). | **BUILD `POST/PATCH/DELETE /entities`** (name + kind from `entity_kind` vocab); **DELETE blocked while any account references the entity** — an honest served 400 (the account-delete-guard precedent, `accounts.py:139-148`), enforced in the service (no DB cascade). §3b add, backend-first. | **✅ ACCEPTED + AMENDMENT H** — first graduate `entity_kind` to **MASTER-DATA §2 + `/refdata`** with served labels (the `policy_status` pattern), **then** build `POST/PATCH/DELETE /entities` (name + kind vocab-enforced); DELETE blocked while any account references the entity (service-level 400, no cascade). Fail-first. |
| **9-7 ⚑** | **The default "Household" entity — protected? renamable? deletable?** | The Phase-4.1 migration creates one entity **named "Household"/self** and assigns every account to it (`f4a9c2b71e08_entities.py:33,46-52`); there is **no `is_default` flag** — it is just "the lowest-id entity". Nothing today can rename or delete it. D-029: "Household" is a valid entity **name**, not special. | **No special-casing:** "Household" is renamable + re-kindable like any entity (D-029). It is **delete-blocked by the same FK guard** (every account references it today, so it cannot be deleted until accounts are reassigned) — **no separate floor**. Since `account.entity_id` is nullable, no "must always have ≥1 entity" invariant is added (an account may be entity-less; the FK guard alone governs). *(If the owner wants a protected default that can never be deleted, say so — that's an `is_default` flag + a new rule.)* | **✅ ACCEPTED** — **no special-casing** for "Household" (D-029): renamable, re-kindable, same FK guard, **no `is_default`**, no ≥1-entity invariant (`entity_id` stays nullable). |
| **9-8 ⚑** | **`?entity_id` scoping — is entity filtering USER-VISIBLE on this page (or anywhere)?** | 15 portfolio readers **filter** by `entity_id` (incl. `GET /accounts` itself, `accounts.py:36`); Policy/Scenarios/Insurance/Estate **reject 400** (household-scoped); **NO frontend consumer of `entity_id` exists** (0 callers in `frontend/src/`). R-35/R-33 park per-entity planning/policies as a **data-model change, not a query param**. | **NO entity switcher / page-level scope this milestone** (specs are silent; do not invent a global switcher — the Portfolio/Home/Net-worth household-only precedent). Entity is shown as an **account attribute** (a column + the editable form field, D-064), **not** a filter over the page. The `?entity_id` param stays **dormant** (no new UI caller) until R-35 lands per-entity views. The four household 400s stay honest, untouched. | **✅ ACCEPTED** — entity is an **account attribute**, **not** a page filter; the `?entity_id` param stays **dormant** (no new UI caller); **no switcher** invented. |
| **9-9** | **Kind + currency write-validation — enforce (400) or silent-coerce?** | On create, an out-of-vocab `kind` **silently coerces to `brokerage`** (`accounts.py:114`); on PATCH it is **silently dropped** (`:131`). `currency` is `upper()[:3]` with **no vocab check** (`:115,133`) — differs from the strict `base_currency` enforcement. Silent coercion is a Guarantee honesty gap. | **Enforce on write:** out-of-vocab `kind` → **400**; `currency` not in `SUPPORTED_CURRENCIES` → **400** (the `policy_status`/`base_currency` precedent). The MasterSelect UI constrains input anyway; the 400 protects the API path. §3b behaviour delta + fail-first test. | **✅ ACCEPTED** — **enforce**: out-of-vocab `kind` → 400 (RED on today's `brokerage` coercion); `currency` not in `SUPPORTED_CURRENCIES` → 400 (RED on today's `upper()[:3]`). Plain-language details, no decision IDs. |
| **9-10** | **Money on the page (D-105) — served display strings + affix.** | `accounts_report` serves **raw floats** (`value`, `total`) with **whole-unit rounding** (`_f`, `accounts.py:27`) and **no `*_display`, no per-account base-currency affix** — unlike `/portfolio/summary`. Money **is** shown here (per-account value + total), so this is NOT the Estate counts-only N/A. | **Add served `value_display` / `total_display` strings + the `base_currency` affix** (the Insurance/Scenarios/Net-worth precedent, `.lf-stat__unit`); frontend renders verbatim, computes nothing. Multi-currency accounts: base-currency rollup with affix + native-currency chips. §3b reshape. | **✅ ACCEPTED** — add served `value_display` / `total_display` + `base_currency`; drop the whole-unit `_f` rounding in favour of the platform display path; non-base accounts carry the currency code (§12in-1). Fail-first: raw-float-only shape → RED. |
| **9-11** | **Account rollups as linked P-1 summaries — the LINK target.** | IA says rollups link to the holdings/value reader (`IA:250`), but `/portfolio/holdings` carries **no account field** and takes only `?symbol`/`?entity_id` (`portfolio.py:128-154`) — there is **no account-scoped Holdings view** to link to. | **Add an account-scoped Holdings link:** either `GET /portfolio/holdings?account_id=` (scoped reader, the `?symbol` precedent) **or** surface `HoldingView.account_id` + a client filter on Holdings. Pick the endpoint-param route (one canonical reader, no client recompute). §3b reshape. *(If the owner prefers no per-account drill-down for v2, the rollup is display-only with a documented no-link — say which.)* | **✅ ACCEPTED + AMENDMENT G** — the drill-down lands on the Holdings **PAGE** (URL account filter → visible, clearable chip), **Phase-1** work (dated delta note in `page-holdings.md` + pre-pass re-run). **Phase 0 ships only** `GET /portfolio/holdings?account_id=` — the one derivation, scoped like the entity chokepoint. |
| **9-12** | **CSV import ↔ account-creation seam — one canonical home.** | `/portfolio/import/{csv,commit}` take optional `?account_id`; the frontend import UI **passes none** and the backend **silently falls back to the first account, else auto-creates "Imported"/brokerage** (`csv_import.py:428-438`). Holdings owns import; Accounts owns creation. | **Keep the seam:** account **creation lives only on `/accounts`**; import continues to attribute to a chosen/first account. **Flag the silent-first-account fallback** as a latent Holdings honesty issue (mis-attribution risk) — a Holdings-page follow-up, **not** re-solved here (no new capability on Accounts). Optionally the import account picker links to `/accounts` to create one first. | **✅ ACCEPTED + RECORDING NOTE** — keep the seam (creation lives only on `/accounts`). The silent-first-account fallback (`csv_import.py:428-438`) → an **08-TECH-DEBT entry** (named location, mis-attribution risk, Holdings-page follow-up) — **recorded this session, not fixed**. |
| **9-13** | **GLOSSARY / SN-class vocabulary sweep.** | GLOSSARY has **Account** (`:66`), **Institution** (`:67`), **Entity** (`:68`), **Cost basis** (`:76`) — but **missing**: "**Cost-basis method**" (the fifo/average concept, distinct from Cost basis), "**Account kind**", "**Rollup / Account rollup**", "**Merge**" (institution merge). Also the served label **`fifo → "Fifo"`** (`refdata.py` titleizer, no override) is wrong — should read **"FIFO"**. | **Author the four missing terms spec-first** (`GLOSSARY.md` then the popover mirror, parity guard), and **add a `_VOCAB_LABEL_OVERRIDES["cost_basis_method"] = {"fifo": "FIFO"}`** so the SERVED label is correct and rendered verbatim (§12es-3 served-label rule). | **✅ ACCEPTED** — author the four terms (**Cost-basis method · Account kind · Rollup · Merge**) spec-first in `GLOSSARY.md`, then the popover mirror (parity green); add `_VOCAB_LABEL_OVERRIDES["cost_basis_method"]["fifo"] = "FIFO"` with a fail-first on the served label ("Fifo" today → RED). |
| **9-14** | **Inherited platform standards (confirm-only).** | Every accepted page inherits these; confirm they apply to Accounts. | **CONFIRM:** `[S]` gate on every write (D-103 ambient PIN, no second prompt); `?entity_id` 400s stay honest on Policy/Scenarios/Insurance/Estate (untouched); `/accounts` added to all three overflow arrays + page-inset guard (1728) + sidebar-density (slot reserved); button anatomy §5.4 (icon+label, 1em glyph); base-currency affix (§14in-7); labels are SERVED labels verbatim (§12es-3). *(Not a decision — a checklist; listed so nothing is silently skipped.)* | **✅ ACCEPTED (checklist)** — all inherited standards apply to Accounts; carried into Phase 1/2 acceptance (§7). |

**Sign-off to start build:** ✅ SIGNED OFF (owner one-pass, 2026-07-16) — §9 has no open blocker · §3b
deltas approved · the §4 amendment (§9-3) resolved as a MasterSelect data-source extension (no new
component). **Phase 0 build authorised** (backend-first, 11 commits; evidence in §11).

---

## 10. VERIFY-FIRST RECORD (D-019)

*Read the engine before assuming shapes. All cites are `app/`-relative unless noted. Contradictions
resolved in CODE, not memory. `⚠` = a premise that diverged from reality (flagged to §3b/§9).*

### 10-1. Accounts + entities endpoints — what exists vs what D-064/D-065 need
- **Account model** `models/__init__.py:124-140`: `name` (120), `kind` (`String(40)`, default
  `"brokerage"`, **free at DB level**), `currency` (`String(3)`, default `"SGD"`), `institution`
  (`String(120)`, **nullable, free text**), `entity_id` (**FK→entities, nullable, indexed**),
  `cost_basis_method` (`String(16)`, default `"fifo"`). No `updated_at`, no soft-delete.
- **Entity model** `models/__init__.py:111-121`: `name` (default `"Household"`), `kind` (default
  `"self"`; vocab self/spouse/trust/company/other in-comment). FK `Account.entity_id → entities.id`,
  relationship `Entity.accounts ⇄ Account.entity`, **no cascade / no `ondelete`**.
- **Accounts CRUD** `routes/accounts.py`: `GET /accounts` (:31, untyped dict), `GET /accounts/list`
  (:38), `POST` (:50, auth), `PATCH` (:57, auth), `DELETE` (:67, auth). **All untyped `-> dict`** — no
  `response_model` stripping. Delete guard `services/accounts.py:139-148` blocks on **transaction count
  (incl. soft-deleted)**, **not holdings**.
- **⚠ `AccountIn` (`accounts.py:24-28`) omits BOTH `entity_id` AND `cost_basis_method`.** So D-064
  (entity assignment) and D-018 (cost-basis selector) — the two headline features — have **no write
  path**. → §3b reshapes (§9-4, §9-5).
- **Entities: read-only end-to-end.** Only `GET /entities` (:43). **No `POST/PATCH/DELETE`, no
  `EntityIn`, no delete-block** — entity write is unimplemented (grep of `app/` finds no
  `session.add(Entity(...))` outside the model). API-CONTRACT.md:74 records the CRUD as a **D-065 add**.
  → §9-6.

### 10-2. The `?entity_id` story — contradiction reconciled (per-endpoint reality)
- **FILTERS (15):** all flow through `entity_account_filter` (`services/portfolio.py:255-266`) →
  `model.account_id IN (SELECT accounts.id WHERE accounts.entity_id = :eid)`, applied at the
  `value_portfolio` chokepoint (`:406-409`) and in `GET /accounts` itself (`accounts.py:36`). Endpoints:
  `/accounts`, `/portfolio/{summary,performance,stats,attribution,attribution.csv}`,
  `/net-worth/statement`, `/portfolio/{liquidity,realised-gains,tax-lots,realised-gains.csv,tags,
  statements,statements.csv,cost-of-ownership}`. **None silently ignore it** — every declared param
  reaches a real filter.
- **REJECTS-400 (4 domains):** `reject_entity_id` dep on **all 8 Estate endpoints** (`estate.py:25-31`);
  inline guards on **Policy** `/policy/drift` (`policy.py:61-62`), **Insurance** `/insurance`
  (`insurance.py:47-48`), **Scenarios** `/portfolio/scenarios` (`portfolio.py:1001-1002` +
  `scenarios.py:54-55`). Reason: those domains have **no entity FK**; scoping = precise-looking meaninglessness.
- **What scoping filters:** holdings/txns have **no entity FK of their own** — entity is reached
  **through the account** (`account.entity_id`). Post Phase-4.1 migration **every account has an
  entity**, so filtering by the default "Household" id returns the whole portfolio; other ids scope to
  that entity's accounts.
- **No frontend consumer:** `frontend/src/` has **0 `entity_id`/`entityId` query callers** — the param
  is **dormant**; Accounts (or a future switcher) would be the first caller. **R-35** (planning) /
  **R-33** (policies) park per-entity as a **data-model change**, not a query param (`ROADMAP.md:45,47`).
  → §9-8: **no switcher invented**; entity is an account attribute.

### 10-3. `Account.kind` free text + `ACCOUNT_KINDS`; cost-basis; currency
- `ACCOUNT_KINDS = [brokerage, bank, retirement, wallet, property, manual, other]`
  (`services/accounts.py:24`); served `/refdata` `account_kind` (`refdata.py:156`).
- **Kind is validated by silent fallback, not rejection:** create coerces an invalid value → `brokerage`
  (`:114`); PATCH silently drops it (`:131`). → §9-9 (enforce).
- **Cost-basis:** `_COST_BASIS_METHOD = [fifo, average]` (`refdata.py:83`), served `cost_basis_method`
  (`:155`); model default `fifo` (`models:138`); **read by the engine** `tax.py:257`
  (contradicts the model's "nothing reads it" comment). **No write path** (⚠ omitted from `AccountIn`).
  → §9-5. **Served label bug: `fifo → "Fifo"`** (titleizer, no override) → §9-13.
- **Currency:** `SUPPORTED_CURRENCIES` (9, `config.py:18`), served `currency` (`refdata.py:153`).
  Account currency write = `upper()[:3]` with **no vocab check** (`accounts.py:115,133`) — vs strict
  `base_currency` enforcement (`config.py:115`). → §9-9.

### 10-4. Institution master scope — greenfield confirmed
- `accounts.institution` (`models:130`, migration `c8a035ade752:26`) and `insurance_policy.insurer`
  (`models:525`, `insurance.py:_FIELDS:142`) are **both free `String(120)`**. **No institutions table /
  model / FK anywhere.**
- **`/refdata` serves ONLY fixed vocabs** (`refdata.py:124-163`); its own docstring says masters are
  "served by their own endpoints" (`:128`) — but **no master router exists** (no
  `institutions.py`/`sector.py`/`masters.py`). **Sector** = free-text column (`models:151`); **Tag** =
  JSON list on `HoldingTag` (`models:592-598`) — **neither is a table with CRUD**. So this is the
  **first extensible master-with-CRUD** — no precedent to copy. → §9-1.
- **Insurance typeahead to supersede:** `Insurance.tsx:131-133` builds `insurers` = client-side distinct
  over `data.policies[].insurer`, fed to `TextInput`'s `suggestions` datalist (`:344-345`) — a
  convenience, not a shared master. → superseded by §9-1.
- **Merge:** behaviour specified (`MASTER-DATA:372-375` — fold + re-point both FK columns + delete
  FK-blocked); **matching/detection unspecified** for institutions (no threshold/normalization, unlike
  Tag). → §9-2 (user-driven, no fuzzy).

### 10-5. Default entity semantics
- Migration `f4a9c2b71e08_entities.py`: server-default name `"Household"` (:33); backfill creates one
  `Household/self` entity and assigns every account (`:46-52`) via `ORDER BY id LIMIT 1`. **No
  `is_default` flag; not renamable/deletable today** (no write routes). The **demo seed does not create
  any Entity** (`seed/demo.py` — the 3 demo accounts have **no `entity_id` set**), so a freshly seeded
  demo may have entity-less accounts until the migration/backfill runs — **the demo seed needs extending
  for this page** (Phase 1). → §9-7.

### 10-6. CSV import wiring — the seam
- `/portfolio/import/{csv,commit}` take optional `?account_id` (`portfolio.py:817,848`) →
  `_ensure_account` (`csv_import.py:428-438`): use it if it resolves; **else the first account; else
  auto-create `"Imported"/brokerage`**. Frontend import UI passes **no `account_id`**
  (`holdings.ts:186-192`; `ImportDialog` `Holdings.tsx:1213-1291`). Account picking exists only in the
  manual Add-transaction dialog (`Holdings.tsx:900`, `Select` over `GET /accounts`). → §9-12 (Accounts
  owns creation; flag the silent fallback as a Holdings follow-up).

### 10-7. Money on this page (D-105)
- `accounts_report` (`services/accounts.py:31-91`) **is the only per-account rollup** — groups
  `value_portfolio()` by `account_id`, includes empty accounts (`:62-65`), serves per account `{value,
  holdings, asset_classes, currencies, stale, low_confidence, last_activity}` + envelope `{base_currency,
  total, count, disclaimer}`. **`value`/`total` are raw floats, whole-unit rounded (`_f`, `:27`), no
  `*_display`, no per-account affix.** `/portfolio/holdings` carries **no account field**
  (`portfolio.py:128-154`); `/portfolio/summary` never groups by account. **Money IS shown → not
  counts-only (contrast Estate §9-3).** → §9-10 (served display strings + affix).

### 10-8. Review / Home seams — clean pre-cuts
- **Review** (`services/review.py:86-260`) emits **no account/entity signal** (grep empty); it counts
  holdings/instruments. The **shared `estate_signals` seam** (`review.py:154-157`) is the pattern any
  future account signal would follow — **none exists yet**. → no Review change needed; if an account
  signal is ever wanted it is a separate decision (not proposed).
- **Home** (`Home.tsx`) has **zero account/entity references**; the `/dashboard/home` aggregate was
  retired; each card reads its own reader. → no Home change.

### 10-9. SN-class vocabulary sweep + platform standards
- **Served strings/labels:** `account_kind` → Brokerage/Bank/Retirement/Wallet/Property/Manual/Other
  (titleized, correct); `entity_kind` → Self/Spouse/Trust/Company/Other (correct);
  **`cost_basis_method` → "Fifo"/Average — "Fifo" is WRONG** (needs override). Account responses serve
  **raw** `kind`/`institution`/`currency` (no `_display`) — the UI maps via `/refdata` labels (D-005),
  so the served-label-verbatim rule (§12es-3) applies. → §9-13.
- **GLOSSARY:** Account/Institution/Entity/Cost basis exist; **Cost-basis method / Account kind / Rollup
  / Merge missing.** → §9-13.
- **Platform standards inherited** (inset guard @1728, three overflow arrays, sidebar-density slot
  reserved, `[S]` gate D-103, entity_id 400s honest, button anatomy §5.4, base-currency affix,
  served-labels-verbatim). → §9-14 (confirm-only).

---

*END OF DRAFT — §9 ruled one-pass (owner, 2026-07-16). Phase 0 evidence follows in §11.*

---

## 11. PHASE 0 EVIDENCE (backend-first, one delta per commit)

*Filled per commit as Phase 0 lands. Each row: the RED cause proven fail-first → the GREEN that closed
it, with cites. Contract regen (`make api-contract-check`) and both suites' state reported at the end.*

| # | Commit (delta) | Decision | Fail-first RED (cause + cite) | GREEN (what closed it) | Contract |
|---|----------------|----------|-------------------------------|------------------------|----------|
| 1 | institutions table + typed CRUD | 9-1 | `test_institutions.py` RED — no `/institutions` route (405 on PATCH, KeyError `id` on POST) | `Institution` model + `services/institutions.py` (normalize/resolve-or-create/rename/FK-block delete) + typed router; 4/4 GREEN. First-seen-casing collapse ("DBS "/"dbs" → one row) proven. | regen ✅ 127→128 paths |
| 2 | merge endpoint (user-driven) | 9-2 | merge tests RED — no `/institutions/merge` route (405) | `POST /institutions/merge {survivor_id,duplicate_id}`: one txn re-points both FK cols (tolerant pre-commit-3) + deletes duplicate; same-id→400, missing→404; 6/6 GREEN. Referencing-row re-point proven in commit 3. | regen ✅ 128→129 paths |
| 3 | 3-step FK re-point migration + DROP both String cols | 9-1+F | `test_institution_migration.py` RED — write path didn't create master rows; delete not FK-blocked; merge re-pointed 0 | `Account`/`InsurancePolicy` swap String→`institution_id` FK + relationship; readers serve name via eager-loaded join; writers resolve-or-create; migration `b3e2f1a9c740` seed(both cols, first-seen)→FK→native DROP; demo seed folds insurers; 5/5 GREEN + isolated fold test + FK-block/merge-repoint now GREEN. Native ALTER (not batch) so child FKs untouched (24/24 db_migrate GREEN). Insurance delta note + suites re-run. | regen ✅ no shape change (untyped routes) |
| 4 | `AccountIn.entity_id` | 9-4 | `test_accounts_write.py` RED — PATCH/POST entity_id silently dropped (AccountIn omits it); nonexistent entity not rejected | `AccountIn.entity_id` (int\|None) + `_resolve_entity_id` FK-validate (honest 400); served in `_account_dict`; not-found→404 / validation→400 split; 2/2 GREEN | regen ✅ AccountIn request schema +entity_id |
| 5 | `AccountIn.cost_basis_method` + rebuild-on-change | 9-5 | `test_accounts_write.py` RED — method dropped by AccountIn; no restatement; realised gains static | `AccountIn.cost_basis_method` (fifo/average, `COST_BASIS_METHODS` single-sourced into /refdata); vocab→400; served in report+`_account_dict`; PATCH that CHANGES method on an account w/ txns → `rebuild_holdings_from_transactions` + `restatement` warning; proven on Demo Brokerage AAPL (FIFO 600 → avg 450, base total moves); 4/4 GREEN | regen ✅ AccountIn +cost_basis_method |
| 6 | `entity_kind` → /refdata, then Entity CRUD | H+9-6 | `test_entities.py` RED — no POST/PATCH/DELETE /entities (405) | `ENTITY_KINDS` single-sourced (`services/entities.py`) + served by /refdata (Amendment H, MASTER-DATA §2 note); `EntityIn`; CRUD w/ kind vocab→400; DELETE FK-blocked (service-level 400); §9-7 no Household special-casing (lowest-id renamable/re-kindable); guaranteed entity_id round-trip; 5/5 GREEN | regen ✅ 129→130 paths |
| 7 | kind/currency write enforcement (400) | 9-9 | `test_accounts_write.py` RED — invalid kind coerced to brokerage (200); "ZZZ" currency accepted (200) | `_validate_kind`/`_validate_currency` on create+update → out-of-vocab kind & unsupported currency both 400 (plain-language); "usd"→"USD" still ok; 7/7 GREEN | n/a (behaviour, no shape change) |
| 8 | `accounts_report` `*_display` + `base_currency` | 9-10 | `test_accounts_write.py` RED — report served raw floats only (no `value_display`/`total_display`) | per-account `value_display` + envelope `total_display` via `format_money_display` (base rollup, bare §12in-1; native codes ride `currencies` chips); whole-unit `_f` dropped (dead-code removed), `value`/`total` now 2dp; `base_currency` already served; 8/8 GREEN | n/a (untyped route, no shape change) |
| 9 | `GET /portfolio/holdings?account_id=` | 9-11+G | `test_holdings_account_scope.py` RED — unknown param ignored → scoped == all portfolio | `account_id` query filters the canonical reader's output on `h.account_id` (the `?symbol` precedent, filter-not-recompute); strict non-empty subset; unknown id → []; 2/2 GREEN. Reader half only — Holdings-page chip is Phase 1 (Amendment G) | regen ✅ +account_id param |
| 10 | GLOSSARY 4 terms + FIFO label override | 9-13 | `test_refdata_cost_basis_label.py` RED — served `fifo` label "Fifo" (titleizer) | `_VOCAB_LABEL_OVERRIDES["cost_basis_method"]["fifo"]="FIFO"` → GREEN; 4 terms (Cost-basis method · Account kind · Rollup · Merge) added to GLOSSARY.md **then** the popover mirror (parity 49/49 GREEN); Institution glossary row de-staled to the FK/master | n/a (refdata serves a free dict — value not shape) |
| 11 | 08-TECH-DEBT entry + CURRENT.md flip | 9-12 | n/a (recording, not a code delta) | 08-TECH-DEBT entry for the silent-first-account import fallback (`csv_import.py:428-438`, mis-attribution risk, Holdings follow-up); CURRENT.md flipped to §9 CLOSED / Phase 0 DONE / specimen next | n/a |

**Suites / gates (Phase 0 close, 2026-07-16):**
- **Backend `pytest`: 825 passed** (exit 0) — up from 803 at the start of Phase 0 (+22: institutions
  CRUD/merge, the isolated migration fold, entities CRUD, account write path, holdings account-scope,
  FIFO label). Ruff clean.
- **Frontend `npm run check` (run from `frontend/`): EXIT 0** — 234 passed (touched only
  `frontend/src/mocks/glossary.ts`; glossary-parity guard green).
- **`make api-contract-check`: green** — regenerated same-commit for every shape change
  (127 → **130 paths**: +`/institutions`, +`/institutions/merge`, +`/entities` write routes;
  `AccountIn` +`entity_id`/`cost_basis_method`; `/portfolio/holdings` +`account_id`).
- **Accepted-page touch (Amendment F):** Insurance `test_insurance_phase1` + `test_insurance_walk1` +
  `test_statements` **re-run GREEN**; `/insurance` still serves `insurer` (name via the join). Delta note
  in `page-insurance.md §16`. (The `*-smoke.spec.ts` live re-runs belong to the Phase-1 batch that swaps
  the Insurance typeahead for the MasterSelect — §9-3.)
- **DB migrations:** single alembic head (`b3e2f1a9c740`); `test_db_migrate` 24/24 (native ALTER fold,
  child FKs intact).

**STOP — Phase 0 complete. No specimen, no assembly this session; Phase 0a (geometry specimen + §9-3
MasterSelect-data-source ratification) is the next session.**

---

## 12. PHASE 0a — GEOMETRY GATE ✅ RATIFIED WITH CONDITION (owner, 2026-07-16)

*The static layout specimen + the §9-3 component ratification frame, authored so the owner could **ratify
the geometry BY LOOKING** before assembly (TEMPLATE §7; the page-home §12ho1-3 rule — a widget list is
not a layout). The owner walked the specimen at `/kitchen-sink` and **RATIFIED the geometry (2026-07-16)
with one condition (§12ac-1) and four acceptances (§12ac-2..5)** — recorded in §12ac below. **Phase 1 is
now UNBLOCKED.** The record of what was PROPOSED at the gate (§12-1..§12-4) is retained verbatim below the
ruling.*

### 12ac. GATE RULING — RATIFIED WITH CONDITION (owner, 2026-07-16)

The owner ratified the specimen geometry. The ⏸ PROPOSED status of §12 flips to **✅ RATIFIED WITH
CONDITION**. Five recorded rulings:

- **§12ac-1 (CONDITION — binds Phase 1 + guarded in Phase 2).** The accounts-table **Value column header
  carries the SERVED base currency** — it reads **`Value ({base_currency})`** (e.g. `Value (SGD)`) built
  from the reader's served `base_currency`, **NEVER hardcoded**. Rationale: a base-converted number under a
  per-row **Currency** column is ambiguous without the header naming the rollup currency; the Holdings
  header carries the served base already (that precedent). **Phase-1:** the header string is composed from
  `report.base_currency`. **Phase-2 guard:** a render test with a **non-SGD** base fixture asserts the
  header follows the served value (RED if hardcoded `SGD`) — the §9-10 served-value discipline extended to
  a header.

- **§12ac-2 (ACCEPTED as shipped — §12-3 flagged decision).** The **cost-basis label is rendered for
  every account** (bank/wallet rows included), because the model always carries a `cost_basis_method`
  value (default `fifo`); **fabricating a blank would be the dishonest option** (Guarantee 3). The
  owner-decision offered in §12-3 (show "—" for cash/bank, needing a served nullability signal) is
  **DECLINED** — the served value is shown verbatim ("FIFO"/"Average") on every row.

- **§12ac-3 (ACCEPTED as shipped — §12-3 flagged decision).** **RowMenu "View holdings"** is the
  Amendment-G P-1 linked-summary affordance on account rows. Ratified as the drill-down entry point; its
  live target (the Holdings-page URL account filter → clearable chip) is the Phase-1 deferred half.

- **§12ac-4 (ACCEPTED as shipped — §12-3 flagged decision).** **`StatusChip` is deliberately unused** on
  this page — accounts carry no status/severity axis (kind/currency/cost-basis are attributes, not
  states). Its absence is ratified as intentional, not an omission.

- **§12ac-5 (RATIFIED AS SHOWN — copy).** The following user-facing copy is ratified exactly as staged in
  the specimen and is now **protected copy** (changing any of it requires a new §-entry):
  1. the **page subtitle** ("…never a second figure.");
  2. **all three EmptyState wordings** (no accounts; no entities / only-Household; empty institution
     master);
  3. the **three dialog bodies** — the entity FK-block reason, the institution FK-block reason (with merge
     offered), and the **merge consequence line** (*"N accounts and M policies will move to {survivor}…"*).
  The merge consequence copy in particular is now protected copy: it is served-count-driven
  (tile-integrity), and any change to its wording needs a §-entry.

**Effect on Phase 1:** compose to the ratified geometry (§12-1..§12-4) with §12ac-1's served-header
condition wired, §12ac-5's copy rendered verbatim from the specimen, and §12ac-2/3/4 shipped as the
specimen showed. The Phase-2 suite carries the §12ac-1 served-header guard.

---

*The record below (§12-1..§12-4) is the PROPOSED specimen as staged at the gate, retained verbatim.*

### 12-1. §-geometry (PROPOSED)

A **Worklist** page (DESIGN-SYSTEM §3): three stacked cards, no overview/donut. **Two masters land
here**, so the two management cards flank the spine:

1. **Accounts DataTable — the page SPINE.** Columns: **institution · kind · currency · cost basis ·
   entity · value · ⋯ RowMenu**, with a **footer Σ totals row** (`total_display` + the base-currency
   affix once, §14in-7). Row actions (Edit / View holdings / Delete) live in the ⋯ `RowMenu` — never a
   wide action column (D-094 posture: bounded, client-side).
2. **Entities card (D-065)** — name · kind · account count + Add entity. `RowMenu` Edit / Delete (Delete
   **disabled** while accounts reference the entity — §9-6, honest not silent).
3. **Institution master card (D-008)** — name · referenced-by counts (accounts + policies) + Add
   institution + `RowMenu` **Rename / Merge / Delete** (Delete **disabled** while referenced — §9-1/§9-2).

Money is written **AS SERVED** (display strings, D-105); per-account value is the base-currency rollup
(§9-10); a non-base account carries its native code in the **Currency** column (§12in-1). Labels are the
**SERVED `/refdata` labels rendered verbatim** (§12es-3) — **"FIFO"** via the §9-13 override, the
account-kind + entity-kind titles.

### 12-2. Frames mounted at `/kitchen-sink` (bleed section, real 1440×724 content region)

- **Populated register** — 8 accounts across 5 institutions; mixed kinds (Bank/Brokerage/Retirement/
  Wallet), currencies (SGD base + USD/INR non-base), cost-basis methods (FIFO/Average). Footer
  **Σ = `1,643,550.00 SGD`** — **tile-integrity green** (equals the sum of the 8 value rows shown, the
  Estate precedent). Honesty: **one entity-less account** (bare em dash — nullable is real, §9-7); the
  default **"Household" entity as an ORDINARY row** (no crown, no special styling — D-029/§9-7); a **long
  hyphenated institution name that TRUNCATES** ("Standard Chartered Priority Banking–Singapore").
- **ALL-EMPTY registers** — usable from zero: accounts + institution-master `EmptyState` (reason + CTA);
  entities shows **only the migration's Household** row (ordinary).
- **§9-3 add-inline institution control** — `MasterSelect` wired to the DB-backed **institution** master
  (**mock-backed here** — kitchen-sink is static; the live POST proves in Phases 2/3a) + the
  `＋ Create new…` add-inline row. Ratifies the affordance's look/behaviour contract (no new component).
- **Entity delete FK-blocked** (§9-6) — staged dialog body: Delete disabled, honest served reason.
- **Institution delete FK-blocked → merge offered** (§9-1/§9-2) — staged dialog body, plain-language 400.
- **Merge dialog mid-flow** (§9-2) — survivor **"DBS"** ← duplicate **"DBS Bank"** (user-driven, no fuzzy
  auto-detect); the re-point consequence stated plainly: *"3 accounts and 1 policy will move to DBS…"*
  (the count matches the master table — tile-integrity).

Composed **ratified `ui/` only** (`DataTable` · `RowMenu` · `MasterSelect` · `Button` · `EmptyState` ·
`PageHeader` — all named in §4). `FooterRow` was exported from the `ui` barrel (it was already a
`DataTable` type; no component change). The staged dialog frames are **static bordered panels** (the
Estate roles-editor precedent) — a portal modal can't sit in a multi-frame gallery; the gate ratifies the
copy + affordance by looking, the live modals wire in Phase 1.

### 12-3. Geometry decisions made beyond §-geometry (flagged per the Estate §12es-1 precedent)

- **Cost-basis label shown for EVERY account, not only lot-holding kinds.** The `cost_basis_method` column
  carries the served label (FIFO/Average) on bank/wallet rows too, because the model always holds a value
  (default `fifo`) and hiding it would be a fabricated blank. **Owner: decide at the gate** whether a
  cash/bank account should instead show "—" for cost basis (would need a served nullability signal — not
  proposed here).
- **RowMenu "View holdings"** included on account rows as the P-1 linked-summary affordance (Amendment G).
  The live target (Holdings page URL account filter) is **Phase-1** work — here it is an inert menu item.
- **`StatusChip` not used** on this page (the plan left it optional; accounts have no status/severity
  axis — kind/currency/cost-basis are attributes, not states). Flagged so its absence is deliberate.

### 12-4. Gate evidence

- **Frontend `npm run check` (from `frontend/`): EXIT 0** — 234 Playwright passed (kitchen-sink overflow
  at 320/375/900/1366 × both themes green; tile-integrity green), lint/typecheck/tokens/unit green.
- **Rendered verification** — screenshotted at `/#/kitchen-sink` in **both themes**: spine columns,
  served labels ("FIFO"/"Average"), truncated long institution, entity-less em dash, footer
  **Σ = 1,643,550.00 SGD**, the two masters' counts consistent, and all six frames present.

**✅ RATIFIED WITH CONDITION (owner, 2026-07-16) — see §12ac above.** The geometry PROPOSED here was
walked at `/kitchen-sink` and signed off with one condition (§12ac-1, served Value header) and four
acceptances (§12ac-2..5). **Phase 1 is UNBLOCKED** — build record follows in §13.

---

## 13. BUILD RECORD — Phases 1 → 2 → 3a (2026-07-16)

*Phase 1 assembly + Phase 2 tests + the Phase-3a scripted pre-pass on a RESET, demo-seeded instance.
Green suites are the entry ticket, NOT acceptance — the owner walk (Phase 3b) is a separate session.*

### 13-1. Backend delta (Phase-1, backend-first) — institution referenced-by counts

The ratified geometry (§12-1 institution master card) and the merge consequence (§12ac-5, **served**
counts "not client-derived") both need per-institution reference counts, which `GET /institutions`
did **not** serve (only `{id,name}`). `InstitutionOut` gains `account_count` + `policy_count`;
`list_institutions` groups a COUNT over **both** FK tables (`accounts` + `insurance_policy`) in one
pass per table. **RED before:** `test_institution_list_serves_referenced_by_counts` KeyErrors on the
`{id,name}`-only shape → GREEN. Contract regenerated same-commit (drift green). Commit `78aac5c`.

### 13-2. Phase 1 — page assembly (commit `03e629e`)

- `frontend/src/api/accounts.ts` — typed client: accounts CRUD, entities CRUD, institutions CRUD +
  merge; served shapes verbatim; `institution`/`insurer` are **NAME** strings (resolve-or-create).
- `Accounts.tsx` + `.css` to the ratified frames. The rollup reader (`/accounts`) omits `entity_id`,
  so the spine **joins `/accounts/list`** for it (and the editable attrs); the null-id
  "account-less holdings" bucket renders read-only. **§12ac-1 CONDITION wired:** the Value header is
  `Value (${report.base_currency})`, composed from the served base. Labels render via
  `useLabelFor` (served `/refdata` labels verbatim — FIFO via the §9-13 override). Footer Σ =
  `total_display` + the base affix once. EmptyStates + FK-block dialog bodies + merge consequence are
  the §12ac-5 protected copy, rendered verbatim with **served/real** counts.
- **[S]-gated editors** (ambient PIN, D-103): account Dialog `size="lg"`; the **§9-3 data-source
  extension goes LIVE** — `MasterSelect` gains an `options` prop so the institution select reads the
  **DB-backed master**, and Create-new POSTs to `/institutions` (parent `onChange`) then re-selects
  the canonical row. Entity editor, institution rename, user-driven merge.
- **§9-5 cost-basis change warning:** editing `cost_basis_method` on an account **with history**
  (`last_activity != null`) interposes a restatement ConfirmDialog **before** the PATCH — **wording
  PROPOSED** ("…realised and unrealised figures will change…"), the owner ratifies it at the walk.
- GlossaryTerm [Help] on the **Account kind** + **Cost-basis method** editor labels (parity green).
  Merge/Rollup appear only as an action label / dialog title (strings) — glossary-defined, not
  surfaced as on-page popovers; revisit at the walk if the owner wants them.

**Deferred halves (commit `688b224`):**
1. **Holdings account chip (Amendment G):** "View holdings" → `#/holdings?account=<id>`; Holdings reads
   the param (`useSearchParams`), fetches the **scoped reader** (`getHoldings(accountId)`), shows a
   clearable chip. Dated delta note in `page-holdings.md`.
2. **Insurance insurer → MasterSelect over the master** (superseded the typeahead). Dated delta note in
   `page-insurance.md §16a`.
3. **Demo seed (§10-5):** entities (Household + Rajan Family Trust + Meera Iyer) + institutions wired to
   every account (Saxo Markets / Citibank Singapore / Citibank — a near-duplicate merge pair with a real
   reference); demo `cash` kind → `bank` (was out of `ACCOUNT_KINDS`). `reset-demo-data.sh` re-seeds via
   `seed_demo_data` automatically. New `test_demo_seed_accounts.py`.
4. Nav flip `/accounts` → `built:true`; route wired; `/accounts` into **all three** `overflow.spec.ts`
   arrays; two chrome/shell tests repointed to `/reports` as the unbuilt fixture.

**Copy-hygiene deviation (recorded):** the ratified subtitle's "…the holdings **reader**…" tripped the
governance-speak guard (`test_copy_hygiene.py` — "reader" is architecture-speak). Reworded to "…a linked
summary of **your holdings** — never a second figure." The ratified tail (§12ac-5) is preserved; the
change is protected-copy-adjacent, **owner confirms the reworded subtitle at the walk**. The specimen
`AccountsMockup.tsx` was reworded identically for parity.

### 13-3. Phase 2 — tests (commit `977b27e`; `npm run check` EXIT 0)

`Accounts.test.tsx` (9) — each guard proven:
- **§12ac-1** — a **non-SGD (INR)** fixture: the header reads `Value (INR)` and `Value (SGD)` is absent
  (**RED if hardcoded**).
- **served labels** — the FIFO cell renders "FIFO", never the titleizer's "Fifo".
- **em-dash** entity-less cell; **footer Σ** == `total_display` == Σ rendered value rows (tile-integrity).
- **EmptyStates**; **entity + institution FK-block bodies verbatim** (§12ac-5) with served counts + merge
  offered; **merge consequence** renders the duplicate's **served** counts and calls the endpoint once
  with `(survivor, duplicate)`; **live master round-trip** (Create-new POSTs, the row appears) +
  **FAIL-FIRST** (a rejecting POST → the institution is NOT added).
`Holdings.test.tsx` (+1) — Amendment-G `?account=` scopes the reader; chip param → chip → clear (unscoped).

**Suites:** `npm run check` (from `frontend/`) **EXIT 0** — lint · typecheck · tokens · **239 Vitest** ·
**246 Playwright** (overflow/inset/tile-integrity incl. `/accounts` at 320/375/900/1366 × both themes).
Backend `pytest`: **829 passed** (+2: institution counts, seed wiring); `test_copy_hygiene` 70 green;
`make api-contract-check` green (130 paths; the institution counts are a field add on `InstitutionOut`).

### 13-4. Phase 3a — scripted pre-pass (`e2e/smoke/accounts-smoke.spec.ts`, commit `6d31d4a`)

DEV-ONLY (`testIgnore: **/smoke/**`), driven against a **RESET, demo-seeded** live instance
(backend 127.0.0.1:8321 + frontend 127.0.0.1:5173), **both themes × 320/375/900/1366**. All 13 parts
GREEN, **0 console errors**:

| Part | What it drove | Result |
|------|---------------|--------|
| 1 | seeded register (3 accounts, 11 institutions, 3 entities; base SGD) | ✅ |
| 2 | §12ac-1 — Value header follows the served base: `Value (SGD)` | ✅ |
| 3 | tile-integrity — footer Σ `796,168.86` == Σ rendered value rows | ✅ |
| 4 | served label — "FIFO" present, "Fifo" absent (case-sensitive) | ✅ |
| 5 | add account with an **inline-created institution** (LIVE POST to `/institutions`) | ✅ |
| 6 | cost-basis change on the seeded account **with transactions** → warning → rebuild | ✅ |
| 7 | delete the smoke account (the account row clears; the institution stays in the master) | ✅ |
| 8 | entity add/rename; Household delete correctly **FK-blocked** (ratified body) | ✅ |
| 9 | institution rename + a **REAL merge** (Citibank → Citibank Singapore, re-points a real account) | ✅ |
| 10 | Amendment-G drill-down: "View holdings" → `?account=` chip → clear | ✅ |
| 12 | containment at 320..1366 — no cell clips WITHOUT truncation (ellipsis is honest, §7) | ✅ |
| 13 | both themes × 4 breakpoints — 0 h-overflow, single vertical scroll region | ✅ |

**Note (Part 6):** the base **total** is unchanged by the restatement (`796,168.86 → 796,168.86`) — a
cost-basis method change moves **realised/unrealised gains**, not the current market value; the live
evidence is the warning firing + the served restatement message (the realised-figure movement is pinned
by the backend fail-first test, §11 commit 5). The **containment guard** correctly excepts
`lf-table__td--trunc` cells: a long institution name (e.g. "Chubb Insurance Singapore") truncates with an
ellipsis at 320px — that is the ratified behaviour (§7 "long names truncate, not overflow"), not a clip.

**Touched accepted-page smokes re-run GREEN:** `insurance-smoke` ✅ (drives the insurer MasterSelect
against the live master), `net-worth-smoke` ✅, `portfolio-smoke` ✅. Two **cold-boot flakes** (a one-time
net-worth 500 and a portfolio attribution-label timeout on the **first** request after a reset) **cleared
on retry** — all core endpoints return 200, Portfolio is untouched by this branch, so neither is a
regression. Holdings has **no** dedicated smoke; its Amendment-G chip is covered by accounts-smoke Part 10
+ the `Holdings.test.tsx` unit round-trip.

### 13-5. STOP — AWAITING OWNER WALK (Phase 3b, next session)

Pre-pass GREEN is the entry ticket, **not** acceptance. **Walk URL:** `http://127.0.0.1:5173/#/accounts`
on the **reset, demo-seeded** instance (Household + Rajan Family Trust + Meera Iyer; Saxo Markets /
Citibank Singapore / Citibank + 8 seeded insurers; the Citibank/Citibank-Singapore merge pair intact).
**Judgment items for the owner:** the §9-5 restatement wording (PROPOSED); the reworded subtitle
(copy-hygiene, §13-2); whether Merge/Rollup want on-page [Help] popovers. **Do NOT self-certify; do not
start 3b.**

---

## 14. OWNER WALK — BATCH 1 (owner, 2026-07-16)

*Findings from the Phase-3b walk of `/#/accounts` on the reset, demo-seeded instance. Everything else on
the page is accepted **contingent on this batch**. Fixed + re-verified below; the owner **re-walks** —
not self-certified. RED→GREEN per fix; the **journey-guard RED** is the headline.*

### §14ac-1 — BUG (+ a gate miss): the accounts table has NO Name column

The spine renders institution · kind · currency · cost basis · entity · value — but **never the
account's own name** (the row's identity). An institution-less account is unidentifiable ("—" ·
Brokerage · INR). The ratified geometry (§12-1) led with **institution**, and the gate (§12) never
caught that a worklist row must show *what it is*. **Fix:** a leading **Name** column (§14ac-5 makes it a
link). Lesson: a management table's first duty is to identify its row.

### §14ac-2 — BUG (a green guard lied): "View holdings" — the JOURNEY was never tested

RowMenu **"View holdings"** was observed arriving at Holdings **unfiltered**. Phase-2's guard tested the
**destination** (Holdings *given* `?account=` → chip + scoped) but **never the journey** (the real
click). **Root cause (proven by repro, not the suspected hash-parse failure):** the click navigated via a
**manual `window.location.hash` write** (`frontend/src/routes/Accounts.tsx:361`). The hash IS placed
correctly (`#/holdings?account=3`) and `useSearchParams` does read it — but bypassing react-router's
navigation makes Holdings **mount with `accountFilter=null` on the first render** (`Holdings.tsx:103`), so
`reloadCore` (`Holdings.tsx:187`, keyed on `accountFilter`, `:202`) fires an **UNFILTERED**
`getHoldings()` that races the corrected scoped fetch. Repro request order was deterministically
`ALL, ALL, SCOPED, SCOPED` — the unfiltered fetch always fires, and its response can win, rendering all
holdings under a "filtered" chip. **Fix:** navigate through react-router (`useNavigate`) via the shared
URL builder (§14ac-5) so Holdings mounts with `?account=` present on render 1 → **only scoped fetches, no
race**. **Lesson (mechanised in TEMPLATE §7):** *a cross-page affordance is guarded as a JOURNEY — the
test clicks the real control and asserts the destination state; a destination-only guard can be green
while the link is broken.*

### §14ac-3 — OWNER DIRECTIVE: the account filter scopes transactions too

The Holdings account chip must scope **both** the holdings table **and** the transactions table.
`GET /portfolio/transactions` takes only paging/sort/filter today (no `account_id`) — a **backend delta**
(`?account_id=`, same chokepoint as holdings), then the ONE chip scopes both; clearing unscopes both.

### §14ac-4 — SCOPE RECORD: entity/institution filtered views → R-35

Entity- and institution-level filtered views are an **owner realization (2026-07-16)**, NOT batched here.
Per the §9-8 ruling (entity is an account attribute, not a page filter; `?entity_id` stays dormant), a
pull-forward is **R-35 activation with its own plan file**. Recorded into **R-35's scope sketch** in
`ROADMAP.md` (§14ac-4), not built this batch.

### §14ac-5 — OWNER ADDITION: the Name cell is a hyperlink to the same filtered Holdings destination

The account **Name** cell links to the **same** filtered Holdings URL as "View holdings" (the
Holdings-symbol → Instrument-Detail precedent). Both affordances consume **ONE shared URL builder**
(`holdingsForAccount(id)`) — a single source for the destination href — so the two entry points can never
silently diverge (two hand-built hrefs to one destination is how one rots).

### §14 — FIX RECORD (RED → GREEN) + STOP

**Backend delta (§14ac-3, backend-first).** `GET /portfolio/transactions?account_id=` — scoped at the
**same WHERE `conds` chokepoint** the count + window both use (`app/api/v1/routes/portfolio.py:462`), so
`total` / "Showing X–Y of Z" stay honest under the filter. Fail-first
(`test_transactions_scoped_by_account_id`): the ignored param today → scoped total == full total → RED →
GREEN. Contract regen same-commit (drift green).

**Frontend.**
- **Shared URL builder** `frontend/src/nav/holdingsLink.ts` → `holdingsForAccount(id)` = `/holdings?
  account=<id>` — the ONE source both entry points consume (§14ac-5).
- **§14ac-1 + §14ac-5 Name column, leading** (`Accounts.tsx`): Name · Institution · Kind · Currency ·
  Cost basis · Entity · Value(base). Name renders as a **`<Link>`** to `holdingsForAccount(r.id)` (the
  Holdings-symbol link precedent, `.acct__namelink`), truncating with a `title`. The account RowMenu is
  re-keyed by **name** (the row's identity). Editor already captured name (`AccountDraft.name`,
  `Accounts.tsx` openAdd/openEdit).
- **§14ac-2 journey fix:** "View holdings" now calls `navigate(holdingsForAccount(r.id))` (react-router)
  — Holdings mounts with `?account=` on render 1, so **only scoped fetches fire, no unfiltered race**.
- **§14ac-3:** the Holdings chip scopes **both** tables (`getTransactions({accountId})`), scope-change
  resets the ledger to page 1, clear unscopes both.

**Journey guards — the headline (`e2e/smoke/accounts-journey-smoke.spec.ts`).** Click the REAL controls,
assert scoped arrival (chip + both tables). Proven **RED on the pre-fix build** (a throwaway probe on the
restored pre-fix files):

| Control | Pre-fix (RED) | Post-fix (GREEN) |
|---|---|---|
| RowMenu "View holdings" | `holdings = ALL,ALL,SCOPED,SCOPED` (unfiltered fetch fires), `txns = ALL,ALL` | `holdings = SCOPED,SCOPED`, `txns = SCOPED,SCOPED`; scopedH 1/14, scopedT 1/10 |
| Account **Name** link | (no Name column existed — §14ac-1) | same scoped arrival via the shared builder |
| Clear chip | (transactions never scoped) | both tables refetch **unscoped** |

**Root cause named (mechanism actually shipped).** Not a hash-parse failure — the hash `#/holdings?
account=3` is correct and `useSearchParams` reads it. The manual `window.location.hash` write made
Holdings mount with `accountFilter=null` on render 1, firing an unfiltered fetch that raced the scoped
one. React-router navigation via the shared builder mounts scoped on render 1 → the unfiltered fetch is
gone. Lesson mechanised in **TEMPLATE §7** (journey guards).

**Re-verify (this batch):** `npm run check` (from `frontend/`) **EXIT 0**; backend `pytest` **831
passed** (+2 transactions scope); `make api-contract-check` green (transactions gains `account_id`);
`accounts-smoke` 13/13 + `accounts-journey-smoke` 2/2 + `portfolio-smoke` GREEN, **0 console errors**;
Holdings delta-note addendum + ROADMAP R-35 scope sketch recorded.

### §14ac-6 — ✅ ACCEPTED (owner, live re-walk, 2026-07-16)

The owner **re-walked both journeys live** on the reset, demo-seeded instance and **ACCEPTED the page**.
Everything that was accepted contingent on batch 1 (§14ac-1..5, FIXED + re-verified) is now unconditional.
**§14 CLOSED; the milestone is closed.** No ⏸ remains anywhere on the page.

**The two carried judgment items are RATIFIED AS SHIPPED by this acceptance:**
- **§9-5 cost-basis restatement wording** (PROPOSED in §13-2) — the ConfirmDialog interposed before a
  method-change PATCH on an account with history reads *"…realised and unrealised figures will change…"*
  → **RATIFIED AS SHIPPED**. This is now protected copy (§12ac-5 discipline): a change needs a new
  §-entry.
- **The reworded subtitle** (copy-hygiene rewrite in §13-2 — *"…a linked summary of your holdings — never
  a second figure."*, replacing the "reader" wording that tripped `test_copy_hygiene`) → **RATIFIED AS
  SHIPPED**, extending the §12ac-5 protected-copy tail. The specimen `AccountsMockup.tsx` carries the
  identical wording (parity).
- On-page [Help] popovers for Merge / Rollup were **not** requested at the walk — they stay glossary-defined
  action-label/dialog-title strings (as shipped, §13-2). No change.

**The batch-1 journey-guard RED proof (§14ac-2) stands as the permanent record** — a cross-page affordance
guarded as a journey (`accounts-journey-smoke.spec.ts`), mechanised in TEMPLATE §7. The four
PROPOSED→RATIFIED items and the central acceptance-log entry are recorded in §15 + `RATIFICATION.md §6`.

**Milestone closed — owner-accepted, not self-certified.**

---

## 15. RETROSPECTIVE — strike-check first, then MECHANISE (2026-07-16)

*The close ritual: strike-check every §9 / §12 / §14 item against the shipped diff FIRST (a claim is not a
change — page-policy §13-2), so nothing was recorded-but-not-landed; THEN fold each lesson into a mechanism,
from the evidence, not memory.*

### 15-1. Strike-check — every §9 / §12 / §14 item landed (verified against the diff, not the plan prose)

- **§9 (14 items) — all shipped, backend-first, evidence per commit in §11.** §9-1/2/F institution master +
  merge + fold-then-drop across **both** FK columns (`c9a4c08`/`e2778a2`/`22c9c52`); §9-4 `AccountIn.entity_id`
  (`79e93f9`); §9-5 `cost_basis_method` + rebuild-on-change (`1a34a02`); §9-6/H entity_kind→/refdata + Entity
  CRUD (`0f7ffaa`); §9-9 kind/currency 400-enforcement (`e674b11`); §9-10 served `*_display` + affix
  (`37c55ff`); §9-11/G `?account_id=` reader (`c211e93`); §9-13 4 terms + FIFO override (`a13f360`); §9-12
  08-TECH-DEBT recording (`f918f61`). §9-3/8/14 were resolution/confirm items (no code) — §9-3 landed as the
  live MasterSelect data-source extension in Phase 1.
- **§12 gate (RATIFIED WITH CONDITION) — all landed.** §12ac-1 served Value header wired + guarded with a
  non-SGD fixture (§13-3); §12ac-2/3/4 shipped as the specimen showed; §12ac-5 protected copy rendered
  verbatim.
- **§14 walk — all five findings FIXED + re-verified, then ACCEPTED (§14ac-6).** §14ac-1 Name column;
  §14ac-2 journey fix (RED proof stands); §14ac-3 transactions `?account_id=`; §14ac-4 R-35 scope sketch
  (recorded, not built); §14ac-5 shared URL builder.
- **No silent no-ops.** Every ratified backend VALUE carries a same-batch code test (the FIFO label override,
  the rebuild-on-change, the 400-enforcement) — the page-review §13 rule held.

### 15-2. Lessons MECHANISED (each lands as a mechanism, from the evidence)

1. **The Name-column gate miss (§14ac-1) → a TEMPLATE §7 specimen rule.** The ratified geometry led with
   **institution** and neither the §12 gate nor the pre-pass caught that the spine **never rendered the
   account's own name** — an institution-less account was unidentifiable ("—" · Brokerage · INR). The gate
   artefact modelled the box but not the row's **identity**. **Mechanism (TEMPLATE §7):** *a table specimen
   must render the row's IDENTITY column, and its honesty cases must include a row identifiable ONLY by that
   column* (the institution-less account is exactly that row — it would have failed the gate by looking).
2. **The journey-guard lesson is ALREADY mechanised — referenced, not re-landed.** §14ac-2 (a cross-page
   affordance is guarded as a JOURNEY: click the real control, assert the destination STATE — a
   destination-only guard can be green while the link is broken) was folded into TEMPLATE §7 in batch 1.
   Cited here; not duplicated.
3. **Enforcing a vocab surfaces latent invalid seed data (evidence, not a new rule).** §9-9's kind-enforcement
   turned the demo seed's out-of-vocab `cash` kind from a silent coercion into a 400 — caught in Phase 1 and
   fixed to `bank` (§13-2). The honesty enforcement did its job on the platform's own fixtures; recorded as a
   worked example of the §9-9 precedent, no new mechanism needed.
4. **One destination, one URL builder (§14ac-5) — a worked instance of the centralization rule.** Two
   hand-built hrefs to the same filtered-Holdings destination is how one rots; `holdingsForAccount(id)` is the
   single source both the Name link and "View holdings" consume. Instance of the existing rule, recorded.
5. **Make the push STRUCTURAL → a TEMPLATE close-ritual step.** The whole v2 rebuild sat **unpushed** on the
   local trunk (255 commits ahead of `origin/main` at this close). Durability is part of closing, not an
   afterthought. **Mechanism (TEMPLATE §8 close ritual):** *close-out commits are pushed to the remote before
   the owner re-uploads* — and this session ends with `git push`.

*The retrospective's own discipline — strike-check the diff before writing the lesson — is why §15-1 lists
commit hashes, not adjectives.*
