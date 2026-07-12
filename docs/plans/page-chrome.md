# page-chrome.md — Global chrome (app shell) build plan

**Status: PLAN ONLY — owner reviews before build** (drafted 2026-07-11). The chrome
is the **shell that wraps every page**, not a content page — so this plan adapts
`TEMPLATE-page-build.md`: it has no single route/ownership of figures; it composes
navigation + global controls + banners + the lock gate, and integrates the four page
templates. Derived from the specs with section refs; open blockers in §9 — build does
not start until they clear.

---

## 1. IDENTITY

| Field | Value | Spec ref |
|-------|-------|----------|
| Name | Global chrome (app shell) | IA §3, DESIGN-SYSTEM §5.5 |
| Route | none — wraps all routes (`main.tsx` shell around `<Routes>`) | — |
| Nav group | n/a (it *is* the nav) | IA §3 |
| Page template | n/a — the **shell** into which the four templates render | DESIGN-SYSTEM §3/§5.5 |
| One-line purpose | Sidebar nav (D-043) + top bar (D-066) + lock gate + banners, composed once around every page | IA §3, IA "Global chrome", DESIGN-SYSTEM §5.5 |

**Composed, not per-page (D-066).** Every element here lives in ONE shell; pages
never re-implement chrome.

---

## 2. OWNERSHIP TABLE

**The chrome owns UI STATE, not figures.** Owns: nav structure, the active
route highlight, per-device display axes (theme/density/contrast/motion, D-078),
rotation on/off (D-044), lock state. **Summarises** (via canonical readers, never
recomputed):

| Summary shown | Canonical source | Reader reused | Link |
|---------------|------------------|---------------|------|
| StaleBanner ("N stale") | Portfolio/summary reader (`has_stale`) | existing summary reader | → Pricing Health |
| UpdateBanner ("vX available") | version check (respects no-egress) | version endpoint (§3b) | → Settings/About |
| DemoBadge | demo-data flag | settings/status | — |
| Clock | device timezone (Settings, D-013) | settings | — |

**Owns nothing content.** Banners/badge are status summaries; the nav owns no data.

---

## 3. API SURFACE

### 3a. Consumed (already in the frozen contract)

| Method + path | Purpose |
|---------------|---------|
| `POST /auth/set-pin`, unlock/session endpoints | LockScreen gate (D-002) — verify against SECURITY-BASELINE |
| `GET /portfolio/summary` (`has_stale`) | StaleBanner signal |
| settings read/write (display, timezone, rotation) | top-bar controls + Clock; rotation **server-persisted** (D-017/D-078) |

### 3b. Contract deltas (BUILD BACKEND-FIRST — likely)

| kind | Endpoint | Decision | Why |
|------|----------|----------|-----|
| verify/add | **version-check** (respects no-egress: zero outbound when enabled) | D-066/D-075 | UpdateBanner. Confirm it exists; if not, add it + the no-egress guard. |
| verify | rotation config (page set + interval), server-persisted | D-044/D-017/D-078 | Confirm the settings shape exists. |
| verify | lock/unlock session contract | D-002 | LockScreen — pin against SECURITY-BASELINE. |

---

## 4. COMPONENTS

*Most chrome pieces are **not in the ratified §5 inventory yet** — DESIGN-SYSTEM
§5.5 describes them but the frontend only has `DisplayControls`. Each new component
is a **DESIGN-SYSTEM amendment** (new components forbidden without one — §9).*

| Component | Role | In inventory? |
|-----------|------|---------------|
| **Sidebar** | 6 fixed groups (D-043), active-route highlight, not reorderable | **NO — amend** |
| **TopBar** | hosts display controls + rotation toggle + Clock + DemoBadge + Detail toggle | **NO — amend** |
| **DisplayControls** | theme/density/contrast/motion — **move INTO the TopBar** | exists (relocate) |
| **StaleBanner** | "N stale" → Pricing Health | **NO — amend** |
| **UpdateBanner** | version available; **zero calls under no-egress** | **NO — amend** |
| **DemoBadge**, **Clock** | demo flag; timezone clock | **NO — amend** |
| **LockScreen** | PIN gate; reuses ConfirmDialog PIN pattern? | **NO — amend** |
| Toast/Dialog/etc. | already ratified; reused | yes |

**Layered cards / scroll / popover rules (D-100/D-101/§6)** apply to any chrome
panels. The **four page templates** render inside the shell's main region.

---

## 6. DECISIONS IN FORCE

