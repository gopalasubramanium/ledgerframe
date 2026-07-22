# Alpha Vantage API — Clean Claude Code Reference

> **Purpose:** compact, implementation-focused reference for Claude Code and other coding agents.  
> **Verified against:** Alpha Vantage's live documentation and official MCP source.  
> **Last reviewed:** 2026-07-22  
> **Coverage:** **124 distinct functions** across all 9 documented API categories.  
> **Canonical request endpoint:** `https://www.alphavantage.co/query`

This file removes marketing text, repeated language-specific examples, screenshots, and narrative material. It retains every documented function, required and optional parameters, accepted values, defaults, output constraints, and free/premium distinctions needed for implementation.

## 1. Access and entitlement model

| Label | Meaning |
| --- | --- |
| **FREE** | The function is not marked premium in the current documentation. It is available under the standard free-key quota. |
| **PREMIUM** | The function is explicitly marked premium. |
| **FREE + PREMIUM ...** | A useful base mode is free, while greater history, scale, or fresher regulated market data requires premium. |

Current account-level rules:

- Standard free service covers the majority of datasets, with **up to 25 API requests per day**.
- Premium plans remove the daily limit and apply a plan-specific requests-per-minute rate.
- Realtime and 15-minute delayed US equity data may require the `entitlement` parameter and an eligible premium market-data entitlement.
- Access labels can change. When Alpha Vantage returns an entitlement message, treat the live response and current premium page as authoritative.
- Commercial redistribution or display may require separate licensing. Do not infer redistribution rights from API access alone.

## 2. Request contract

```text
GET https://www.alphavantage.co/query?function=FUNCTION_NAME&PARAMETER=value&apikey=${ALPHAVANTAGE_API_KEY}
```

Rules for generated code:

1. Read the API key from an environment variable such as `ALPHAVANTAGE_API_KEY`. Never hard-code or log it.
2. Use HTTPS and URL-encode all values. Preserve repeated query keys where the API requires them, notably two `RANGE` parameters for explicit analytics start/end dates.
3. API parameter names are normally lowercase. The analytics functions document `SYMBOLS`, `RANGE`, `OHLC`, `INTERVAL`, `WINDOW_SIZE`, and `CALCULATIONS` in uppercase; preserve those names.
4. Unless an endpoint states otherwise, `datatype=json` is the website API default. Use `datatype=csv` only for endpoints that document it.
5. A successful HTTP status does **not** guarantee a successful API call. Inspect JSON for `Error Message`, `Note`, and `Information`.
6. Implement rate limiting, bounded retries with jitter for transient failures, request timeouts, and response caching where data freshness permits.
7. Do not silently substitute a premium function with a different free dataset. Surface the entitlement limitation to the caller.
8. Symbols may be exchange-qualified, for example `IBM`, `TSCO.LON`, or `RELIANCE.BSE`. Use `SYMBOL_SEARCH` when the exact symbol is uncertain.

### Common response handling

```python
def validate_alpha_vantage_json(payload: dict) -> dict:
    for key in ("Error Message", "Note", "Information"):
        if key in payload:
            raise RuntimeError(f"Alpha Vantage: {payload[key]}")
    return payload
```

## 3. Complete function catalog


## Core Stock APIs

