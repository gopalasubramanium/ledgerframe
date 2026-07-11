# page-net-worth.md — Net worth (overview) page build plan

**Status: PLAN ONLY — owner reviews §9 before any code.** Drafted 2026-07-12 from
`TEMPLATE-page-build.md` (incl. the §7/§8 repeat-finding amendments, Phase-3a scripted-pre-pass
standard, and the progressive-per-card-loading overview standard). Verify-first pass done (§10 — read
what the engine serves before assuming shapes, D-019). **Nothing is built.** Every ambiguity is in
§9; the owner resolves them. This page is the reciprocal of Portfolio: it **owns** the Net worth
headline that Portfolio/Holdings summarise (D-032) — building it completes that wiring.

Net worth is the third **overview-template** page (Portfolio + Home are the others) and the canonical
home for the net-worth headline, its trend, the liquidity ladder, and cash runway (IA §2/§5).

---

## 1. IDENTITY

*Source: INFORMATION-ARCHITECTURE.md §2 (page map), §3 (nav); DESIGN-SYSTEM.md §3.*

| Field | Value | Spec ref |
|-------|-------|----------|
| Page name (H1 = nav label = route) | **Net worth** | IA §2, D-022 |
| Route | `/net-worth` | IA §2, D-022 |
| Redirect | `/snapshot` **→ `/net-worth`** (already live, migration; D-022/D-042) | IA §3, page-chrome |
| Nav group | **Wealth** (Net worth · Portfolio · Holdings · Accounts) | IA §3 |
| Page template | **Overview** (KPI strip / trend chart / summary widgets) | DESIGN-SYSTEM §3 |
| Rotation eligibility | Eligible (Wealth dashboard page) — **confirm ND-11** | IA §3 (D-044) |
| One-line purpose | **Net worth** — the canonical home for the one headline total (Gross assets − Liabilities), its trend, the liquidity ladder, and cash runway. Analytics live on **Portfolio** (D-023); this page summarises Portfolio's headline with a link. | IA §2/§5, D-032/D-036 |

**Subtitle (states the split, mirror of Portfolio):** Net worth = the headline & liquidity view;
**Portfolio** = investment analytics — cross-linked.

---

## 2. OWNERSHIP TABLE

*Copied verbatim from INFORMATION-ARCHITECTURE.md §5 (Net worth). Never re-derived.*

**Owns (canonical, authoritative, fully explained here):**
- **Net worth · Gross assets · Liabilities** (D-032) — the one headline total and its labelled
  components. `Net worth = Gross assets − Liabilities`; `Gross assets = Σ positive holdings' current
  market value, base ccy, today's FX` (GLOSSARY).
- **Net-worth trend** — the headline over time (D-032/D-036).
- **Liquidity ladder** (D-036) — Immediate / Short / Locked / Illiquid, canonical here.
- **Cash runway** (D-036) — liquid ÷ recurring net burn; honest no_data / positive / finite states.
- **Composition-by-class table** (D-033) — an **itemised statement incl. liabilities**; explicitly
  **NOT** a duplicate of Portfolio's allocation *weight* (that answers a different question). A
  **table**, not a donut.
- **Insurance-cash-value valued exclusion line** (D-039/D-081) — the exact labelled line
  **"Insurance cash value (excluded): «amount» — see Insurance"**; the value is **shown but excluded
  from the headline Net worth total**.

**KPI strip (D-054):** **Net worth · Gross assets · Liabilities · Cash & deposits.** The
**composition donut is DROPPED here (D-054) — do NOT reintroduce it** (allocation weight lives on
Portfolio, D-033).