| Decision | What it requires here |
|----------|-----------------------|
| **D-043** | 6 fixed sidebar groups, guessable names (P-4), NOT reorderable; nav-customization removed. |
| **D-066** | Chrome composed once; theme/density/contrast/motion in the top bar; StaleBanner/UpdateBanner/DemoBadge/Clock/rotation live here. |
| **D-044** | Rotation toggle in the top bar; config server-persisted; skips errored/empty pages. |
| **D-040** | The Detail toggle leaves the top bar but **only Home branches on it**. |
| **D-075/D-060** | **No-egress**: with the toggle on, the UpdateBanner/version-check makes **zero** outbound calls. |
| **D-002** | LockScreen is an access lock (PIN), not encryption; per SECURITY-BASELINE. |
| **D-078** | Display axes are per-device (localStorage); rotation is server-persisted (not localStorage). |
| **D-045** | First-run checklist replaces PersonaOnboarding (base ccy, tz, PIN, provider, no-egress) — see §9 (scope). |
| **D-067 / P-6** | The **Ask panel** is chrome per §5.5 but rides the AI pipeline — **DEFERRED to the AI-surfaces milestone** (like the Instrument Detail explainer); shell leaves a slot, D-067 intact (§9). |
| **D-042/D-022/D-056** | Route redirects: `/snapshot`→`/net-worth`, `/planning`→`/cash-flow`, `/global` removed. |

---

## 7. ACCEPTANCE CRITERIA

- [ ] **Sidebar**: 6 groups in fixed order (D-043), active route highlighted, guessable names; no reorder control.
- [ ] **Top bar** hosts theme/density/contrast/motion (moved from the page), rotation toggle, Clock, DemoBadge, Detail toggle.
- [ ] **StaleBanner** shows only when `has_stale`, links to Pricing Health; hidden otherwise (honest).
- [ ] **UpdateBanner** respects no-egress: **network trace shows zero outbound calls** when the toggle is on (D-075).
- [ ] **LockScreen** gates the app on a PIN install; a no-PIN install is unaffected (D-002).
- [ ] **Route redirects** (`/snapshot`, `/planning`, `/global`) behave per D-042.
- [ ] **Rendered layout verification** (1366 & 1920 + a narrow width, both themes + high-contrast): sidebar collapse behaviour, top bar wrap, banners.
- [ ] **Both densities/themes/contrast**; interactive open states verified in both themes.
- [ ] **The four templates** render correctly inside the shell (a page from each variant).

---

## 8. BUILD PHASES

- **Phase 0 — Contract deltas (§3b):** verify/add version-check (+ no-egress guard), rotation config, lock/unlock; regenerate contract same commit.
- **Phase 0a — §5 amendments:** ratify the new chrome components at `/kitchen-sink` before assembly. **✅ RATIFIED 2026-07-11 (see §10).**
- **Phase 1 — Shell assembly: ✅ DONE (`93b717c`).** `AppShell` composes Sidebar + slim TopBar + status strips + lock gate once around every route (`AppRoutes`); kitchen-sink stays outside. `DisplayControls` moved out of pages into the TopBar. Redirects wired (`/snapshot`→`/net-worth`, `/planning`→`/cash-flow`, `/global` removed); unbuilt routes → honest `NotBuilt`. **C-3:** patched the missing no-egress guard on `GET /system/version-check` (zero outbound under no-egress) + backend network-trace acceptance test; summary gained `stale_count`.
- **Phase 2 — Tests: ✅ DONE.** Shell integration (`AppShell.test.tsx`, 7): chrome composed once; a page from each of the four templates renders inside the shell; lock gate; UpdateBanner-on-update; redirects; NotBuilt fallback. Backend C-3 network-trace test. **Frontend 79 tests · backend 479 · drift/typecheck/lint/contract all green.**
- **Phase 3 — Owner acceptance walk (LIVE): ⏳ PENDING — the owner drives this.** Not self-certified. Owner drives the real app (both themes + high-contrast + a narrow width); each finding → numbered §-entry, re-verified live.

---

## 9. NEEDS DECISION — ALL RESOLVED (owner, 2026-07-11)

