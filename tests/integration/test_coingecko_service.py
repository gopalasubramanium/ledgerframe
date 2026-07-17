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


async def test_sync_now_refetches_full_master_not_kept_stale(app_client, monkeypatch):
    """§14dr-15 — a network Sync-now (no uploaded file) always refetches the FULL coins/list
    and re-upserts the master, mirroring amfi_refresh (which always refetches NAVAll.txt).
    The old `if coins == 0` guard kept a seeded/stale cache forever (2 demo coins vs ~17k),
    so XRP/Ripple was unfindable. RED before the fix: coins stays 2. GREEN: > 10,000 and the
    picker's master resolves Ripple."""
    # The demo seed leaves a stale 2-coin cache (bitcoin/ethereum) — the owner's exact state.
    before = (await app_client.get("/api/v1/coingecko/status")).json()
    assert before["coins"] == 2  # seeded/stale — NOT empty

    # Stub the network: a full coins/list (order-of-magnitude of the real feed), incl. Ripple.
    big_list = [{"id": f"coin-{i}", "symbol": f"c{i}", "name": f"Coin {i}"} for i in range(12000)]
    big_list.append({"id": "ripple", "symbol": "xrp", "name": "XRP"})

    async def _fake_list(timeout: float = 20.0):
        return big_list

    async def _fake_prices(ids, timeout: float = 20.0):
        return {}  # no price call needed for the master-count assertion

    import app.providers.market.coingecko as cg_provider
    monkeypatch.setattr(cg_provider, "fetch_coins_list", _fake_list)
    monkeypatch.setattr(cg_provider, "fetch_prices", _fake_prices)

    r = await app_client.post("/api/v1/coingecko/refresh")  # no file → network Sync-now
    assert r.status_code == 200
    # Order-of-magnitude, not a brittle exact count — a real refresh, not a kept-stale cache.
    assert r.json()["coins"] > 10_000

    # The picker then finds Ripple from the synced master (the dr-12/dr-13 guard extended).
    hits = (await app_client.get("/api/v1/coingecko/search", params={"q": "ripple"})).json()["results"]
    assert any(c["id"] == "ripple" for c in hits)


async def test_status_synced_at_never_then_after_refresh(session):
    """§14dr-13 — CoinGecko status serves an honest last-synced timestamp: None until the
    coin master is synced (the never-synced empty), an ISO string after. Uses the clean
    `session` fixture (no demo seed) so 'never synced' is genuinely empty."""
    fresh = await cg.status(session)
    assert fresh["coins"] == 0 and fresh["synced_at"] is None   # never synced
    await cg.refresh_coins(session, json.loads(COINS_BYTES))
    after = await cg.status(session)
    assert after["coins"] == 5 and isinstance(after["synced_at"], str) and after["synced_at"]
