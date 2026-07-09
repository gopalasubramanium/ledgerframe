# 02 — Data Model

Source of truth for the schema of a ground-up rebuild. All ORM models live in a single
module: `app/models/__init__.py`. Money is stored as **TEXT** and round-tripped through
`decimal.Decimal` (`app/db/base.py:24` `DecimalText`); datetimes are stored **naive-UTC**
and always returned tz-aware UTC (`app/db/base.py:50` `UTCDateTime`). SQLite is the default
backend (WAL, `foreign_keys=ON`, `busy_timeout=30000` — `app/db/base.py:139`), but a
Postgres/MySQL async URL may be injected via `LEDGERFRAME_DB_URL` (`app/core/config.py:44`).

> **Schema authority:** Production boots via **Alembic migrations** (`app/main.py:113`
> `run_migrations`). `Base.metadata.create_all` is used only by test fixtures. The ORM
> money columns are intentionally TEXT on every dialect so the ORM schema matches the
> migrated schema exactly (`app/db/base.py:24-34`).

---

## 1. Enums

| Enum | File:line | Values (stored as) |
|------|-----------|--------------------|
| `AssetClass` | `app/models/__init__.py:26` | `equity, etf, mutual_fund, bond, cash, fixed_deposit, commodity, crypto, property, private, retirement, liability, other` — **stored as `String(20)`, not a DB enum** |
| `TxnType` | `app/models/__init__.py:42` | `buy, sell, dividend, interest, deposit, withdrawal, fee, split, bonus, merger, transfer` — stored as `String(16)` |

Many other "enum-like" fields are **free-text strings with a documented value set but no DB
constraint** — see §4 (master-data flags). Examples: `Account.kind`, `Entity.kind`,
`Instrument.asset_subclass`, `Goal.basis`, `Obligation.recurrence`, `InsurancePolicy.policy_type`.

---

## 2. Tables

Types below are the ORM column types. `DecimalText`=TEXT holding a Decimal; `UTCDateTime`=DateTime
stored naive-UTC. "ISO date" columns are `String(10)`/`String(12)` holding `yyyy-mm-dd` text.

### 2.1 Identity & settings

#### `users` (`User`, `:61`)
| Field | Type | Constraints / notes |
|-------|------|--------------------|
| id | int PK | |
| name | String(80) | default `"Owner"` |
| pin_hash | String(255) nullable | Argon2 hash; null = no PIN set (unlocked) |
| created_at | UTCDateTime | default `utcnow` |
| tokens_valid_after | Float | default 0.0; float epoch — tokens with `iat` < this are invalid. Bumped on PIN change (§1.7 session revocation) |

Single-row table in practice (one owner).

#### `revoked_token` (`RevokedToken`, `:73`)
| jti | String(64) PK | revoked session token id |
| revoked_at | UTCDateTime | default utcnow |

Used by `/auth/lock` to blacklist a specific token id.

#### `api_token` (`ApiToken`, `:81`)
| id | int PK | |
| name | String(80) | default `"API token"` |
| token_hash | String(64) unique index | **SHA-256** of the raw token (fast hash OK: 256-bit entropy) |
| prefix | String(16) | leading chars, identification only |
| created_at | UTCDateTime | |
| last_used_at | UTCDateTime nullable | |
| revoked_at | UTCDateTime nullable | non-null = revoked |

Raw token shown once at creation, never retrievable. Read-only (GET/HEAD) scope enforced in `deps.py`.

#### `settings` (`Setting`, `:101`)
| key | String(80) PK | |
| value | Text | default `""` |
| updated_at | UTCDateTime | default utcnow, onupdate utcnow |

Generic key/value store. **Never holds secrets.** Keys written by the Settings API are allow-listed
(`app/api/v1/routes/settings.py:23`): `base_currency, rotation_seconds, refresh_interval_seconds,
privacy_mode, reduced_motion, high_contrast, voice_enabled, display_sleep_minutes, ai_model,
focus_page, rotation_pages`. Also used internally for briefing text, feed URLs, demo-seed flag.

