# page-net-worth.md — Net worth (overview) page build plan

**Status: Phases 0/0a/1/2 + Phase-3a scripted pre-pass GREEN (2026-07-12) — STOPPED for the owner's
Phase-3b acceptance walk.** §9 all-resolved (§9); Phase 0 shipped the ND-3/ND-4 backend deltas
(§11); Phase-0a confirmed existing components suffice (no §5 amendment); `/net-worth` assembled +
routed + nav-built; tests + overflow suite extended; ND-1 demo snapshots seeded. The pre-pass drives
the live page on seeded demo and runs GREEN ×3 — populated trend, **on-page statement reconciliation
to the KPI headline** (795,980.93 == 795,980.93), KPI equal-geometry at 320/375/900/1366, 0 overflow
× both themes, 0 console errors, no residual skeletons. Build record: §12; Phase-3b walk batches 1–2
in §13. **Next: the owner's re-verify of batch 2.**

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

### 3b. Contract deltas — APPROVED + PINNED (owner 2026-07-12), BUILT in Phase 0

Two deltas approved (ND-3, ND-4); pinned shapes below; **built backend-first, contract regenerated
same commit** (§11). ND-1 stays frontend + demo-seed (no delta). All others assemble over existing
endpoints.

| kind | Endpoint | Decision | Pinned shape |
|------|----------|----------|--------------|
| **field add** | `GET /portfolio/summary` → **`cash_and_deposits`** | ND-3 / D-054 | additive `float` on the existing dict (untyped endpoint → contract unchanged). **`cash_and_deposits = Σ positive market_value_base of holdings with `asset_class ∈ {cash, fixed_deposit}`**, base ccy today's FX — the literal "Cash & deposits" reading of the GLOSSARY definition. Served string; no client math. |
| **NEW path** | `GET /net-worth/statement` | ND-4 / D-033 | `{ base_currency, rows:[{asset_class, value}], gross_assets, liabilities, net_worth }` — **signed**: asset classes positive, **liability rows negative**, ordered assets-desc then liabilities; `net_worth = value_portfolio.total_value` and **`Σ rows == net_worth == /portfolio/summary.total_value`** (reconciles to the headline). Frontend resolves `asset_class` → label via `/refdata` (D-005). **Contract +1 (→ 129 paths).** |

**Statement ≠ allocation (recorded rule, ND-4):** `allocation_by_class` stays **gross-only** (positive
weights, liabilities excluded, D-033/page-portfolio ND-4). The **statement** is a signed balance that
**includes** liabilities and nets to the headline. The two answer different questions and are **never
interchanged** (enforced in the service docstring `ValuationResult.class_statement`).

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

## 9. NEEDS DECISION — RESOLVED (owner, 2026-07-12)

All 14 items resolved by the owner. Each resolution below **matched an option laid out at draft**
(none required re-opening). The detailed option text is retained beneath the resolutions as the
considered-options record.

**Resolutions (owner, 2026-07-12):**
- **ND-1 — trend data source (RESOLVED).** Product: honest **EmptyState** ("history accumulates as the
  appliance runs") + **`coverageNote`** thin-history handling. **Demo seed gains synthetic net-worth
  snapshots** (demo-only, seed-flag convention — the sanctioned-demo-data pattern, cf. D-104 tags).
  **Backfill REJECTED — recorded:** a reconstructed history needs **historical FX (ROADMAP R-8,
  parked)** and would **fabricate history for manual assets** (property/cash have no price series) —
  contra Guarantee 3. Pre-pass asserts the **demo** chart is populated; the **fresh-instance
  EmptyState** is covered by a render test.
- **ND-2 — trend shape/window (RESOLVED).** `PriceChart` **single-series (net_worth only), NO
  benchmark** on this page. Windows reuse the **ratified set minus intraday** (1M/3M/6M/YTD/1Y/5Y/Max),
  **default Max** while history is young. Windowing is a **frontend display-slice** of the served
  series (no param, no math) — the history endpoint stays param-less.
- **ND-3 — Cash & deposits (RESOLVED, backend delta).** Serve the figure on the net-worth reader per
  the GLOSSARY definition; frontend renders the served string. **Pinned + built** (§3b): `cash +
  fixed_deposit`, positive, base ccy. *(Interpretation flag: the GLOSSARY wording "immediately/
  near-term available cash" is loose; the built figure is the literal "cash & deposits" reading —
  surfaced in the §11 verification report for confirmation.)* Contract regen same commit.
- **ND-4 — composition statement (RESOLVED, backend delta).** **Signed per-class STATEMENT reader**
  (assets by class + liability rows negative + net total reconciling to the headline), **distinct from
  `allocation_by_class`** (allocation stays gross-only; **statement ≠ allocation** — rule recorded in
  §3b + the service docstring). **Pinned + built** (§3b), contract +1 (→129).
- **ND-5 — insurance exclusion line (RESOLVED).** Verbatim D-039/D-081 wording, shown **whenever ≥1
  insurance policy exists**; with **zero policies the line is omitted** (an exclusion notice with no
  exclusions is noise). **Judgment flag:** this conditional display is an **owner call on D-039's
  "stated visibly"** — recorded so a later reader knows it was deliberate, not a drop.
- **ND-6/7 — ReviewCard + Portfolio-headline summaries (RESOLVED).** Standard **P-1
  summary-with-reader** pattern, linked, **no figures beyond what the canonical pages show**. Concrete
  Review reader (`/portfolio/review` vs `/review/centre`) pinned at Phase-1 assembly (non-blocking).
- **ND-8 — liquidity ladder (RESOLVED).** Renders as a **TABLE** (numbers-first, existing components).
  A segmented-bar visual is **NOT built** — noted as possible polish, **no ROADMAP entry**.
- **ND-9 — runway card (RESOLVED).** Card **labels its basis honestly** — the served burn-rate
  definition + period next to the figure + GLOSSARY [Help]. **Engine basis verified UNAMBIGUOUS**
  (`runway.py`): `liquid ÷ recurring **monthly** net burn` (recurring expenses − income,
  monthly-equivalent via `MONTHLY_FACTOR`), at today's FX, `once` excluded (D-057); served
  `note`+`disclaimer` state it. → No STOP; no new component.
- **ND-10 — entity scope (RESOLVED).** **Household-default, no selector** (Accounts precedent); log
  the `entity_id` wiring as a future Accounts item.
- **ND-11 — rotation (RESOLVED).** **Eligible: YES.**
- **ND-12/13 — freshness + thin-history (RESOLVED).** Served freshness flags + `coverageNote` copy per
  the established pattern; **no new invention**.
- **ND-14 — CSV (DECLINED, not deferred).** **No CSV on this page** — exports are **Reports** territory
  (D-038/D-050). Recorded as declined.

---

**Considered options (draft record — the resolutions above are authoritative):** each item was an
ambiguity the specs do not settle; options were laid out for the owner. Items flagged **⚠ CONTRACT
GAP** were the ones that became backend deltas (ND-3/ND-4).

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
figure), ND-4 (composition-incl-liabilities reader) were the **potential backend deltas**; everything
else is assembly over verified endpoints. **→ §9 now RESOLVED; Phase 0 built ND-3 + ND-4 (§11).**

---

## 11. PHASE 0 — CONTRACT DELTAS BUILT (2026-07-12) — STOP for owner review

Built the two approved deltas backend-first (ND-3, ND-4), contract regenerated in the same commit,
backend tests added. **Phase 0 completes here and STOPS for the owner** before Phase-0a/1.

**Shipped:**
1. **ND-3 — `cash_and_deposits` on `GET /portfolio/summary`** (`app/api/v1/routes/portfolio.py`):
   `Σ positive market_value_base of holdings with asset_class ∈ {cash, fixed_deposit}`, base ccy,
   `to_display` string. Additive field on the untyped dict endpoint → **contract paths unchanged**.
2. **ND-4 — `GET /net-worth/statement`** (new): served by `ValuationResult.class_statement()`
   (`app/services/portfolio.py`) → `{base_currency, rows:[{asset_class, value}], gross_assets,
   liabilities, net_worth}`; signed (liabilities negative, ordered last); **`Σ rows == net_worth ==
   summary.total_value`**. **Contract +1 → 129 paths** (`API-CONTRACT.json` + `docs/openapi.json`
   regenerated, drift green).

**Tests (backend, `tests/integration/test_portfolio_engine.py`):**
- `test_class_statement_is_signed_and_reconciles_to_net_worth` — **exact Decimal reconciliation** to
  the headline (7000 = 1000 equity + 10000 cash − 4000 liability), liabilities negative + ordered
  last, and statement ≠ allocation (no liability row in allocation).
- `test_net_worth_statement_and_cash_deposits_reconcile_at_api` — HTTP boundary: `cash_and_deposits`
  served + cross-checked against the holdings it sums; statement nets to the headline; liabilities
  negative. **Suite: 492 passed** (+2); ruff + contract-drift green.

**⚠ One interpretation to confirm (ND-3):** GLOSSARY defines "Cash & deposits" loosely as
"immediately/near-term available cash". The built figure is the **literal reading = cash class +
fixed-deposit class**. If the owner intended a different set (e.g. include mutual-fund/"short"
liquidity, or cash only), that's a one-line change — **confirm before Phase 1**.

**Resulting Phase-0a scope (as predicted — little):**
- **No new chart modes.** The trend is `PriceChart` **line mode, single series** (ND-2) — the existing
  component; **no comparison/benchmark** here.
- **No new components.** KPI strip = `TrendStat`; net-worth statement + liquidity ladder = `DataTable`
  (ND-8 table, not a bar); runway = `TrendStat` + served note (ND-9); ReviewCard/sparkline = existing.
  **No DESIGN-SYSTEM §5 amendment expected** — Phase-0a is a **confirm-at-kitchen-sink** that
  `PriceChart`(line) + `DataTable` + `TrendStat` cover the page, not an amendment.
- **Demo-seed synthetic net-worth snapshots (ND-1)** is a Phase-1 data task (demo-only, seed-flag),
  needed so the Phase-3a pre-pass can assert a populated trend; the fresh-instance EmptyState gets a
  render test.

**Sign-off to start Phase-0a/1:** confirm the ND-3 interpretation · confirm no §5 amendment is wanted
(existing components suffice) · then Phase-0a (kitchen-sink confirm) → Phase 1 assembly.

**→ Owner confirmed both (2026-07-12):** ND-3 = cash + fixed_deposit ("deposits" = fixed deposits,
not short-liquidity funds) — the KPI's scope is on record here; no §5 amendment (existing components
cover it). Phases 0a/1/2/3a executed below (§12).

---

## 12. PHASES 0a / 1 / 2 / 3a — BUILT + PRE-PASS GREEN (2026-07-12) — STOP for the owner's walk

- **Phase 0a — CONFIRM ONLY (no specimens).** Owner confirmed `PriceChart`(line) + `DataTable` +
  `TrendStat` cover the page; **no DESIGN-SYSTEM §5 amendment**, no kitchen-sink specimen to ratify.
- **Phase 1 — assembly** (`frontend/src/routes/NetWorth.tsx` + `.css`, `api/net-worth.ts`;
  `/net-worth` routed, nav entry `built`). Composes the OWNED content over the verified readers with
  **progressive per-card loading**: KPI strip (Net worth / Gross assets / Liabilities / **Cash &
  deposits = cash + fixed_deposit**, ND-3) with **equal geometry straight from the grid** (§12b4-1,
  no wrapper); net-worth trend (`PriceChart` line, single series, **client-sliced windows**, default
  Max, honest EmptyState + coverageNote when thin, ND-1/ND-2); composition **statement** (`DataTable`,
  signed, negative liability row, net total that reconciles to the headline, ND-4 — "statement ≠
  allocation" stated on-page); liquidity ladder (`DataTable`, ND-8); cash runway (honest no_data/
  positive/finite + **basis label**, ND-9); insurance valued exclusion line (verbatim D-039/D-081,
  **shown only when ≥1 policy**, ND-5); Portfolio-headline + sparkline + `ReviewCard` summaries (P-1,
  ND-6/7). **ND-1 demo snapshots:** 26 synthetic weekly `NetWorthSnapshot` rows (demo-only, seed-flag)
  ending at today's real seeded net worth — no history fabricated on a real install.
- **Phase 2 — tests.** `NetWorth.test.tsx` (7, incl. the **fresh-instance empty-history EmptyState**
  render test); overflow suite extended to `/net-worth` (320/375/900/1366 × both themes) + the
  shared-inset check. Hardening: `DataTable` defaults `rows=[]`; a partial liquidity payload degrades
  to an EmptyState (never crashes). Two shell tests updated (Net worth now built; unbuilt-route
  example → `/accounts`). **Frontend check: 120 vitest + 49 overflow + lint/typecheck/tokens/build.**
- **Phase 3a — scripted pre-pass GREEN ×3** (`e2e/smoke/net-worth-smoke.spec.ts`, dev-only). On the
  seeded demo (post ND-1 re-seed): **populated trend line**; **on-page statement reconciliation to the
  KPI headline** (795,980.93 == 795,980.93); **KPI equal width+height per row** at all four
  breakpoints; liquidity ladder + Liquid line; runway basis label; insurance line omitted (0 demo
  policies); **no residual skeletons**; **0 overflow** at 320/375/900/1366 × both themes; **0 console
  errors**. Backend: statement/cash-deposits reconciliation verified live + by tests (§11).

**Commits:** `2282926` (draft) · `a2c3c1e` (§9 + Phase 0 deltas) · `b2af0fb` (Phase 1) · `0db1475`
(Phase 2) · Phase-3a close-out. **STOP — the Phase-3b acceptance walk is the owner's.**

---

## 13. PHASE-3B WALK — batch 1 (owner, 2026-07-12)

Recorded, fixed, pre-pass re-run green, awaiting owner re-verify. (Page NOT closed.)

1. **§12b1-1 — KPI strip centre-aligned.** Applied the ratified centre-aligned tile treatment
   (`.nw__kpis .lf-stat { align-items: center; text-align: center }`), matching the Portfolio rails.
   Equal geometry still comes from the grid (§12b4-1). Visual — owner ratifies at re-verify.
2. **§12b1-2 — Composition totals x-offset BUG (structural fix + assertion).** The totals
   (Gross assets / Liabilities / Net worth) were a `<dl>` OUTSIDE the table's scroll region, so their
   right-aligned values ignored the scrollbar gutter that shifts the body's Value column → a
   horizontal offset. **Fixed structurally:** `DataTable` gains a **`footer`** prop rendering total
   rows as `<tfoot>` inside the SAME `<table>` — footer and body now share **one column grid AND the
   scroll gutter by construction**, so a total can never drift from its column. The net row is ruled +
   bold (`.lf-table__foot--emph`). **Pre-pass assertion added:** the tfoot Value cell's right edge is
   x-aligned (≤1px) with a body Value cell, **both themes** — verified 0px light + dark. (The runway
   card keeps its own `.nw__totals` dl — no table there, no gutter, no offset.)
3. **§12b1-3 — Portfolio + Review summaries equal height.** The row grid now stretches
   (`align-items: stretch`) and the Review cell fills its stretched cell (`display:flex` +
   `flex:1`), so content can't shrink a card. **Pre-pass assertion added** (same rule as the KPI /
   §12b4-1 geometry): the two `.nw__summaries` cards are equal height per row — verified 443/443.
4. **§12b1-4 — VERIFY ONLY (no build): snapshot schema for the R-28 liquid/illiquid trend.**
   Reported, nothing built (snapshot shape untouched, no chart mode):
   - **`net_worth_snapshots`** stores **scalar totals only**: `ts, base_currency, assets,
     liabilities, net_worth`. **No liquidity or class decomposition.**
   - **`portfolio_snapshots`** has a `detail_json` Text column (comment "allocations etc."), but the
     worker (`app/worker.generate_snapshots`) **writes it empty (`"{}"`)** — so **no historical
     decomposition exists** in practice.
   - **Implication for R-28:** a liquid-vs-illiquid stacked-area trend has **no historical data
     today**. It would require the worker to **start persisting a liquidity/class split going
     forward** (populate `detail_json` or add columns). **ND-1's no-backfill honesty applies to any
     split too:** historical liquidity can't be reconstructed without historical FX/prices (ROADMAP
     R-8, parked) and would **fabricate** a split for manual assets (property/cash have no series).
     → R-28 should be a **forward-only, opt-in** decomposition, mirroring ND-1. **Owner's call.**

**Checks after batch 1:** frontend **120 vitest + 49 overflow + lint/typecheck/tokens/build** green.
Live pre-pass GREEN ×3 (centre-aligned KPIs, footer↔body value x-aligned 0px both themes, summary
cards equal height 443/443, populated trend, on-page reconciliation, 0 overflow, 0 console errors).

**Batch 1 — RATIFIED (owner, 2026-07-12, seen live):** centre-aligned KPI strip (§12b1-1).

## PHASE-3B WALK — batch 2 (owner, 2026-07-12)

Recorded, fixed, pre-pass re-run green, awaiting owner re-verify. (Page NOT closed.)

1. **§12b2-1 — DataTable footer: separator rule above the totals.** Added a visible separator rule
   above the totals section (the first `<tfoot>` row) **in the component** — every reconciling-totals
   table inherits it (`.lf-table tfoot .lf-table__foot:first-child .lf-table__td { border-top: …
   --border-strong }`), both themes. Pre-pass asserts the rule is present (1px) light + dark.
2. **§12b2-2 — Portfolio summary card: sparkline overlapped the stat tiles (BUG + assertion).** The
   card body had no vertical-flow discipline (the `width:100%; overflow:visible` Sparkline sat on the
   stat grid). Fixed: content flows in a **flex column with a gap** (`.nw__psummary`) and the
   sparkline lives in its own full-width block (`.nw__spark`). **Pre-pass assertion added:** in the
   `[data-card="portfolio-summary"]` card, the sparkline does **not** overlap `.nw__prow` and all
   content stays **within the card bounds** at 320/375/900/1366 — verified (−8px gap, within=true).
3. **§12b2-3 — Honest metadata: PriceChart legend "View: Simple" described an absent control.** The
   legend showed `View: Simple` even where no Simple/Advanced toggle exists. **Rule recorded: a
   metadata/legend line describes only a control that EXISTS on the page.** Fixed in `PriceChart` —
   the View line renders only when `controls` is passed (its toggle is present); Net worth (no toggle)
   omits it, Instrument Detail (has the toggle) keeps it. **Audit of all `MetaStrip` usages**
   (InstrumentDetail, KitchenSink): those items describe **data/taxonomy** (Class, Sector, Currency…)
   or **present controls** (theme/density) — **no absent-control lines**; the only offender was the
   PriceChart legend, now fixed.
4. **§12b2-4 — ROADMAP R-28 registered (+ mirrored to DECISIONS.md register).** Liquid-vs-illiquid
   net-worth trend decomposition — **forward-only + opt-in** per the §12b1-4 schema report + ND-1
   honesty: worker persists a liquidity split **going forward** (snapshot detail, shape TBD in the
   plan file); **NO backfill** (grounds recorded: historical FX R-8 + manual-asset fabrication); a
   **`PriceChart` stacked-area mode is a §5 amendment gate**; plan-file gate standard. **Nothing
   built** (snapshot shape untouched, no chart mode). ROADMAP.md R-28 + DECISIONS register.

**Reusable outcomes:** the `DataTable` `footer`/`<tfoot>` totals primitive now carries its own
section separator (any reconciling-totals table inherits it); the **honest-metadata rule** (legend/
MetaStrip lines describe only present controls) is recorded for future pages.

**Checks after batch 2:** frontend **120 vitest + 49 overflow + lint/typecheck/tokens/build** green.
Live pre-pass GREEN ×3 (totals separator both themes, no sparkline overlap + in-bounds all
breakpoints, View line gone, plus all batch-1 + Phase-3a assertions).
