# 03 — API Surface

Every FastAPI endpoint. Base prefix `/api/v1` (`app/api/v1/router.py:31`). The frontend
calls these through a thin typed client, `frontend/src/lib/api.ts` (method → endpoint map
inline below in the "Client / Callers" column). OpenAPI is served at `/api/openapi.json`
and Swagger at `/api/docs` (`app/main.py:151`); a committed snapshot lives at
`docs/openapi.json` (may be stale — regenerate via `scripts/gen_openapi.py`).

## Auth model (applies to every row)

Router-wide dependency `require_read_auth` (`app/api/deps.py:113`, wired at
`app/main.py:193`) gates **all** `/api/v1/*` GET/HEAD when a PIN is set. Layered guards:

| Guard | File:line | Rule |
|-------|-----------|------|
| `require_read_auth` | deps.py:113 | Router-wide. No PIN → open. PIN set → valid session cookie/bearer **or** valid read-only `Authorization: Token` (GET/HEAD only). Auth routes always open. |
| `require_auth` | deps.py:77 | Per-route on mutations. No PIN → open (local). API token on a mutation → **403**. |
| `require_session` | deps.py:159 | Token management. Rejects API tokens outright (403). Open on no-PIN local. |
| `require_pin` | deps.py:184 | Irreversible actions. **Requires a PIN to exist** (403 otherwise) + valid session. |
| `require_metrics_access` | deps.py:141 | `/metrics`: loopback OR valid session. |

Non-`/api/v1` endpoints: `GET /health`, `GET /.well-known/security.txt`, `GET /metrics`
(gated), and the SPA catch-all `GET /{full_path}` (`app/main.py:171-216`).

Notation below: **[A]**=require_auth, **[S]**=require_session, **[P]**=require_pin, **[R]**=read-gated only. "Client" = `api.*` method in `api.ts` (— = not called by the SPA).

---

## system (`routes/system.py`)

| Method | Path | Auth | Request | Response (key fields) | Side effects | Client / Callers |
|--------|------|------|---------|-----------------------|--------------|------------------|
| GET | /system/status | R | — | version, env, demo_mode, market_provider, base_currency, timezone, ai_enabled, voice_enabled, allow_lan, pin_set, db_ok, data_dir, data_writable, stale_after_seconds | none | `systemStatus` — store/app.tsx |
| GET | /ai/status | R | — | AIHealth (available, provider, detail, models) | none | `aiStatus` — Settings |
| GET | /system/providers | R | — | active, capabilities{}, default_priority[] | none | — |
| GET | /system/identifier-duplicates | R | — | duplicates[], count | none | `identifierDuplicates` — PricingHealth |
| GET | /system/data-source | R | — | provider, has_api_key, base_currency, stale_after_seconds, providers[], supports_indices, av_tier, restart_required, admin_available | AV tier probe (1 quote) | `dataSource` — Settings |
| PUT | /system/data-source | A | {provider, api_key?, base_currency?, stale_after_seconds?} | ok, applied, note | **writes .env**, reload_settings, fx.clear_cache, restart worker | `setDataSource` — Settings |
| GET | /system/config | R | — | timezone, api_port, stale_after_seconds, autolock_minutes, rotation_default_seconds, data_dir, backup_keep, backup_age_recipient, kiosk_url | none | `config` — Settings |
| PUT | /system/config | A | {values{}} | ok, note | writes .env, reload_settings | `setConfig` — Settings |
| GET | /system/ai-config | R | — | enabled, provider, hailo_base_url, model, openai_base_url, has_openai_key, providers[] | none | `aiConfig` — AiConfigCard |
| PUT | /system/ai-config | A | {enabled, provider, hailo_base_url?, model?, openai_base_url?, openai_api_key?} | ok, available, detail | writes .env, reload, health probe, restart worker | `setAiConfig` — AiConfigCard |
| POST | /system/reset-data | A | — | ok, note | **deletes** all portfolio/market data; sets no-reseed flag | `resetData` — Settings |
| GET | /system/staleness | R | — | stale, count, refreshable | none | `staleness` — StaleBanner/store |
| POST | /system/refresh-data | A | — | ok, refreshed, total, skipped, succeeded[], failed[], errors[] | fetches quotes for all shown symbols (40s budget, 8s/symbol) | `refreshData` — Settings |
| POST | /system/fetch-history | A | `?days=365` | ok, with_history[], no_history[], total | fetches/caches daily history | `fetchHistory` — Settings |
| GET | /system/version-check | R | — | current, latest, update_available, url | GitHub HTTP (best-effort) | `versionCheck` — Settings/UpdateBanner |
| GET | /system/update-status | R | — | running, ok, failed, status, version, log_tail | reads update log files | `updateStatus` — Settings/UpdateBanner |
| GET | /system/admin/available | R | — | available (sudo + helper) | none | `adminAvailable` — Settings |
| POST | /system/admin | A | {action, arg?} | ok, action, arg, output | **runs root helper** via `sudo -n` (allow-listed actions only) | `admin` — Settings |
| GET | /help | R | `?q=` | categories[], entries[] (or ranked) | none | `helpContent` — Help |

