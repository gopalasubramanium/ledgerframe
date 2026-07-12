# page-markets.md — Markets page build plan

**Status: PLAN ONLY — owner reviews §9 before any code.** Drafted 2026-07-12 from
`TEMPLATE-page-build.md` (incl. the §7/§8 fail-first + reproduce-the-defect-first amendments, the
Reports-group/worklist-shape note, the Phase-3a scripted-pre-pass standard, and progressive-per-card
loading). Verify-first pass done (§10 — read what the markets/quotes/indices/watchlist readers
actually serve before assuming shapes, D-019). **Nothing is built.** Every ambiguity is in §9; the
owner resolves them.

Markets is the **Markets-group** home page and the canonical home for **quotes, indices, market
status, Gainers/Losers, symbol search, the instrument grid, the Global tab, and watchlist
management** (IA §5, D-037/D-034/D-051/D-052). It **absorbs the removed `/global` page's job** (the
Global tab; no redirect exists, D-042). Shipping it **unblocks ROADMAP R-17** — the TickerStrip's
index entries link here (§9 ND-5, REQUIRED in scope).

---

## 1. IDENTITY

*Source: INFORMATION-ARCHITECTURE.md §2 (page map), §3 (nav + rotation); DESIGN-SYSTEM.md §3.*

| Field | Value | Spec ref |
|-------|-------|----------|
| Page name (H1 = nav label = route) | **Markets** | IA §2, D-022 |
| Route | `/markets` | IA §2 |
| Nav group | **Markets** (Markets · Heatmap · News) | IA §3 |
| Page template | **Overview + worklist hybrid** — market-status/indices/Gainers-Losers header over an instrument-grid + watchlists worklist body. **Template fit is a §9 item (ND-3).** | DESIGN-SYSTEM §3 |
| Rotation eligibility | **Confirm ND-9** (dashboard-class? Markets is a live-data page) | IA §3 (D-044) |
| One-line purpose | **Markets** — quotes, indices, market status, **Gainers/Losers** (price-move lists, D-034), symbol search, the instrument grid, the **Global** tab (world indices), and **watchlist management**. Region-news dropped → links to News (D-051). | IA §2/§5 |

**`/global` is removed with no redirect (D-042);** this page **owns the Global tab** that did its job.

---

## 2. OWNERSHIP TABLE

*Copied verbatim from INFORMATION-ARCHITECTURE.md §5 (Markets). Never re-derived.*