#### `provider_configs` (`ProviderConfig`, `:108`)
| id | int PK | |
| kind | String(40) | `market` / `ai` / `voice` — **free text** |
| name | String(80) | |
| enabled | Boolean | default True |
| config_json | Text | default `"{}"` — **never holds raw secrets** |
| updated_at | UTCDateTime | |

> **NOTE:** This table appears defined but is not obviously read/written by any route
> (secrets live in `.env`; provider selection lives in `.env` via `envfile.py`). Candidate
> dead table — see OPEN-QUESTIONS / 08-TECH-DEBT.

### 2.2 Accounts, instruments, market data

#### `entities` (`Entity`, `:121`)
| id | int PK | |
| name | String(80) | default `"Household"` |
| kind | String(40) | default `"self"`; values `self, spouse, trust, company, other` — **free text** |
| created_at | UTCDateTime | |
| accounts | relationship → Account | back_populates |

Ownership entity (Phase 4.1). Migration assigns every existing account to a single default entity.

#### `accounts` (`Account`, `:134`)
| id | int PK | |
| name | String(120) | |
| kind | String(40) | default `"brokerage"`; also `manual` (auto-created), and `ACCOUNT_KINDS` set in `app/services/accounts.py` — **free text** |
| currency | String(3) | default `"SGD"` |
| institution | String(120) nullable | **free text** (platform/broker name) |
| created_at | UTCDateTime | |
| entity_id | int FK→entities.id nullable, index | Phase 4.1 |
| cost_basis_method | String(16) | default `"fifo"`; `fifo`/`average`/(future `spec`) — Phase 4.4 |
| holdings | relationship → Holding | |
| entity | relationship → Entity | |

#### `instruments` (`Instrument`, `:153`)
| id | int PK | |
| symbol | String(40) index | |
| exchange | String(20) nullable | |
| name | String(160) | default `""` |
| asset_class | String(20) | default `equity` (AssetClass) |
| currency | String(3) | default `"USD"` |
| sector | String(80) nullable | **free text** |
| country | String(60) nullable | **free text** |
| market_cap | DecimalText nullable | |
| is_manual_price | Boolean | default False |
| annual_cost_bps | DecimalText nullable | §4.6 expense ratio (bps); null = not set (NOT zero) |
| asset_subclass | String(40) nullable | ETF/REIT/mutual_fund/derivative/… **free text** |
| asset_category | String(40) nullable | reporting family — **free text** |
| liquidity_profile | String(20) nullable | `listed/redeemable/locked/illiquid/manual` — **free text** |
| valuation_method | String(30) nullable | persisted preferred method |
| pricing_currency | String(3) nullable | |
| domicile_country | String(2) nullable | ISO-3166 alpha-2 |
| listing_country | String(2) nullable | |
| exchange_mic | String(10) nullable | ISO 10383 MIC |
| source_override | String(40) nullable | force a provider |
| last_verified_at | UTCDateTime nullable | |

Constraint: `UniqueConstraint(symbol, exchange)` = `uq_instr_symbol_exch` (`:180`).

#### `instrument_identifiers` (`InstrumentIdentifier`, `:183`)
| id | int PK | |
| instrument_id | int FK→instruments.id index | |
| id_type | String(24) | `isin/cusip/figi/sedol/amfi_code/kite_token/coingecko_id/provider_symbol` |
| value | String(64) | |
| provider | String(40) nullable | for provider_symbol rows |
| is_primary | Boolean | default False |
| created_at | UTCDateTime | |

Constraints/indexes (`:196`):
- `uq_ident_instr_type_value` unique(instrument_id, id_type, value)
- `ix_ident_type_value` index(id_type, value)
- `uq_ident_high_conf` — **partial unique** index on (id_type, value) where id_type ∈ HIGH_CONFIDENCE_IDS → a high-confidence id can't point at two instruments
- `uq_ident_provider_symbol` — partial unique(provider, value) where id_type='provider_symbol'

`HIGH_CONFIDENCE_IDS` (`:212`) = `{isin, cusip, figi, sedol, amfi_code, kite_token, coingecko_id}`.

#### `amfi_schemes` (`AmfiScheme`, `:215`) — Indian MF master + NAV cache
| code | String(12) PK | |
| name | String(200) index | |
| isin_growth | String(20) nullable index | |
| isin_reinvest | String(20) nullable | |
| fund_house | String(120) nullable | |
| category | String(160) nullable | |
| nav | DecimalText nullable | |
| nav_date | String(12) nullable | ISO date |
| updated_at | UTCDateTime | |

