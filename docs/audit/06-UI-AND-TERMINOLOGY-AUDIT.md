# 06 — UI & Terminology Audit

## (a) Input controls

Every user-facing input, with whether it **should be master-driven** (backed by a controlled
vocabulary / reference list rather than free text). "Master?" = Yes means it should come from a
shared, deduped reference source. Many already use a `<select>` seeded from a client list or a
`/…/meta` endpoint, but those lists are **duplicated across frontend and backend and not enforced
in the DB** (see 02 §4).

| Page / component | Field | Control | Master? | Notes |
|------------------|-------|---------|---------|-------|
| PortfolioEditor · TxnForm | date/time | datetime-local | — | |
| | type | select (TXN_TYPES) | Yes✓ | enum in `api.ts:450` (10 values — omits `merger`) & backend TxnType (11) — **mismatch** |
| | symbol | free text | **partly** | should resolve to an instrument/identifier; currency auto-filled from suffix |
| | asset_class | select (TXN_ASSET_CLASSES, 6) | Yes✓ | subset of full 13; another copy |
| | country | select (COUNTRIES, 12) | Yes✓ | `refdata.ts` list (12) ≠ backend has none enforced |
| | quantity/price/fees/taxes | number | — | |
| | currency | select (inline CURRENCIES, **22**) | Yes✓ | ≠ refdata CURRENCIES (14) ≠ config SUPPORTED_CURRENCIES (9) — **3 divergent lists** |
| | note | free text | — | |
| PortfolioEditor · AssetManager | label | free text | partly | manual asset name (holding_key) |
| | asset_class | select (ASSET_CLASSES, 13) | Yes✓ | |
| | value/currency | number/select | Yes✓ (ccy) | |
| AddAssetWizard | symbol/name/qty/price/date/value + per-type meta | mixed | partly | FD rate, bond coupon, property valuation date etc. free text |
| Holdings | search | free text | — | client filter |
| Markets | search | free text | — | provider search |
| | new watchlist name | free text | — | |
| InstrumentDetail | asset_class/country/name/source_override | selects/text | Yes✓ | edit instrument |
| | ongoing cost (bps) | number | — | |
| Policy | dimension/bucket/target/min/max | select+text+number | **Yes** | bucket is **free text** but should match the dimension's master (asset_class/currency/region) |
| Planning | goal name/amount/date/currency/basis/note | text/number/date/select | Yes (ccy,basis) | basis select; currency free? |
| | obligation name/amount/due/currency/recurrence/kind/note | mixed | Yes (recurrence,kind,ccy) | |
| ContributionsCard | name/amount/currency/frequency/kind | mixed | Yes (freq,kind,ccy) | |
| Insurance | name/insurer/policy_type/policy_number/insured_person/cover/currency/cash_value/premium/frequency/dates/nominee/documents/notes/status | mixed | **insurer, policy_type = Yes** | policy_type & frequency from `/insurance/meta`; **insurer, insured_person, nominee free text** |
| Estate | contact name/relationship/roles/phone/email/notes; document title/category/location/status/review_date/related_to/notes; profile will_status/executor/... | mixed | **relationship, roles, category = Yes** | roles/category from `/estate/meta`; **relationship, executor, related_to, location free text** |
| Accounts | name/institution/kind/currency | text+select | **institution = Yes** | kind from ACCOUNT_KINDS; **institution free text (platform master needed)** |
| TagsCard | tags | free text (chips) | **Yes** | user tag master (dedupe/rename) |
| Settings · General | base currency | select (SUPPORTED_CURRENCIES) | Yes✓ | |
| | timezone | **free text** | **Yes** | should be IANA tz select |
| | data folder / age recipient / web port / intervals | text/number | — | |
| Settings · Prices | provider | select | Yes✓ | |
| | API key | password | — | |
| Settings · Intelligence | news feed URLs | textarea (free text URLs) | — | |
| | AI provider/base url/model/key | select+text+password | provider✓ | |
| Settings · Security | PIN | password (numeric) | — | |
| Adapter cards | file upload (AMFI/CoinGecko/ECB/Kite) | file | — | |

**Master-data lists that exist but are duplicated / unenforced:**
`ASSET_CLASSES` (backend `AssetClass` enum, `api.ts:453`, `refdata.ts:2`), `CURRENCIES`
(config `SUPPORTED_CURRENCIES` 9, `refdata.ts` 14, PortfolioEditor inline 22), `COUNTRIES`
(`refdata.ts` 12), and service-side sets surfaced via meta endpoints (`ACCOUNT_KINDS`,
`POLICY_TYPES`, `FREQUENCIES`, `DOC_CATEGORIES`, `CONTACT_ROLES`, `WILL_STATUSES`, `DOC_STATUSES`,
`GOAL_BASES`, `OBLIGATION_KINDS`, `RECURRENCES`, contribution KINDS). **Recommendation: one
canonical master source (DB reference tables or a single shared schema) driving both layers.**

## (b) Terminology table

Terms shown to users, synonyms/inconsistencies across pages, and a proposed canonical term.