**Owns (canonical, authoritative, fully explained here):**
- **Quotes, indices, market status** (D-037).
- **Gainers / Losers** — **price-move** lists ranked by price change (D-034); **NOT**
  Contributors/Detractors (that contribution-weighted pair is **Portfolio's**, D-024). GLOSSARY
  which-list rule is protected.
- **Region tabs; symbol search; the instrument grid; the Global tab** (world indices).
- **Real-vs-ETF-proxy badge** — a **protected honesty feature** (D-051): a world index shown via a
  liquid ETF proxy (not the real index level) is labelled as such, never passed off as the index.
- **Watchlist management** — create/delete lists, add/remove items — **management lives ONLY here**
  (D-052).

**Dropped:** region-news blocks → **link to News region groups** (D-051).

**Summarises:** — (nothing).

**Links to:** **News** (region groups, D-051) · **InstrumentDetail** per symbol (scoped quote/news,
P-3) · **Heatmap** (sibling Markets page). The **TickerStrip index entries link here** (R-17, ND-5).

**Enforcement corollary (P-1/D-031):** every quote/index/status figure is a **served display value**
from the markets readers; the frontend performs **no money math** (ranking Gainers/Losers is a
**display sort of served `change_pct`**, not a computation — confirm framing in ND-1).

---

## 3. API SURFACE

*Source: API-CONTRACT.json (frozen) + API-CONTRACT.md. Verify-first shapes are pinned in §10.*

### 3a. Endpoints consumed (already in the frozen contract)

| Method + path | Purpose on this page | Response shape (verified §10) |
|---------------|----------------------|-------------------------------|
| `GET /markets/overview` | the instrument grid + market status | `{quotes, instruments:[{symbol,name,asset_class,currency,country,held,quote}], market_status, demo_mode}` — **no Gainers/Losers list (ND-1)**; no region param (ND-2) |
| `GET /markets/global` | the **Global tab** (world indices by region) + the D-051 badge | `{groups:[{region, items:[{symbol,label,quote}]}], market_status, demo_mode, real_indices}` — indices are a **hardcoded backend universe** (`_GLOBAL_MARKETS`, ND-7) |
| `GET /markets/search?q=` | symbol search | `{results:[…provider search hits…]}` |
| `GET /watchlists` | watchlist panel (lists + item quotes) | `{watchlists:[{id,name,items:[{symbol,name,quote}]}]}` |
| `POST /watchlists` · `DELETE /watchlists/{id}` | create / delete a list (**`require_auth`**, ND-4) | `{ok,id}` / `{ok}` |
| `POST /watchlists/{id}/items` · `DELETE /watchlists/{id}/items/{symbol}` | add / remove an item (**`require_auth`**) | `{ok}` |
| `GET /instruments/search?q=&asset_class=` | class-aware picker for add-to-watchlist (D-097) | `existing`/`other_class`/`suggestions` (reused from Holdings) |

### 3b. Contract deltas (needed but not in the baseline — BUILD BACKEND-FIRST)

**None asserted.** The one candidate — a **served Gainers/Losers list** — is raised in **§9 ND-1**
(the alternative is a display-sort of the served overview quotes, no delta). Suspected gaps go to
**§9, not a §3b guess.** Any approved delta regenerates `API-CONTRACT.json` + `docs/openapi.json`
same commit (`make api-contract-check`).

---

## 4. COMPONENTS

*Source: DESIGN-SYSTEM.md §5 (ratified) + §3 (templates). Ratified only; a missing affordance is a §9
amendment request. Data-wired to real endpoints.*

| Ratified component | Role on this page | Data source (real endpoint) | Not exercised at kitchen-sink |
|--------------------|-------------------|-----------------------------|-------------------------------|
| **PageHeader** | H1 "Markets" + subtitle + actions (search, new watchlist) | — | multiple actions |
| **DataTable** | the **instrument grid**; **Gainers/Losers** lists; **watchlist** item tables | `/markets/overview.instruments`, `/watchlists` | sort by served `change_pct`; a `held` badge column |
| **QuoteCardRow** (D-046) | compact **indices / Global-tab** quote rows (or the grid header) | `/markets/global.groups` | a quote row with the real-vs-ETF-proxy badge |
| **Select** (or a tab control) | **region tabs**, quote-view scope | view-scope (ND-2) | region tabs — a Tabs affordance may be a §5 amendment (ND-2) |
| **InstrumentPicker** | symbol **search** + add-to-watchlist (class-aware, D-097) | `/markets/search`, `/instruments/search` | search feeding both the grid and watchlist-add |
| **RowMenu** | watchlist item actions (remove; open); grid row → InstrumentDetail | — | remove-item (auth) |
| **ConfirmDialog (+[S])** | create/delete list, remove item (`require_auth`, ND-4) | — | `[S]`-gated watchlist mutation |
| **ProvenanceBadge / StalenessChip** | per-quote freshness; the **real-vs-ETF-proxy** badge (D-051) | `quote` fields; `real_indices` + per-item symbol | protected-honesty proxy badge |
| **TrendStat / a status pill** | **market status** (open/closed) + headline index moves | `market_status` | a market-open/closed indicator |
| **EmptyState** | no watchlists, empty search, unreachable reader | reader shapes | empty-watchlist / no-results |
| **GlossaryTerm** | `[Help]` on Gainers/Losers, Index, ETF proxy, Market status | GLOSSARY | Gainers/Losers vs Contributors/Detractors distinction |

**Affordances the ratified inventory may lack (amendment — resolve in §9 before build):**
- **Region tabs (ND-2).** If region filtering is a **tab bar** (not a `Select`), a **Tabs** affordance
  may be a DESIGN-SYSTEM §5 amendment. Confirm `Select`/segmented buttons suffice, or propose Tabs.
- **Market-status pill.** A small open/closed indicator — confirm a ratified element covers it
  (a chip/`TrendStat`) or it is a tiny §5 note.

**Component usage rules the build must honour (template §4):**
- **Which-list rule (D-024, protected):** these are **Gainers/Losers** (price-move), **never**
  Contributors/Detractors — copy is guarded.
- **No frontend money math:** Gainers/Losers is a **display sort of served `change_pct`** (ND-1), not
  a computed ranking of prices.
- **Real-vs-ETF-proxy is protected honesty (D-051):** a proxy is always labelled; never shown as the
  real index.
- **Watchlist mutations are `require_auth`** (`[S]`, ND-4); server-side; no client fabrication.
- **Scroll = content only, header outside (D-101);** grids/watchlists cap at `--table-max-h`.
- **DataTable caption sr-only inside titled cards** (DESIGN-SYSTEM §5.2); reconciling totals use `<tfoot>`.

---

## 5. VOCABULARIES

*Source: MASTER-DATA.md + served data. Every categorical → its master/served source.*

| Field on this page | Vocabulary / source | Fixed / served | Ref |
|--------------------|---------------------|----------------|-----|
| Instrument **asset_class** (grid) | `AssetClass` | fixed (served label) | MASTER-DATA §2 |
| **Region** (tabs / Global groups) | served `region` on `/markets/global.groups`; grid `country` | **served** (Global regions: Americas/Europe/Asia-Pacific/Commodities/Crypto) — **or** the D-083 six buckets? (ND-2) | §10; D-083 |
| **Index universe** | `_GLOBAL_MARKETS` (backend constant) | **hardcoded backend list, not a master, not user-editable** (ND-7) | markets.py |
| **Search** provider hits | `/markets/search` / `/instruments/search` | served | §10 |
| Quote **source** (if a select) | served provider list | served (D-005) — but see ND-8 (source select is Home's, D-052) | IA §5 |

All quote/status/region/index labels are **served display strings** — render verbatim; never hardcode.

---

## 6. DECISIONS IN FORCE

*Source: docs/audit/DECISIONS.md — each with what it forbids/requires here.*

| Decision | What it forbids / requires on this page |
|----------|------------------------------------------|
| **D-024** | Two movers pairs: this page shows **Gainers / Losers** (price-move), **never** Contributors/Detractors (Portfolio's contribution-weighted pair) or the retired "Top movers". |
| **D-034** | **Gainers/Losers canonical here** (Contributors/Detractors = Portfolio). |
| **D-037** | Quotes / indices / market status canonical here; **News** is canonical for briefing + grouped headlines (this page **links** to News, never duplicates it). |
| **D-051** | Keep region tabs, search, indices, Gainers/Losers, instrument grid, **Global tab**, the **real-vs-ETF-proxy badge** (protected honesty). **Drop region-news blocks → link to News.** |
| **D-052** | **Watchlist management lives ONLY here** (create/delete lists, add/remove items). Home shows watchlist quotes via a source select (that is Home's, not this page — ND-8). |
| **D-042** | `/global` removed, **no redirect**; this page owns the Global tab that did its job. |
| **D-005 / D-050** | Served vocab/labels (zero-copy); any export server-side. |
| **D-069 / D-002** | Watchlist mutations `require_auth` (`[S]`); under **no-egress**, live quotes degrade to **honest stale**, never fabricated (Guarantee 5). |

---

## 7. ACCEPTANCE CRITERIA

*Checkable, user-visible. Includes honesty states + theme/density + overflow + the §7/§8 fail-first rule.*

- [ ] **Quotes / instrument grid (D-037):** the served instruments render with quotes + a `held`
      badge; sortable; freshness flagged (D-027); no frontend money math.
- [ ] **Gainers / Losers (D-024/D-034):** labelled exactly that — **never "Contributors/Detractors"**;
      **price-move** ranking (display sort of served `change_pct`, ND-1); honest empty state.
- [ ] **Global tab (D-042/D-051):** world indices by region; the **real-vs-ETF-proxy badge** shown on
      any proxy-sourced index (protected honesty); `real_indices`/per-item symbol drive it.
- [ ] **Market status (D-037):** open/closed shown honestly from `market_status`.
- [ ] **Search (D-037):** symbol search returns served hits; a hit links to InstrumentDetail / adds to
      a watchlist (class-aware, D-097).
- [ ] **Watchlist management (D-052):** create/delete lists + add/remove items, all `require_auth`
      (`[S]`); honest empty state; no client fabrication.
- [ ] **Region-news dropped → News links (D-051):** no region-news blocks; region groups link to News.
- [ ] **R-17 ticker wiring (ND-5, REQUIRED):** the TickerStrip's index entries now **link to `/markets`**
      (holdings still → InstrumentDetail, D-098); the ticker §-entry (index-link) is **closed**.
- [ ] **Terms match GLOSSARY;** copy hygiene — no decision IDs / enum keys (`^GSPC`, `change_pct`) in
      any user string; `[Help]` on Gainers/Losers (with the which-list distinction), Index, ETF proxy.
- [ ] **No-egress honesty:** live quotes degrade to stale, never faked (Guarantee 5).
- [ ] **Both themes + both densities;** interactive OPEN states (region tabs, search, watchlist
      dialogs) verified in both themes.
- [ ] **Rendered layout + overflow:** verified at 320/375/900/1366 both themes, zero horizontal
      overflow — **extend the overflow suite** to `/markets`. Geometry fixes **fail-first** (§7/§8).

---

## 8. BUILD PHASES

*One commit per phase. Backend deltas FIRST. Nothing assembled against a non-existent endpoint.
**Do not start until §9 clears.***

- **Phase 0 — Contract deltas (only if §9 turns ND-1 toward a served Gainers/Losers list):**
  backend-first; regenerate contract same commit; drift green. *(Skip if ND-1 = display-sort.)*
- **Phase 0a — DESIGN-SYSTEM §5 amendment (only if ND-2 needs a Tabs affordance / ND-6 a status
  pill):** author PROPOSED, ratify at `/kitchen-sink` before assembly.
- **Phase 1 — Page assembly:** compose ratified components over the readers; progressive per-card
  loading; honest empty/error/stale states; instrument grid + Gainers/Losers + Global tab + market
  status + search + watchlist management + News links; **R-17 ticker wiring**.
- **Phase 2 — Tests:** component/render + acceptance (§7); **extend the overflow suite to `/markets`**;
  a **which-list copy test** (Gainers/Losers, never Contributors/Detractors); the **R-17 ticker-link**
  test; drift/typecheck/lint/build green.
- **Phase 3a — Scripted pre-pass (MUST be green before the walk):** drive the live page + real backend
  on seeded demo; assert populated grid/indices/gainers-losers/watchlists, the proxy badge, market
  status, search, the R-17 ticker link, 0 overflow, 0 console errors; fix everything it surfaces first.
- **Phase 3b — Owner acceptance walk (LIVE, judgment items only):** each finding → a numbered
  `page-markets.md §*` entry, fixed + re-verified live, geometry fixes **fail-first**. **Owner closes the page.**

---

## 9. NEEDS DECISION — OPEN (owner resolves; nothing resolved here)

Each item is an ambiguity the specs do not settle. Options laid out; **I resolved none.** Items
flagged **⚠ CONTRACT/SCOPE GAP** may need a backend delta or an owner scope call.

- **ND-1 — Gainers/Losers source. ⚠ CONTRACT GAP.** **`/markets/overview` does NOT serve a
  Gainers/Losers list** — it serves the instrument grid (`instruments[].quote.change_pct`). Options:
  **(a)** derive the two lists by **display-sorting the served overview quotes** by `change_pct`
  (top/bottom N — a display sort of served values, no money math), **or (b)** a **backend delta**
  serving `gainers`/`losers`. Also the **universe** to rank (all overview instruments? held only? a
  fixed market set?). Owner picks the source + universe.
- **ND-2 — Region tabs. ⚠ possible §5 amendment.** `/markets/overview` has **no region param**;
  instruments carry `country`/`asset_class`; `/markets/global` groups by `region`
  (Americas/Europe/Asia-Pacific/Commodities/Crypto). Options: **(a)** client-side filter of the served
  grid by region (which region set — the Global regions, or the **D-083 six buckets** used elsewhere?),
  **(b)** a backend region param. And the **control**: a `Select` vs a **Tabs** affordance (a §5
  amendment if Tabs). Owner picks region model + control.
- **ND-3 — Template fit (owner-flagged).** Markets is an **overview + worklist hybrid** — a
  market-status/indices/Gainers-Losers header (overview-ish) over an instrument-grid + watchlists
  worklist body. Confirm the treatment (DESIGN-SYSTEM §3 does not assign Markets a single template);
  record the hybrid shape for the Markets group (Heatmap/News follow).
- **ND-4 — Watchlist management UX.** CRUD is served + `require_auth` (`[S]`), and **Markets owns it**
  (D-052 — settled, not reopened). Confirm the affordances: **multiple lists** (the GET returns many);
  a watchlists panel of `DataTable`s; **add** via the class-aware `InstrumentPicker`/search; **remove**
  via `RowMenu`; **create/delete list** via `ConfirmDialog` (`[S]`). Any list-rename? (no rename
  endpoint exists — confirm out-of-scope or a delta).
- **ND-5 — R-17 ticker wiring (REQUIRED in scope).** The `TickerStrip` index entries are **currently
  unlinked** (holdings → InstrumentDetail, indices unlinked, D-098). On Markets' ship they **link to
  `/markets`**. Confirm the **target** (`/markets`, or a Global-tab anchor/deep-link) and that the
  **ticker index-link §-entry is closed** this milestone (the ticker's `href` for index items is set;
  `fetchTickerQuotes` in `api/chrome.ts` currently sets no href on indices).
- **ND-6 — Real-vs-ETF-proxy badge (D-051, protected honesty).** Served by `real_indices` (global) +
  the per-item symbol (proxy vs `^index`). Confirm the **badge placement** (per Global-tab index) +
  the protected copy (a proxy is labelled, never shown as the index).
- **ND-7 — Index universe.** `_GLOBAL_MARKETS` is a **backend constant** (5 regions, ~14 indices), not
  a served master, **not user-editable**. Confirm it stays **visible-not-editable** (like routing under
  D-072); a user-configurable index set would be a ROADMAP item, not v2. Owner confirms.
- **ND-8 — Quote source select.** The **QuoteCardRow source select** (markets/holdings/global/watchlist)
  is a **Home** feature (D-046/D-047/D-052) — on **Markets** the sections render directly (grid, Global,
  watchlists), no source-select card. Confirm the source select is **not** a Markets affordance.
- **ND-9 — Rotation eligibility (D-044).** Confirm YES/NO for a live-data Markets page.
- **ND-10 — Entity scope (D-065).** Markets is market data (not portfolio-scoped) — confirm **no
  `entity_id`** here (the readers take none; verified §10).
- **ND-11 — Heatmap boundary (D-053).** The **Heatmap is its own page** (`/heatmap`, D-053) — confirm
  Markets **links** to it and does **not** embed the treemap.

**Lower-risk confirms (owner ratifies with the above):** served labels throughout (D-005); the
which-list rule (Gainers/Losers here, never Contributors/Detractors, D-024); watchlist mutations
`[S]`-gated; no-egress → honest stale.

---

## 10. VERIFY-FIRST FINDINGS (2026-07-12) — read before assuming shapes (D-019)

Ran the read-what-the-engine-serves pass before drafting §3/§4. **No shape was assumed; gaps went to
§9, not §3b.**

| Item | What the engine actually serves | Source |
|------|--------------------------------|--------|
| Markets overview | `{quotes, instruments:[{symbol,name,asset_class,currency,country,held,quote}], market_status, demo_mode}` — the instrument grid; **NO gainers/losers**; **no region param** | `markets.py:61` |
| Markets global | `{groups:[{region, items:[{symbol,label,quote}]}], market_status, demo_mode, real_indices}` — world indices by region; `real_indices` = real-vs-proxy (D-051) | `markets.py:141` |
| Index universe | **hardcoded** `_GLOBAL_MARKETS` (Americas/Europe/Asia-Pacific/Commodities/Crypto, ~14 entries), ETF-proxy ⇄ `^index`; **not a served master, not user-editable** | `markets.py:98` |
| Markets search | `{results:[…provider hits…]}` | `markets.py:166` |
| Watchlists | `GET {watchlists:[{id,name,items:[{symbol,name,quote}]}]}`; create/delete list + add/remove item all **`require_auth`**; **no rename endpoint** | `watchlists.py` |
| Gainers/Losers | **NOT served as a list** — must be a display-sort of the overview quotes or a backend delta (ND-1) | contract (absent) |
| Entity scope | markets readers take **no `entity_id`** (market data, not portfolio-scoped) | route signatures |
| Ticker index link | `fetchTickerQuotes` sets `href` on **holdings only** (→ InstrumentDetail); **indices unlinked** — R-17 wires them → `/markets` (ND-5) | `api/chrome.ts` |

**Owner sign-off surface (all in §9):** ND-1 (Gainers/Losers source — the one potential §3b delta),
ND-2 (region model + Tabs), ND-3 (template fit), ND-5 (R-17 ticker wiring — required), plus the
confirms (ND-4/6/7/8/9/10/11). **No further build until the owner resolves §9.**
