# SPDX-License-Identifier: AGPL-3.0-or-later
"""Zerodha Kite market-data adapter (opt-in, READ-ONLY).

This adapter is for **market data + instrument metadata only**. It NEVER places
orders, GTT, or syncs holdings/positions/funds — those endpoints are not reachable
from here (a strict allow-list refuses anything that isn't a read-only quote /
instruments endpoint). Credentials come from configuration (env), never the DB, and
are never logged. On an expired/invalid session it raises a clear
:class:`KiteSessionExpired` so the UI can say "Kite session expired" rather than a
generic price error. Interactive login / OTP / 2FA is never automated.
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from app.core.money import D, price
from app.core.symbols import currency_for_symbol
from app.providers.market.mock import MockMarketDataProvider
from app.schemas.common import Candle, EntitlementStatus, FxRate, Instrument, MarketStatus, NewsItem, Quote

log = logging.getLogger(__name__)
_BASE = "https://api.kite.trade"

# The ONLY endpoint prefixes this adapter may ever call — all read-only market data.
# Anything else (orders, gtt, portfolio, funds, user, …) is refused outright.
_ALLOWED_PREFIXES = ("quote", "quote/ltp", "quote/ohlc", "instruments")

# Venue suffix → Kite exchange segment.
_EXCHANGE_MAP = {"NSE": "NSE", "BSE": "BSE", "NFO": "NFO", "MCX": "MCX", "CDS": "CDS", "BFO": "BFO"}


class KiteSessionExpired(Exception):
    """Kite access token is missing/expired — the user must re-generate it."""


@dataclass(frozen=True)
class KiteInstrument:
    instrument_token: int
    exchange: str
    tradingsymbol: str
    name: str
    segment: str
    instrument_type: str          # EQ | FUT | CE | PE
    lot_size: int
    expiry: str | None            # ISO date for derivatives
    strike: float | None


def _is_allowed(path: str) -> bool:
    p = path.lstrip("/")
    return any(p == pre or p.startswith(pre + "/") or p.startswith(pre + "?") for pre in _ALLOWED_PREFIXES)


def to_kite_symbol(symbol: str, exchange: str | None = None) -> str:
    """Map a LedgerFrame symbol to Kite's ``EXCHANGE:TRADINGSYMBOL``."""
    s = symbol.upper().strip()
    if ":" in s:
        return s                                   # already EXCHANGE:SYMBOL
    if "." in s:
        base, suf = s.rsplit(".", 1)
        return f"{_EXCHANGE_MAP.get(suf, 'NSE')}:{base}"
    ex = _EXCHANGE_MAP.get((exchange or "").upper(), "NSE")
    return f"{ex}:{s}"


def parse_instruments_csv(text: str) -> list[KiteInstrument]:
    """Parse the Kite instruments master CSV (equities + F&O + commodities)."""
    out: list[KiteInstrument] = []
    for row in csv.DictReader(io.StringIO(text)):
        try:
            token = int(row["instrument_token"])
        except (KeyError, ValueError, TypeError):
            continue
        strike = None
        try:
            sv = float(row.get("strike") or 0)
            strike = sv if sv else None
        except (ValueError, TypeError):
            strike = None
        out.append(KiteInstrument(
            instrument_token=token,
            exchange=(row.get("exchange") or "").strip().upper(),
            tradingsymbol=(row.get("tradingsymbol") or "").strip().upper(),
            name=(row.get("name") or "").strip(),
            segment=(row.get("segment") or "").strip(),
            instrument_type=(row.get("instrument_type") or "").strip().upper(),
            lot_size=int(float(row.get("lot_size") or 1)),
            expiry=(row.get("expiry") or "").strip() or None,
            strike=strike,
        ))
    return out