| # | Item | Resolution (owner, 2026-07-11) |
|---|------|--------------------------------|
| C-1 | **New chrome components** not in the ratified inventory | **Authorized** — author all seven (Sidebar/TopBar/StaleBanner/UpdateBanner/DemoBadge/Clock/LockScreen) as PROPOSED; owner ratifies at `/kitchen-sink` in **Phase 0a before shell assembly**. |
| C-2 | **Ask panel (D-067)** rides the AI pipeline | **Deferral confirmed** — same call as the Instrument Detail explainer; shell **reserves a slot**, D-067 recorded **pending, not dropped**. |
| C-3 | **Version-check endpoint + no-egress guard** | **Proceed** — endpoints already exist (`system/version-check`, `system/update-status`). **Verify both make zero outbound calls under no-egress + add the network-trace acceptance test**; patch only if the guard is missing. Not a new-endpoint delta. |
| C-4 | **First-run checklist (D-045)** scope | **Accepted** — checklist is **its own small plan after the shell**; chrome reserves the **first-run gate slot only**. |
| C-5 | **LockScreen ↔ session/PIN contract** | **Reconcile as proposed** against SECURITY-BASELINE (`auth/set-pin`, `auth/unlock`, `auth/lock`, `auth/state` exist). **Owner sub-decision (D-103): purge-PIN NEVER binds to the unlock session — purge always demands fresh PIN, regardless of lock state.** Recorded in SECURITY-BASELINE §3 + DECISIONS D-103. |
| C-6 | **Sidebar collapse / responsive behaviour** | **Approved (D-102)** — **off-canvas/collapsible below laptop width with a top-bar toggle; fixed at laptop+**. Added to INFORMATION-ARCHITECTURE §3 (gap closed). |

---

**Sign-off to start build:** ✅ C-1..C-6 resolved (owner 2026-07-11). §3b reduces
to verification (C-3 endpoints exist; C-5 auth surface exists). **Proceeding: Phase
0a (author the seven components + kitchen-sink specimens), then PAUSE for owner
ratification** before shell assembly. Ask panel deferral (C-2) recorded; D-102 (IA)
and D-103 (SECURITY-BASELINE) recorded.

---

## 10. PHASE 0a — RATIFIED (owner, 2026-07-11) ✅

**Phase 0a is RATIFIED.** Kitchen-sink look passed: the icon toggles (stateful-glyph
rule, DESIGN-SYSTEM §5.5) and the LockScreen blur+scrim verified **illegible in both
themes**; `☰` reserved and collision-free at narrow width. The seven chrome components,
the stateful-glyph rule, and the LockScreen blur are ratified as committed
(`acf2d1a` · `77a355e` · `f0f4419`). Build proceeds to Phase 1 (shell assembly).

Full record of what was built + amended (kept as build history):

### 10a. Build + amendment history (RATIFIED)

The seven chrome components are authored as **PROPOSED** in `frontend/src/components/ui/`
and staged at `/kitchen-sink`. DESIGN-SYSTEM §5.5 carries the chrome-component inventory
table. `NAV_GROUPS` (`ui/nav.ts`) encodes the D-043 six groups verbatim from IA §3, each
`NavItem` with a `built` flag. **No shell assembly, no router wiring, no backend change
yet** — Phase 1 does that after re-ratify.

**Owner amendments applied (2026-07-11):**
1. **TopBar recomposed** — slim (~48px) calm bar; display axes + rotation + Detail are
   **icon-only** buttons (tooltip + aria-label carry state), right-aligned; Clock + DemoBadge
   at right. Brand "LedgerFrame" top-left **only at narrow widths** (sidebar carries it at
   laptop+ → one brand at a time, never two).
2. **Banners OUT of the bar** — StaleBanner/UpdateBanner render as **full-width slim status
   strips BELOW the top bar** (normal flow, push content, never overlay), only when active.
3. **Sidebar progressive reveal** — all six D-043 group headers always show; only **built**
   pages appear as entries (`item.built`; only Holdings today); header-only where none built.
   `showAll` previews the full skeleton.
4. **Bolder active rail** — new `--nav-rail-width: 3px` token (tokens.css); Sidebar `is-active`
   uses it.

**Icon re-ratify amendments applied (2026-07-11):**
- **Stateful-glyph rule** (recorded in DESIGN-SYSTEM §5.5): every stateful toggle now
  renders a **state-distinct glyph per state** (theme ☀/☾/◐, density ≡/≣, contrast
  ▨/◧/■, motion ≈/—/≋, rotation ↻/⊘, Detail ╱-line/╪-candlestick); tooltip names it;
  no glyph collisions — `☰` reserved for the sidebar/menu toggle.
- **LockScreen over a blurred snapshot** — `backdrop-filter: blur(--lock-blur)` (24px
  token) + heavy `--lock-scrim`, with an `@supports` fallback to near-opaque
  `--lock-scrim-opaque` where blur is unsupported, so content is genuinely unreadable
  on every browser (D-002 — no ambient shoulder-view). Blur radius recorded as a token.

**Checks:** lint · typecheck · token-drift · **72 frontend tests** · build — all green.

**Owner's quick kitchen-sink look (icons + lock blur), then Phase 1:**

- [ ] **Icon toggles** — clicking each changes the *glyph*, not just the tooltip; the six
  controls read as distinct; `☰` only ever the menu toggle.
