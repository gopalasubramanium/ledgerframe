# 05 — Providers, Routing & Grounded AI

## Part A — Market data providers

### A.1 Registry & selection (`app/providers/market/__init__.py`)
`get_provider()` (cached singleton) picks by `LEDGERFRAME_MARKET_PROVIDER`:
`csv`→CSV, `mock`/`demo`/``→Mock, `yahoo`→Yahoo, `eodhd`→Eodhd, `kite`→Kite, else→External
(Alpha Vantage). **All non-trivial imports are lazy and degrade to Mock on any error** (never
crash demo mode). `reset_provider()` clears the cache (settings change / tests). Interface
`MarketDataProvider` Protocol (`base.py:20`): `get_quote, get_history, search_instruments,
get_market_status, get_fx_rate, get_news`.

### A.2 Provider capability registry (`router.py:53`, `CAPABILITIES`)

| Provider | quote | history | search | fx | news | indices | fetch_on_demand | needs_key | asset_classes | regions | entitlement |
|----------|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|---|---|---|
| mock | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | – | all | * | delayed |
| csv | ✓ | ✓ | – | – | – | – | ✓ | – | equity, etf | * | end-of-day |
| yahoo | ✓ | ✓ | ✓ | ✓ | – | ✓ | **✗** | – | all | * | delayed |
| alphavantage | ✓ | ✓ | ✓ | ✓ | – | ✓ | **✗** | ✓ | equity, etf, fx, crypto, index | US, * | delayed |
| amfi_nav | ✓ | ✓ | ✓ | – | – | – | ✗ | – | mutual_fund | IN | end-of-day |
| coingecko | ✓ | – | ✓ | – | – | – | ✗ | – | crypto | * | delayed |
| ecb_fx | ✗ | – | – | ✓ | – | – | ✗ | – | fx | * | end-of-day |
| eodhd | ✓ | ✓ | ✓ | ✓ | – | ✓ | ✗ | ✓ | equity, etf, fx, crypto, index, mutual_fund | US, SG, IN, * | delayed |
| kite | ✓ | – | ✓ | – | – | – | ✗ | ✓ | equity, derivative, commodity | IN | delayed |

`fetch_on_demand=False` → **rate-limited**: pages serve cache, worker/button refreshes. All quotes
carry `EntitlementStatus` (never `real-time` — the validator blocks any "real-time/live" claim).

### A.3 Per-provider behaviour

| Provider | File | Endpoint / source | Pacing / rate-limit handling | Fallback |
|----------|------|-------------------|------------------------------|----------|
| **Mock** | mock.py | none (deterministic DEMO) | n/a | — (is the fallback) |
| **CSV** | csv_provider.py | files in `imports_dir` | offline; latest row = EOD quote | mock for FX/search/news |
| **Yahoo** | yahoo.py | `query1.finance.yahoo.com` chart/search | **shared process lock, 1.5s min interval**, 3 retries w/ 429 backoff (`_get`, :93) | Mock for status/FX/search/news |
| **Alpha Vantage** (External) | external.py | `www.alphavantage.co/query` | free tier ~25 req/day; `Semaphore(1)` serialises; `_check_limit` detects notices; **learns Index Data tier** from first index probe (`av_tier` premium/free/unknown) | Mock; ETF proxies when not premium |
| **EODHD** | eodhd.py | `eodhd.com/api` | `Semaphore(2)`, 0.6s sleep on throttle | UNAVAILABLE quote |
| **Kite** | kite.py | `api.kite.trade` | read-only; `KiteSessionExpired` → 401 | UNAVAILABLE; creds from **env only** |

### A.4 Metadata adapters (opt-in, cache tables)