#### `coingecko_coins` (`CoingeckoCoin`, `:231`)
| id | String(80) PK | canonical CoinGecko id |
| symbol | String(30) index | |
| name | String(120) index | |
| market_cap_usd | DecimalText nullable | |
| updated_at | UTCDateTime | |

#### `ecb_fx_rates` (`EcbFxRate`, `:243`)
| currency | String(3) PK | |
| rate | DecimalText | EUR → currency |
| as_of | String(12) nullable | |
| updated_at | UTCDateTime | |

Reference-FX fallback for translation only; never a trading quote.

#### `kite_instruments` (`KiteInstrument`, `:254`)
| instrument_token | Integer PK | |
| exchange | String(12) index | |
| tradingsymbol | String(60) index | |
| name | String(120) | default `""` |
| segment | String(20) nullable | |
| instrument_type | String(6) nullable | `EQ/FUT/CE/PE` |
| lot_size | Integer | default 1 |
| expiry | String(12) nullable | |
| strike | DecimalText nullable | |
| updated_at | UTCDateTime | |

#### `quotes` (`Quote`, `:272`) — latest quote per instrument
| instrument_id | int FK→instruments.id **PK** | one row per instrument |
| price | DecimalText | |
| previous_close | DecimalText nullable | |
| currency | String(3) | default USD |
| source | String(40) | default `"mock"` — provider name |
| entitlement | String(20) | default `"delayed"` (realtime/delayed/eod/unavailable) |
| market_time | UTCDateTime nullable | |
| received_at | UTCDateTime | default utcnow |

#### `price_history` (`PriceHistory`, `:286`)
| id | int PK | |
| instrument_id | int FK index | |
| interval | String(10) | default `"1d"` |
| ts | UTCDateTime | |
| open/high/low/close | DecimalText | |
| volume | DecimalText nullable | |

Index: `ix_hist_instr_interval_ts` unique(instrument_id, interval, ts) (`:297`).

### 2.3 Portfolio

#### `holdings` (`Holding`, `:305`)
| id | int PK | |
| account_id | int FK→accounts.id index | |
| instrument_id | int FK→instruments.id nullable index | null = manual asset |
| label | String(160) nullable | for manual assets — **free text** |
| asset_class | String(20) | default equity |
| quantity | DecimalText | default 0 |
| avg_cost | DecimalText | per-unit, native ccy; default 0 |
| manual_value | DecimalText nullable | non-null = manual asset |
| currency | String(3) | default USD |
| meta | Text nullable | JSON per-asset metadata (FD/bond/property/etc.) |
| deleted_at | UTCDateTime nullable index | §3.5 soft-delete |
| account | relationship → Account | |

**Important:** Holdings are **derived/rebuilt from transactions** (`rebuild_holdings_from_transactions`);
manual holdings (`manual_value` set) are preserved across rebuilds. `holding_key` used by tags =
instrument symbol OR manual label.

#### `transactions` (`Transaction`, `:328`)
| id | int PK | |
| account_id | int FK index | |
| instrument_id | int FK nullable index | |
| type | String(16) | TxnType |
| ts | UTCDateTime index | |
| quantity | DecimalText | default 0 |
| price | DecimalText | default 0 (for MERGER: carries ratio) |
| fees | DecimalText | commissions/charges |
| taxes | DecimalText | stamp duty/withholding |
| amount | DecimalText | signed cash impact |
| currency | String(3) | default USD |
| note | String(255) nullable | |
| import_batch | String(40) nullable | dedupe key for CSV import |
| deleted_at | UTCDateTime nullable index | §3.5 soft-delete |
| fx_to_base | DecimalText nullable | §4.2 trade-date FX (native→base at commit) |
| fx_base | String(3) nullable | base currency the fx was captured against |
| related_instrument_id | int FK nullable | §4.3 MERGER target B |

#### `portfolio_snapshots` (`PortfolioSnapshot`, `:362`)
| id | int PK; ts UTCDateTime index; base_currency String(3); total_value/cost_basis/unrealised_pl/day_change DecimalText; detail_json Text (allocations) |