| Function | Access | Purpose | Required parameters | Optional parameters / defaults | Important notes |
| --- | --- | --- | --- | --- | --- |
| TIME_SERIES_INTRADAY | PREMIUM | Current and 20+ years of intraday equity OHLCV, including extended hours; raw or split/dividend-adjusted. | `symbol`, `interval` | `adjusted=true`; `extended_hours=true`; `month=YYYY-MM`; `outputsize=compact\|full` (default `compact`); `datatype=json\|csv` (default `json`); `entitlement=realtime\|delayed` | `interval`: `1min\|5min\|15min\|30min\|60min`. `compact` = latest 100 points. `full` = trailing 30 days, or the specified full month. |
| TIME_SERIES_DAILY | FREE + PREMIUM DEPTH | Raw daily equity OHLCV with 20+ years of history. | `symbol` | `outputsize=compact\|full` (default `compact`); `datatype=json\|csv` (default `json`) | `compact` (latest 100 points) is free. `full` (20+ years) requires premium. |
| TIME_SERIES_DAILY_ADJUSTED | PREMIUM | Daily raw OHLCV plus adjusted close, dividends, and splits. | `symbol` | `outputsize=compact\|full`; `datatype=json\|csv`; `entitlement=realtime\|delayed` | Covers 20+ years. Entire function is documented as premium. |
| TIME_SERIES_WEEKLY | FREE | Weekly raw OHLCV; latest point is the current partial week. | `symbol` | `datatype=json\|csv` | 20+ years of weekly history. |
| TIME_SERIES_WEEKLY_ADJUSTED | FREE | Weekly OHLCV plus adjusted close and dividend information. | `symbol` | `datatype=json\|csv` | 20+ years of weekly history. |
| TIME_SERIES_MONTHLY | FREE | Monthly raw OHLCV; latest point is the current partial month. | `symbol` | `datatype=json\|csv` | 20+ years of monthly history. |
| TIME_SERIES_MONTHLY_ADJUSTED | FREE | Monthly OHLCV plus adjusted close and dividend information. | `symbol` | `datatype=json\|csv` | 20+ years of monthly history. |
| GLOBAL_QUOTE | FREE EOD + PREMIUM FRESHNESS | Latest price, volume, and change data for one global ticker. | `symbol` | `datatype=json\|csv`; `entitlement=realtime\|delayed` | Without entitlement, updates at end of trading day. US realtime or 15-minute delayed quotes require premium. |
| REALTIME_BULK_QUOTES | PREMIUM | Realtime US quotes for up to 100 comma-separated symbols. | `symbol` | `datatype=json\|csv` | Requires a plan that includes Realtime US Market Data. |
| SYMBOL_SEARCH | FREE | Best-match global stocks, ETFs, and mutual funds for a search phrase. | `keywords` | `datatype=json\|csv` | Use before market-data calls when an exact exchange-qualified symbol is unknown. |
| MARKET_STATUS | FREE | Open/closed status of major equity, forex, and crypto venues worldwide. | None | None | JSON response. |

## Index Data APIs

| Function | Access | Purpose | Required parameters | Optional parameters / defaults | Important notes |
| --- | --- | --- | --- | --- | --- |
| INDEX_DATA | PREMIUM | Daily, weekly, or monthly OHLC history for 200+ major indices. | `symbol`, `interval` | `datatype=json\|csv` | `interval=daily\|weekly\|monthly`; examples: `DJI`, `SPX`, `COMP`, `NDX`, `VIX`, `RUT`. |
| INDEX_CATALOG | FREE | Full catalog of supported index symbols and long-form names. | None | `datatype=json\|csv` | Use this rather than hard-coding the supported index universe. |

## Options Data APIs

| Function | Access | Purpose | Required parameters | Optional parameters / defaults | Important notes |
| --- | --- | --- | --- | --- | --- |
| REALTIME_OPTIONS | PREMIUM — 600/1200 RPM PLAN | Realtime US option chain with optional Greeks and implied volatility. | `symbol` | `require_greeks=false`; `contract`; `expiration=YYYY-MM-DD`; `datatype=json\|csv` | All expirations returned unless filtered. Documentation requires the 600- or 1200-requests/minute premium plan. |
| REALTIME_PUT_CALL_RATIO | FREE | Realtime put-call ratio for the full chain and by expiration. | `symbol` | None | JSON response. |
| REALTIME_VOLUME_OPEN_INTEREST_RATIO | FREE | Realtime volume-to-open-interest ratio for an option chain. | `symbol` | None | JSON response. |
| HISTORICAL_OPTIONS | PREMIUM | Historical full option chain with IV and common Greeks from 2008 onward. | `symbol` | `date=YYYY-MM-DD`; `contract`; `expiration=YYYY-MM-DD`; `datatype=json\|csv` | If `date` is omitted, returns the previous trading session. |
| HISTORICAL_PUT_CALL_RATIO | FREE | Historical put-call ratio for the full chain and by expiration. | `symbol` | `date=YYYY-MM-DD` | If omitted, `date` defaults to the previous trading session; dates after 2008-01-01. |
| HISTORICAL_VOLUME_OPEN_INTEREST_RATIO | FREE | Historical volume-to-open-interest ratio. | `symbol` | `date=YYYY-MM-DD` | If omitted, `date` defaults to the previous trading session; dates after 2008-01-01. |

## Alpha Intelligence