| Adapter | Fetch URL | Publishes into | Mapping id | Notes |
|---------|-----------|----------------|-----------|-------|
| AMFI | `portal.amfiindia.com/spages/NAVAll.txt` | `amfi_schemes` + Quote (`source=amfi_nav`, OFFICIAL_NAV) | `amfi_code` | Indian MF NAV; upload or download |
| CoinGecko | `api.coingecko.com/api/v3` (coins/list, simple/price) | `coingecko_coins` + Quote | `coingecko_id` | canonical id mapping only |
| ECB FX | `ecb.europa.eu/.../eurofxref-daily.xml` | `ecb_fx_rates` (EUR→ccy) | — | reference FX fallback only |
| Kite instruments | `api.kite.trade/instruments` | `kite_instruments` | `kite_token` | F&O identity; no orders |

### A.5 Quote persistence & staleness (`services/market.py`)
- `refresh_quote` (:163): routes per instrument (see A.6). If the selected source ≠ active
  provider → returns cached (never overwrites a NAV/canonical price). Null price → keep cache
  (column NOT NULL). Race-safe **upsert ON CONFLICT** on instrument_id.
- `get_cached_quote` (:216): marks CACHED/stale if older than threshold; UNAVAILABLE if none.
- `display_quote` (:249): cache when fresh; live fetch only for `fetch_on_demand` providers.
- `is_stale` (`market.py:31`): `age > stale_after_seconds` (default 900); EOD/NAV get
  `max(threshold, 30h)` (`_EOD_STALE_SECONDS`) — daily data is fresh for the day.
- `get_history_cached` (:262): caches candles in `price_history`; refetch at most once per
  `max_age_hours=12` per (instrument, interval) via a `Setting` marker; empty result never locks
  the marker; history routed like quotes (`_history_source`).
- `reclassify_instruments` (:385): infers asset class from linked ids / crypto heuristic
  (`_COMMON_CRYPTO`), backfills country, repairs mis-scraped names on crypto/MF.
- FX in `services/fx.py`: USD-triangulated cross rates, 10-min cache, ECB fallback (see 04 §12).

### A.6 PriceSourceRouter decision tree — `router.route()` (`router.py:195`)

Pure/testable. Inputs: instrument_id, symbol, asset_class, asset_subclass, listing_country,
mappings (id_types present), active_provider, has_manual, source_override, cached_source,
availability. Live context gathered by `route_for_instrument` (`services/market.py:136`).

**Lanes** (`lane_for`, :128) → `DEFAULT_PRIORITY` (:112):

| Lane | Trigger | Priority chain (only *configured & capable* used) |
|------|---------|---------------------------------------------------|
| in_equity | equity/etf, IN | kite → eodhd → alphavantage → yahoo → csv → manual |
| sg_equity | equity/etf, SG | eodhd → alphavantage → yahoo → csv → manual |
| us_equity | equity/etf, else | eodhd → alphavantage → yahoo → csv → manual |
| in_mutual_fund | mutual_fund, IN | amfi_nav → statement → manual |
| global_fund | mutual_fund, non-IN | eodhd → alphavantage → statement → manual |
| crypto | crypto | coingecko → alphavantage → yahoo → csv → manual |
| fx | — | alphavantage → yahoo → ecb_fx → cache |
| bond | bond | eodhd → statement → manual → accrual |
| deposit | fixed_deposit | statement → accrual → manual |
| retirement | retirement | amfi_nav → statement → manual |
| derivative | subclass=derivative | kite → statement → manual |
| manual_only | cash/property/private/liability/insurance/other | statement → manual |

**Decision order** (what wins, what can never overwrite what):
1. **source_override** wins if a known source (`CAPABILITIES`). Unknown → ignored + reason.
2. **manual-only lanes** (`manual_only`, `deposit`): value from user/statement, never a feed.
   `manual` if has_manual else `None`+"set a manual value".
3. **Cache-publish lanes** (amfi_nav↔amfi_code, coingecko↔coingecko_id): a cache-publish source
   OWNS the price only when mapped AND `cached_source == src`. **Mutual fund is strict** — NAV or
   manual only (never an equity feed); if mapped but no NAV → "awaiting NAV"; if unmapped →
   `mapping_required`, manual/None. **Crypto** legitimately falls through to the active provider
   when unmapped (`mapping_required` flag set but symbol pricing works).
