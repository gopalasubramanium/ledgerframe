# 01 — Feature Inventory

Every user-facing feature, grouped by page. Routes are declared in
`frontend/src/App.tsx:164`. The nav order/labels are in `frontend/src/lib/nav.ts`
(user-customisable per device). API method names refer to `frontend/src/lib/api.ts`
(full endpoint map in 03). Charts are SVG components in `components/Chart.tsx`
(`Donut`, `Sparkline`, `LineSeries`) plus an ECharts-based `Heatmap` (only page using
ECharts). Badges/pills in `components/ui.tsx` (`DataBadge`, `ChangePill`, `Figure`, `Card`,
`DemoBadge`, `Skeleton`) and `GlossaryTerm`.

## Global chrome (App.tsx)

| Element | Behaviour |
|---------|-----------|
| Top bar | Wordmark, `DemoBadge` (when demo_mode), Clock (timezone), ActivityPip (toasts/running actions), theme cycle (light→dark→system), **Simple/Expert toggle** (`toggleMode`), rotation toggle, **Ask** button (opens `AskPanel`) |
| Sidebar | Collapsible rail (localStorage `lf_sidebar_collapsed`); mobile drawer; nav items from `loadNav()` |
| StaleBanner | Above main content; polls `/system/staleness`, offers one-click refresh |
| UpdateBanner | Polls version-check; prompts update |
| PersonaOnboarding | First run (localStorage `lf_persona` unset) — sets mode+density (see 06) |
| Rotation | Cycles `["/", "/portfolio", "/markets", "/heatmap", "/news"]` every 30s when enabled |
| LockScreen | Shown when `locked` (PIN set) or LAN-exposed without PIN (setup mode) |
| Ask panel | Grounded AI chat (SSE `streamChat`), shows fact pack + streamed answer |

### Simple/Expert toggle — **only two pages branch on `mode`**
- **Home** (`Home.tsx:26`): Simple hides ticker strip, allocation card, movers-performance-topholdings row, markets row, headlines — leaving portfolio headline + movers + full-width briefing. Expert shows everything.
- **Settings** (Appearance card): sets the mode.
- **All other pages ignore mode** — they render identically in Simple and Expert. (See 08-TECH-DEBT: the toggle is nearly a no-op app-wide.)

---

## Home (`/`)

Master dashboard aggregating Portfolio + Markets + News. APIs: `home`, `portfolioSummary`,
`holdings`, `performance(90,SPY)`, `watchlists`, `news`, `marketsGlobal`, `refreshBriefing`.

| Feature | What | Charts/Tables/Badges | DUPLICATION |
|---------|------|----------------------|-------------|
| ReviewCard | "What needs attention" (from `/review/centre`) | chips | Also on Snapshot; canonical = Review page |
| Ticker strip (Expert) | Source select: markets/holdings/global/watchlist | TickerStrip | Markets page shows same quotes |
| Portfolio headline | Total value, today, total return, unrealised, cost basis + perf sparkline | `Sparkline`, `DataBadge` stale | Portfolio, Snapshot, Holdings all show value/day/unrealised |
| Allocation (Expert) | Asset-class donut + top sectors bars | `Donut` | Portfolio (donut ×3), Snapshot (donut) |
| Today's movers | Gainers/detractors | MoverList | Portfolio contributors, Markets movers |
| Performance (Expert) | 90d sparkline + return/excess/maxDD | `Sparkline` | Portfolio PerformancePanel (fuller) |
| Top holdings (Expert) | Top 5 by value, weight bars | — | Holdings table, Portfolio concentration |
| World indices / your markets / watchlist+FX (Expert) | Compact quote cards | ChangePill | Markets page (canonical) |
| Daily Briefing | AI/deterministic briefing text + refresh | Markdown | News page briefing |
| Headlines (Expert) | 6 RSS headlines | — | News page (canonical) |

## Portfolio (`/portfolio`)

Analytics view. APIs: `portfolioSummary`, `holdings` (+ panels fetch their own).

| Feature | Charts/Tables | DUPLICATION |
|---------|---------------|-------------|
| Stat rail (6): value, today, total return, unrealised, cost basis, positions | — | Home headline, Snapshot KPI, Holdings header |
| PerformancePanel | line chart vs benchmark, benchmark picker | Home perf, Snapshot trend |
| Contributors (top/bottom) | MoverList | Home movers |
| Allocation by class / sector / currency | `Donut` ×3 + legends | Home/Snapshot donuts |
| Concentration | weight bars (top 6) | Home top holdings, key-stats concentration |
| KeyStatsPanel | metric grid (XIRR, TWR, vol, drawdown, concentration…) via `stats` | ReportsPack RiskAttribution |
| AttributionPanel | per-class/sector contribution via `attribution` | ReportsPack |
| CostOfOwnershipCard | recorded fees + estimated ongoing cost | — |
| TagsCard | allocation by tag + per-holding tag editor | — |

