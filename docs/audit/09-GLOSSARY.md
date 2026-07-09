# 09 — Glossary

One canonical definition per domain term. Consistent with the in-app Help knowledge base
(`app/services/help.py`, served at `GET /help` and used by the AI as `help_facts`), with
conflicts found in 06 resolved. Terms marked **[Help]** have a full what/why/improves entry in
the help catalogue (and a `term-*` id used by `GlossaryTerm` popovers).

## Instruments, holdings, accounts

| Term | Canonical definition |
|------|----------------------|
| **Instrument** | A tradable/valuable security identified by symbol+exchange, with taxonomy (asset class/subclass, country, sector) and linked identifiers (ISIN/AMFI/CoinGecko/Kite/…). Model `Instrument`. |
| **Identifier** | A normalized key mapping an instrument to the outside world (`id_type`, `value`): ISIN, CUSIP, FIGI, SEDOL, amfi_code, kite_token, coingecko_id, provider_symbol. High-confidence ids are globally unique. |
| **Holding / Position** | A quantity of one instrument in one account. **Derived** from the transaction ledger via FIFO (rebuilt on every mutation) — except **manual holdings** (a `manual_value` you maintain), which survive rebuilds. Use **Position** for the count, **Holding** for the row. |
| **Manual asset / holding** | A holding valued by a user-entered `manual_value` (cash, property, private, FD, insurance cash value), not a market quote. |
| **Lot** | A single parcel from one buy, with its own acquisition date and unit cost. FIFO consumes lots oldest-first. |
| **Tax lot / Open lot** | An unsold lot with acquisition date, quantity, cost, and holding period. **[Help term-fifo]** |
| **Account** | A container of holdings at an institution, with a currency, kind, and (Phase 4.1) an owning entity. |
| **Institution / Platform** | The broker/bank an account is held at (`Account.institution`, free text today). |
| **Entity** | An ownership entity (Self/Spouse/Trust/Company/Household). Every account belongs to one; consolidated views span all. Model `Entity`. |
| **Liability** | An `AssetClass.LIABILITY` holding; counted **negative** toward net worth. |

## Valuation & provenance

| Term | Canonical definition |
|------|----------------------|
| **Total value** | Sum of every holding's current market value in base currency at today's FX — a point-in-time snapshot. **[Help term-total-value]** |
| **Net worth** | Assets minus liabilities in base currency. In code this equals `value_portfolio.total_value` because liabilities are already negative. |
| **Cost basis** | Quantity × FIFO average cost (native ccy → base). |
| **Valuation method** | How a value was established: `market_quote`, `official_nav`, `broker_quote`, `manual_valuation`, `statement_import`, `calculated_accrual`, `estimated_value`, `fx_reference`, `unavailable`. **[Help term-valuation-method]** (enum `ValuationMethod`). |
| **Provenance** | The traceable record of where a value came from — source, valuation method, identifier mapping, timestamp. **[Help term-provenance]** |
| **Entitlement** | The best data grade a source claims: real-time, delayed, end-of-day, cached, unavailable (`EntitlementStatus`). LedgerFrame never claims real-time. **[Help term-entitlement-stale]** |
| **Stale** | A cached quote older than `stale_after_seconds` (default 900s; EOD/NAV: 30h). Flagged, never hidden or faked. **[Help term-entitlement-stale]** |
| **Data confidence** | 0-100 score of how well-sourced a value is: base by valuation method minus itemised penalties (stale −20, needs-mapping −15, unavailable −15). Value-weighted at portfolio level. **[Help term-confidence]** |
| **Status (Pricing Health)** | One word: Fresh / Delayed / End-of-day / Cached / Manual / Estimated / Unavailable (`provenance.health_status`). |
| **Mapping required** | An instrument needs an identifier (AMFI code / CoinGecko id) before it can be priced by its cache-publish source. |
| **Auth required** | A configured, higher-priority keyed provider is missing credentials. |

## Returns & performance

| Term | Canonical definition |
|------|----------------------|
| **Realised gain** | Sale proceeds − FIFO-matched cost of the parcels sold. Native currency exact; base total at today's FX (indicative) or trade-date FX. **[Help term-realised-gains]** Not tax advice. |
| **Unrealised P/L** | Current market value − cost basis on holdings still held (paper gain). **[Help term-unrealised-pl]** |
| **Income** | Dividends + interest recorded in the ledger, base currency at today's FX. **[Help term-income]** |
| **Income yield** | Recorded income ÷ current total value (trailing, backward-looking). **[Help term-income-yield]** |
| **Total return** | Overall % gain/loss vs cost basis, since-inception cumulative. **[Help term-total-return]** |
| **1-year return / volatility / max drawdown** | Trailing-12-month figures from the invested performance series; 0.0 can mean "no data". **[Help term-period-return / term-volatility / term-max-drawdown]** |
| **XIRR** | Money-weighted return — the IRR of dated cash flows (accounts for size/timing of your flows). "Not applicable" on thin history. **[Help term-xirr-twr]** |
| **TWR** | Time-weighted return — chain-linked daily returns with external flows removed (for benchmark comparison). **[Help term-xirr-twr]** |
| **Return / volatility** | 1Y return ÷ 1Y volatility. **Explicitly NOT a Sharpe ratio** (no risk-free rate subtracted). **[Help term-return-volatility]** |
| **Return attribution** | Per-holding contribution (weight × return, in signed pp) rolled to class/sector, with an explicit **residual** (income + realised + closed positions) so Σ contributions + residual = headline. Single-period approximation. **[Help term-attribution]** |
| **Beta / Correlation / Downside deviation / Information ratio / Tracking error** | Benchmark-relative (or downside) risk metrics needing no risk-free rate. **[Help term-beta / -correlation / -downside-deviation / -information-ratio / -tracking-error]** Sharpe/Sortino deliberately excluded. |