| Function | Access | Purpose | Required parameters | Optional parameters / defaults | Important notes |
| --- | --- | --- | --- | --- | --- |
| NEWS_SENTIMENT | FREE | Live and historical market news with article-, ticker-, and topic-level sentiment. | None | `tickers`; `topics`; `time_from`; `time_to`; `sort=LATEST\|EARLIEST\|RELEVANCE`; `limit=50` (max 1000) | `time_from/time_to`: `YYYYMMDDTHHMM` UTC. Prefix crypto and FX filters as `CRYPTO:BTC` and `FOREX:USD`. |
| EARNINGS_CALL_TRANSCRIPT | FREE | Earnings-call transcript with LLM-derived sentiment signals. | `symbol`, `quarter` | None | `quarter=YYYYQn`; quarters from `2010Q1`. |
| TOP_GAINERS_LOSERS | FREE EOD + PREMIUM FRESHNESS | Top 20 US gainers, losers, and most-active tickers. | None | `entitlement=realtime\|delayed` | Without entitlement, updates at end of trading day. |
| INSIDER_TRANSACTIONS | FREE | Latest and historical transactions by company insiders. | `symbol` | `from=YYYY-MM-DD` | Filter returns transactions on or after the date. |
| INSTITUTIONAL_HOLDINGS | FREE | Institutional ownership and holdings for an equity. | `symbol` | None | JSON response. |
| ANALYTICS_FIXED_WINDOW | FREE + PREMIUM SCALE | Return, risk, drawdown, histogram, autocorrelation, covariance, and correlation metrics over a fixed range. | `SYMBOLS`, `RANGE`, `INTERVAL`, `CALCULATIONS` | `OHLC=close` | Free: up to 5 symbols/request. Premium: up to 50. |
| ANALYTICS_SLIDING_WINDOW | FREE + PREMIUM SCALE | Rolling analytics over a moving window. | `SYMBOLS`, `RANGE`, `INTERVAL`, `WINDOW_SIZE`, `CALCULATIONS` | `OHLC=close` | Free: up to 5 symbols and 1 metric/request. Premium: up to 50 symbols and multiple metrics. |

## Fundamental Data

| Function | Access | Purpose | Required parameters | Optional parameters / defaults | Important notes |
| --- | --- | --- | --- | --- | --- |
| OVERVIEW | FREE | Company profile, financial ratios, and key metrics. | `symbol` | None | JSON; generally refreshed when the company reports. |
| ETF_PROFILE | FREE | ETF metrics, allocations, and constituent holdings. | `symbol` | None | JSON. |
| DIVIDENDS | FREE | Historical and declared future dividend distributions. | `symbol` | `datatype=json\|csv` |  |
| SPLITS | FREE | Historical stock-split events. | `symbol` | `datatype=json\|csv` |  |
| INCOME_STATEMENT | FREE | Annual and quarterly normalized income statements. | `symbol` | None | JSON; GAAP/IFRS-normalized fields. |
| BALANCE_SHEET | FREE | Annual and quarterly normalized balance sheets. | `symbol` | None | JSON; GAAP/IFRS-normalized fields. |
| CASH_FLOW | FREE | Annual and quarterly normalized cash-flow statements. | `symbol` | None | JSON; GAAP/IFRS-normalized fields. |
| SHARES_OUTSTANDING | FREE | Quarterly basic and diluted shares outstanding. | `symbol` | `datatype=json\|csv` |  |
| EARNINGS | FREE | Annual and quarterly EPS history, estimates, and surprises. | `symbol` | None | JSON. |
| EARNINGS_ESTIMATES | FREE | Annual and quarterly EPS/revenue estimates, analyst counts, and revisions. | `symbol` | None | JSON. |
| LISTING_STATUS | FREE | Active or delisted US stocks and ETFs, including historical snapshots. | None | `date=YYYY-MM-DD`; `state=active\|delisted` (default `active`) | CSV. Historical dates later than 2010-01-01. |
| EARNINGS_CALENDAR | FREE | Expected earnings over the next 3, 6, or 12 months. | None | `symbol`; `horizon=3month\|6month\|12month` | CSV. |
| IPO_CALENDAR | FREE | Expected IPOs over the next three months. | None | None | CSV. |

## Forex