#### `net_worth_snapshots` (`NetWorthSnapshot`, `:374`)
| id PK; ts index; base_currency; assets/liabilities/net_worth DecimalText |

### 2.4 Watchlists, news, notes

- `watchlists` (`Watchlist`, `:387`): id, name String(120), sort_order int; items cascade-delete.
- `watchlist_items` (`WatchlistItem`, `:397`): id, watchlist_id FK(CASCADE) index, instrument_id FK, sort_order.
- `market_news` (`MarketNews`, `:408`): id, headline String(400), summary Text?, url String(600)?, source String(120), published_at index, symbols_csv String(255), fetched_at. *(Cache table; feeds are mostly fetched live — see 08.)*
- `notes` (`Note`, `:420`): id, instrument_id FK nullable index, body Text, created_at, updated_at. *(No route observed writes/reads Notes — candidate dead table; see OPEN-QUESTIONS.)*

### 2.5 Dashboards

- `dashboard_configs` (`DashboardConfig`, `:434`): id, name String(80) default "default", rotation_seconds int default 30, focus_page String(40)?; items cascade.
- `dashboard_rotation_items` (`DashboardRotationItem`, `:445`): id, config_id FK(CASCADE) index, page String(40), enabled bool, sort_order.

> **NOTE:** Rotation/focus are also persisted as `settings` rows (`focus_page`, `rotation_pages`,
> `rotation_seconds`). Two storage mechanisms for the same concept — see 06/08.

### 2.6 AI conversations

- `ai_conversations` (`AIConversation`, `:460`): id, title String(160), created_at; messages cascade.
- `ai_messages` (`AIMessage`, `:470`): id, conversation_id FK(CASCADE) index, role String(16) (user/assistant/system), content Text, facts_json Text default "{}", created_at.

> **NOTE:** The AI chat endpoint streams via SSE and does not appear to persist conversations/messages.
> These two tables may be unused by current routes — see OPEN-QUESTIONS.

### 2.7 Audit & backups

- `audit_events` (`AuditEvent`, `:486`): id, ts index default utcnow, category String(40) (auth/mutation/security/system), action String(80), detail Text (**never secrets**).
- `backup_records` (`BackupRecord`, `:495`): id, ts, filename String(255), size_bytes int, encrypted bool, sha256 String(64)?.

### 2.8 Investment Policy (stores intent only)

- `investment_policy` (`InvestmentPolicy`, `:510`): id, name String(80), base_currency String(3)? (null→settings base), default_band_pct Decimal default 5, max_position_pct Decimal? (optional risk band), notes Text?, is_active bool, created_at, updated_at; targets cascade.
- `policy_targets` (`PolicyTarget`, `:525`): id, policy_id FK index, dimension String(20) (`asset_class`/`currency`/`region`), bucket String(40) (e.g. equity/SGD/India — **free text**), target_pct Decimal, min_pct?, max_pct?. Unique(policy_id, dimension, bucket) = `uq_policy_target`.

Drift/band status/concentration are computed **live**, never stored.

### 2.9 Planning — goals & obligations (intent only)

- `goals` (`Goal`, `:544`): id, name String(80), target_amount Decimal, target_date String(10)? ISO, currency String(3)? (null→base), basis String(16) default `net_worth` (`net_worth`/`liquid`/`none`), note Text?, created_at, updated_at.
- `obligations` (`Obligation`, `:557`): id, name String(80), amount Decimal, due_date String(10) ISO, currency String(3)?, recurrence String(12) default `once` (`once/monthly/quarterly/annual`), kind String(8) default `expense` (`expense`/`income`), note Text?, created_at, updated_at.

### 2.10 Review log

- `review_log` (`ReviewLog`, `:575`): id, reviewed_at index default utcnow, net_worth Decimal, base_currency String(3) default SGD, confidence int, drift_flags int, attention_count int, note Text?, next_review_date String(10)? ISO.

### 2.11 Insurance (W3) — protection register, isolated

