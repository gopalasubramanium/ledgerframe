# SPDX-License-Identifier: AGPL-3.0-or-later
"""CoinGecko crypto adapter (opt-in) — canonical-ID pricing.

Source: CoinGecko's public API (no key on the free tier). This module is the parser
+ HTTP fetch only; storage/lookup lives in ``app/services/coingecko.py``. Spec rules:

- Resolve and store the **canonical CoinGecko id**, never symbol alone — many coins
  share a symbol (e.g. two different tokens are both "btc"), so a holding must be
  mapped by id.
- Support multiple target currencies (USD/SGD/INR…).
- A missing / zero / non-positive price is **unavailable — never fabricated**.
- No wallet keys or private wallet access. Deterministic, fixture-driven tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

BASE_URL = "https://api.coingecko.com/api/v3"
VS_CURRENCIES = ("usd", "sgd", "inr", "eur", "gbp")


@dataclass(frozen=True)
class CoinMeta:
    id: str
    symbol: str
    name: str


@dataclass(frozen=True)
class CoinPrice:
    id: str
    prices: dict[str, Decimal]      # ccy(lower) -> price (>0 only)
    market_cap_usd: Decimal | None
    last_updated: datetime | None


def parse_coins_list(data: list) -> list[CoinMeta]:
    out: list[CoinMeta] = []
    for row in data or []:
        cid = str(row.get("id", "")).strip()
        if not cid:
            continue
        out.append(CoinMeta(id=cid, symbol=str(row.get("symbol", "")).strip().lower(),
                            name=str(row.get("name", "")).strip()))
    return out


def _dec(v) -> Decimal | None:
    try:
        d = Decimal(str(v))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return d if d > 0 else None


def parse_simple_price(data: dict) -> dict[str, CoinPrice]:
    """Parse a ``/simple/price`` response into per-id prices. Zero/absent prices are
    dropped (unavailable), never coerced to a fabricated value."""
    out: dict[str, CoinPrice] = {}
    for cid, row in (data or {}).items():
        if not isinstance(row, dict):
            continue
        prices: dict[str, Decimal] = {}
        for ccy in VS_CURRENCIES:
            p = _dec(row.get(ccy))
            if p is not None:
                prices[ccy] = p
        ts = row.get("last_updated_at")
        out[str(cid)] = CoinPrice(
            id=str(cid), prices=prices,
            market_cap_usd=_dec(row.get("usd_market_cap")),
            last_updated=datetime.fromtimestamp(ts, UTC) if isinstance(ts, (int, float)) else None,
        )
    return out


async def fetch_coins_list(timeout: float = 20.0) -> list:
    import httpx

    async with httpx.AsyncClient(timeout=timeout, headers={"User-Agent": "LedgerFrame/1.0 (+local)"}, follow_redirects=True) as c:
        r = await c.get(f"{BASE_URL}/coins/list")
        r.raise_for_status()
        return r.json()


async def fetch_prices(ids: list[str], timeout: float = 20.0) -> dict:
    if not ids:
        return {}
    import httpx

    params = {
        "ids": ",".join(sorted(set(ids))),
        "vs_currencies": ",".join(VS_CURRENCIES),
        "include_market_cap": "true", "include_last_updated_at": "true",
    }
    async with httpx.AsyncClient(timeout=timeout, headers={"User-Agent": "LedgerFrame/1.0 (+local)"}, follow_redirects=True) as c:
        r = await c.get(f"{BASE_URL}/simple/price", params=params)
        r.raise_for_status()
        return r.json()