| Function | Access | Purpose | Required parameters | Optional parameters / defaults | Important notes |
| --- | --- | --- | --- | --- | --- |
| CURRENCY_EXCHANGE_RATE | FREE | Realtime exchange rate between any physical or digital currencies. | `from_currency`, `to_currency` | `datatype=json\|csv` | Shared by the FX and cryptocurrency documentation sections. |
| FX_INTRADAY | PREMIUM | Realtime intraday OHLC for a physical-currency pair. | `from_symbol`, `to_symbol`, `interval` | `outputsize=compact\|full`; `datatype=json\|csv` | `interval=1min\|5min\|15min\|30min\|60min`. |
| FX_DAILY | FREE | Daily OHLC for a physical-currency pair. | `from_symbol`, `to_symbol` | `outputsize=compact\|full`; `datatype=json\|csv` | `compact` = latest 100 points; `full` = full history. |
| FX_WEEKLY | FREE | Weekly OHLC for a physical-currency pair. | `from_symbol`, `to_symbol` | `datatype=json\|csv` |  |
| FX_MONTHLY | FREE | Monthly OHLC for a physical-currency pair. | `from_symbol`, `to_symbol` | `datatype=json\|csv` |  |

## Cryptocurrencies

| Function | Access | Purpose | Required parameters | Optional parameters / defaults | Important notes |
| --- | --- | --- | --- | --- | --- |
| CRYPTO_INTRADAY | PREMIUM | Realtime intraday OHLCV for a digital currency in a market currency. | `symbol`, `market`, `interval` | `outputsize=compact\|full`; `datatype=json\|csv` | `interval=1min\|5min\|15min\|30min\|60min`. |
| DIGITAL_CURRENCY_DAILY | FREE | Daily crypto history, quoted in the market currency and USD. | `symbol`, `market` | `datatype=json\|csv` | Refreshed daily at midnight UTC. |
| DIGITAL_CURRENCY_WEEKLY | FREE | Weekly crypto history, quoted in the market currency and USD. | `symbol`, `market` | `datatype=json\|csv` | Refreshed daily at midnight UTC. |
| DIGITAL_CURRENCY_MONTHLY | FREE | Monthly crypto history, quoted in the market currency and USD. | `symbol`, `market` | `datatype=json\|csv` | Refreshed daily at midnight UTC. |

## Commodities

| Function | Access | Purpose | Required parameters | Optional parameters / defaults | Important notes |
| --- | --- | --- | --- | --- | --- |
| GOLD_SILVER_SPOT | FREE | Live spot price of gold or silver. | `symbol` | None | `symbol=GOLD\|XAU\|SILVER\|XAG`. |
| GOLD_SILVER_HISTORY | FREE | Historical gold or silver close prices. | `symbol`, `interval` | `datatype=json\|csv` | `interval=daily\|weekly\|monthly`. |
| WTI | FREE | West Texas Intermediate crude-oil prices. | None | `interval=monthly`; `datatype=json\|csv` | `interval=daily\|weekly\|monthly`. |
| BRENT | FREE | Brent crude-oil prices. | None | `interval=monthly`; `datatype=json\|csv` | `interval=daily\|weekly\|monthly`. |
| NATURAL_GAS | FREE | Henry Hub natural-gas spot prices. | None | `interval=monthly`; `datatype=json\|csv` | `interval=daily\|weekly\|monthly`. |
| COPPER | FREE | Global copper prices. | None | `interval=monthly`; `datatype=json\|csv` | `interval=monthly\|quarterly\|annual`. |
| ALUMINUM | FREE | Global aluminum prices. | None | `interval=monthly`; `datatype=json\|csv` | `interval=monthly\|quarterly\|annual`. |
| WHEAT | FREE | Global wheat prices. | None | `interval=monthly`; `datatype=json\|csv` | `interval=monthly\|quarterly\|annual`. |
| CORN | FREE | Global corn prices. | None | `interval=monthly`; `datatype=json\|csv` | `interval=monthly\|quarterly\|annual`. |
| COTTON | FREE | Global cotton prices. | None | `interval=monthly`; `datatype=json\|csv` | `interval=monthly\|quarterly\|annual`. |
| SUGAR | FREE | Global sugar prices. | None | `interval=monthly`; `datatype=json\|csv` | `interval=monthly\|quarterly\|annual`. |
| COFFEE | FREE | Global coffee prices. | None | `interval=monthly`; `datatype=json\|csv` | `interval=monthly\|quarterly\|annual`. |
| ALL_COMMODITIES | FREE | Global all-commodities price index. | None | `interval=monthly`; `datatype=json\|csv` | `interval=monthly\|quarterly\|annual`. |

## Economic Indicators