4. **Active provider** if in chain or mock → `market_quote`.
5. else manual (if has_manual) or `None` + "no configured source can price this holding".

`_auth_gap` (:161): flags `auth_required` when a higher-priority **configured** keyed source is
missing credentials. Terminal sources (manual/statement/accrual/cache) never gate auth.

Output `RouteDiagnostic`: lane, priority_chain, source_selected, valuation_method,
mapping_required, auth_required, has_manual_override, reason — **surfaced in Pricing Health**.

**Guarantee:** the active market provider can never overwrite a NAV or a canonical-id crypto price
with a wrong equity quote (`refresh_quote` checks `source_selected` first).

### A.7 Source override validation — `validate_source_override` (`market.py:90`)
Rejects: unknown source; manual-only asset class; asset-class/region not covered by the source;
amfi_nav without an amfi_code on a MF; coingecko without a coingecko_id on a crypto; keyed source
without credentials. Empty/"auto"/"none" clears the override.

---

## Part B — AI providers

### B.1 Registry (`app/providers/ai/__init__.py`)
`get_ai_provider()` by settings: `!ai_enabled` or `disabled`→**Disabled**; `openai_compatible` +
base URL→**OpenAICompatible**; else→**Hailo/Ollama** (default). `reset_ai_provider()` on config
change.

| Provider | File | Endpoint | Privacy | Notes |
|----------|------|----------|---------|-------|
| **Disabled** | disabled.py | none | deterministic fact-only answers | health always unavailable |
| **Hailo/Ollama** | hailo_ollama.py | local `http://127.0.0.1:8000` (`/hailo/v1/list`, `/api/chat`) | **on-device** | auto-selects a 1-2B model (`_model_rank`); streams; degrades cleanly |
| **OpenAI-compatible** | openai_compatible.py | user base URL (`/models`, `/chat/completions`) | **local if loopback URL, else remote (off-device)** | Bearer key; stream + non-stream fallback; rich connect-error diagnostics |

`ai_status` / `ai/grounding-status` report privacy mode (deterministic/local/remote) — remote only
when `openai_compatible` + non-loopback URL. `_is_local_url` checks localhost/127.0.0.1/::1.
Contracts: `AIRequest` (temperature 0.2, max_tokens 4000 to allow reasoning models), `AIChunk`,
`HealthStatus`, `GroundingFact` (`schemas/ai.py`).

### B.2 Grounded pipeline — `ai/grounding.py:answer_stream` (SSE)
1. `gather_facts(session, question)` → yield `{type:facts}` first (UI shows source/timestamp/stale).
2. Provider health + in-process rate limit (`_rate_limited`: `ai_max_requests_per_minute`, default
   20/min). If unavailable/limited → **deterministic template answer** from facts only.
3. If no facts → `REFUSAL_NO_FACTS`.
4. `classify_intent` → `build_messages(question, intent, facts)` → provider `chat`.
5. **Safe streaming**: model output is **buffered server-side, never streamed raw**. `strip_reasoning`
   removes `<think>` blocks. Empty → template fallback.
6. `validate_grounded_answer(answer, facts, question)` — on failure the model text is **discarded**
   and the deterministic template shown.
7. Only validated text is emitted (chunked by sentence). `done` includes provider/intent/model.

### B.3 Fact-pack construction — `ai/tools.py:gather_facts`
The **only** source of numbers the AI may reference (never computes, never calls providers direct).
Fact producers: `portfolio_facts`, `movers_facts`, `allocation_facts`, `watchlist_quote_facts`,
`market_facts`, `news_facts` (sanitised), `help_facts`, `data_quality_facts`, `networth_facts`,
`performance_facts` (from `key_stats`), `holdings_facts`, `instrument_deep_facts`
(price + 6-mo trend/range + your position + headlines).

