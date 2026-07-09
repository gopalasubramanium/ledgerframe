# SPDX-License-Identifier: AGPL-3.0-or-later
"""EODHD global-market adapter (opt-in, keyed).

A broad market-data provider (US / SG / India / global equities & ETFs, FX, crypto,
indices) implementing the ``MarketDataProvider`` protocol — selectable like Alpha
Vantage. Uses EODHD's official endpoints only; the key is read from configuration and
never logged/stored in the DB. On any failure it degrades to cached/mock data so the
dashboard never breaks. The pure helpers (symbol mapping + parsers) are fixture-tested;
the network methods are never called in test runs.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

import httpx

from app.core.money import D, price
from app.core.symbols import currency_for_symbol
from app.providers.market.mock import MockMarketDataProvider
from app.schemas.common import (
    Candle,
    EntitlementStatus,
    FxRate,
    Instrument,
    MarketStatus,
    NewsItem,
    Quote,
)

log = logging.getLogger(__name__)
_BASE = "https://eodhd.com/api"

# Map our venue suffixes / exchange names → EODHD exchange codes. Unknown suffixes are
# passed through (EODHD-native like ".US"/".SG" already work), so search results that
# come back as CODE.EXCHANGE round-trip cleanly.
_SUFFIX_MAP = {
    "NSE": "NSE", "BSE": "BSE", "SI": "SG", "SGX": "SG", "SG": "SG",
    "L": "LSE", "LSE": "LSE", "T": "TSE", "TSE": "TSE", "HK": "HK",
    "TO": "TO", "AX": "AU", "DE": "XETRA", "PA": "PA", "SW": "SW",
    "US": "US", "NASDAQ": "US", "NYSE": "US", "AMEX": "US",
}
_CRYPTO = {"BTC", "ETH", "SOL", "XRP", "ADA", "DOGE", "DOT", "LTC", "BCH", "LINK", "AVAX", "MATIC"}
_NA = {None, "", "NA", "N/A", "null"}


def to_eodhd_symbol(symbol: str, exchange: str | None = None) -> str:
    """Map a LedgerFrame symbol (+optional exchange) to an EODHD ``CODE.EXCHANGE``."""
    s = symbol.upper().strip()
    if s.startswith("^"):
        return f"{s[1:]}.INDX"                       # index
    if "." in s:
        base, suf = s.rsplit(".", 1)
        return f"{base}.{_SUFFIX_MAP.get(suf, suf)}"  # pass unknown suffixes through
    if s in _CRYPTO:
        return f"{s}-USD.CC"
    if exchange:
        code = _SUFFIX_MAP.get(exchange.upper(), "US")
        return f"{s}.{code}"
    return f"{s}.US"                                   # bare ticker = US


def _num(v):
    return None if (isinstance(v, str) and v.strip() in _NA) or v is None else v


def realtime_to_quote(data: dict, symbol: str, exchange: str | None, source: str = "eodhd") -> Quote:
    now = datetime.now(UTC)
    ccy = currency_for_symbol(symbol, exchange) or "USD"
    close = _num(data.get("close"))
    if close is None:
        return Quote(symbol=symbol.upper(), exchange=exchange, price=None, currency=ccy,
                     source=source, entitlement=EntitlementStatus.UNAVAILABLE,
                     received_at=now, is_stale=True)
    prev = _num(data.get("previousClose"))
    px, pclose = price(close), (price(prev) if prev is not None else None)
    ts = data.get("timestamp")
    return Quote(
        symbol=symbol.upper(), exchange=exchange, price=px, previous_close=pclose,
        change=price(px - pclose) if pclose is not None else None,
        change_pct=D(round((px - pclose) / pclose * 100, 4)) if pclose else None,
        currency=ccy, source=source, entitlement=EntitlementStatus.DELAYED,
        market_time=datetime.fromtimestamp(ts, UTC) if isinstance(ts, (int, float)) else now,
        received_at=now,
    )


def parse_eod(data: list) -> list[Candle]:
    out: list[Candle] = []
    for row in data or []:
        try:
            out.append(Candle(
                ts=datetime.fromisoformat(str(row["date"])).replace(tzinfo=UTC),
                open=price(row["open"]), high=price(row["high"]), low=price(row["low"]),
                close=price(row["close"]),
                volume=D(row["volume"]) if row.get("volume") is not None else None,
            ))
        except (KeyError, ValueError, TypeError):
            continue
    return out


def parse_search(data: list) -> list[Instrument]:
    _TYPE = {"common stock": "equity", "etf": "etf", "fund": "mutual_fund",
             "mutual fund": "mutual_fund", "index": "index", "currency": "fx"}
    out: list[Instrument] = []
    for row in data or []:
        code = str(row.get("Code", "")).strip()
        if not code:
            continue
        ex = str(row.get("Exchange", "")).strip().upper()
        sym = code if ex in {"US", "NASDAQ", "NYSE", ""} else f"{code}.{ex}"
        out.append(Instrument(
            symbol=sym, exchange=ex or None, name=str(row.get("Name", "")).strip(),
            asset_class=_TYPE.get(str(row.get("Type", "")).strip().lower(), "equity"),
            currency=str(row.get("Currency", "USD")).strip() or "USD",
            country=str(row.get("Country", "")).strip() or None,
        ))
    return out


class EodhdProvider:
    fetch_on_demand = False  # rate-limited: serve cache, refresh via worker/button

    def __init__(self, name: str, api_key: str):
        if not api_key:
            raise ValueError("eodhd provider requires an API key")
        self.name = name
        self._key = api_key
        self._mock = MockMarketDataProvider()
        self._sem = asyncio.Semaphore(2)

    async def _get(self, path: str, params: dict) -> object:
        params = {**params, "api_token": self._key, "fmt": "json"}
        async with self._sem, httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            for attempt in range(2):  # one retry with backoff
                try:
                    r = await client.get(f"{_BASE}/{path}", params=params)
                    r.raise_for_status()
                    return r.json()
                except httpx.HTTPError:
                    if attempt == 0:
                        await asyncio.sleep(0.6)
                    else:
                        raise
        return None

    async def get_quote(self, symbol: str, exchange: str | None = None) -> Quote:
        try:
            data = await self._get(f"real-time/{to_eodhd_symbol(symbol, exchange)}", {})
            if isinstance(data, dict):
                return realtime_to_quote(data, symbol, exchange, self.name)
        except Exception as exc:  # noqa: BLE001 — never fabricate; return unavailable
            log.warning("eodhd quote unavailable for %s: %s", symbol, exc)
        now = datetime.now(UTC)
        return Quote(symbol=symbol.upper(), exchange=exchange, price=None,
                     currency=currency_for_symbol(symbol, exchange) or "USD", source=self.name,
                     entitlement=EntitlementStatus.UNAVAILABLE, received_at=now, is_stale=True)

    async def get_history(self, instrument_id: str, interval: str, start: datetime, end: datetime) -> list[Candle]:
        try:
            data = await self._get(f"eod/{to_eodhd_symbol(instrument_id)}", {
                "from": start.date().isoformat(), "to": end.date().isoformat(), "period": "d",
            })
            if isinstance(data, list):
                return parse_eod(data)
        except Exception as exc:  # noqa: BLE001
            log.warning("eodhd history unavailable for %s: %s", instrument_id, exc)
        return []

    async def search_instruments(self, query: str) -> list[Instrument]:
        try:
            data = await self._get(f"search/{query}", {"limit": 12})
            if isinstance(data, list):
                return parse_search(data)
        except Exception as exc:  # noqa: BLE001
            log.info("eodhd search fell back to mock: %s", exc)
        return await self._mock.search_instruments(query)

    async def get_fx_rate(self, base: str, quote: str) -> FxRate:
        base, quote = base.upper(), quote.upper()
        now = datetime.now(UTC)
        try:
            data = await self._get(f"real-time/{base}{quote}.FOREX", {})
            rate = _num(data.get("close")) if isinstance(data, dict) else None
            if rate is not None:
                return FxRate(base=base, quote=quote, rate=D(rate), source=self.name, received_at=now)
        except Exception as exc:  # noqa: BLE001
            log.info("eodhd FX fell back to mock for %s/%s: %s", base, quote, exc)
        return await self._mock.get_fx_rate(base, quote)

    async def get_market_status(self, market: str) -> MarketStatus:
        return await self._mock.get_market_status(market)

    async def get_news(self, instruments: list[str]) -> list[NewsItem]:
        return []
