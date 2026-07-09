# 04 — Calculation Engine

Every deterministic calculation. **Guarantee enforced project-wide:** all money math is
`decimal.Decimal`; the AI layer never computes any of these numbers (`services/portfolio.py:4`).
Floats appear only at the JSON edge via `to_display` (`core/money.py:40`). "Not applicable"
(`None`) is returned rather than a fabricated number whenever inputs are insufficient.

## 0. Precision & money primitives (`app/core/money.py`)

| Fn | Rule | Line |
|----|------|------|
| `D(x)` | coerce to Decimal; ""/None→0; raises on garbage | :18 |
| `money(x)` | quantize 2dp, ROUND_HALF_UP | :30 |
| `price(x)` | quantize 6dp (FX & crypto) | :35 |
| `to_display(x)` | Decimal→float at JSON boundary only | :40 |
| `pct_change(cur, prev)` | `(cur-prev)/prev*100` 2dp; **None when prev==0** | :45 |

Storage: money as TEXT (`DecimalText`), datetimes naive-UTC (`UTCDateTime`). `PRICE_Q=1e-6`,
`CENTS=0.01`.

---

## 1. FIFO cost basis — `compute_fifo` (`services/portfolio.py:78`)

Pure function; replays one instrument's transactions in time order (`_sort_ts` normalises
naive/aware). Lots = `deque([qty, unit_cost])`.

| Txn type | Effect |
|----------|--------|
| BUY | push lot; `unit_cost = price + (fees+taxes)/qty`; skip qty≤0 |
| SELL | consume **oldest lots first**; `proceeds = qty*price − (fees+taxes)`; `realised_pl += proceeds − cost_of_sold` |
| SPLIT | `ratio = price field` (default 1); each lot: qty×ratio, unit_cost÷ratio |
| BONUS | append lot `[qty, 0]` (zero-cost shares → avg cost falls) |
| DIVIDEND/INTEREST | `income += amount or qty*price` |
| MERGER | **clears lots** (no realised gain); cross-instrument transfer handled by `resolve_mergers` |
| TRANSFER/others | no effect |

Outputs `FifoResult(quantity, cost_basis, realised_pl, income)`, `avg_cost = cost_basis/quantity`.
**Edge cases:** oversell (remaining after lots empty) is silently not matched; fees+taxes both
increase cost / reduce proceeds.

**Displayed:** every holding's avg cost & cost basis (Holdings, Portfolio, Snapshot), realised
P/L & income in `key_stats` (ReportsPack), realised-gains report.

### 1a. Holdings rebuild — `rebuild_holdings_from_transactions` (`portfolio.py:347`)
- Excludes soft-deleted txns (`deleted_at IS NULL`); calls `resolve_mergers` first.
- Groups by (account_id, instrument_id); replays `compute_fifo`; deletes old instrument-linked
  holdings (preserves `manual_value` rows); creates a Holding per position with qty>0.
- Native currency inferred from symbol suffix (`currency_for_symbol`) — authoritative over stored.
- Called after every txn mutation, reclassify, instrument PATCH, holding refresh.

### 1b. Merger resolution — `resolve_mergers` (`services/tax.py:185`)
Cross-instrument: A absorbed into B at ratio R (`price` field), target `related_instrument_id`.
Carries A's open lots into B as synthetic BUYs at original acquisition date, `qty×R`, `cost÷R`
(total cost preserved), carrying acq FX. Method-aware (FIFO source → per-lot; average source →
one pooled lot dated at oldest). Processes oldest-first for chains A→B→C. **No-merger portfolio
passes through byte-identical.** No-op unless a MERGER txn exists.

---

## 2. Portfolio valuation — `value_portfolio` (`portfolio.py:214`)

Values every non-soft-deleted holding at latest cached quote → base currency. Optional
`entity_id` scope (`entity_account_filter`, `:200`).

Per holding decision tree (`:254`):
1. `manual_value` set → `MANUAL_VALUATION`, value = manual_value (native).
2. has symbol + instrument + not `is_manual_price` → `get_cached_quote`; if no cache and
   `warm` and provider `fetch_on_demand` → `refresh_quote`. If price: `MARKET_QUOTE` (or
   `OFFICIAL_NAV` if `source=="amfi_nav"`); value = qty×price. Else fall to cost →
   `ESTIMATED_VALUE`, `is_priced=False`.
3. else (manual-priced instrument / manual asset) → cost fallback, `MANUAL_VALUATION`.

