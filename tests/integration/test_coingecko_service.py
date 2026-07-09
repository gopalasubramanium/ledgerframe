# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 4: CoinGecko service + API — refresh master, search (canonical id vs symbol
collision), exact mapping, and price → market quote. No network."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select

from app.models import Instrument
from app.models import Quote as QuoteRow
from app.services import coingecko as cg
from app.services.identity import set_identifier

_FX = Path(__file__).parents[1] / "fixtures"
COINS_BYTES = (_FX / "coingecko_coins_list.json").read_bytes()
PRICES = json.loads((_FX / "coingecko_simple_price.json").read_text())


async def test_refresh_master_search_and_map_api(app_client):
    r = await app_client.post("/api/v1/coingecko/refresh",
                              files={"file": ("coins.json", COINS_BYTES, "application/json")})
    assert r.status_code == 200 and r.json()["coins"] == 5

    # Search by symbol returns BOTH coins sharing "btc" — the user picks the id.
    btc = (await app_client.get("/api/v1/coingecko/search", params={"q": "btc"})).json()["results"]
    assert {c["id"] for c in btc} == {"bitcoin", "binance-peg-bitcoin"}
    # Exact canonical id resolves precisely.
    one = (await app_client.get("/api/v1/coingecko/search", params={"q": "bitcoin"})).json()["results"]
    assert any(c["id"] == "bitcoin" for c in one)

    # Map a holding to the exact canonical id. (Use the peg coin — the demo already
    # owns "bitcoin", and a high-confidence id can map to only one instrument.)
    await app_client.post("/api/v1/portfolio/transactions", json={
        "symbol": "MYBTC", "type": "buy", "ts": "2024-01-01T10:00:00",
        "quantity": 1, "price": 40000, "currency": "USD"})
    m = await app_client.post("/api/v1/instruments/MYBTC/map-coingecko", json={"id": "binance-peg-bitcoin"})
    assert m.status_code == 200 and m.json()["id"] == "binance-peg-bitcoin"


async def test_publish_prices_writes_market_quote(session):
    # Master + a mapped instrument, then publish from the price fixture.
    await cg.refresh_coins(session, json.loads(COINS_BYTES))
    instr = Instrument(symbol="MYBTC", name="My Bitcoin", currency="USD")
    session.add(instr)
    await session.flush()
    await set_identifier(session, instr.id, "coingecko_id", "bitcoin", is_primary=True)

    published = await cg.publish_prices(session, PRICES)
    assert published == 1

    q = (await session.execute(select(QuoteRow).where(QuoteRow.instrument_id == instr.id))).scalars().first()
    assert q is not None
    assert str(q.price) == "68000.5" and q.source == "coingecko"
    assert q.entitlement == "delayed" and q.currency == "USD"


async def test_zero_price_not_published(session):
    await cg.refresh_coins(session, json.loads(COINS_BYTES))
    instr = Instrument(symbol="MYSOL", name="My Solana", currency="USD")
    session.add(instr)
    await session.flush()
    await set_identifier(session, instr.id, "coingecko_id", "solana", is_primary=True)  # zero price
    published = await cg.publish_prices(session, PRICES)
    assert published == 0
    q = (await session.execute(select(QuoteRow).where(QuoteRow.instrument_id == instr.id))).scalars().first()
    assert q is None  # never fabricated