- [ ] **LockScreen** — open it and confirm **nothing behind is legible** at any zoom
  (blur + scrim); access-lock hint; Unlock gated at 6+ digits; error on PIN `000000`.
  *(No headless browser is installed, so this visual illegibility check is the owner's;
  illegibility is engineered not to depend on blur — the heavy/opaque scrim guarantees it.)*
- [ ] Rest re-ratified as committed (slim TopBar, status strips, Sidebar reveal, active rail).

**On re-ratify → Phase 1** (shell assembly): mount Sidebar + slim TopBar + status strips +
lock gate around `<Routes>`, move DisplayControls out of the page into the TopBar, wire
redirects (D-042/D-022/D-056), and add the C-3 no-egress network-trace test.

---

## 11. PHASE 3 — OWNER ACCEPTANCE WALK (LIVE)

Owner-driven live walk; each finding a numbered §-entry, fixed, then re-verified live
by the owner. Not self-certified.

### Batch 1 (owner, 2026-07-11) — **§11-1, §11-3 RE-VERIFIED live ✅; §11-4 RATIFIED (reopened → completed)**

- **§11-1 — RE-VERIFIED ✅. Nav toggle (☰) showed at laptop+ alongside the fixed sidebar.** Bug: the
  hide rule `.lf-topbar__navtoggle { display:none }` (0,1,0) lost to `.lf-iconbtn {
  display:inline-flex }` (0,1,0) by stylesheet import order (TopBar imports chrome.css
  then structure.css), so the toggle rendered at every width. Fix: raised the selector
  to `.lf-topbar .lf-topbar__navtoggle` (0,2,0) for both the base hide and the narrow-
  width show, so it beats `.lf-iconbtn` regardless of order. Confirmed it toggles at the
  **single 900px breakpoint** — the same one the sidebar uses for its fixed↔off-canvas
  switch (`.lf-sidebar` + `.lf-sidebar__brand`), not a second breakpoint. `chrome.css`.
- **§11-2 — Off-canvas open/dismiss (D-102).** ☰ → `AppShell` `setNavOpen` → Sidebar
  `open` → `.is-open` slide-in + scrim (verified wired). Backdrop click already closed it
  (scrim `onClick=onClose`); **Esc did not** — added an Escape keydown listener on the
  Sidebar (active only while open). NavLink click still closes on navigation. Added a
  render test: open shows panel+scrim `is-open`; Esc and backdrop each call `onClose`;
  closed = no Esc handler. `Sidebar.tsx`, `chrome.test.tsx`.
- **§11-3 — RE-VERIFIED ✅ + ADDENDUM done. Removed the page-level "← Home" link from Holdings.** D-066: navigation is
  chrome, composed once; the link predated the shell and now duplicated the Sidebar.
  Checked `TEMPLATE-page-build.md` and DESIGN-SYSTEM §3 (worklist + entity-detail
  templates) — **neither mandates a back affordance**, so removed it (and its now-empty
  `hold__bar`). **Addendum (owner):** also removed Instrument Detail's contextual
  **"← Holdings"** link (and its `ins__bar`) — the Sidebar is the nav (D-066);
  entity→parent duplication isn't needed. `Holdings.tsx`, `InstrumentDetail.tsx`.
- **§11-4 — "Export CSV" RATIFIED; reopened → COMPLETED.** The label is ratified. The
  batch-1 fix was incomplete (only the DataTable toolbar button); audited **all**
  export/import buttons app-wide and applied it: the Holdings **page-header** Export still
  read "Export (server-side)" → now the ratified label (and, per §11-13, an icon button
  with `aria-label="Export CSV"`). No "Export (server-side)" literal remains in any button.
  `DataTable.tsx`, `Holdings.tsx`.

### Batch 2 (owner, 2026-07-11) — fixed, awaiting owner live re-verify + PROPOSED ratifications

- **§11-5 — Icon-button uniformity.** `.lf-iconbtn` now a fixed **`--iconbtn-size`**
  square (tokenized) with a single glyph size, glyph flex-centered, so the 7 bar controls
  render visually uniform (`⊘ ╱ ╪ ☾ …`). Kitchen-sink row shows all bar glyphs side by
  side. `tokens.css`, `structure.css`, `KitchenSink.tsx`.
- **§11-6 — Tooltip copy.** Stateful toggles now read **"Function: state"** only
  (stripped "— click to change"); `aria-label` matches the tooltip. `DisplayControls.tsx`,
  `TopBar.tsx` (+ `App.test.tsx` selectors).