- `insurance_policy` (`InsurancePolicy`, `:594`): id, name String(120), insurer String(120)? (**free text**), policy_type String(30) default `other`, policy_number String(80)?, insured_person String(120)?, cover_amount Decimal, currency String(3) default SGD, cash_value Decimal? (**NOT injected into net worth**), premium Decimal?, premium_frequency String(12) default `annual`, start_date/renewal_date String(10)? ISO, nominee String(120)?, linked_goal_id int? (**soft link, no FK**), documents Text? (JSON `[{label,have}]`), notes Text?, status String(12) default `active`, created_at.

### 2.12 Estate & document readiness (W4) — isolated, no FKs

- `estate_profile` (`EstateProfile`, `:622`): id, will_status String(16) default `none` (`none/draft/executed/needs_update`), will_location String(160)?, executor String(120)?, last_reviewed String(10)?, next_review_date String(10)?, notes Text?.
- `estate_contact` (`EstateContact`, `:633`): id, name String(120), relationship String(60)? (**free text** — role), roles Text default `"[]"` (JSON list), phone String(40)?, email String(120)?, notes Text?, created_at.
- `estate_document` (`EstateDocument`, `:645`): id, title String(120), category String(24) default `other`, location String(160)?, status String(12) default `present` (`present/missing/outdated`), review_date String(10)?, related_to String(120)? (**free text, no FK**), notes Text?, created_at.

### 2.13 Tags + contributions (W8)

- `holding_tag` (`HoldingTag`, `:664`): id, account_id int index, holding_key String(200) (instrument symbol or manual label), tags Text default `"[]"` (JSON list of **free-text** tag strings). Unique(account_id, holding_key) = `uq_holding_tag`.
- `contribution` (`Contribution`, `:673`): id, name String(120), amount Decimal, currency String(3) default SGD, frequency String(12) default `monthly` (`monthly/quarterly/annual/once`), kind String(12) default `invest` (`invest/withdraw/prepay`), target_goal_id int? (**soft link**), start_date String(10)?, active bool, note Text?, created_at.

---

## 3. Alembic migrations (in order)

Linear chain; head = `d1e7a4c02f95`. Files in `app/db/migrations/versions/`.

| # | Revision | Slug | Summary of ops |
|---|----------|------|----------------|
| 1 | c8a035ade752 | initial_schema | Creates core tables: accounts, ai_conversations, ai_messages, audit_events, backup_records, dashboard_configs, dashboard_rotation_items, instruments, market_news, net_worth_snapshots, notes, portfolio_snapshots, price_history, provider_configs, quotes, settings, transactions, users, watchlists, watchlist_items, holdings (+ indexes) |
| 2 | b2f1c7d9e004 | add_transaction_taxes | `transactions.taxes` column (+ backfill UPDATE) |
| 3 | a3d21f7e5b10 | phase2_identity_taxonomy | `instruments` taxonomy columns; creates `instrument_identifiers` (+ indexes); backfills provider_symbol/currency/country via UPDATE |
| 4 | b4e77c9a1f22 | phase4_amfi_schemes | creates `amfi_schemes` (+ name/isin indexes) |
| 5 | c5f88d0b3a41 | phase4_coingecko_coins | creates `coingecko_coins` (+ symbol/name indexes) |
| 6 | d6a99e1c2b73 | phase4_ecb_fx | creates `ecb_fx_rates` |
| 7 | e7b1a2c4d905 | phase4_kite_instruments | creates `kite_instruments` (+ exchange/tradingsymbol indexes) |
| 8 | f8c2a1b3d704 | ident_uniqueness | partial unique indexes: high-confidence ids + provider_symbol |
| 9 | a9d3e5f70218 | holding_meta | `holdings.meta` column |
| 10 | b4e6c1f27a90 | investment_policy | creates `investment_policy`, `policy_targets` (+ index) |
| 11 | c5f7a2e91b30 | goals_obligations | creates `goals`, `obligations` |
| 12 | d6a8b3f04c21 | obligation_kind | `obligations.kind` column |
| 13 | e7c9d4a13b52 | review_log | creates `review_log` (+ index) |
| 14 | f1a2c7d5e9b3 | insurance_policy | creates `insurance_policy` |
| 15 | a3b8e1f42c67 | estate | creates `estate_profile`, `estate_contact`, `estate_document` |
| 16 | b5c9f0a71d84 | tags_contributions | creates `holding_tag` (+ index), `contribution` |
| 17 | c4d1e8a92f60 | session_revocation | creates `revoked_token`; `users.tokens_valid_after` column |
| 18 | d5e2f0b83a19 | api_token | creates `api_token` (+ token_hash index) |
| 19 | e3f8a1c92d45 | soft_delete | `holdings.deleted_at`, `transactions.deleted_at` (+ indexes) |
| 20 | f4a9c2b71e08 | entities | creates `entities`; `accounts.entity_id` (+ index); seeds default entity via INSERT + backfill |
| 21 | a1c8f34b9d62 | trade_date_fx | `transactions.fx_to_base`, `transactions.fx_base` |
| 22 | b7d2f4a91c53 | merger_target | `transactions.related_instrument_id` |
| 23 | c9a1e4f78b62 | cost_basis_method | `accounts.cost_basis_method` |
| 24 | d1e7a4c02f95 | instrument_annual_cost_bps | `instruments.annual_cost_bps` **(HEAD)** |