| Function | Access | Purpose | Required parameters | Optional parameters / defaults | Important notes |
| --- | --- | --- | --- | --- | --- |
| REAL_GDP | FREE | US real GDP. | None | `interval=annual\|quarterly`; `datatype=json\|csv` | Default `annual`. |
| REAL_GDP_PER_CAPITA | FREE | Quarterly US real GDP per capita. | None | `datatype=json\|csv` |  |
| TREASURY_YIELD | FREE | US Treasury yield for a selected maturity. | None | `interval=daily\|weekly\|monthly`; `maturity=3month\|2year\|5year\|7year\|10year\|30year`; `datatype=json\|csv` | Defaults: `monthly`, `10year`. |
| FEDERAL_FUNDS_RATE | FREE | US federal-funds rate. | None | `interval=daily\|weekly\|monthly`; `datatype=json\|csv` | Default `monthly`. |
| CPI | FREE | US consumer price index. | None | `interval=monthly\|semiannual`; `datatype=json\|csv` | Default `monthly`. |
| INFLATION | FREE | Annual US consumer-price inflation. | None | `datatype=json\|csv` |  |
| RETAIL_SALES | FREE | Monthly US advance retail sales. | None | `datatype=json\|csv` |  |
| DURABLES | FREE | Monthly US manufacturers' new durable-goods orders. | None | `datatype=json\|csv` |  |
| UNEMPLOYMENT | FREE | Monthly US unemployment rate. | None | `datatype=json\|csv` |  |
| NONFARM_PAYROLL | FREE | Monthly US total nonfarm payroll. | None | `datatype=json\|csv` |  |

## Technical Indicators

### Shared technical-indicator parameters

These rules apply unless a row below overrides them:

- `symbol` — equity symbol, or an FX/crypto pair format supported by the endpoint.
- `interval` — `1min`, `5min`, `15min`, `30min`, `60min`, `daily`, `weekly`, or `monthly`.
- `series_type` — `close`, `open`, `high`, or `low`.
- `time_period` — positive integer.
- `month=YYYY-MM` — optional historical-month selection, particularly for intraday calculations; current documentation supports historical months from 2000-01.
- `datatype=json|csv` — optional; website default is `json`.
- `entitlement=realtime|delayed` — optional where documented. Omit it for the default historical/end-of-day mode. Realtime and 15-minute delayed US data require an eligible premium entitlement.
- `apikey` — always required.
- Moving-average type (`matype` and related fields): `0=SMA`, `1=EMA`, `2=WMA`, `3=DEMA`, `4=TEMA`, `5=TRIMA`, `6=T3`, `7=KAMA`, `8=MAMA`.