Admin allow-list (`system.py:24`): status, restart, restart-worker, doctor, backup, lan{on/off}, voice{on/off}, ai{on/off}, kiosk{on/off}, update.

## auth (`routes/auth.py`)

| Method | Path | Auth | Request | Response | Side effects | Client |
|--------|------|------|---------|----------|--------------|--------|
| POST | /auth/set-pin | special | {pin(4-32)} | ok, token | sets/changes PIN (Argon2), revoke_all sessions, set cookie. First PIN loopback-only when LAN-exposed. Changing PIN needs valid token. Rate-limited. | `setPin` — Settings/LockScreen |
| POST | /auth/unlock | special | {pin} | ok, token | verify PIN, issue token, set cookie. Rate-limited (429+Retry-After). | `unlock` — LockScreen |
| POST | /auth/lock | open | — | ok | revoke presented token, delete cookie | `lock` — Settings |
| GET | /auth/state | open | — | pin_set | none | `authState` — store |

## dashboard (`routes/dashboard.py`)

| GET | /dashboard/home | R | — | now, timezone, demo_mode, market_status, portfolio{}, top_movers{gainers,losers}, markets[], fx[], briefing{} | lazily generates briefing on first load | `home` — Home, News |

Home markets tiles = `SPY, QQQ, GLD, BTC` (`dashboard.py:21`). FX pairs derived from held currencies.

## markets (`routes/markets.py`)

| Method | Path | Auth | Request | Response | Side effects | Client |
|--------|------|------|---------|----------|--------------|--------|
| GET | /markets/overview | R | — | quotes[], instruments[] (symbol,name,asset_class,currency,country,held,quote), market_status, demo_mode | creates missing default-overview instrument rows | `marketsOverview` — Markets, Heatmap |
| GET | /markets/global | R | — | groups[region,items], market_status, demo_mode, real_indices | — | `marketsGlobal` — Home, Markets, News |
| GET | /markets/search | R | `?q=` (1-40) | results[] (symbol,name,asset_class,currency) | provider search | `search` — Markets, InstrumentDetail |
| PATCH | /instruments/{symbol} | A | {asset_class?, country?, name?, source_override?} | ok, symbol, asset_class, country, name, source_override | validates source override; **rebuilds holdings** | `editInstrument` — InstrumentDetail |
| PUT | /instruments/{symbol}/ongoing-cost | A | {annual_cost_bps?} | ok, symbol, annual_cost_bps | metadata-only write; **no rebuild** | `setOngoingCost` — InstrumentDetail |
| GET | /instruments/{symbol} | R | — | quote, instrument{...taxonomy, identifiers[], asset_detail, history_status} | backfills instrument name | `— (InstrumentDetail loads via history/news + ?)` |
| GET | /instruments/{symbol}/news | R | — | symbol, items[] | provider + RSS fetch | `instrumentNews` — InstrumentDetail |
| GET | /instruments/{symbol}/history | R | `?interval=1d&days=180` | symbol, interval, candles[] | fetches/caches history | `history` — InstrumentDetail |

