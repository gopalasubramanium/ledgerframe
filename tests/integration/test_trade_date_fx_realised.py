# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 4.2 Unit C — trade-date FX realised gains (money-path computation).

A NEW historical-FX realised total values each leg at its OWN stored trade-date rate
(proceeds × fx_sell − cost × fx_buy), ADDITIVELY, beside the retained current-FX total.
R7 never-mix: a NULL on either leg excludes the whole event. Proven in all four directions.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from app.core.config import get_settings
from app.models import Account, Instrument, Transaction, TxnType
from app.models import Quote as QuoteRow
from app.services import fx
from app.services.analytics import key_stats
from app.services.tax import realised_gains_report

UTC_ = UTC


def _base_and_foreign() -> tuple[str, str]:
    base = get_settings().base_currency.upper()
    return base, ("EUR" if base != "EUR" else "USD")


async def _seed_lot(session, currency, buy_fx, sell_fx, base):
    """One instrument: buy 10@100 then sell 5@250 in 2024, with the given stored trade-date
    rates on each leg (None = 'unavailable'). Native realised gain = (250-100)*5 = 750."""
    acc = Account(name="Broker", currency=base, entity_id=None)
    session.add(acc)
    await session.flush()
    instr = Instrument(symbol="AAPL", currency=currency)
    session.add(instr)
    await session.flush()
    session.add(QuoteRow(instrument_id=instr.id, price=Decimal("300"), previous_close=Decimal("300"),
                         currency=currency, source="mock", entitlement="delayed", received_at=datetime.now(UTC_)))

    def _fx(v):
        return (Decimal(str(v)), base) if v is not None else (None, None)

    buy_rate, buy_base = _fx(buy_fx)
    sell_rate, sell_base = _fx(sell_fx)
    session.add_all([
        Transaction(account_id=acc.id, instrument_id=instr.id, type=TxnType.BUY,
                    ts=datetime(2024, 1, 1, tzinfo=UTC_), quantity=Decimal("10"), price=Decimal("100"),
                    fees=Decimal("0"), taxes=Decimal("0"), amount=Decimal("-1000"), currency=currency,
                    fx_to_base=buy_rate, fx_base=buy_base),
        Transaction(account_id=acc.id, instrument_id=instr.id, type=TxnType.SELL,
                    ts=datetime(2024, 6, 1, tzinfo=UTC_), quantity=Decimal("5"), price=Decimal("250"),
                    fees=Decimal("0"), taxes=Decimal("0"), amount=Decimal("1250"), currency=currency,
                    fx_to_base=sell_rate, fx_base=sell_base),
    ])
    await session.flush()
    return acc, instr


# --------------------------------------------------------------------------- #
# (1) MUST-STAY: a domestic portfolio → historical == current == native (rate 1 everywhere).
# --------------------------------------------------------------------------- #
async def test_domestic_historical_equals_current_equals_native(session):
    base, _ = _base_and_foreign()
    await _seed_lot(session, currency=base, buy_fx=1, sell_fx=1, base=base)  # domestic: rate 1 both legs

    rep = await realised_gains_report(session, year=2024)
    assert rep["base_realised_total_current_fx"] == 750.0     # native, current FX (rate 1)
    assert rep["base_realised_total_historical_fx"] == 750.0  # trade-date FX == native
    assert rep["realised_fx_events_excluded"] == 0
    # Per-currency native figure is untouched.
    assert rep["currency_groups"][0]["realised_total"] == 750.0


# --------------------------------------------------------------------------- #
# (2) SHOULD-CHANGE: a foreign lot with DIFFERENT buy/sell rates → per-leg historical gain,
#     and it differs from the current-FX total (proving trade-date FX actually applied).
# --------------------------------------------------------------------------- #
async def test_foreign_historical_uses_per_leg_rates_and_differs(session, monkeypatch):
    base, foreign = _base_and_foreign()
    await _seed_lot(session, currency=foreign, buy_fx="1.30", sell_fx="1.40", base=base)

    # Pin the CURRENT rate so the current-FX total is deterministic (and clearly ≠ historical).
    async def current_rate(_a, _b):
        return Decimal("1.35")
    monkeypatch.setattr(fx, "get_rate", current_rate)

    rep = await realised_gains_report(session, year=2024)
    # Historical = proceeds×fx_sell − cost×fx_buy = 1250×1.40 − 500×1.30 = 1100.
    assert rep["base_realised_total_historical_fx"] == 1100.0
    # Current-FX = native gain × today's rate = 750 × 1.35 = 1012.50.
    assert rep["base_realised_total_current_fx"] == 1012.5
    # Trade-date FX genuinely applied → the two totals differ.
    assert rep["base_realised_total_historical_fx"] != rep["base_realised_total_current_fx"]
    assert rep["realised_fx_events_excluded"] == 0
    assert rep["currency_groups"][0]["realised_total"] == 750.0  # native untouched


# --------------------------------------------------------------------------- #
# (3) NEVER-MIX (R7): a foreign lot with a rate on ONE leg only → excluded from the
#     historical total (not half-computed), while still counted in the current-FX total.
# --------------------------------------------------------------------------- #
async def test_one_leg_null_is_excluded_not_mixed(session, monkeypatch):
    base, foreign = _base_and_foreign()
    # Buy has a stored rate, sell does NOT → the whole event is "trade-date FX unavailable".
    await _seed_lot(session, currency=foreign, buy_fx="1.30", sell_fx=None, base=base)

    async def current_rate(_a, _b):
        return Decimal("1.35")
    monkeypatch.setattr(fx, "get_rate", current_rate)

    rep = await realised_gains_report(session, year=2024)
    assert rep["realised_fx_events_excluded"] == 1             # the event is excluded...
    assert rep["base_realised_total_historical_fx"] == 0.0     # ...not half-computed
    assert rep["base_realised_total_current_fx"] == 1012.5     # ...but still in the current-FX total


# --------------------------------------------------------------------------- #
# (4) CONSISTENCY: key_stats and the tax report expose the identical (current, historical) pair.
# --------------------------------------------------------------------------- #
async def test_key_stats_and_report_agree(session):
    from app.providers.market import reset_provider
    reset_provider()
    fx.clear_cache()

    base, foreign = _base_and_foreign()
    await _seed_lot(session, currency=foreign, buy_fx="1.30", sell_fx="1.40", base=base)

    rep = await realised_gains_report(session, year=2024)
    ks = await key_stats(session, base)

    for field in ("base_realised_total_current_fx", "base_realised_total_historical_fx",
                  "realised_fx_events_excluded"):
        assert rep[field] == ks[field], f"{field} diverged: report={rep[field]} key_stats={ks[field]}"
    # And the historical figure genuinely used per-leg rates (1250×1.40 − 500×1.30 = 1100).
    assert ks["base_realised_total_historical_fx"] == 1100.0