- **§11-7 — DEMO audit (no hardcodes found).** All demo/mock signals derive from data,
  not literals: **DemoBadge** renders only when the demo-data flag is on (its "Demo data"
  text is the badge's label, not a state literal); **"Source: mock"** on Instrument Detail
  comes from `quote.source` provider provenance (`{quote.source}`), not a hardcode; the
  only `mock`/`Mock` strings are the **kitchen-sink gallery caption** and **test fixtures**
  (both legitimately mock). **No fix needed** — reported per-instance as data (fine).
- **§11-8 — Spec-ID leak.** Removed decision IDs from user-facing copy: Instrument Detail
  subtitle `(P-3)` and Holdings summary `(D-023)`. The Import dialog dry-run explainer
  (which carried `(D-012)` + an impl tip) is rewritten plain **(PROPOSED)**: *"Nothing is
  written until you review. Fix or exclude flagged rows first. Exported transaction files
  re-import cleanly."* (Remaining `D-`/`P-`/`§` occurrences are code comments only.)
  `InstrumentDetail.tsx`, `Holdings.tsx`.
- **§11-9 — Page subtitle clamp.** Template-level: below the 900px breakpoint the
  `PageHeader` purpose line clamps to **one line with ellipsis** — applies to all four
  templates (every page uses `PageHeader`). `structure.css`.
- **§11-11 — TopBar narrow overflow (PROPOSED, D-102 ext.).** Below 900px the display axes
  + rotation + Detail collapse into a single **`⋯` overflow popover** (`aria-label="Display
  settings"`, reuses surface tokens, outside-click/Esc close); the bar shows ☰ + brand +
  overflow + Clock + DemoBadge and **never wraps ≥320px** (`flex-wrap:nowrap`). New pattern
  → DESIGN-SYSTEM §5.5 amendment (PROPOSED); kitchen-sink note + live in the App-shell
  specimen when narrowed. `TopBar.tsx`, `chrome.css`.
- **§11-12 — Clock + DemoBadge placement (PROPOSED).** **Clock:** time-only in the bar at
  all widths; full date + IANA timezone in the tooltip/`aria-label`. **DemoBadge:** at
  laptop+ renders in the **sidebar footer** (bottom-left); at narrow it stays in the bar;
  never hidden while demo is active. `Clock.tsx`, `Sidebar.tsx` (footer slot), `TopBar.tsx`,
  `AppShell.tsx`, `chrome.css`.
- **§11-13 — Page-action icon buttons (PROPOSED, §5.5 amendment).** Page-level actions are
  icon-only `.lf-iconbtn` with tooltip + matching `aria-label`: Instrument Detail **Edit**
  `✎`; Holdings **Import** `↥` / **Export CSV** `↧`. **Exception:** primary **Add** stays a
  labeled primary button. Kitchen-sink specimen row. `InstrumentDetail.tsx`, `Holdings.tsx`.

**PROPOSED items needing owner ratification at the kitchen sink:** §11-8 import copy,
§11-11 overflow popover, §11-12 Clock/DemoBadge, §11-13 page-action icon buttons
(+ the §11-4 "Export CSV" label, now ratified). Specimens staged under the chrome section.

**Checks:** frontend 80 tests · drift/typecheck/lint/build green; backend untouched.
**STOP — owner re-verifies live + ratifies the PROPOSED items at the kitchen sink.**

### Batch 3 (owner, 2026-07-11)

- **§11-14 — REGRESSION: narrow-width horizontal overflow (fixed first, committed alone).**
  Root cause: batch-2 §11-9 gave the `PageHeader` subtitle `white-space:nowrap` at narrow
  widths, but `PageHeader` wrapped title+subtitle in a plain `<div>` with no `min-width:0`
  — so the nowrap subtitle expanded that div past the viewport (horizontal scroll;
  StaleBanner spanning only the visible width; dead band right of content). **Structural
  fix:** nest title+subtitle in `.lf-pageheader__titles` (`min-width:0; flex:1 1 auto`) so
  the subtitle clamps instead of pushing wide; `.lf-pageheader` gains `flex-wrap:wrap`; the
  TopBar brand truncates (`min-width:0`/ellipsis) so the bar never overflows either.
  **Regression test:** `overflow.test.tsx` permanently guards the structural invariant
  (PageHeader nests the shrinkable titles wrapper). **Limitation (honest):** a true pixel
  test — `scrollWidth <= clientWidth` at 320/375/900/1366px on the document + shell content
  container — needs a **real browser**; jsdom has no layout engine (scrollWidth/clientWidth
  are always 0, so such a test passes vacuously). That breakpoint suite is specced for
  **Playwright (ADR pending)** — owner to approve the dev-dependency + browser download;
  owner verifies 320px live meanwhile. `PageHeader.tsx`, `structure.css`, `chrome.css`,
  `overflow.test.tsx`.

- **§11-15 — SVG icon set: lucide-react (ADR-0003, PROPOSED for kitchen-sink ratify).**
  Adopted `lucide-react` as the platform icon set — **bundled + tree-shaken per-icon
  import** (`src/icons.ts`), no CDN, no runtime fetch (no-egress applies to assets). All
  Unicode glyphs replaced: bar toggles (theme Sun/Moon/Monitor, density Rows2/Rows4,
  contrast Contrast/Circle/Disc, motion Waves/Minus/Wind, rotation RotateCw/Ban, Detail
  LineChart/CandlestickChart), Menu, overflow + RowMenu `MoreHorizontal`, page actions
  (Pencil/Upload/Download/Plus). The stateful-icon rule (§5.5) is unchanged — the
  assignment table now lists icon names. Icons size from `--icon-size`, colour from
  `currentColor` (theme-aware; drift-clean). **Bundle-size delta: JS 350.5 → 356.9 kB raw
  (+6.4 kB), gzip 109.1 → 111.1 kB (+2.1 kB)** — only the ~20 icons in use are bundled.
  Kitchen-sink row shows every bar icon at final size (both themes). `icons.ts`,
  `DisplayControls.tsx`, `TopBar.tsx`, `RowMenu.tsx`, page actions, `tokens.css`,
  `structure.css`.
- **§11-16 — Page-header actions all icon-only + framed (revises §11-13; PROPOSED).**
  Owner decision: **every** page-header action is icon-only, on a **visible bordered
  surface** (`.lf-iconbtn--framed`, not ghost) — Holdings Import/Export CSV, Instrument
  Detail Edit. **Add** goes icon-only too (`Plus`) but keeps the **accent-filled**
  `.lf-iconbtn--primary` for primary emphasis. Tooltip + aria-label on each. Kitchen-sink
  specimen row. `structure.css`, `Holdings.tsx`, `InstrumentDetail.tsx`.

- **§11-17 — TickerStrip global footer (D-047 AMENDMENT, PROPOSED).**
  - **(4a) Data verified:** the frozen contract already exposes index quotes via
    **`/markets/global`** (S&P 500, Nasdaq, FTSE, DAX, Nikkei, Hang Seng, Nifty 50,
    STI…) and holdings quotes via **`/portfolio/holdings`** (symbol, price,
    day_change_pct, is_stale). **No new endpoint or provider change → indices INCLUDED**
    (no contract change this batch).
  - **(4b) D-047 amended:** TickerStrip promoted from Home-Full-only to a fixed, always-
    visible **global-chrome footer**, all widths. Home Full no longer duplicates it.
  - **(4c) Requirements met:** footer height is a token (`--ticker-height`); it sits at
    the bottom of the shell's main column so content **reserves the space** (never hidden
    behind it); **mobile safe-area** respected (`env(safe-area-inset-bottom)`); quotes =
    holdings + indices; **staleness flagged per item** (amber `TriangleAlert`).
  - **(4d) Lock:** the footer is **not rendered at all while locked** (`!locked` guard) —
    the strongest no-leak guarantee (D-002). **Render test:** lock open ⇒ `.lf-ticker`
    absent; unlocked ⇒ present.
  - **(4e) Reduced motion:** the marquee halts and the strip becomes **static + manually
    scrollable** (`data-motion="reduced"` → `overflow-x:auto`, RATIFICATION §1.6).
  - Component reshaped to `TickerQuote[]` (`symbol/price/changePct/stale`); reader
    `fetchTickerQuotes` (holdings + indices, degrades safely). Kitchen-sink specimen +
    the shell footer are live. `TickerStrip.tsx`, `api/chrome.ts`, `AppShell.tsx/.css`,
    `data.css`, `tokens.css`, `icons.ts`; IA §4, DESIGN-SYSTEM §5.2, DECISIONS D-047.