Global markets map (`markets.py:98`): Americas/Europe/Asia-Pacific/Commodities/Crypto with (proxy,index,label) triples. `_AV_INDEX` maps ^ indices → AV symbols.

## portfolio (`routes/portfolio.py`) — the largest surface

| Method | Path | Auth | Request | Response (key) | Side effects | Client |
|--------|------|------|---------|----------------|--------------|--------|
| GET | /portfolio/summary | R | `?entity_id` | base_currency, total_value, cost_basis, unrealised_pl, day_change, total_return_pct, has_stale, allocation_by_class/currency/sector, top_gainers/losers | none | `portfolioSummary` — Home, Holdings, Portfolio, Snapshot, ReportsPack |
| GET | /portfolio/holdings | R | — | base_currency, holdings[] (see `_hv`) | none | `holdings` — many pages |
| GET | /portfolio/pricing-health | R | — | base_currency, holdings[] (valuation_method, label, status, source, entitlement, route_*, confidence…), summary{}, confidence{} | none | `pricingHealth` — PricingHealth |
| POST | /portfolio/pricing-health/{id}/refresh | A | — | ok, refreshed, source, price, entitlement | re-fetches 1 quote, rebuild | `refreshHolding` — PricingHealth |
| GET | /portfolio/performance | R | `?days=365&benchmark=SPY&include_manual=false&entity_id` | base_currency, benchmark_symbol, series[], benchmark[], stats{} | none | `performance` — Home, Snapshot |
| GET | /portfolio/benchmarks | R | — | benchmarks[] | none | `benchmarks` |
| GET | /portfolio/stats | R | `?benchmark&entity_id` | base_currency, metrics[] | none | `stats` — ReportsPack |
| GET | /portfolio/attribution | R | `?days&benchmark&entity_id` | attribution{}, risk{} | none | `attribution` — ReportsPack, KeyStatsPanel |
| GET | /portfolio/transactions | R | `?limit=500` | transactions[] (excludes soft-deleted) | none | `transactions` — PortfolioEditor |
| POST | /portfolio/transactions | A | TransactionIn | ok, transaction_id, holdings_rebuilt | ensures acct/instr, captures trade-date FX, rebuild | `addTransaction` — PortfolioEditor |
| PUT | /portfolio/transactions/{id} | A | TransactionIn | ok, holdings_rebuilt | rebuild | `updateTransaction` |
| DELETE | /portfolio/transactions/{id} | A | — | ok, holdings_rebuilt | **soft-delete**, rebuild | `deleteTransaction` |
| POST | /portfolio/transactions/{id}/restore | A | — | ok, holdings_rebuilt | clears deleted_at, rebuild | `restoreTransaction` |
| POST | /portfolio/reclassify | A | — | reclassified, renamed, countries_set, total | fixes instruments, rebuild | `reclassify` — Settings |
| GET | /portfolio/manual-holdings | R | — | holdings[] | none | `manualHoldings` — PortfolioEditor |
| POST | /portfolio/manual-holdings | A | ManualHoldingIn | ok, id | creates manual holding (whitelisted meta) | `addManualHolding` |
| PUT | /portfolio/manual-holdings/{id} | A | ManualHoldingIn | ok | update | `updateManualHolding` |
| DELETE | /portfolio/manual-holdings/{id} | A | — | ok | soft-delete | `deleteManualHolding` |
| POST | /portfolio/manual-holdings/{id}/restore | A | — | ok | clears deleted_at | `restoreManualHolding` |
| POST | /portfolio/purge-deleted | **P** | — | ok, holdings_purged, transactions_purged, holdings_rebuilt | **hard-deletes** all soft-deleted rows | — (empty trash) |
| GET | /portfolio/import/template | R | — | CSV text | none | `csvTemplateUrl` |
| POST | /portfolio/import/csv | A | multipart file, `?account_id` | imported, errors[], holdings_rebuilt | imports, rebuild | `importCsv` |
| POST | /portfolio/import/preview | R | multipart file | batch, already_imported, summary, rows[] | **non-mutating** | `importPreview` — PortfolioEditor |
| POST | /portfolio/import/commit | A | multipart file, `?account_id&skip_duplicates=true` | ok, imported, skipped_duplicates, errors, note | idempotent import, rebuild | `importCommit` — PortfolioEditor |
| GET | /net-worth/history | R | — | history[] | none | `netWorthHistory` — ReportsPack |
| GET | /portfolio/liquidity | R | `?entity_id` | LiquidityLadder | none | `liquidity` — Snapshot |
| GET | /portfolio/runway | R | — | Runway | none | `runway` — Snapshot |
| GET | /portfolio/review | R | — | ReviewFeed | none | `review` |
| GET | /review/centre | R | — | sections{trust,policy,liquidity,goals,changed}, attention[], last_review | none | `reviewCentre` — Review, ReportsPack |
| GET | /review/history | R | — | history[] | none | `reviewHistory` — Review |
| POST | /review/log | A | {note?, next_review_date?} | ok, id | records ReviewLog snapshot | `logReview` — Review |
| GET | /portfolio/realised-gains | R | `?year&long_term_days=365&entity_id` | RealisedGains | none | `realisedGains` — Reports, ReportsPack |
| GET | /portfolio/tax-lots | R | `?long_term_days&entity_id` | TaxLots | none | `taxLots` — Reports |
| GET | /portfolio/realised-gains.csv | R | `?year&long_term_days&entity_id` | CSV attachment | none | (link) |
| GET | /portfolio/scenarios | R | `?entity_id` | ScenarioReport | none | `scenarios` — Scenarios |
| GET | /portfolio/tags | R | `?entity_id` | TagReport | none | `portfolioTags` — TagsCard |
| PUT | /portfolio/holdings/{id}/tags | A | {tags[≤16]} | ok, tags | sets HoldingTag | `setHoldingTags` — TagsCard |
| GET | /portfolio/statements | R | `?year&entity_id` | StatementsReport | none | `statements` — Reports |
| GET | /portfolio/statements.csv | R | `?year&entity_id` | CSV attachment | none | (link) |
| GET | /portfolio/cost-of-ownership | R | `?year&entity_id` | CostOfOwnershipData | none | `costOfOwnership` — CostOfOwnershipCard |