## Allocation, risk, policy

| Term | Canonical definition |
|------|----------------------|
| **Allocation weight** | Each asset group's share of **gross** assets (liabilities excluded). **[Help term-allocation-weight]** |
| **Concentration** | Share of gross assets in the biggest positions — largest single + top-5. **[Help term-concentration]** |
| **HHI** | Herfindahl-Hirschman Index — Σ squared weights; 1/N (equal) → 1 (single). **[Help term-hhi]** |
| **Investment policy (IPS)** | Stored **intent**: target allocation per dimension (asset_class/currency/region), tolerance bands, optional concentration limit. Intent only — drift is computed live. |
| **Drift & bands** | Actual − target share; if beyond the band, "over"/"under". Reporting, never a trade instruction. **[Help term-drift]** |
| **Dimension / Bucket** | Dimension = asset_class/currency/region; bucket = a value within it (equity/SGD/India). |
| **Region** | Mapped from listing country: IN→India, SG→Singapore, US→US, else Global. |

## Liquidity, planning, cash

| Term | Canonical definition |
|------|----------------------|
| **Liquidity ladder** | Assets grouped by time-to-cash: Immediate / Short / Locked / Illiquid (from `liquidity_profile` override or asset class). **[Help term-liquidity]** |
| **Liquid** | Immediate + Short rungs. |
| **Cash runway** | Liquid assets ÷ recurring net burn (expenses − income), at today's FX. Status: no_data / positive / finite. **[Help term-runway]** |
| **Goal** | A target amount with a basis (net_worth/liquid/none); progress computed live. |
| **Obligation** | A recurring or one-off future cash flow (expense/income); feeds runway + next-12-months total. |
| **Contribution** | A recorded plan (invest/withdraw/prepay); shown as monthly-equivalent; does **not** reduce runway. |
| **Scenario** | A deterministic "what-if" shock on today's values — a scenario, never a forecast. |

## Cost & organisation

| Term | Canonical definition |
|------|----------------------|
| **Recorded fees** | Actual commissions + taxes from the ledger for a year (a currency fact). |
| **Estimated ongoing cost** | Forward estimate = expense ratio (`annual_cost_bps`) × current value. Kept **separate** from recorded fees, never blended. **[Help term-ongoing-cost]** |
| **Statements** | Income, fees, cash flow, realised-vs-unrealised from recorded transactions (for review / your accountant). |
| **Review / Review Centre** | A live "what needs a look" feed from existing signals; a recorded review snapshots state to `ReviewLog`. |

## Corporate actions & FX

| Term | Canonical definition |
|------|----------------------|
| **Split** | Corporate action scaling lots by the ratio in the `price` field. |
| **Bonus** | Zero-cost extra shares (average cost falls). |
| **Merger** | Instrument A absorbed into B at ratio R; A's lots carried into B as synthetic buys (`resolve_mergers`), no realised event. |
| **Trade-date FX** | The native→base rate captured live at commit **only when the trade date is today**; else honestly unavailable. Used for the trade-date-FX realised total. |
| **Reference FX (ECB)** | EUR-based reference rates used only as an FX fallback for translation, never a trading quote. |
| **Base currency** | The single reporting currency everything is translated to (`LEDGERFRAME_BASE_CURRENCY`). |

## System

| Term | Canonical definition |
|------|----------------------|
| **Provider / Source** | A market-data adapter (mock/csv/yahoo/alphavantage/eodhd/kite) or metadata adapter (amfi_nav/coingecko/ecb_fx). "Source" = the one that owns a given price (routing). |
| **Router / Routing** | Per-instrument decision of which source owns a price (`route`), shown in Pricing Health. |
| **Detail level (Simple/Expert)** | Presentation-only view mode; only Home actually branches on it today. |
| **Demo mode** | `market_provider == "mock"` — deterministic DEMO data, entitlement delayed, seeded on empty DB. |

> Guarantee (Help `guarantee`): LedgerFrame never places trades, gives buy/sell/hold or tax/
> financial advice, or fabricates a price/headline/figure. Unavailable data shows "—" with a
> reason. Local-first, no telemetry.

<!-- AUDIT COMPLETE -->