**Batch-3 checks:** frontend tests green (incl. the overflow guard + lock-hides-ticker);
drift/typecheck/lint/build green. **STOP — owner re-verifies live** (320px width, the
kitchen-sink icon row, the ticker under lock) **+ ratifies the PROPOSED items**
(lucide icon set, all-icon framed page actions, TickerStrip footer / D-047 amendment).

### Batch 4 (owner, 2026-07-11)

- **§11-18 — TickerStrip tuning: speed + density tokens; faster default (PROPOSED).**
  Exposed the marquee scroll duration and item spacing as tokens (`--ticker-scroll
  -duration`, `--ticker-gap`; height already `--ticker-height`). Default speed set
  **noticeably faster — 22s (was 40s)**; owner ratifies the final value at the kitchen
  sink. Kitchen-sink specimen shows **three speeds side by side** (Faster 14s · Default
  22s · Slower 36s). Recorded **"ticker scroll speed as a per-device display setting
  (D-078)"** as **ROADMAP R-16** for the future Settings page plan — **NOT built now**.
  `tokens.css`, `data.css`, `KitchenSink.tsx`, `ROADMAP.md`.
- **§11-19 — Ticker symbol links (D-098).** Each **holdings** symbol links to
  `/instrument/{symbol}` (reader sets `href`; TickerStrip wraps it in a router `Link`).
  **Indices took the UNLINKED path** and render as plain `<strong>` — reasoning: an
  index's ticker label (e.g. "US · S&P 500") has **no instrument-detail record/route**,
  so linking it would be a dead link; and its canonical home, **Markets, isn't built yet**
  (a link there would hit the NotBuilt fallback). Unlinked is the honest choice now — when
  Markets ships, indices can link to their canonical home there (noted as a follow-up).
  Render test asserts holdings link + index unlinked. `TickerStrip.tsx`, `api/chrome.ts`,
  `data.css`, `chrome.test.tsx`.
  - **CLOSED (owner-verified live, 2026-07-12):** R-17 shipped with the Markets build — index
    entries now link to `/markets` (`fetchTickerQuotes` sets the `href`; owner verified the
    index-click lands on Markets). The interim "unlinked" path is retired. See page-markets §12mk3-3.