**Overlap note:** `/portfolio/summary`, `/portfolio/holdings`, `/dashboard/home` all re-run
`value_portfolio` and return overlapping figures (total value, day change, movers). See 06/08.

## policy (`routes/policy.py`)

| GET | /policy | R | — | PolicyDoc | none | `policy` — Policy |
| GET | /policy/drift | R | `?entity_id` | PolicyDrift | none | `policyDrift` — Policy, ReportsPack |
| PUT | /policy | A | PolicyMetaIn | PolicyDoc | update intent | `putPolicy` — Policy |
| PUT | /policy/targets | A | {targets[≤200]} | PolicyDoc | replace targets | `putPolicyTargets` — Policy |

## planning (`routes/planning.py`)

| GET | /goals | R | — | GoalsReport | | `goals` — Planning |
| POST | /goals [A] | GoalIn | {id} | create | `createGoal` |
| PATCH | /goals/{id} [A] | GoalIn | {id} | update | `patchGoal` |
| DELETE | /goals/{id} [A] | — | ok | delete | `deleteGoal` |
| GET | /obligations | R | — | ObligationsReport | | `obligations` — Planning |
| POST/PATCH/DELETE | /obligations[/{id}] [A] | ObligationIn | id/ok | CRUD | `createObligation/patchObligation/deleteObligation` |
| GET | /contributions | R | — | ContributionsReport | | `contributions` — ContributionsCard |
| POST/PATCH/DELETE | /contributions[/{id}] [A] | ContributionIn | ok+ | CRUD | `addContribution/updateContribution/deleteContribution` |