- **Day change** = `(price − previous_close) × qty` (only when quote has previous_close).
- FX to base via `fx.convert`. **Liabilities** (`AssetClass.LIABILITY`) counted **negative**
  toward net worth (`sign=-1`, `:293`).
- Sector: instrument.sector else `_SECTOR_MAP` fallback (`portfolio.py:30`, ~70 tickers).
- Rollups: `total_value, cost_basis, unrealised_pl (=mv−cost), day_change, has_stale`.
- `total_return_pct = pct_change(total_value, cost_basis)`; `allocation(key)`,
  `sector_allocation()` (positive-value + resolved sector only).

`top_movers(val, n)` (`:402`): gainers/losers by `day_change_base` among priced holdings;
losers filtered to negatives only.

**Displayed:** `/portfolio/summary`, `/portfolio/holdings`, `/dashboard/home`, and consumed by
almost every downstream report (drift, liquidity, scenarios, attribution, review, etc.).

---

## 3. Returns

### 3.1 XIRR (money-weighted) — `core/xirr.py:19`
Bisection over dated flows. Convention: invested = negative, returned/value = positive; final
value dated today added. **None** when <2 flows or no sign change. Bracket `[-0.999999, 10]`,
widens to 1000 once; 200 iterations; result 2dp %. Consumed by `key_stats` → "Money-weighted
return (XIRR)". Manual/statement assets excluded (no dated flow).

### 3.2 TWR (time-weighted) — `core/twr.py:18` + `analytics.time_weighted_return` (:344)
Chain-links daily investment returns with external flows removed:
`r = (V[t] − flow[t] − V[t-1]) / V[t-1]`. Skips steps where `V[t-1]<=0` or `r<=-1`. **None** when
<2 valid links or thin history (`n<20` days, <2 txns). Reconstructs point-in-time holdings from
transactions × cached historical closes; current FX applied across history (documented
simplification). Best-effort (8-12s budget). Consumed by `key_stats` → "Time-weighted return".

### 3.3 Performance series — `analytics.performance_series` (:229)
"Today's holdings valued back through time." Time axis = benchmark daily candles. Portfolio value
per day = Σ (qty × carry-forward close × FX × sign). Manual assets excluded unless
`include_manual`. Benchmark indexed to portfolio start value. **Stats** (`:330`): return_pct,
benchmark_return_pct, excess_pct, max_drawdown_pct, `volatility_pct = pstdev(daily) × √252 × 100`,
best/worst day. Empty stats when axis <2. FX current-rate simplification. 12s budget → cached only.
Consumed by `/portfolio/performance` (Home, Snapshot) + `key_stats` + `risk_metrics`.