def parse_quote(data: dict, symbol: str, exchange: str | None, source: str = "kite") -> Quote:
    """Parse one entry from Kite's /quote ``data`` map into a Quote."""
    now = datetime.now(UTC)
    ccy = currency_for_symbol(symbol, exchange) or "INR"
    ltp = data.get("last_price")
    if ltp in (None, 0, "0"):
        return Quote(symbol=symbol.upper(), exchange=exchange, price=None, currency=ccy,
                     source=source, entitlement=EntitlementStatus.UNAVAILABLE, received_at=now, is_stale=True)
    ohlc = data.get("ohlc") or {}
    prev = ohlc.get("close")
    px, pclose = price(ltp), (price(prev) if prev else None)
    return Quote(
        symbol=symbol.upper(), exchange=exchange, price=px, previous_close=pclose,
        change=price(px - pclose) if pclose else None,
        change_pct=D(round((px - pclose) / pclose * 100, 4)) if pclose else None,
        currency=ccy, source=source, entitlement=EntitlementStatus.DELAYED,
        market_time=now, received_at=now,
    )


class KiteProvider:
    fetch_on_demand = False

    def __init__(self, api_key: str, access_token: str):
        if not api_key or not access_token:
            raise ValueError("kite provider requires an API key and access token")
        self.name = "kite"
        self._api_key = api_key
        self._access_token = access_token
        self._mock = MockMarketDataProvider()

    def _headers(self) -> dict:
        # Kite auth: read-only market data only. Token is never logged.
        return {"Authorization": f"token {self._api_key}:{self._access_token}", "X-Kite-Version": "3"}

    async def _get(self, path: str, params: dict | None = None):
        if not _is_allowed(path):
            # Hard guard: this adapter must never reach a trading/account endpoint.
            raise ValueError(f"refused non-market-data Kite endpoint: {path!r}")
        async with httpx.AsyncClient(timeout=10, headers=self._headers(), follow_redirects=True) as client:
            r = await client.get(f"{_BASE}/{path.lstrip('/')}", params=params or {})
            if r.status_code in (401, 403):
                raise KiteSessionExpired("Kite session expired — regenerate your access token.")
            r.raise_for_status()
            return r.json()

    async def get_quote(self, symbol: str, exchange: str | None = None) -> Quote:
        ksym = to_kite_symbol(symbol, exchange)
        now = datetime.now(UTC)
        try:
            payload = await self._get("quote", {"i": ksym})
            entry = (payload.get("data") or {}).get(ksym)
            if isinstance(entry, dict):
                return parse_quote(entry, symbol, exchange, self.name)
        except KiteSessionExpired:
            raise
        except Exception as exc:  # noqa: BLE001 — never fabricate; unavailable
            log.warning("kite quote unavailable for %s: %s", symbol, exc)
        return Quote(symbol=symbol.upper(), exchange=exchange, price=None,
                     currency=currency_for_symbol(symbol, exchange) or "INR", source=self.name,
                     entitlement=EntitlementStatus.UNAVAILABLE, received_at=now, is_stale=True)

    async def fetch_instruments(self) -> str:
        """Download the read-only instrument master (CSV). Guarded + auth-checked."""
        if not _is_allowed("instruments"):  # defensive; "instruments" is allow-listed
            raise ValueError("refused")
        async with httpx.AsyncClient(timeout=30, headers=self._headers(), follow_redirects=True) as client:
            r = await client.get(f"{_BASE}/instruments")
            if r.status_code in (401, 403):
                raise KiteSessionExpired("Kite session expired — regenerate your access token.")
            r.raise_for_status()
            return r.text

    async def get_history(self, instrument_id: str, interval: str, start: datetime, end: datetime) -> list[Candle]:
        # Kite history needs an instrument_token (from the master); not wired here —
        # history is cached from other sources. Return empty rather than guess.
        return []

    async def search_instruments(self, query: str) -> list[Instrument]:
        # The master search is served by the /kite/search endpoint (DB-backed); the
        # session-less provider path falls back to demo search.
        return await self._mock.search_instruments(query)

    async def get_fx_rate(self, base: str, quote: str) -> FxRate:
        return await self._mock.get_fx_rate(base, quote)   # Kite has no FX

    async def get_market_status(self, market: str) -> MarketStatus:
        return await self._mock.get_market_status(market)

    async def get_news(self, instruments: list[str]) -> list[NewsItem]:
        return []