| Function | Access | Output | Required parameters | Function-specific optional parameters / constraints |
| --- | --- | --- | --- | --- |
| SMA | FREE HISTORICAL + PREMIUM FRESHNESS | Simple moving average | `symbol`, `interval`, `time_period`, `series_type` |  |
| EMA | FREE HISTORICAL + PREMIUM FRESHNESS | Exponential moving average | `symbol`, `interval`, `time_period`, `series_type` |  |
| WMA | FREE HISTORICAL + PREMIUM FRESHNESS | Weighted moving average | `symbol`, `interval`, `time_period`, `series_type` |  |
| DEMA | FREE HISTORICAL + PREMIUM FRESHNESS | Double exponential moving average | `symbol`, `interval`, `time_period`, `series_type` |  |
| TEMA | FREE HISTORICAL + PREMIUM FRESHNESS | Triple exponential moving average | `symbol`, `interval`, `time_period`, `series_type` |  |
| TRIMA | FREE HISTORICAL + PREMIUM FRESHNESS | Triangular moving average | `symbol`, `interval`, `time_period`, `series_type` |  |
| KAMA | FREE HISTORICAL + PREMIUM FRESHNESS | Kaufman adaptive moving average | `symbol`, `interval`, `time_period`, `series_type` |  |
| MAMA | FREE HISTORICAL + PREMIUM FRESHNESS | MESA adaptive moving average | `symbol`, `interval`, `series_type` | `fastlimit=0.01`; `slowlimit=0.01` |
| VWAP | PREMIUM | Volume-weighted average price | `symbol`, `interval` | Intraday intervals only |
| T3 | FREE HISTORICAL + PREMIUM FRESHNESS | Triple exponential T3 moving average | `symbol`, `interval`, `time_period`, `series_type` |  |
| MACD | PREMIUM | Moving average convergence/divergence | `symbol`, `interval`, `series_type` | `fastperiod=12`; `slowperiod=26`; `signalperiod=9` |
| MACDEXT | FREE HISTORICAL + PREMIUM FRESHNESS | MACD with configurable moving-average types | `symbol`, `interval`, `series_type` | `fastperiod=12`; `slowperiod=26`; `signalperiod=9`; `fastmatype=0`; `slowmatype=0`; `signalmatype=0` |
| STOCH | FREE HISTORICAL + PREMIUM FRESHNESS | Stochastic oscillator | `symbol`, `interval` | `fastkperiod=5`; `slowkperiod=3`; `slowdperiod=3`; `slowkmatype=0`; `slowdmatype=0` |
| STOCHF | FREE HISTORICAL + PREMIUM FRESHNESS | Fast stochastic oscillator | `symbol`, `interval` | `fastkperiod=5`; `fastdperiod=3`; `fastdmatype=0` |
| RSI | FREE HISTORICAL + PREMIUM FRESHNESS | Relative strength index | `symbol`, `interval`, `time_period`, `series_type` |  |
| STOCHRSI | FREE HISTORICAL + PREMIUM FRESHNESS | Stochastic RSI | `symbol`, `interval`, `time_period`, `series_type` | `fastkperiod=5`; `fastdperiod=3`; `fastdmatype=0` |
| WILLR | FREE HISTORICAL + PREMIUM FRESHNESS | Williams %R | `symbol`, `interval`, `time_period` |  |
| ADX | FREE HISTORICAL + PREMIUM FRESHNESS | Average directional movement index | `symbol`, `interval`, `time_period` |  |
| ADXR | FREE HISTORICAL + PREMIUM FRESHNESS | Average directional movement index rating | `symbol`, `interval`, `time_period` |  |
| APO | FREE HISTORICAL + PREMIUM FRESHNESS | Absolute price oscillator | `symbol`, `interval`, `series_type` | `fastperiod=12`; `slowperiod=26`; `matype=0` |
| PPO | FREE HISTORICAL + PREMIUM FRESHNESS | Percentage price oscillator | `symbol`, `interval`, `series_type` | `fastperiod=12`; `slowperiod=26`; `matype=0` |
| MOM | FREE HISTORICAL + PREMIUM FRESHNESS | Momentum | `symbol`, `interval`, `time_period`, `series_type` |  |
| BOP | FREE HISTORICAL + PREMIUM FRESHNESS | Balance of power | `symbol`, `interval` |  |
| CCI | FREE HISTORICAL + PREMIUM FRESHNESS | Commodity channel index | `symbol`, `interval`, `time_period` |  |
| CMO | FREE HISTORICAL + PREMIUM FRESHNESS | Chande momentum oscillator | `symbol`, `interval`, `time_period`, `series_type` |  |
| ROC | FREE HISTORICAL + PREMIUM FRESHNESS | Rate of change | `symbol`, `interval`, `time_period`, `series_type` |  |
| ROCR | FREE HISTORICAL + PREMIUM FRESHNESS | Rate-of-change ratio | `symbol`, `interval`, `time_period`, `series_type` |  |
| AROON | FREE HISTORICAL + PREMIUM FRESHNESS | Aroon up/down | `symbol`, `interval`, `time_period` |  |
| AROONOSC | FREE HISTORICAL + PREMIUM FRESHNESS | Aroon oscillator | `symbol`, `interval`, `time_period` |  |
| MFI | FREE HISTORICAL + PREMIUM FRESHNESS | Money flow index | `symbol`, `interval`, `time_period` |  |
| TRIX | FREE HISTORICAL + PREMIUM FRESHNESS | One-period ROC of a triple-smoothed EMA | `symbol`, `interval`, `time_period`, `series_type` |  |
| ULTOSC | FREE HISTORICAL + PREMIUM FRESHNESS | Ultimate oscillator | `symbol`, `interval` | `timeperiod1=7`; `timeperiod2=14`; `timeperiod3=28` |
| DX | FREE HISTORICAL + PREMIUM FRESHNESS | Directional movement index | `symbol`, `interval`, `time_period` |  |
| MINUS_DI | FREE HISTORICAL + PREMIUM FRESHNESS | Minus directional indicator | `symbol`, `interval`, `time_period` |  |
| PLUS_DI | FREE HISTORICAL + PREMIUM FRESHNESS | Plus directional indicator | `symbol`, `interval`, `time_period` |  |
| MINUS_DM | FREE HISTORICAL + PREMIUM FRESHNESS | Minus directional movement | `symbol`, `interval`, `time_period` |  |
| PLUS_DM | FREE HISTORICAL + PREMIUM FRESHNESS | Plus directional movement | `symbol`, `interval`, `time_period` |  |
| BBANDS | FREE HISTORICAL + PREMIUM FRESHNESS | Bollinger bands | `symbol`, `interval`, `time_period`, `series_type` | `nbdevup=2`; `nbdevdn=2`; `matype=0` |
| MIDPOINT | FREE HISTORICAL + PREMIUM FRESHNESS | Midpoint over a period | `symbol`, `interval`, `time_period`, `series_type` |  |
| MIDPRICE | FREE HISTORICAL + PREMIUM FRESHNESS | Midpoint price using highs/lows | `symbol`, `interval`, `time_period` |  |
| SAR | FREE HISTORICAL + PREMIUM FRESHNESS | Parabolic SAR | `symbol`, `interval` | `acceleration=0.01`; `maximum=0.20` |
| TRANGE | FREE HISTORICAL + PREMIUM FRESHNESS | True range | `symbol`, `interval` |  |
| ATR | FREE HISTORICAL + PREMIUM FRESHNESS | Average true range | `symbol`, `interval`, `time_period` |  |
| NATR | FREE HISTORICAL + PREMIUM FRESHNESS | Normalized average true range | `symbol`, `interval`, `time_period` |  |
| AD | FREE HISTORICAL + PREMIUM FRESHNESS | Chaikin accumulation/distribution line | `symbol`, `interval` |  |
| ADOSC | FREE HISTORICAL + PREMIUM FRESHNESS | Chaikin A/D oscillator | `symbol`, `interval` | `fastperiod=3`; `slowperiod=10` |
| OBV | FREE HISTORICAL + PREMIUM FRESHNESS | On-balance volume | `symbol`, `interval` |  |
| HT_TRENDLINE | FREE HISTORICAL + PREMIUM FRESHNESS | Hilbert transform instantaneous trendline | `symbol`, `interval`, `series_type` |  |
| HT_SINE | FREE HISTORICAL + PREMIUM FRESHNESS | Hilbert transform sine wave | `symbol`, `interval`, `series_type` |  |
| HT_TRENDMODE | FREE HISTORICAL + PREMIUM FRESHNESS | Hilbert transform trend-versus-cycle mode | `symbol`, `interval`, `series_type` |  |
| HT_DCPERIOD | FREE HISTORICAL + PREMIUM FRESHNESS | Hilbert transform dominant-cycle period | `symbol`, `interval`, `series_type` |  |
| HT_DCPHASE | FREE HISTORICAL + PREMIUM FRESHNESS | Hilbert transform dominant-cycle phase | `symbol`, `interval`, `series_type` |  |
| HT_PHASOR | FREE HISTORICAL + PREMIUM FRESHNESS | Hilbert transform phasor components | `symbol`, `interval`, `series_type` |  |

