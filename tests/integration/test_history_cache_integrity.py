# SPDX-License-Identifier: AGPL-3.0-or-later
"""§14dr-25 — history-cache integrity. Fail-first pins for the served-history comb.

The `price_history` unique key is `(instrument_id, interval, ts)` — the exact
timestamp, not the trading date. Legacy DEMO candles stamp a non-midnight
time-of-day; REAL alphavantage/eodhd candles stamp 00:00:00 UTC. The same
trading DATE under two timestamps therefore stored TWO rows at two price levels
→ the served series alternated real/demo = a sawtooth "comb", on instrument
history AND the Performance benchmark.

These pins assert the cache serves strictly-unique-ascending trading dates, real
supersedes demo for a shared date, and the benchmark inherits both.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import app.services.market as market
from app.models import Account, Entity, Holding, Instrument, PriceHistory


class _RealStub:
    """A non-mock ('real') provider so get_history_cached serves the cache
    (is_demo=False) instead of regenerating from the demo generator."""

    name = "alphavantage"
    fetch_on_demand = False

    async def get_history(self, *a, **k):
        return []


def _use_real_provider(monkeypatch):
    monkeypatch.setattr(market, "get_provider", lambda: _RealStub())


async def _seed_comb(session, symbol="AAPL", real_close="190", demo_close="250", days=4):
    """Seed the owner's persistent-instance state: for each of `days` trading
    dates, a REAL candle at midnight and a legacy DEMO candle at 14:32."""
    instr = Instrument(symbol=symbol, name=f"{symbol} Inc.", asset_class="equity", currency="USD")
    session.add(instr)
    await session.flush()
    base_day = datetime(2026, 7, 1, tzinfo=UTC)
    for i in range(days):
        d = base_day + timedelta(days=i)
        session.add(PriceHistory(
            instrument_id=instr.id, interval="1d", ts=d.replace(hour=0, minute=0, second=0),
            open=Decimal(real_close), high=Decimal(real_close), low=Decimal(real_close),
            close=Decimal(real_close), volume=Decimal("2000000")))
        session.add(PriceHistory(
            instrument_id=instr.id, interval="1d", ts=d.replace(hour=14, minute=32, second=7),
            open=Decimal(demo_close), high=Decimal(demo_close), low=Decimal(demo_close),
            close=Decimal(demo_close), volume=Decimal("1000000")))
    await session.flush()
    return instr


def _dates(candles):
    return [c.ts.date() for c in candles]


async def test_served_history_has_unique_ascending_dates(session, monkeypatch):
    _use_real_provider(monkeypatch)
    await _seed_comb(session)
    end = datetime.now(UTC)
    start = end - timedelta(days=60)
    candles = await market.get_history_cached(session, "AAPL", "1d", start, end, allow_fetch=False)

    dates = _dates(candles)
    assert dates == sorted(dates), "served dates must be ascending"
    assert len(dates) == len(set(dates)), f"served dates must be UNIQUE (no comb); got {dates}"


async def test_real_supersedes_demo_for_a_shared_date(session, monkeypatch):
    _use_real_provider(monkeypatch)
    await _seed_comb(session, real_close="190", demo_close="250")
    end = datetime.now(UTC)
    start = end - timedelta(days=60)
    candles = await market.get_history_cached(session, "AAPL", "1d", start, end, allow_fetch=False)

    # every served candle carries the REAL level (190), never the demo residue (250)
    closes = {str(c.close) for c in candles}
    assert closes == {"190"}, f"real must supersede demo; got closes {closes}"


async def test_benchmark_series_inherits_unique_dates(session, monkeypatch):
    _use_real_provider(monkeypatch)
    # benchmark SPY with the comb; one priced holding so a portfolio series exists
    await _seed_comb(session, symbol="SPY", real_close="500", demo_close="620")
    aapl = await _seed_comb(session, symbol="AAPL", real_close="190", demo_close="250")
    ent = Entity(name="Self", kind="self")
    session.add(ent)
    await session.flush()
    acct = Account(entity_id=ent.id, name="Brokerage", kind="brokerage", currency="USD")
    session.add(acct)
    await session.flush()
    session.add(Holding(account_id=acct.id, instrument_id=aapl.id, asset_class="equity",
                        quantity=Decimal("10"), avg_cost=Decimal("100"), currency="USD"))
    await session.flush()

    from app.services.analytics import performance_series

    out = await performance_series(session, "USD", days=60, benchmark="SPY")
    bench_dates = [datetime.fromisoformat(p["ts"]).date() for p in out["benchmark"]]
    assert bench_dates == sorted(bench_dates), "benchmark dates ascending"
    assert len(bench_dates) == len(set(bench_dates)), f"benchmark must not comb; got {bench_dates}"


async def test_served_repair_purges_demo_residue_idempotently(session):
    # 4 dates × (real@midnight + demo@14:32) = 8 rows.
    await _seed_comb(session)
    from sqlalchemy import select

    from app.models import PriceHistory
    from app.services.market import repair_history_demo_residue

    r1 = await repair_history_demo_residue(session)
    assert r1 == {"purged": 4, "instruments": 1}, r1
    rows = (await session.execute(select(PriceHistory))).scalars().all()
    assert len(rows) == 4 and {str(r.close) for r in rows} == {"190"}, "real survives, demo purged"

    r2 = await repair_history_demo_residue(session)
    assert r2["purged"] == 0, "idempotent: a second run finds nothing"


async def test_upsert_real_supersedes_demo_residue(session, monkeypatch):
    """A REAL fetch overwrites a demo-residue row for the same date (precedence),
    stamps `source`, and leaves strictly one row per date."""
    from sqlalchemy import select

    from app.models import Instrument, PriceHistory

    instr = Instrument(symbol="MSFT", name="Microsoft", asset_class="equity", currency="USD")
    session.add(instr)
    await session.flush()
    day = datetime(2026, 7, 5, tzinfo=UTC)
    # a lone legacy demo residue row (non-midnight ts, no source)
    session.add(PriceHistory(instrument_id=instr.id, interval="1d",
                             ts=day.replace(hour=14, minute=32, second=7),
                             open=Decimal("250"), high=Decimal("250"), low=Decimal("250"),
                             close=Decimal("250"), volume=Decimal("1")))
    await session.flush()

    class _RealFetch:
        name = "alphavantage"
        fetch_on_demand = True

        async def get_history(self, *a, **k):
            from app.schemas.common import Candle
            return [Candle(ts=day, open=Decimal("190"), high=Decimal("190"),
                           low=Decimal("190"), close=Decimal("190"), volume=Decimal("2"))]

    monkeypatch.setattr(market, "get_provider", lambda: _RealFetch())
    # route history to the active provider for a plain equity
    monkeypatch.setattr(market, "_history_source", lambda diag, name: (name, "test"))

    end = datetime.now(UTC)
    candles = await market.get_history_cached(session, "MSFT", "1d", end - timedelta(days=30), end)
    assert [str(c.close) for c in candles] == ["190"], "real supersedes the demo residue"

    rows = (await session.execute(
        select(PriceHistory).where(PriceHistory.instrument_id == instr.id))).scalars().all()
    assert len(rows) == 1, f"one row per date, got {len(rows)}"
    assert rows[0].source == "alphavantage" and str(rows[0].close) == "190"
    assert rows[0].ts.hour == 0 and rows[0].ts.minute == 0, "ts normalised to midnight"