| Concept | Terms seen (page) | Inconsistency | Canonical |
|---------|-------------------|---------------|-----------|
| Portfolio total | "Total value" (Portfolio), "Net worth" (Snapshot KPI), "Portfolio value" (Home/briefing) | total_value is used for both "total value" and "net worth" | **Total value** (portfolio) vs **Net worth** (incl. liabilities) — but code uses one figure; clarify |
| Net worth page | nav "Snapshot" / route `/snapshot` / H1 "Net worth" | label ≠ route ≠ heading | **Net worth** |
| Analytics page | nav "Portfolio" / "Analytics" chip / "manage holdings" | "Portfolio" is analytics, "Holdings" is management | **Portfolio (analytics)** / **Holdings (management)** |
| Movers | "Top movers", "Contributors", "Gainers/Detractors", "Top gainers/losers" | 3 phrasings | **Gainers / Detractors** |
| Day change | "Today", "Today's change", "Day", "day_change" | | **Today's change** |
| Realised gain | "Realised gains", "Realised P/L", "Realised" | | **Realised gain** |
| Unrealised | "Unrealised P/L", "Unrealised", "paper gain" | | **Unrealised P/L** |
| Data freshness | "stale", "Cached", "Delayed", "as_of", entitlement | overlapping | see 09 (entitlement vs staleness) |
| Valuation source | "source", "provider", "routing", "route_source" | | **Source** (provenance) |
| Ongoing cost | "Estimated ongoing cost", "expense ratio", "annual_cost_bps", "cost of ownership" | | **Ongoing cost (expense ratio)** |
| Concentration | "Concentration", "HHI", "Largest position", "Top 5" | | keep distinct (see 09) |
| Ownership entity | "entity", "Household", "Self/Spouse/Trust" | only surfaced in ReportsPack | **Entity** |
| Account vs platform | "account", "institution", "platform" (docs) | institution = platform | **Account** (name) + **Institution** |
| Simple/Expert | "Simple/Expert" (top bar), "Detail level" (Settings) | two labels for same control | **Detail level: Simple/Expert** |
| Review | "Review Centre", "Needs a look", "What needs attention", "Attention" | | **Review** |
| Return/vol | "Return / volatility" explicitly "NOT Sharpe" | risk of misreading as Sharpe | keep the disclaimer |

## (c) Same information on multiple pages → ONE canonical home

(See 01 duplication summary for the full matrix.) Recommendations:

| Information | Canonical home | Elsewhere → link, don't recompute |
|-------------|----------------|-----------------------------------|
| Portfolio value / day / unrealised / return | **Portfolio** | Home, Holdings, Snapshot, Review, Pack |
| Allocation donuts | **Portfolio** | Home, Snapshot, Pack |
| Movers / contributors | **Portfolio** | Home, Markets |
| Performance chart | **Portfolio** | Home, Snapshot |
| Net-worth trend + liquidity + runway | **Net worth (Snapshot)** | Pack, Scenarios, Review |
| Review / attention | **Review** | Home, Snapshot (ReviewCard) |
| Briefing + headlines | **News** | Home, Markets |
| Market quotes / indices | **Markets** | Home, InstrumentDetail |
| Policy drift | **Policy** | Review, Pack |
| Pricing provenance / confidence | **Pricing Health** | Review (trust) |

## (d) Navigation map

Routes (`App.tsx:164`). Nav order/labels from `nav.ts` (17 items, user-reorderable). `/global`
redirects to `/markets`.

| Route | Nav label | How reached | Notes |
|-------|-----------|-------------|-------|
| `/` | Home | nav, logo, rotation | landing |
| `/portfolio` | Portfolio | nav, Home links | analytics |
| `/holdings` | Holdings | nav, Portfolio "manage", Home top-holdings | CRUD |
| `/accounts` | Accounts | nav | |
| `/markets` | Markets | nav, Home cards, rotation | |
| `/heatmap` | Heatmap | nav, rotation | |
| `/news` | News | nav, Home "more", rotation | |
| `/snapshot` | Snapshot ("Net worth") | nav | |
| `/review` | Review | nav, ReviewCard | |
| `/policy` | Policy | nav | |
| `/planning` | Planning | nav, Snapshot runway link | |
| `/insurance` | Insurance | nav | |
| `/estate` | Estate | nav | |
| `/scenarios` | Scenarios | nav | |
| `/settings` | Settings | nav, various deep links | |
| `/help` | Help | nav | |
| `/legal` | Legal | nav, Footer | |
| `/reports` | — (not in nav) | Portfolio "Reports" btn, Holdings? | **orphan from nav** — only reachable via in-page links |
| `/reports/pack` | — | Reports link | orphan from nav |
| `/pricing-health` | — | Holdings/InstrumentDetail links | orphan from nav |
| `/instrument/:symbol` | — | any symbol link | detail |
| `/global` | — | redirect → `/markets` | dead route (legacy) |

**Orphaned from the sidebar** (reachable only via in-page links, easy to miss): Reports,
Reports Pack, Pricing Health. **Dead route:** `/global`. **Dead ends:** none critical — every page
has nav back. Consider surfacing Reports & Pricing Health in nav or under Portfolio.

<!-- AUDIT COMPLETE -->