Routing: `_resolve_symbols` maps names via `_ALIASES` + upper-case tickers (minus `_TICKER_STOP`).
Boolean keyword flags (`is_market/is_news/is_networth/is_perf/is_alloc/is_movers/is_holdings/is_watch`)
+ a `personal` regex decide which producers run. Pure instrument questions stay focused; data-quality
and help intents prepend the relevant facts. Falls back to portfolio+movers when empty. `_dedupe`
caps at 20.

### B.4 Intent classification — `ai/intent.py` (deterministic, first-match)
16 intents (`Intent` enum). Ordered regex rules (`_RULES`, :35): DAILY_BRIEFING, AI_NEWS_BRIEFING,
PRICING_HEALTH, DATA_QUALITY, NEWS, EXPLANATION_OF_METRIC, ALLOCATION, EXPOSURE, RISK_CONCENTRATION,
PERFORMANCE, MARKET_REGION, PORTFOLIO_MOVEMENT, SETTINGS_HELP, PORTFOLIO_OVERVIEW; bare
ticker + "how is…doing" → INSTRUMENT_QUESTION; else UNKNOWN_GENERAL_QUESTION. Shapes fact gathering
and answer focus (`prompt_builder._INTENT_FOCUS`).

### B.5 Prompt assembly — `ai/prompt_builder.py` + `ai/prompts.py`
Messages = `[system: SYSTEM_PROMPT, system: render_facts(facts), user: question + intent focus]`.
`SYSTEM_PROMPT` hard rules: use ONLY the FACTS, quote numbers exactly, **no invented
value/holding/quote/%/date/source**, no fresh arithmetic, **no buy/sell/hold advice**, note STALE
figures, end with "Information only, not financial advice." `render_facts` lists label:value +
source/as_of/entitlement/STALE metadata.

### B.6 Injection defenses — `ai/safety.py:sanitize_untrusted`
News/RSS/provider text is **untrusted**. Before entering a fact pack: strip HTML/script, replace
`_INJECTION` patterns ("ignore previous instructions", "reveal api key", "you are now", role
prefixes, jailbreak/DAN…) with `[filtered]`, cap 300 chars. Applied to every headline
(`news_facts`, `/news/grouped`).

### B.7 Answer validation — `ai/safety.py`
`validate_answer` (:62) hard fails: empty; secret-like (`sk-…`, `api_key=`, `LEDGERFRAME_*=`,
`bearer …`); buy/sell recommendation language (`_RECOMMENDATION`).
`validate_grounded_answer` (:112) adds, on top:
- blocks "real-time/live data" claims (`_REALTIME`) — data is delayed;
- every significant money/% number must trace to a fact by **first-3-significant-digits**
  (`_sig3`); years 1900-2100 exempted;
- every ticker-like token must appear in facts/question (minus `_TICKER_OK` allow-list);
- any quoted 25+ char string (headline) must appear verbatim in the facts.
Failure → deterministic fact-only answer. Same validation gates the **daily briefing**
(`services/briefing.py:166`) and News AI briefing.

### B.8 Briefing — `services/briefing.py`
`_deterministic_briefing`: value, today's change, total return, top movers, market line,
concentration (≥15%), data-quality notes. `generate_briefing` optionally lets the model **narrate
the same facts** (may add no numbers), validated by `validate_grounded_answer`; else the template.
Stored in `settings` (`daily_briefing`, `daily_briefing_ts`); Home lazily generates on first load,
worker refreshes daily.

### B.9 Key guarantees for rebuild
- AI never computes money; deterministic engine is the single source (see 04).
- Untrusted content sanitised in; model output validated out; unsafe/ungrounded text never shown.
- Off-device transmission only via `openai_compatible` + non-loopback URL, surfaced in UI.
- Every answer ends with the fixed disclaimer.

<!-- AUDIT COMPLETE -->