Validation sets (service constants): `GOAL_BASES`, `OBLIGATION_KINDS`, `RECURRENCES`.

## insurance (`routes/insurance.py`)

| GET | /insurance | R | — | report (totals, cover_by_type, upcoming_renewals, policies[]) | | `insurance` — Insurance |
| GET | /insurance/meta | R | — | policy_types[], frequencies[] | | `insuranceMeta` |
| POST/PATCH/DELETE | /insurance[/{id}] [A] | PolicyIn | ok+ | CRUD | `addInsurance/updateInsurance/deleteInsurance` |

## estate (`routes/estate.py`)

| GET | /estate | R | — | EstateReport (profile, contacts[], documents[], readiness) | | `estate` — Estate |
| GET | /estate/meta | R | — | doc_categories, contact_roles, will_statuses, doc_statuses | | `estateMeta` |
| PUT | /estate/profile [A] | ProfileIn | ok | update profile | `putEstateProfile` |
| POST/PATCH/DELETE | /estate/contacts[/{id}] [A] | ContactIn | ok+ | CRUD | `addEstateContact/updateEstateContact/deleteEstateContact` |
| POST/PATCH/DELETE | /estate/documents[/{id}] [A] | DocumentIn | ok+ | CRUD | `addEstateDocument/updateEstateDocument/deleteEstateDocument` |

## tokens (`routes/tokens.py`) — API token management

| GET | /tokens [S] | — | tokens[] (metadata only) | | — |
| POST | /tokens [S] | {name} | id, name, prefix, token(once), note | mint token | — |
| DELETE | /tokens/{id} [S] | — | ok | revoke | — |

> **Note:** No SPA page currently manages tokens (no `api.*` method). Managed via curl/docs.

## accounts (`routes/accounts.py`)

| GET | /accounts | R | `?entity_id` | AccountsReport (rollup) | | `accounts` — Accounts |
| GET | /accounts/list | R | — | accounts[], kinds[] | | `accountsList` — PortfolioEditor |
| GET | /entities | R | — | entities[] | | `entities` — ReportsPack |
| POST/PATCH/DELETE | /accounts[/{id}] [A] | AccountIn | ok+ | CRUD (delete fails if holdings) | `addAccount/updateAccount/deleteAccount` |

## watchlists (`routes/watchlists.py`)

| GET | /watchlists | R | — | watchlists[] with quotes | | `watchlists` — Home, Markets, InstrumentDetail |
| POST | /watchlists [A] | {name, symbols[]} | ok, id | create | `createWatchlist` — Markets |
| POST | /watchlists/{id}/items [A] | {symbol} | ok, watchlist_id | add (dedup) | `addWatchItem` |
| DELETE | /watchlists/{id}/items/{symbol} [A] | — | ok | remove item | `removeWatchItem` |
| DELETE | /watchlists/{id} [A] | — | ok | delete list | `deleteWatchlist` |

## news (`routes/news.py`)

| GET | /news | R | — | items[], rss_count | RSS + provider fetch | `news` — Home, Markets, News |
| GET | /news/grouped | R | — | groups[6 areas], total | RSS + provider, sanitised | `groupedNews` — News, Review |
| GET | /news/feeds | R | — | feeds[], defaults[] | | `feeds` — Settings |
| PUT | /news/feeds [A] | {feeds[]} | ok, feeds | set feed URLs | `setFeeds` — Settings |
| GET | /news/feeds/test | R | — | results[] | tests each feed | `feedsTest` — Settings |
| GET | /briefing | R | — | text, generated_at | | `briefing` |
| POST | /briefing/refresh [A] | — | text | regenerates briefing | `refreshBriefing` — Home, News |