## 4. Alpha Intelligence parameter dictionaries

### `NEWS_SENTIMENT.topics`

Accepted topic values:

`blockchain`, `earnings`, `ipo`, `mergers_and_acquisitions`, `financial_markets`, `economy_fiscal`, `economy_monetary`, `economy_macro`, `energy_transportation`, `finance`, `life_sciences`, `manufacturing`, `real_estate`, `retail_wholesale`, `technology`

Multiple topics are comma-separated.

### Analytics `RANGE`

Accepted forms:

- `full`
- `{N}day`, `{N}week`, `{N}month`, `{N}year`
- Intraday only: `{N}minute`, `{N}hour`
- One month: `YYYY-MM`
- One day: `YYYY-MM-DD`
- Explicit start/end: repeat `RANGE`, for example `RANGE=2023-07-01&RANGE=2023-08-31`
- Intraday timestamps may include minute precision, for example `YYYY-MM-DDTHH:MM:SS`

### `ANALYTICS_FIXED_WINDOW.CALCULATIONS`

- `MIN`
- `MAX`
- `MEAN`
- `MEDIAN`
- `CUMULATIVE_RETURN`
- `VARIANCE` or `VARIANCE(annualized=True)`
- `STDDEV` or `STDDEV(annualized=True)`
- `MAX_DRAWDOWN`
- `HISTOGRAM` or `HISTOGRAM(bins=N)`; default bins = 10
- `AUTOCORRELATION` or `AUTOCORRELATION(lag=N)`; default lag = 1
- `COVARIANCE` or `COVARIANCE(annualized=True)`
- `CORRELATION`, `CORRELATION(method=KENDALL)`, or `CORRELATION(method=SPEARMAN)`; default method = PEARSON