## Holdings (`/holdings`)

The single add/edit/delete surface. APIs: `portfolioSummary`, `holdings` + editor APIs.

- **Sortable table** (7 cols: Asset, Qty, Price, Value, Cost basis, Unrealised, Day) with `aria-sort`, client search, **CSV export** (client-side), stale ⚠ and Manual markers, per-row link to InstrumentDetail.
- Buttons: Pricing health link, Export, **Edit/import** → `PortfolioEditor` modal, **Add asset** → `AddAssetWizard`.
- `PortfolioEditor`: Transactions tab (ledger table, sort/search, add/edit/**soft-delete with 10s undo**, CSV template download, **2-step import** preview→commit) + Manual assets tab (add/edit/delete). Txn form fields: datetime, type (select), symbol (free text, auto-currency from suffix), asset_class (select, 6 classes), country (select), qty, price, fees, taxes, currency (select), note. Split/bonus hints.
- `AddAssetWizard`: guided asset creation (see 06).
- DUPLICATION: value/positions header dup of Portfolio/Snapshot.

## Markets (`/markets`)

Region-first (India/Singapore/US/Global/Watchlists). APIs: `marketsOverview`, `marketsGlobal`,
`watchlists`, `news`, `search`, watchlist mutations.

- Region tabs with held-counts; symbol **search** (dropdown, add-to-watchlist); region indices strip; region movers (gainers/losers cards); region news; instrument grid (all/held/watch subfilter, star toggle); Global tab world-indices grid (real vs ETF-proxy badge). Watchlists panel: create/delete lists, add/remove items.
- Badges: `ChangePill`, `DataBadge` stale, held ● marker, real-indices/ETF-proxy label.
- DUPLICATION: quotes/movers/news overlap Home & News; `/global` route redirects here.

## Heatmap (`/heatmap`)

APIs: `holdings`, `marketsOverview`. Single ECharts treemap/heatmap of holdings (only ECharts
usage in the app). DUPLICATION: same holdings data as Holdings/Portfolio.

## News (`/news`)

APIs: `groupedNews`, `holdings`, `home`, `marketsGlobal`, `news`, `refreshBriefing`.
Grouped headlines by area (My holdings/India/Singapore/US/Global/Macro-FX); My holdings ranked by
relevance (weight×recency); AI briefing + refresh. Chips per area. DUPLICATION: briefing (Home),
headlines (Home/Markets).

## Snapshot (`/snapshot`) — "Net worth"

APIs: `portfolioSummary`, `holdings`, `performance(365,SPY,include_manual)`, `liquidity`, `runway`.

- ReviewCard; KPI strip (net worth, assets, liabilities, cash & deposits); net-worth trend (`LineSeries`, 12mo pct chip); composition donut; **net worth by class table** (value/cost/unrealised/%NW); **liquidity ladder** (rungs w/ bars, liquid%, `GlossaryTerm` term-liquidity); **cash runway** (status: no_data/positive/finite, `GlossaryTerm` term-runway).
- DUPLICATION: value/day/allocation dup of Home/Portfolio; net-worth trend also in ReportsPack.

## Policy (`/policy`)

APIs: `policy`, `policyDrift`, `putPolicy`, `putPolicyTargets`. Set target allocation per
dimension (asset_class/currency/region) with bands + concentration limit; drift table (target vs
actual, over/under/in_band chips, `GlossaryTerm` term-drift); 2 tables. DUPLICATION: drift also in
ReportsPack + Review.

## Planning (`/planning`)

APIs: `goals`, `obligations`, goal/obligation CRUD (+ ContributionsCard: `contributions` CRUD).
Goals (name, target amount, target date, currency, basis, note) with progress; obligations
(recurring/one-off, expense/income) feeding runway; contributions (invest/withdraw/prepay). Inline
`type="date"` inputs, edit ✎. DUPLICATION: runway inputs surface on Snapshot/Scenarios.

## Reports (`/reports`)

APIs: `realisedGains`, `statements`, `taxLots`. Year + long-term-days controls; statements cards
(income/fees/cashflow/realised-vs-unrealised); realised gains tables (per currency, current-FX +
trade-date-FX totals, `GlossaryTerm` term-realised-gains); open tax lots table (`GlossaryTerm`
term-fifo); **CSV exports** (realised gains, statements); link to quarterly pack. Streams an AI
report? (grep showed streamChat use — a "explain this report" helper).

## Reports → Pack (`/reports/pack`)

APIs: `netWorthHistory`, `reviewCentre`, `entities`, and per-entity `portfolioSummary`,
`policyDrift`, `realisedGains`, `stats`, `attribution`. Print-optimised quarterly pack:
consolidated (net-worth trend + review) then per-entity sections (net worth donut, drift table,
realised table, risk+attribution). Reuses reader outputs verbatim (disclaimers preserved). Print
button.

## Review (`/review`) — "Review Centre"

APIs: `reviewCentre`, `reviewHistory`, `groupedNews`, `logReview`. Section verdicts
(trust/policy/liquidity/goals/changed), attention list, **Mark reviewed** (records ReviewLog with
note + next review date), review history table, `GlossaryTerm` ×2. DUPLICATION: ReviewCard on
Home/Snapshot shows same data.

## Insurance (`/insurance`)

APIs: `insurance`, `insuranceMeta`, insurance CRUD. Protection register: totals (cover, cash value,
premium), cover-by-type, upcoming renewals, policies table; add/edit/delete (policy_type & frequency
from `/insurance/meta`; insurer, insured_person, nominee free text; date inputs; documents checklist).
Cash value **not** in net worth (isolated).

## Estate (`/estate`)

APIs: `estate`, `estateMeta`, contacts + documents CRUD, profile PUT. Will status/executor,
contacts (roles from meta, phone/email free text), documents (category from meta, status), readiness
counts. Date inputs, checkboxes for document "have".

## Accounts (`/accounts`)

APIs: `accounts` + (via PortfolioEditor?) account CRUD. Wealth grouped by account/institution
(rollup: value, holdings count, asset classes, currencies, stale/low-confidence counts, last
activity). Add/edit/delete account (kind from `ACCOUNT_KINDS`; institution free text). DUPLICATION:
holdings values dup of Holdings.

## Scenarios (`/scenarios`)

APIs: `scenarios`. Stress "what-if" on today's holdings: exposures (equities/crypto/property/FX),
7 asset shock scenarios, liquidity what-ifs (income-stop, obligation-due). 7 cards. Read-only.

## Pricing Health (`/pricing-health`)

APIs: `pricingHealth`, `identifierDuplicates`, `refreshHolding`. Per-holding diagnostics table
(instrument, class, value, valuation label, **status chip** Fresh/Delayed/EOD/Cached/Manual/
Estimated/Unavailable, **confidence** score+band, source+entitlement, **routing** source + map/auth
chips, as-of, refresh ↻ + correct-source ⚙). Status-filter chips, search, identifier-duplicate
banner, portfolio confidence card (`GlossaryTerm` term-confidence). Canonical provenance home.

## Instrument Detail (`/instrument/:symbol`)

APIs: `history`, `instrumentNews`, `holdings`, `watchlists`, `editInstrument`, `setOngoingCost`
(+ `/instruments/{symbol}` for meta). Price + day move, `LineSeries` price history, taxonomy/
identifiers/asset-detail, news, position (if held), edit instrument (asset_class/country/name/
source_override), set ongoing cost (bps), add to watchlist. `DataBadge`. Also streams an AI
"explain this instrument" via streamChat.

## Help (`/help`)

APIs: `helpContent`. Searchable knowledge base (pages + terms + guarantees) — see 09-GLOSSARY.

## Legal (`/legal`)

Static: license/trademark/disclaimer content, an "I understand" checkbox. 4 cards.

## Settings (`/settings`)

4 tabs: **Prices** (data source provider + API key, av-tier plan badge, refresh/fetch-history/
reclassify/clear-data, AMFI/CoinGecko/ECB/Kite opt-in cards), **General** (base currency, timezone,
rotation/refresh/sleep/stale intervals, appearance theme/mode/density/language/reduced-motion/
high-contrast, nav customization, security PIN + autolock + lock now, advanced web-port/data-folder/
backups/age-recipient), **Intelligence** (AI config card, news feeds textarea + test), **System**
(About, system controls LAN/voice/AI/kiosk on-off via admin helper, maintenance restart/status/
doctor/backup/update, status & data-sources diagnostics). Toast notifications.

---

## Cross-page duplication summary (full list — canonical home recommended in 06)

| Information | Appears on | Recommended canonical |
|-------------|-----------|-----------------------|
| Total value / day change / unrealised | Home, Portfolio, Holdings, Snapshot, Review, ReportsPack | Portfolio (headline), reused via one summary reader |
| Allocation donut (class) | Home, Portfolio, Snapshot, ReportsPack | Portfolio |
| Top movers / contributors | Home, Portfolio, Markets | Portfolio |
| Performance chart | Home, Portfolio, Snapshot | Portfolio |
| Net-worth trend | Snapshot, ReportsPack | Snapshot |
| Review/attention (ReviewCard) | Home, Snapshot, Review | Review |
| Briefing | Home, News | News |
| Headlines | Home, Markets, News | News |
| Quotes/indices | Home, Markets, InstrumentDetail | Markets |
| Drift | Policy, Review, ReportsPack | Policy |
| Runway | Snapshot, Scenarios, Review | Snapshot |
| Confidence/provenance | PricingHealth, Review (trust) | PricingHealth |

<!-- AUDIT COMPLETE -->