### 3.4 Key stats panel — `analytics.key_stats` (:32)
Deterministic metric list (ReportsPack "stats"). Metrics: Total value, Unrealised/Realised P/L,
Income (div+int), Income yield, Total return, XIRR, TWR, 1Y return/volatility, Return/volatility
(labelled — **not a true Sharpe**, no risk-free rate), Max drawdown, allocation weights (cash,
equity, crypto, alternatives), Largest position & Top-5 concentration (÷ **gross** assets so a
mortgage can't distort), Positions count. Also exposes `base_realised_total_current_fx` vs
`base_realised_total_historical_fx` (trade-date FX) + `realised_fx_events_excluded`.

---

## 4. Attribution & risk (§4.5, read-only)

### 4.1 Return attribution — `analytics.attribution` / `_attribute_core` (:490)
Single-period, price-based decomposition. Per-holding contribution =
`unrealised_pl_base / total_cost × 100` (pp, 4dp) — computed directly so zero-cost lots are exact.
Rolled to asset class & sector (`Unclassified` for null). **Explicit residual** =
`headline − Σ contributions`, where `headline = (unrealised+realised+income)/cost×100`. Residual
absorbs income + realised + closed positions ⇒ `Σ contrib + residual == headline` by construction.
`residual_breakdown` splits income/realised (indicative). **Unavailable** shape when no holdings /
cost≤0 (never crash). `days` accepted but method is since-inception (Brinson deferred). Displayed:
AttributionPanel (ReportsPack).

### 4.2 Risk metrics — `analytics.risk_metrics` / `_risk_from_series` (:616)
Over the **same** performance series (single source of truth). No risk-free rate → only:
- **beta** = cov(port,bench)/var(bench)
- **correlation** of daily returns
- **downside_deviation** = `pstdev(negative returns) × √252 × 100` (0 if no downside)
- **information_ratio** = excess / (tracking_error); te==0 → 0 or None
- **tracking_error** = `pstdev(active) × √252 × 100`
- **hhi** = Σ weightᵢ² over positive holdings (1/N for N equal)

Sharpe & Sortino **deliberately excluded** (need risk-free rate). Thin data → per-metric None.
Displayed: KeyStatsPanel (ReportsPack).

---

## 5. Realised gains & tax lots — `services/tax.py`

Separate read-only FIFO replay `fifo_report` (:94) that emits lot-level `RealisedEvent` +
`OpenLot` — **never touches `compute_fifo`**. Supports `method` = fifo | average (§4.4):
- **average**: sell cost from pooled avg `total_cost/total_qty`; acquisition **date** from oldest
  lot; trade-date FX not applied.
- Per-account method (`Account.cost_basis_method`, default fifo); groups by (account, instrument)
  so a sell never consumes another account's lots.

`realised_gains_report` (:284): grouped by native currency; neutral short/long split at
`long_term_days` threshold (0-3660); per-currency realised/short/long/income; base total at
**current FX** (caveated) + **trade-date-FX total** (`gain_base_historical`, each leg at own
stored `fx_to_base` when `fx_base==base`, else event excluded, counted in
`realised_fx_events_excluded`). Not tax advice. CSV export sanitises cells (formula-injection safe).

`tax_lots_report` (:373): open lots per holding with holding_days & long_term flag.

**Trade-date FX** (`_leg_rate`, :40): only valid when `fx_base == current base` (a base change
invalidates it). Captured live at commit only when trade ts == today UTC (`fx.capture_rate`,
`services/fx.py:70`) — backdated trades honestly `None`.

Displayed: Reports page (realised gains, tax lots), ReportsPack.

---

## 6. Allocation, drift & concentration — `services/policy.py`

`compute_drift` (:77): live per read (never stored). Dimensions `asset_class | currency | region`
(`region_of` maps IN→India, SG→Singapore, US→US, else Global, `:26`). For each targeted bucket:
- `actual_pct = actual_value / gross × 100` (gross = positive holdings)
- band: `lower = min_pct or target−default_band`, `upper = max_pct or target+default_band`
  (clamped 0-100)
- `status = under | in_band | over`; `drift_pct = actual − target`; `gap_base = actual − target×gross`
- `untargeted` buckets listed separately; `coverage_pct = Σ target_pct`.

**Concentration** (only if `max_position_pct` set): holdings with weight > limit, sorted desc.
Reporting only — never names a trade. Displayed: Policy page, ReportsPack, feeds into Review.

---

## 7. Liquidity ladder — `services/liquidity.py`

`rung_of(hv)` (:43): explicit `liquidity_profile` override (`listed→immediate`,
`redeemable→short`, `locked`, `illiquid`) else by asset class (`_RUNG_BY_CLASS`, :25). Rungs:
immediate / short / locked / illiquid / unclassified (+ liability kept separate). `liquidity_ladder`
(:50): value per rung, pct & cumulative_pct of gross, `liquid_pct = (immediate+short)/gross`,
liabilities negative. Displayed: Snapshot; `liquid` feeds goals/runway/scenarios; `liquid_pct`
feeds Review Centre.

---

## 8. Cash runway — `services/runway.py:26`

`liquid ÷ net monthly burn`, at today's FX. `net_burn = monthly_expense − monthly_income` over
recurring obligations (`MONTHLY_FACTOR`: monthly=1, quarterly=1/3, annual=1/12; **'once' excluded**
— lumpy). Status: `no_data` (nothing recorded) / `positive` (income covers, no drawdown) /
`finite` (`runway_months = liquid/net_burn`, capped 1200 for date). `liquid` from
`_basis_values` (immediate+short rungs). Displayed: Snapshot, Scenarios, Review Centre.

---

## 9. Goals & obligations — `services/planning.py`

`goals_report` (:68): per goal, `target_base` at current FX; `current` from basis
(net_worth/liquid/none); `progress_pct = current/target×100`, `remaining_base`, `days_to_target`.
`obligations_report` (:98): expands recurrences over a 12-month horizon (`_occurrences`),
`next_12m_total` = Σ expense outflows (income excluded), FX current. `_add_months` clamps day.
Displayed: Planning, feeds Scenarios/Review/Contributions.

`contributions_report` (`contributions.py:96`): monthly-equivalent invest/withdraw
(`_FREQ_MONTHLY`, once=0), `monthly_net_investing`, `monthly_cash_out_with_expenses`
(= expense + invest). **Deliberately does NOT reduce runway** (a contribution builds wealth).

---

## 10. Data confidence — `services/confidence.py`

`score_holding` (:37): base by valuation method (market_quote=100, official_nav=95,
calculated_accrual=85, manual_valuation=70, estimated_value=40, unavailable=20), then penalties:
stale −20, mapping_required −15, entitlement==unavailable −15; clamped 0-100. Each deduction
listed (`confidence_factors`). `band_of`: high≥80, medium≥50, low<50. `summarise` (:59):
**value-weighted** overall score + by-band counts/value_pct. Displayed: PricingHealth (per-holding
+ portfolio confidence), Review Centre trust section.

---

## 11. Provenance & staleness — `core/provenance.py`, quotes

`valuation_label` (:28): precedence unavailable → "Price unavailable"; stale/cached market quote →
"Stale cached value"; else method label. Manual/NAV/statement never overridden by staleness.
`health_status` (:58): one word — Fresh / Delayed / End-of-day / Cached / Manual / Estimated /
Unavailable. `EntitlementStatus` (`schemas/common.py:13`): real-time / delayed / end-of-day /
cached / unavailable. `ValuationMethod` (:29): 9 methods (see 09-GLOSSARY). Staleness threshold =
`LEDGERFRAME_STALE_AFTER_SECONDS` (default 900s); `is_stale` computed in market service.

---

## 12. FX — `services/fx.py`

`get_rate(base, quote)` (:28): same-ccy→1; 10-min in-process cache (`_TTL=600`). USD pairs asked
of provider, fallback to ECB reference (`ecb_fx.reference_rate`). **Cross rates triangulated
through USD** (`USD/quote ÷ USD/base`) — direct exotic crosses are unreliable. `convert` multiplies.
`capture_rate` (:70): trade-date FX, only today's UTC date, same-ccy=1, else None on failure/
unresolved/degrade-to-1 sentinel. `reference_rate` (ecb_fx) returns method direct/inverse/
triangulated/identity/unavailable.

---

## 13. Review feed — `services/review.py`

`review_report` (:37): aggregates signals into "what needs a look" items (area/title/severity),
each wrapped in try/except so one failure never breaks the feed. Sources & thresholds:
policy out-of-band + concentration; low-confidence (<50) & stale counts; thin liquidity
(`_LIQUID_THIN_PCT=15`); goals within `_GOAL_SOON_DAYS=90`; obligations within 30; insurance
renewals within 30 (or overdue); estate signals; runway < `_RUNWAY_LOW_MONTHS=6`; corporate
actions (split/bonus) within 45 days ("verify"). Empty → "Nothing needs a look right now."
`review_centre` (:174): one verdict per section (trust/policy/liquidity/goals/changed) + attention
list + last_review. `record_review` snapshots ReviewLog (net_worth, confidence, drift_flags,
attention_count). Displayed: Review page, ReportsPack.

---

## 14. Scenarios (stress) — `services/scenarios.py:28`

Deterministic "what if" on today's holdings. Exposures: equities (equity+etf+mutual_fund), crypto,
property, foreign (native≠base). Asset shocks: equities −10/−20/−30%, risk (equity+crypto) −20%,
crypto −50%, property −10%, FX −10%. Each: `delta = exposure × pct`, `new_net_worth`, `pct_change`.
Liquidity what-ifs: income-stop runway (`liquid/monthly_expense`), obligation-due
(`liquid − next_12m`, covered flag). Scenario not forecast. Displayed: Scenarios page.

---

## 15. Cost of ownership — `services/cost_of_ownership.py:34`

Two **never-blended** blocks:
- `recorded_fees`: reuses statements report's selected-year fee total (single source) — currency
  only, no annualised %.
- `estimated_ongoing_cost`: Σ `market_value_base × annual_cost_bps / 10000` over instrument-linked
  holdings with a non-null rate; null-rate holdings surfaced as `unavailable` (never 0); coverage
  "covers N of M". `estimated_annual_total`=None when nothing has a rate.

No combined total by design. Displayed: CostOfOwnershipCard.

---

## Notes for rebuild

- **Single source of truth pattern:** downstream reports consume `value_portfolio` /
  `fifo_report` outputs; they never re-derive money. Preserve this.
- **Honesty invariants:** None-not-fabricated (XIRR/TWR/attribution/FX), residual reconciliation,
  never-mix trade-date and current FX, liabilities negative, gross-asset denominators.
- **Time budgets** guard slow providers (performance 12s, TWR 8s, key_stats sub-calls 12-14s).
- `_carry_forward` (`analytics.py:207`) normalises naive/aware datetimes — a repeated gotcha.

<!-- AUDIT COMPLETE -->