- **§11-20 — Lock verification assist (information only, no code change).**
  Set a PIN against the running backend (loopback; the first PIN needs no auth):
  ```
  curl -X POST http://127.0.0.1:8321/api/v1/auth/set-pin \
    -H 'Content-Type: application/json' -d '{"pin":"123456"}'
  ```
  (`PinPayload`: `pin`, 4–32 chars; use 6+ digits per the SECURITY-BASELINE §3 policy.
  Then reload the app → the LockScreen gates it; unlock with the same PIN.) **Clear-PIN:
  there is NO clear/remove-PIN endpoint in the frozen contract** — the auth surface is
  `set-pin` · `unlock` · `lock` · `state`. `set-pin` only *changes* an existing PIN (and
  that requires an unlocked session/token); it cannot clear one. To undo for testing,
  reset the instance data or clear `User.pin_hash` in the dev DB directly.

**Batch-4 checks:** frontend 83 tests green (incl. overflow guard, lock-hides-ticker,
ticker links); drift/typecheck/lint/build green; backend untouched. **STOP — owner
re-verifies live.**

### Batch-4 re-verify + Phase-3 close-out (owner, 2026-07-11)

- **§11-17 lock clause — OWNER-VERIFIED LIVE (D-002).** set-pin curl → reload → the gate
  renders, content is illegible, the **ticker is ABSENT under lock**, wrong-PIN shows the
  error, unlock works. The D-002 no-leak-under-lock requirement is verified.
- **§11-20 addendum — clear the dev PIN (return to no-PIN demo state):**
  ```
  sqlite3 "$HOME/.local/share/ledgerframe-dev/db/ledgerframe.db" "UPDATE users SET pin_hash=NULL;"
  ```
  (Still the honest picture: the contract has **no** clear-PIN endpoint; this edits the dev
  SQLite directly. Run with the backend stopped, or it takes effect on the next read.)