**Summarises (other pages' info — via the named reader, linked, never recomputed):**

| Summary shown | Canonical page | Shared reader reused | Link target |
|---------------|----------------|----------------------|-------------|
| Portfolio headline (Today's change etc.) | Portfolio (`/portfolio`) | `/portfolio/summary` (D-032) | `/portfolio` |
| Performance **sparkline** (not the picker/chart) | Portfolio (`/portfolio`) | `/portfolio/performance` (D-035) | `/portfolio` |
| ReviewCard | Review (`/review`, unbuilt) | Review reader (D-038) | `/review` (signpost, ND-6) |

**Links to:** "edit obligations" → **Cash flow** (`/cash-flow`, D-036) · **Insurance**
(`/insurance`, the exclusion line) · **Portfolio** (headline). Both cross-page targets are pages not
yet built → **signpost links** (per the Holdings D-092 pattern), confirm in §9.

**Enforcement corollary (P-1/D-031):** the Net worth headline and every component are read from the
canonical reader (`value_portfolio` via `/portfolio/summary`), never recomputed in the frontend.
Portfolio and Holdings **summarise this page's headline** — this page must not, in turn, recompute
anything they own. **No frontend money math.**

---

## 3. API SURFACE

*Source: API-CONTRACT.json (frozen) + API-CONTRACT.md. Verify-first findings that pin these shapes
are in §10.*

### 3a. Endpoints consumed (already in the frozen contract)

| Method + path | Purpose on this page | Response shape (verified §10) |
|---------------|----------------------|-------------------------------|
| `GET /portfolio/summary` | KPI strip: Net worth (`total_value`), Gross assets (`gross_assets`), Liabilities (`liabilities`); `has_stale`/`stale_count`; the summarised Portfolio headline (`day_change`, `total_return_pct`) | keys verified (ND-4 added `gross_assets`/`liabilities`); **"Cash & deposits" NOT served — ND-3** |
| `GET /net-worth/history` | Net-worth **trend** chart | `{history:[{ts, assets, liabilities, net_worth, currency}]}` — **worker-written snapshots, no params, no backfill — ND-1/ND-2** |
| `GET /portfolio/liquidity` | Liquidity ladder | `{base_currency, gross_assets, rungs:[{key,label,value,pct,cumulative_pct}], liquid_pct, liabilities, disclaimer}` (served labels, D-005) |
| `GET /portfolio/runway` | Cash runway card | `{base_currency, liquid, monthly_expense, monthly_income, net_monthly_burn, runway_months, runway_date, status, note, disclaimer}` (status: no_data/positive/finite) |
| `GET /portfolio/performance?days=&benchmark=&include_manual=` | linked performance **sparkline** (D-035; NOT the picker/chart) | `series` (verified last milestone) — window default, ND-7 |
| `GET /insurance` | insurance valued exclusion line | `total_cash_value` (+ `count`) — see §10; Insurance page unbuilt → signpost, ND-5 |
| `GET /portfolio/review` **or** `GET /review/centre` | ReviewCard summary (D-038) | shape not yet pinned — **ND-6** (which reader; whether in scope now) |

**Entity scoping:** `liquidity` accepts `entity_id`; `runway`, `net-worth/history`, `insurance` do
**not** (verified §10). Household-default posture per **ND-10**.

### 3b. Contract deltas (needed but not in the baseline — BUILD BACKEND-FIRST)

**None asserted here.** Per house style, **suspected gaps go to §9, not a §3b guess.** Two owner-facing
gaps that *may* need a backend delta are raised as **ND-1/ND-3/ND-4** (net-worth history
backfill/seed; "Cash & deposits" figure; composition-by-class-incl-liabilities reader). If the owner
chooses a backend route for any, it becomes a §3b delta built **backend-first**, regenerating
`API-CONTRACT.json` + `docs/openapi.json` in the same commit (`make api-contract-check`).

---

## 4. COMPONENTS

*Source: DESIGN-SYSTEM.md §5 (ratified inventory) + §3 (overview template). Ratified only; a missing
affordance is a §9 amendment request. Data-wired to real endpoints (no mock fixtures on a canonical
page). Progressive per-card loading is the overview standard (each card resolves on its own reader).*

| Ratified component | Role on this page | Data source (real endpoint) | Not exercised at kitchen-sink |
|--------------------|-------------------|-----------------------------|-------------------------------|
| **PageHeader** | H1 "Net worth" + D-023/D-032 subtitle + actions (export?) | — | — |
| **TrendStat** | KPI strip (Net worth / Gross assets / Liabilities / Cash & deposits); runway figure | `/portfolio/summary`, `/portfolio/runway` | a 4-tile KPI strip |
| **PriceChart** (line mode) | net-worth **trend** (single series; house-SVG) | `/net-worth/history` | a non-price value-over-time series; thin/empty history (ND-1/ND-13) |
| **DataTable** | composition-by-class table (itemised, incl. liabilities); liquidity ladder as a rung table | ND-4 reader; `/portfolio/liquidity` | a table that includes a negative (liability) row |
| **ReviewCard** | summarised Review verdict (D-038) | Review reader (ND-6) | on a non-Review page |
| **EmptyState** | honest empty trend (no snapshots), no runway data (no obligations), no policies | reader "unavailable"/empty shapes | insufficient-history trend (ND-13) |
| **StalenessChip / ProvenanceBadge** | headline/trend freshness (D-027) | `summary.has_stale`; per-point ts | on a KPI + on a value-over-time chart (ND-12) |
| **GlossaryTerm** | `[Help]` on Net worth, Gross assets, Liquidity ladder, Liquid, Cash runway, Cash & deposits | GLOSSARY | multiple `[Help]` anchors |
| **Sparkline** | the linked Portfolio performance summary | `/portfolio/performance` | a summary sparkline that links out (ND-7) |

**Affordances the ratified inventory may lack (amendment — resolve in §9 before build):**
- **Liquidity-ladder visual.** The ladder is a graded time-to-cash breakdown; the donut is **dropped
  here (D-054)**. Options: render as a **DataTable** (rung · value · pct · cumulative — no new
  component) or a **segmented horizontal bar** (a possible §5 amendment). **ND-8.**
- **Runway card.** Likely a `TrendStat` (runway_months) + a status note + a small burn breakdown
  (expense / income / net) — confirm no new component needed (**ND-9**).

**Component usage rules the build must honour (template §4):**
- **Cards layered (D-100);** a card's canonical cross-link lives in the card header, top-right.
- **House-SVG charts only (D-053);** the trend is `PriceChart` line mode. **No donut here (D-054).**
- **Scroll = content only, header outside (D-101);** any table caps at `--table-max-h`.
- **No raw `<input>`/`<select>`;** any window/toggle is `ui/Select`/`Switch`.
- **Progressive per-card loading (§12-8 overview standard);** Skeleton → data / EmptyState / error.
- **A recurring page-local pattern extracts to the component layer.**

---

## 5. VOCABULARIES

*Source: MASTER-DATA.md. Every categorical → its master + the control.*

| Field on this page | Vocabulary / master | Fixed (/refdata) or extensible | MASTER-DATA ref |
|--------------------|---------------------|-------------------------------|-----------------|
| Composition **class** rows | `AssetClass` (incl. `liability`) | fixed | MASTER-DATA §2 |
| Liquidity **rung** labels | served by `/portfolio/liquidity` (`label`) | **served system labels, not a master** | served (D-005 zero-copy) |
| Runway **status** | served enum `no_data`/`positive`/`finite` → served `note` | served | §10 |
| Trend **window** (if any) | view-scope UI (ND-2) | n/a (view state) | `Select`/tabs — ND-2 |

Liquidity rung labels and runway notes are **served display strings** (D-005) — render them verbatim,
never hardcode. Class labels resolve through the served `labelFor("asset_class", …)` (the §12-3 rule
from Portfolio — never render a raw enum key).

---

## 6. DECISIONS IN FORCE

*Source: docs/audit/DECISIONS.md — each with what it forbids/requires here.*

| Decision | What it forbids / requires on this page |
|----------|------------------------------------------|
| **D-022** | Route is `/net-worth` (nav label = H1 = route); `/snapshot` redirects (live). |
| **D-023** | Net worth = headline/liquidity view; **Portfolio = analytics**. Subtitle states the split; cross-link. **No analytics (allocation weight, benchmark, attribution) here.** |
| **D-032** | This page is **canonical** for Net worth / Gross assets / Liabilities; it **summarises** the Portfolio headline with a link. Portfolio/Holdings summarise THIS headline (reciprocal). |
| **D-033** | The composition here is an **itemised statement incl. liabilities**, explicitly **not** Portfolio's allocation weight. |
| **D-036** | Liquidity ladder + cash runway canonical here; "edit obligations" → Cash flow. |
| **D-039 / D-081** | Insurance cash value **excluded from the headline total**, shown as the labelled valued line **"Insurance cash value (excluded): «amount» — see Insurance"**; stated on Insurance too. |
| **D-054** | KPI strip = Net worth / Gross assets / Liabilities / Cash & deposits; the **composition donut is DROPPED — do not reintroduce**. |
| **D-057** | **Protected semantics:** `once` obligations **excluded** from recurring burn; contributions **never reduce** runway. (Runway copy must not contradict this.) |
| **D-086** | No annualized/fabricated figure below the minimum-history threshold — the trend shows cumulative history honestly; thin/empty history → EmptyState, never a fabricated curve. |
| **D-065** | Entity scoping (Household default; entity selector belongs to Accounts, not here — ND-10). |
| **D-005 / D-050** | Served vocab/labels (zero-copy); any CSV export is server-side. |
| **D-027 / Guarantee 3** | Every empty/"—" region states a reason; stale flagged, never hidden or faked. |

---

## 7. ACCEPTANCE CRITERIA

*Checkable, user-visible. Includes honesty states + theme/density + overflow + the §7/§8 pre-pass
assertion rule.*

- [ ] **KPI strip (D-054):** Net worth · Gross assets · Liabilities · **Cash & deposits** — every
      figure from the canonical reader, **no frontend math**, freshness-flagged. `Net worth = Gross
      assets − Liabilities` reads consistently (GLOSSARY). (Cash & deposits source per ND-3.)
- [ ] **Net-worth trend (D-032/D-086):** the headline over time from `/net-worth/history`; **honest
      EmptyState when there are <2 snapshots** (fresh instance), never a fabricated curve; freshness
      shown (ND-12/ND-13). Behaviour with the real snapshot cadence is demonstrated (ND-1).
- [ ] **Liquidity ladder (D-036):** Immediate / Short / Locked / Illiquid with served labels, value,
      pct, cumulative; `Liquid = Immediate + Short` stated; the `disclaimer` shown verbatim.
- [ ] **Cash runway (D-036/D-057):** liquid ÷ recurring net burn; **all three honest states**
      (no_data / positive / finite) render with the served `note`; runway never invented without
      obligations; the `disclaimer` shown verbatim; contributions/`once` obligations copy does not
      contradict D-057.
- [ ] **Composition-by-class table (D-033):** an itemised statement **including the liability row**
      (negative), distinct from Portfolio allocation; **no donut (D-054)**.
- [ ] **Insurance valued line (D-039/D-081):** exact copy **"Insurance cash value (excluded):
      «amount» — see Insurance"**; value shown, **excluded from the headline**; links/signposts to
      Insurance (ND-5).
- [ ] **Summarises, never recomputes (P-1/D-032):** Portfolio headline + performance sparkline are
      linked summaries via Portfolio's readers; ReviewCard via the Review reader (ND-6/ND-7).
- [ ] **Honesty (Guarantee 3):** every empty / "—" region states a reason; stale flagged (D-027).
- [ ] **Terms match GLOSSARY;** copy hygiene — no decision IDs / impl notes / internal enum keys
      (`net_worth`, `immediate`, `finite`) in any user string; `[Help]` links resolve.
- [ ] **Cross-links:** Net worth ↔ Portfolio; Cash flow (edit obligations); Insurance (exclusion
      line) — pages-not-built resolve to honest signposts (ND-5).
- [ ] **No analytics here (D-023):** no allocation-weight donut, no benchmark/attribution.
- [ ] **Both themes + both densities;** interactive OPEN states verified in both themes.
- [ ] **Rendered layout + overflow:** verified by rendering at 320/375/900/1366px both themes, zero
      horizontal overflow — **extend the Playwright overflow suite (ADR-0004)** to `/net-worth`.
- [ ] **Every visual/geometry fix ships a pre-pass assertion (TEMPLATE §7/§8):** KPI-strip tile
      geometry (equal per row) and chart/table fit each get a rendered-measurement pre-pass assertion
      at all breakpoints (learned on Portfolio §12b4-1 — a repeat finding = a fix with no assertion).

---

## 8. BUILD PHASES

*One commit per phase. Backend deltas FIRST. Nothing assembled against a non-existent endpoint.
**Do not start until §9 clears.***

- **Phase 0 — Contract deltas (only if §9 turns ND-1/ND-3/ND-4 toward a backend route):**
  backend-first; regenerate `API-CONTRACT.json` + `docs/openapi.json` same commit; drift green.
  *(Skip if all three resolve frontend-only / read existing endpoints.)*
- **Phase 0a — DESIGN-SYSTEM §5 amendment (only if ND-8 needs a segmented-bar ladder / ND-9 a runway
  card):** author PROPOSED, ratify at `/kitchen-sink` before assembly.
- **Phase 1 — Page assembly:** compose ratified components over the readers; progressive per-card
  loading; honest empty/error/stale states (esp. the empty trend + no_data runway); KPI strip;
  trend; liquidity ladder; runway; composition table; insurance valued line; Net worth↔Portfolio
  cross-links; Cash flow / Insurance signposts.
- **Phase 2 — Tests:** component/render tests + acceptance (§7); **extend the Playwright overflow
  suite to `/net-worth`**; drift/typecheck/lint/build green; visual check both themes/densities.
- **Phase 3a — Scripted pre-pass (MUST be green before the walk):** an `e2e/smoke`-style driver
  against the live app + real backend on a seeded instance; drive every control + link; assert
  populated states + **KPI/geometry pre-pass assertions** + 0 console errors; **resolve how the
  trend gets populated data (ND-1)** so the pre-pass isn't asserting against an empty chart; fix
  everything it surfaces first.
- **Phase 3b — Owner acceptance walk (LIVE, judgment items only):** owner drives the rendered app;
  each finding → a numbered `page-net-worth.md §*` entry, fixed + re-verified live. **Owner closes
  the page** — never self-certified.

---

## 9. NEEDS DECISION — OPEN (owner resolves; nothing resolved here)

Each item is an ambiguity the specs do not settle. Options are laid out for the owner; **I have
resolved none.** Items flagged **⚠ CONTRACT GAP** may need a backend delta (then §3b, backend-first).

- **ND-1 — Net-worth trend data source ⚠ CONTRACT/DATA GAP.** `/net-worth/history` returns persisted
  `NetWorthSnapshot` rows written **only by the worker on a 6-hour interval** (`app/worker.py:136`);
  **no demo seeding, no backfill** (verified §10). So a fresh/demo instance has an **empty or
  single-point trend**, and the Phase-3a pre-pass cannot show a populated chart. Options: **(a)**
  accept an honest EmptyState and accumulate forward (trend is genuinely sparse until the appliance
  runs a while); **(b)** **seed synthetic demo snapshots** (demo-only, like the tag-seed exception)
  so demo/pre-pass render a real line; **(c)** add a **backfill** that reconstructs historical net
  worth from cached price history + transactions (the way `analytics.py` reconstructs the performance
  series) — a backend delta. Which? This gates the trend chart's populated pre-pass.
- **ND-2 — Trend chart shape + window.** `/net-worth/history` takes **no params** and returns **all**
  snapshots. **(a)** Plot **net_worth only**, or **assets / liabilities / net_worth** (the endpoint
  serves all three per point)? **(b)** Window control (1M/3M/1Y/Max like Portfolio) — served as a
  **frontend display slice** of the returned series (no math, allowed) or a **new `?days=` param**
  (backend delta)? Owner picks the series set + windowing mechanism.
- **ND-3 — "Cash & deposits" KPI (D-054) ⚠ CONTRACT GAP.** GLOSSARY defines it as "immediately/
  near-term available cash" but **no reader serves that exact figure** (verified §10). Candidates:
  **(a)** the liquidity **`immediate` rung** — but its served label is "Immediate (cash & listed)",
  i.e. it **includes listed equities**, not just cash & deposits; **(b)** a **new/derived figure**
  (cash class + fixed-deposit) served by a small backend addition; **(c)** redefine the KPI to an
  existing served figure (e.g. `liquid`). Owner picks the definition + source (frontend cannot invent
  the figure — no money math).
- **ND-4 — Composition-by-class table incl. liabilities (D-033) ⚠ CONTRACT GAP.** After the Portfolio
  ND-4 change, `/portfolio/summary.allocation_by_class` is **gross-only (positive holdings, no
  liability row)** — so it **cannot** feed an itemised statement that must **include liabilities**
  (verified §10). No current endpoint serves a per-class breakdown **with** liabilities. Options:
  **(a)** a **new/extended reader** (e.g. `allocation_by_class_signed` or a `/net-worth/composition`
  endpoint that lists every class incl. the negative liability line) — backend delta; **(b)** reshape
  an existing reader to also emit the signed per-class map. Either way it stays a **table, never a
  donut** (D-054). Owner picks the reader shape.
- **ND-5 — Insurance valued line + signpost.** The line reads `/insurance.total_cash_value` (served,
  §10). The **Insurance page is not built** → the "see Insurance" target is a **signpost** (Holdings
  D-092 pattern). Confirm: **(a)** show the line only when `count > 0` / `total_cash_value != 0`, or
  always (with «amount» = 0 / "none")? **(b)** the signpost target/behaviour until Insurance ships.
  **(c)** entity scope — `insurance_report` takes **no `entity_id`** (household-wide), consistent with
  ND-10.
- **ND-6 — ReviewCard source + scope (D-038).** Two readers exist (`/portfolio/review`,
  `/review/centre`); the Review page is unbuilt. **(a)** Which reader feeds the summarised ReviewCard?
  **(b)** Is the ReviewCard **in scope for this milestone**, or deferred until the Review page (show a
  slot/signpost now)? Home also shows a ReviewCard — keep them one summarised reader.
- **ND-7 — Portfolio-headline summary set.** IA says "Portfolio headline (Today's change etc.)" +
  "linked performance sparkline". Confirm the **exact summarised fields** (Today's change only, or +
  Total return / Unrealised P/L?) and the **sparkline window** (`/portfolio/performance` default
  `days`, `benchmark` irrelevant here). It must be a **linked summary** (no recompute, no picker —
  the picker lives only on Portfolio, D-035).
- **ND-8 — Liquidity-ladder visual (possible §5 amendment).** Donut dropped (D-054). Render the
  ladder as **(a)** a **DataTable** (rung · value · pct · cumulative — no new component) or **(b)** a
  **segmented horizontal bar** (a DESIGN-SYSTEM §5 amendment, ratified at kitchen-sink)? Owner picks.
- **ND-9 — Runway card presentation.** Propose: `TrendStat` (runway_months, or the status word when
  not finite) + the served `note` + a small breakdown (monthly expense / income / net burn) +
  `runway_date`. Confirm this needs **no new component** and the honest-state copy (no_data/positive/
  finite) is shown verbatim from `note`. "Edit obligations → Cash flow" is a **signpost** (Cash flow
  unbuilt).
- **ND-10 — Entity scope (D-065).** `liquidity` accepts `entity_id`; `runway`, `net-worth/history`,
  `insurance` do **not** (verified §10). Confirm **household-default, no selector** here (mirror of
  Portfolio ND-8), logging the `entity_id` wiring as a future Accounts-milestone item.
- **ND-11 — Rotation eligibility (D-044).** Confirm **YES** (Wealth dashboard page), matching
  Portfolio.
- **ND-12 — Trend freshness/provenance (D-027).** History points carry `ts` + `currency` but **no
  per-point freshness flag**; `summary` carries `has_stale`/`stale_count`. How is trend/headline
  staleness surfaced (a StalenessChip on the headline; a "last snapshot «ts»" label on the chart)?
- **ND-13 — Thin-history threshold copy (D-086 analog).** Below how many snapshots does the trend show
  the honest "insufficient history" EmptyState (proposal: <2 points), and what is the exact copy?
- **ND-14 — Server-side export (D-050), optional.** Does Net worth offer a CSV export (e.g. the
  composition statement or the trend)? If yes it is server-side (client never builds the file); if no,
  state so. Owner confirms scope.

**Lower-risk confirms (owner ratifies with the above):** subtitle wording (D-023 split) · the KPI
tile set order · whether the performance sparkline is shown at all this milestone vs deferred with
ReviewCard.

---

## 10. VERIFY-FIRST FINDINGS (2026-07-12) — read before assuming shapes (D-019)

Ran the read-what-the-engine-serves pass before drafting §3/§4. **No shape was assumed; gaps went to
§9, not §3b.**

| Item | What the engine actually serves | Source |
|------|--------------------------------|--------|
| Net worth headline | `/portfolio/summary.total_value` = `value_portfolio` net-of-liabilities (= Net worth); ND-4 added served `gross_assets` + `liabilities` | `portfolio.py` `value_portfolio`; summary payload |
| Net-worth history | `{history:[{ts, assets, liabilities, net_worth, currency}]}`, ordered by ts; **persisted `NetWorthSnapshot`** rows | `app/api/v1/routes/portfolio.py:829` |
| Snapshot writer | **worker only, every 6h** (`interval, hours=6`); **no demo seed, no backfill endpoint** | `app/worker.py:79`, `:136`; `app/seed/demo.py` (none) |
| Liquidity ladder | `{base_currency, gross_assets, rungs:[{key,label,value,pct,cumulative_pct}], liquid_pct, liabilities, disclaimer}`; rungs from `liquidity_profile` override else asset class; served labels | `app/services/liquidity.py` |
| `Liquid` definition | **Immediate + Short** rungs — the SAME definition used by runway (`rung_of`) | `liquidity.py:79`, `planning.py:59` |
| Cash runway | `{liquid, monthly_expense, monthly_income, net_monthly_burn, runway_months, runway_date, status, note, disclaimer}`; status no_data/positive/finite; `once` excluded; income offsets burn (D-057) | `app/services/runway.py` |
| "Cash & deposits" KPI | **NOT served** as a distinct figure (GLOSSARY defines it; no reader emits it) | `/portfolio/summary`, GLOSSARY §51 |
| Composition incl. liabilities | **NOT served** — `summary.allocation_by_class` is gross-only (no liability row) after Portfolio ND-4 | `portfolio.py` `allocation()`; page-portfolio §11 |
| Insurance cash value | `/insurance.total_cash_value` (+ `count`); explicitly reported-not-included (`insurance.py:5`) | `app/services/insurance.py:151` |
| Entity scoping | `liquidity` accepts `entity_id`; `runway` / `net-worth/history` / `insurance` do **not** | route signatures |

**Resulting owner sign-off surface (all in §9):** ND-1 (trend data source), ND-3 ("Cash & deposits"
figure), ND-4 (composition-incl-liabilities reader) are the **potential backend deltas**; everything
else is assembly over verified endpoints. **No build until the owner resolves §9.**