> Note: many Phase-4 features landed "schema only in Unit A" — the column exists before any
> reader/writer uses it (see model comments). Cross-check with 08-TECH-DEBT for columns not
> yet consumed (`domicile_country`, `cost_basis_method`=average, `related_instrument_id` merger
> handling raises).

---

## 4. Free-text fields that conceptually should reference master data

Flagged per the audit brief. "Master-driven" = candidate for a controlled vocabulary /
reference table / FK instead of an unconstrained string.

| Table.field | Current type | Concept | Recommended master |
|-------------|--------------|---------|--------------------|
| accounts.kind | String(40) free | account type | enum/reference (`ACCOUNT_KINDS` exists in service but not enforced in DB) |
| accounts.institution | String(120) free | platform/broker | **institution/platform master** (dedupe "DBS" vs "DBS Bank") |
| accounts.currency, *.currency (all) | String(3) free | currency | `SUPPORTED_CURRENCIES` list — not DB-enforced |
| entities.kind | String(40) free | entity type | enum `self/spouse/trust/company/other` |
| instruments.sector | String(80) free | sector | **sector master** (GICS-like) |
| instruments.country / listing_country / domicile_country | free / ISO2 | country | **country/region master** (ISO-3166) |
| instruments.asset_subclass / asset_category | String free | instrument taxonomy | **instrument-type master** |
| instruments.liquidity_profile | String(20) free | liquidity | enum `listed/redeemable/locked/illiquid/manual` |
| holdings.label / holding_key | String free | manual asset name | user-owned, but should key to a stable id |
| policy_targets.bucket | String(40) free | allocation bucket | should match the master for its dimension (asset_class/currency/region) |
| goals.basis | String(16) free | goal basis | enum `net_worth/liquid/none` |
| obligations.recurrence/kind | String free | recurrence/type | enum |
| insurance_policy.policy_type | String(30) free | insurance type | **insurance-type master** (`POLICY_TYPES` in service) |
| insurance_policy.insurer | String(120) free | insurer | **insurer master** |
| estate_contact.relationship / roles | free / JSON | relationship/role | **relationship + role master** (`CONTACT_ROLES` in service) |
| estate_document.category | String(24) free | document type | **document-type master** (`DOC_CATEGORIES` in service) |
| holding_tag.tags | JSON free strings | tags | user-defined tag master (dedupe/rename) |
| contribution.frequency/kind | String free | recurrence/type | enum |
| provider_configs.kind | String(40) free | provider kind | enum market/ai/voice |

Note: several of these already have a canonical list defined **in the service layer** (e.g.
`ACCOUNT_KINDS`, `POLICY_TYPES`, `FREQUENCIES`, `DOC_CATEGORIES`, `CONTACT_ROLES`,
`WILL_STATUSES`, `DOC_STATUSES`, `GOAL_BASES`, `OBLIGATION_KINDS`, `RECURRENCES`) and are
surfaced via `/…/meta` endpoints — but they are **not enforced at the DB layer**, and the
frontend `refdata.ts`/`policyTemplates.ts` carry parallel copies. See 06-UI-AND-TERMINOLOGY.

<!-- AUDIT COMPLETE -->
