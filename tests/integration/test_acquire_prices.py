# SPDX-License-Identifier: AGPL-3.0-or-later
"""R-43 §12 step 6 — per-instrument price-acquisition orchestration (equity AV full-depth + the
class-routed crypto/fund fetchers). The build-history preflight must acquire each held instrument's
history from the provider that can serve its class (§12-R3) BEFORE valuing — the fix for F-1's
sparse/wrong-instrument store. Fetchers are monkeypatched (deterministic, no network)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal


async def _seed(session):
    from app.models import Account, AssetClass, Instrument, InstrumentIdentifier, TxnType
    from app.models import Transaction as Txn
    from app.services.portfolio import rebuild_holdings_from_transactions

    acc = Account(name="A", currency="SGD")
    session.add(acc)
    await session.flush()
    tsla = Instrument(symbol="TSLA", currency="USD", pricing_currency="USD", asset_class=AssetClass.EQUITY)
    btc = Instrument(symbol="BTC", currency="USD", pricing_currency="USD", asset_class=AssetClass.CRYPTO)
    fund = Instrument(symbol="102000", currency="INR", pricing_currency="INR", asset_class=AssetClass.MUTUAL_FUND)
    session.add_all([tsla, btc, fund])
    await session.flush()
    session.add_all([
        InstrumentIdentifier(instrument_id=btc.id, id_type="coingecko_id", value="bitcoin"),
        InstrumentIdentifier(instrument_id=fund.id, id_type="amfi_code", value="102000"),
    ])
    old = datetime.now(UTC) - timedelta(days=400)  # a >100-day span → AV outputsize=full
    for instr in (tsla, btc, fund):
        session.add(Txn(account_id=acc.id, instrument_id=instr.id, type=TxnType.BUY,
                        ts=old, quantity=Decimal("1"), price=Decimal("10"), currency="USD"))
    await session.flush()
    await rebuild_holdings_from_transactions(session)
    return tsla, btc, fund


async def test_acquire_prices_routes_each_class_to_its_provider(session, monkeypatch):
    """§12 step 6: equity → the active provider's daily history (AV outputsize=full over the full
    span); crypto → CoinGecko; fund → AMFI archive chunks. Each held instrument's history is stored
    from the RIGHT provider — a crypto is never sent to AV's equity endpoint (§12-R3)."""
    from sqlalchemy import select

    from app.models import PriceHistory
    from app.services import acquire

    tsla, btc, fund = await _seed(session)

    eq_calls: list = []

    async def _fake_get_history(sess, symbol, interval, start, end, **kw):
        eq_calls.append((symbol, interval, (end - start).days))
        return []  # the AV path is exercised + tested elsewhere; here we assert it is CALLED

    d1 = int((datetime.now(UTC) - timedelta(days=3)).timestamp() * 1000)
    d2 = int((datetime.now(UTC) - timedelta(days=2)).timestamp() * 1000)

    async def _fake_cg(cid, vs, start, end, timeout=30.0):
        assert cid == "bitcoin"
        return {"prices": [[d1, 64024.63], [d2, 65010.0]], "total_volumes": []}

    async def _fake_amfi(a, b, mf=None, tp=None, timeout=30.0):
        return ("Scheme Code;Scheme Name;ISIN Div Payout/ISIN Growth;ISIN Div Reinvestment;"
                "Net Asset Value;Repurchase Price;Sale Price;Date\n"
                f"102000;SBI Fund A;INF001;INF002;45.10;;;{a.strftime('%d-%b-%Y')}\n")

    monkeypatch.setattr("app.services.market.get_history_cached", _fake_get_history)
    monkeypatch.setattr("app.services.acquire.fetch_market_chart_range", _fake_cg)
    monkeypatch.setattr("app.services.acquire.fetch_nav_history", _fake_amfi)

    counts = await acquire.acquire_prices(session, "SGD")

    # Equity: the active-provider daily history was fetched over a >100-day span (→ AV full).
    assert eq_calls and eq_calls[0][0] == "TSLA" and eq_calls[0][1] == "1d" and eq_calls[0][2] > 100
    assert counts["equity"] == 1
    # Crypto rows are stored from CoinGecko, never AV.
    crypto_rows = (await session.execute(
        select(PriceHistory).where(PriceHistory.instrument_id == btc.id))).scalars().all()
    assert crypto_rows and all(r.source == "coingecko" for r in crypto_rows)
    # Fund rows are stored from AMFI.
    fund_rows = (await session.execute(
        select(PriceHistory).where(PriceHistory.instrument_id == fund.id))).scalars().all()
    assert fund_rows and all(r.source == "amfi_nav" for r in fund_rows)


async def test_acquire_prices_skips_unmapped_crypto_honestly(session, monkeypatch):
    """§12 step 6: a crypto instrument with no coingecko_id is skipped HONESTLY (logged) — no
    fabricated candle, no wrong-provider fetch, and the rest of the book still acquires."""
    from sqlalchemy import func, select

    from app.models import Account, AssetClass, Instrument, PriceHistory, TxnType
    from app.models import Transaction as Txn
    from app.services import acquire
    from app.services.portfolio import rebuild_holdings_from_transactions

    acc = Account(name="A", currency="SGD")
    session.add(acc)
    await session.flush()
    doge = Instrument(symbol="DOGE", currency="USD", pricing_currency="USD", asset_class=AssetClass.CRYPTO)
    session.add(doge)
    await session.flush()
    session.add(Txn(account_id=acc.id, instrument_id=doge.id, type=TxnType.BUY,
                    ts=datetime.now(UTC) - timedelta(days=200), quantity=Decimal("1"),
                    price=Decimal("1"), currency="USD"))
    await session.flush()
    await rebuild_holdings_from_transactions(session)

    def _boom(*a, **k):
        raise AssertionError("an unmapped crypto must NOT trigger a fetch")
    monkeypatch.setattr("app.services.acquire.fetch_market_chart_range", _boom)

    counts = await acquire.acquire_prices(session, "SGD")
    assert counts["crypto"] == 0 and counts["skipped"] >= 1
    total = (await session.execute(select(func.count()).select_from(PriceHistory))).scalar()
    assert total == 0  # nothing fabricated