## ai (`routes/ai.py`)

| GET | /ai/facts | R | `?q` | intent, facts[], count, disclaimer | **no model call** | `— (AskPanel direct)` |
| GET | /ai/grounding-status | R | — | grounded, narration, model, ai_enabled, mode, remote, privacy_label, last_error | | AskPanel |
| POST | /ai/chat | R | {question(1-500)} | **SSE stream** (facts/delta/done) | model call (grounded) | `streamChat` — AskPanel, others |

## settings (`routes/settings.py`)

| GET | /settings | R | — | stored{}, defaults{} | | `settings` — Settings |
| PUT | /settings [A] | {values{}} | ok, applied, restarted_worker | allow-listed keys; base_currency writes .env + restarts worker | `updateSettings` — Settings |

## backup (`routes/backup.py`)

| POST | /backup/create [A] | — | filename, size_bytes, encrypted, sha256 | creates backup archive | — |
| POST | /backup/restore [A] | {filename, force?, identity_file?} | result | restores (guarded) | — |

## amfi / coingecko / ecb / kite (opt-in metadata adapters)

| Method | Path | Auth | Notes | Client |
|--------|------|------|-------|--------|
| GET | /amfi/status | R | schemes, priced, as_of | `amfiStatus` — AmfiCard |
| GET | /amfi/search | R | `?q` scheme search | `amfiSearch` |
| POST | /amfi/refresh [A] | file? | download/parse NAVAll.txt | `amfiRefresh` |
| POST | /instruments/{symbol}/map-amfi [A] | {code} | maps scheme code; classifies as MF; publishes NAV; 409 on dup id | `mapAmfi` |
| GET | /coingecko/status | R | coins, mapped | `coingeckoStatus` — CoingeckoCard |
| GET | /coingecko/search | R | `?q` | `coingeckoSearch` |
| POST | /coingecko/refresh [A] | file? | coin master + prices | `coingeckoRefresh` |
| POST | /instruments/{symbol}/map-coingecko [A] | {id} | maps canonical id; classifies crypto | `mapCoingecko` |
| GET | /fx/ecb/status | R | currencies, as_of, loaded | `ecbStatus` — EcbFxCard |
| POST | /fx/ecb/refresh [A] | file? | ECB daily XML | `ecbRefresh` |
| GET | /fx/convert | R | `?from&to` effective + ECB ref + method | — |
| GET | /kite/status | R | configured, instruments, by_exchange (never secrets) | `kiteStatus` — KiteCard |
| GET | /kite/search | R | `?q` | — |
| POST | /kite/refresh-instruments [A] | file? | import instrument master (read-only) | `kiteRefreshInstruments` |
| POST | /instruments/{symbol}/map-kite [A] | {instrument_token} | maps token; classifies | — |

> **No Kite order/trading endpoints exist** — market-data metadata only (`routes/kite.py` docstring).

---

## Cross-cutting observations

- **Rebuild fan-out:** many mutations call `rebuild_holdings_from_transactions` (all txn CRUD,
  reclassify, PATCH instrument, refresh_holding). `ongoing-cost` deliberately does **not**.
- **Near-duplicate readers:** `/portfolio/summary` vs `/portfolio/holdings` vs `/dashboard/home`
  (portfolio totals); `/portfolio/review` vs `/review/centre` (review feeds); `/news` vs
  `/news/grouped` (headlines). Consolidation candidates — see 06/08.
- **Entity scoping:** `entity_id` query param threaded through summary, performance, stats,
  attribution, drift, liquidity, realised-gains, tax-lots, scenarios, tags, statements,
  cost-of-ownership, accounts (client helper `withEntity`, `api.ts:125`).
- **CSV/exports:** `.csv` endpoints return `text/csv` with `Content-Disposition` attachment.
- **Multipart uploads:** import csv/preview/commit, amfi/coingecko/ecb/kite refresh (optional file).

<!-- AUDIT COMPLETE -->
