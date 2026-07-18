# SPDX-License-Identifier: AGPL-3.0-or-later
"""R-43 §12 step 7 — coverage preflight on Build history (F-1).

Before (and while) a backfill runs, the trigger surfaces a per-instrument coverage summary
(earliest/latest real candle + per-currency FX coverage) so the F-1 zero-coverage garbage line is
never built blind. The served numbers must match the store exactly.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal


async def _seed(session):
    from app.models import (
        Account,
        AssetClass,
        EcbFxHistory,
        Instrument,
        PriceHistory,
        TxnType,
    )
    from app.models import Transaction as Txn
    from app.services.portfolio import rebuild_holdings_from_transactions

    acc = Account(name="A", currency="SGD")
    session.add(acc)
    await session.flush()
    tsla = Instrument(symbol="TSLA", currency="USD", pricing_currency="USD", asset_class=AssetClass.EQUITY)
    btc = Instrument(symbol="BTC", currency="USD", pricing_currency="USD", asset_class=AssetClass.CRYPTO)
    session.add_all([tsla, btc])
    await session.flush()
    # TSLA: 3 daily candles 2026-01-01..03. BTC: none (uncovered).
    for day in (1, 2, 3):
        session.add(PriceHistory(instrument_id=tsla.id, interval="1d",
                                 ts=datetime(2026, 1, day, tzinfo=UTC),
                                 open=Decimal("100"), high=Decimal("100"), low=Decimal("100"),
                                 close=Decimal("100"), source="alphavantage"))
    # USD FX coverage on two dates.
    for day in (1, 2):
        session.add(EcbFxHistory(currency="USD", as_of=date(2026, 1, day).isoformat(), rate=Decimal("1.1")))
    for instr in (tsla, btc):
        session.add(Txn(account_id=acc.id, instrument_id=instr.id, type=TxnType.BUY,
                        ts=datetime(2026, 1, 1, tzinfo=UTC), quantity=Decimal("1"),
                        price=Decimal("10"), currency="USD"))
    await session.flush()
    await rebuild_holdings_from_transactions(session)
    return tsla, btc


async def test_coverage_summary_matches_the_store(session):
    """§12 step 7: the per-instrument coverage summary reports earliest/latest real candle + count
    and per-currency FX coverage that match the store exactly; an uncovered holding is flagged."""
    from app.services.coverage import coverage_summary

    await _seed(session)
    summ = await coverage_summary(session, "SGD")
    by_symbol = {i["symbol"]: i for i in summ["instruments"]}

    tsla = by_symbol["TSLA"]
    assert tsla["price_earliest"] == "2026-01-01" and tsla["price_latest"] == "2026-01-03"
    assert tsla["price_days"] == 3
    assert tsla["fx_currency"] == "USD"
    assert tsla["fx_earliest"] == "2026-01-01" and tsla["fx_latest"] == "2026-01-02"
    assert tsla["covered"] is True

    btc = by_symbol["BTC"]
    assert btc["price_days"] == 0 and btc["price_earliest"] is None
    assert btc["covered"] is False        # no price history yet
    assert btc["summary"]                 # a served human string (D-105)

    assert summ["total"] == 2 and summ["covered_count"] == 1
    assert summ["all_covered"] is False


async def test_coverage_endpoint_serves_the_summary(app_client):
    """§12 step 7: GET /net-worth/coverage serves the summary for the trigger UI (D-105)."""
    r = await app_client.get("/api/v1/net-worth/coverage")
    assert r.status_code == 200
    d = r.json()
    assert "instruments" in d and "all_covered" in d and "total" in d
    assert isinstance(d["instruments"], list)