### `ANALYTICS_SLIDING_WINDOW.CALCULATIONS`

- `MEAN`
- `MEDIAN`
- `CUMULATIVE_RETURN`
- `VARIANCE` or `VARIANCE(annualized=True)`
- `STDDEV` or `STDDEV(annualized=True)`
- `COVARIANCE` or `COVARIANCE(annualized=True)`
- `CORRELATION`, `CORRELATION(method=KENDALL)`, or `CORRELATION(method=SPEARMAN)`

`WINDOW_SIZE` is an integer with a hard minimum of 10.

## 5. Output and data-format notes

- JSON is the default for most endpoints.
- CSV is supported only when `datatype` is documented. Do not append `datatype=csv` blindly.
- `LISTING_STATUS`, `EARNINGS_CALENDAR`, and `IPO_CALENDAR` are CSV-oriented utility feeds.
- Options ratio functions are JSON-only in the current documentation.
- Financial-statement endpoints return normalized annual and quarterly records.
- Digital-currency daily/weekly/monthly responses quote values in both the selected market currency and USD.
- Latest weekly/monthly time-series points may represent the current partial week/month.
- Realtime options and realtime/delayed US equity data are regulated datasets and have stricter entitlement requirements.

## 6. Recommended Claude Code implementation policy

When asked to implement an Alpha Vantage feature:

1. Select the exact function from the catalog.
2. Check its access label before coding.
3. Validate required parameters and enumerated values locally.
4. Omit optional parameters rather than sending empty strings.
5. Set `datatype=json` explicitly when structured parsing is needed.
6. Add `entitlement` only when the user has confirmed an eligible premium entitlement.
7. Centralize HTTP transport, authentication, throttling, caching, and Alpha Vantage error-envelope handling.
8. Use typed endpoint wrappers rather than allowing arbitrary unvalidated query parameters.
9. Record source timestamps and the requested freshness in stored data.
10. Add integration tests using mocked responses; do not consume the daily quota in ordinary unit tests.

### Suggested environment and base client

```bash
export ALPHAVANTAGE_API_KEY="replace-me"
```

```python
from __future__ import annotations

import os
from typing import Any
import requests

BASE_URL = "https://www.alphavantage.co/query"

class AlphaVantageError(RuntimeError):
    pass

def alpha_vantage_get(
    function: str,
    *,
    timeout: float = 20.0,
    **params: Any,
) -> dict[str, Any]:
    api_key = os.environ.get("ALPHAVANTAGE_API_KEY")
    if not api_key:
        raise AlphaVantageError("ALPHAVANTAGE_API_KEY is not set")

    query = {
        "function": function,
        "apikey": api_key,
        **{k: v for k, v in params.items() if v is not None},
    }

    response = requests.get(BASE_URL, params=query, timeout=timeout)
    response.raise_for_status()

    content_type = response.headers.get("content-type", "")
    if "json" not in content_type.lower():
        raise AlphaVantageError(
            "Expected JSON. Set datatype=json or handle CSV separately."
        )

    payload = response.json()
    for key in ("Error Message", "Note", "Information"):
        if key in payload:
            raise AlphaVantageError(str(payload[key]))
    return payload
```

## 7. Deliberately excluded noise

The following material was removed because it is not needed as code reference:

- repeated Python, Node.js, PHP, and C# examples;
- demo-key URLs;
- marketing copy and product promotions;
- screenshots, videos, spreadsheet guidance, and community-library listings;
- repeated definitions already captured once under common parameters.

No documented API function was removed.

## 8. Sources and maintenance

Primary sources:

- API documentation: https://www.alphavantage.co/documentation/
- Free-key support and quota: https://www.alphavantage.co/support/
- Premium access: https://www.alphavantage.co/premium/
- Official Alpha Vantage MCP implementation: https://github.com/alphavantage/alpha_vantage_mcp

### Scope boundary

The official MCP source currently exposes `REALTIME_OPTIONS_FMV`, but the requested live website documentation does not list or define that function as of 2026-07-22. It is therefore **not included in the 124 website-documented function count**. Add it only after its public API contract and entitlement requirements appear in the website documentation.

Maintenance rule: re-check the table of contents, premium labels, entitlement text, rate limits, and official MCP signatures before major releases or at least quarterly.