- **§11-21 — Playwright breakpoint overflow suite (ADR-0004, APPROVED + wired).** Added
  `@playwright/test` + `e2e/overflow.spec.ts`: **24 checks** (320/375/900/1366 × `/`,
  `/holdings`, `/instrument/:symbol` × light/dark) assert `scrollWidth ≤ clientWidth` on
  the document + `.lf-shell__content`. **Wired into `npm run check`** (`test:overflow`,
  after Vitest; Playwright's `webServer` builds + `vite preview`s the app). CI must
  `npx playwright install chromium` first (browser not bundled — noted in the ADR).
  **Green: 24/24** — the §11-14 fix is now enforced at 320px in a real browser.

**RATIFICATIONS FLIPPED (owner, 2026-07-11):** §11-15 lucide icon set (ADR-0003); §11-16
page-action icon-button pattern (recorded as the DESIGN-SYSTEM §5.5 standard); §11-17
TickerStrip footer / D-047 amendment (DECISIONS + DESIGN-SYSTEM §5.2 flipped to ratified);
§11-18 ticker speed **set to 30s**, height/gap ratified (R-16 stands); §11-19 indices
unlinked ratified (R-17 recorded for the Markets plan); batch-2 overflow popover / Clock /
DemoBadge placement ratified. The Phase-0a chrome inventory marker is flipped to ratified.

### OPEN before Phase-3 close-out

1. **D-101 themed scrollbar-thumb polish** — **NOT** addressed in batches 1–4 (no scrollbar
   CSS touched). Given a named home: **ROADMAP R-18**. A real browser is now available
   (ADR-0004 chromium) to verify the thumb paints and close it. *Cosmetic; not blocking.*
2. **Deferred by prior decision (not this milestone):** the **Ask panel (D-067)** stays
   deferred to the AI-surfaces milestone (C-2); the **first-run checklist (D-045)** is its
   own later small plan (C-4). Both intentionally out of chrome scope.
3. **Future links parked:** per-device ticker speed setting (R-16, Settings plan);
   indices→Markets link (R-17, Markets plan).

Nothing else is open. With the ratifications flipped and the overflow suite green, the
chrome build is ready for **Phase-3 close-out** on owner sign-off.

---

## 12. RETROSPECTIVE — first non-page (shell) plan through the loop

Page-chrome is the **first plan that is not a content page** — the app shell that
wraps every route. Recorded so the template absorbs the differences.

### 12a. What the shell needed that `TEMPLATE-page-build.md` didn't anticipate

- **No single route / no figure ownership.** §1 (IDENTITY) assumes one route + one H1;
  the shell has neither. §2 (OWNERSHIP) assumes *figures* owned/summarised; the chrome
  owns **UI STATE** (nav, display axes, rotation, lock) and only **summarises status**
  (stale count, version, demo, clock) via canonical readers. The template's ownership
  frame had to be re-read as "UI-state ownership."
- **Cross-page acceptance, not single-page.** "Done" for the shell meant **a page from
  each of the four templates renders inside it** + redirects + lock gate — acceptance
  criteria that span the app, not one page's happy path.
- **A regression class the template never named: layout/overflow ACROSS every page.**
  A narrow-width fix on a shared primitive (`PageHeader` subtitle, §11-9) silently broke
  horizontal layout **on every page** (§11-14). Unit tests were green — jsdom has no
  layout engine. This forced a **real-browser breakpoint suite** (ADR-0004).
- **"New component = amendment" scaled to a whole inventory.** The template's one-
  component amendment rule became a **Phase 0a** step: author seven chrome components as
  PROPOSED, ratify the *set* at `/kitchen-sink` before assembly. Worked well; the shell
  reused it verbatim.
- **Composed once, not per-page (D-066).** The opposite of a page plan — the deliverable
  is that pages **stop** re-implementing chrome (back-links, DisplayControls removed).

### 12b. Concrete lessons (encoded — see 12c)

- **(a) jsdom cannot catch layout/overflow.** Any visual-affecting change needs the
  **Playwright overflow suite (ADR-0004)** extended alongside — green Vitest is not
  acceptance for layout. (§11-14.)
- **(b) Copy hygiene.** Decision IDs (`D-0…`/`P-…`/`§…`) and implementation notes
  (`server-side`, endpoint/enum names) must **never** reach a user-facing string — only
  code comments/plan docs. (§11-8: the `(D-012)` + `"server-side"` leaks.)
- **(c) Label/copy changes are app-wide.** A changed label is grepped and fixed at
  **every** instance in the same change, not just where found. (§11-4 recurred because the
  first fix hit only one of two Export buttons.)

### 12c. Template / REVIEW-GUIDE amendments (applied this commit)

Applied to `TEMPLATE-page-build.md`:
- **Governing rules:** added **Copy hygiene** + **Label/copy changes are app-wide**.
- **§7 acceptance:** the layout-verification line now also requires **extending the
  Playwright overflow suite (ADR-0004)** for the page; added a **copy-hygiene** checkbox.
- **§8 Phase 2:** extend the Playwright overflow suite for any layout-affecting change.
- **New "Shell / global-chrome plans" note** (top): such a plan adapts the template —
  UI-state (not figure) ownership, cross-page acceptance, layout/overflow as the
  regression surface.

**Flagged for owner (judgment-y, NOT applied):** whether `REVIEW-GUIDE.md` (the plain-
language owner companion) should also carry a one-line owner-facing quality bar — *"you
should never see an internal code (like D-012) or jargon on screen."* It's owner-facing
and fits, but REVIEW-GUIDE has so far avoided dev-process notes — owner's call.

### 12d. Patterns extracted to the platform (reusable beyond chrome)

`.lf-iconbtn` (+ `--framed`/`--primary`) icon-button system · the **stateful-icon rule**
· the lucide icon set (`src/icons.ts`, ADR-0003) · the **page-action icon-button
pattern** (DESIGN-SYSTEM §5.5) · the TickerStrip global footer · the Playwright overflow
suite (ADR-0004) — all now platform-wide, available to every future page.
