# SPDX-License-Identifier: AGPL-3.0-or-later
"""§4.4 Unit B — average-cost in the tax replay. FIFO stays the default (unchanged); average
cost is a new branch selected per account by cost_basis_method. Each vector proves one point.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

from app.core.config import get_settings
from app.models import Account, Instrument, Transaction, TxnType
from app.services.tax import fifo_report, realised_gains_report


def _txn(ttype, date, qty, px, fx=None, fx_base=None, ccy="USD"):
    return SimpleNamespace(
        type=ttype, ts=datetime.fromisoformat(date),
        quantity=Decimal(str(qty)), price=Decimal(str(px)), fees=Decimal("0"), taxes=Decimal("0"),
        currency=ccy, fx_to_base=(Decimal(str(fx)) if fx is not None else None), fx_base=fx_base)


# (1) FIFO unchanged (R6): the default method IS fifo, and it consumes the oldest lot.
def test_fifo_is_the_untouched_default():
    txns = [_txn(TxnType.BUY, "2024-01-01", 100, 10),
            _txn(TxnType.BUY, "2024-02-01", 100, 20),
            _txn(TxnType.SELL, "2024-03-01", 100, 30)]
    assert fifo_report(txns) == fifo_report(txns, method="fifo")   # default == explicit fifo
    (events, _lots) = fifo_report(txns, method="fifo")
    assert events[0].cost == Decimal("1000")       # oldest lot @ 10
    assert sum(e.gain for e in events) == Decimal("2000")   # proceeds 3000 − cost 1000


# (2) Average vs FIFO divergence: buy 100@10 then 100@20, sell 100 — different correct gains.
def test_average_vs_fifo_divergence():
    txns = [_txn(TxnType.BUY, "2024-01-01", 100, 10),
            _txn(TxnType.BUY, "2024-02-01", 100, 20),
            _txn(TxnType.SELL, "2024-03-01", 100, 30)]
    fifo_gain = sum(e.gain for e in fifo_report(txns, method="fifo")[0])
    avg_gain = sum(e.gain for e in fifo_report(txns, method="average")[0])
    assert fifo_gain == Decimal("2000")    # FIFO: 3000 − 1000 (oldest $10 lot)
    assert avg_gain == Decimal("1500")     # average: 3000 − 100 × avg($15)
    assert fifo_gain != avg_gain


# (3) Bonus under average (R7): the bonus lowers the pool average; a later sale uses the blend.
def test_bonus_under_average_uses_blended_avg():
    txns = [_txn(TxnType.BUY, "2024-01-01", 100, 10),
            _txn(TxnType.BONUS, "2024-02-01", 100, 0),      # 100 free shares → pool 200 @ avg $5
            _txn(TxnType.SELL, "2024-03-01", 100, 20)]
    (avg_ev, _) = fifo_report(txns, method="average")
    assert avg_ev[0].cost == Decimal("500")        # 100 × avg $5
    assert avg_ev[0].gain == Decimal("1500")       # 2000 − 500
    # FIFO consumes the oldest $10 lot instead → cost 1000, gain 1000 (different, both correct).
    assert fifo_report(txns, method="fifo")[0][0].gain == Decimal("1000")


# (4) Holding period (Decision B): an average sale's date is the OLDEST open lot's.
def test_average_holding_period_from_oldest_lot():
    txns = [_txn(TxnType.BUY, "2020-01-01", 100, 10),
            _txn(TxnType.BUY, "2024-01-01", 100, 20),
            _txn(TxnType.SELL, "2024-06-01", 50, 30)]
    e = fifo_report(txns, method="average")[0][0]
    assert e.acquired_ts == datetime(2020, 1, 1)   # oldest open lot, not the 2024 buy
    assert e.holding_days > 365                     # long-term
    assert e.cost == Decimal("750")                 # 50 × avg($15) — cost pooled, date FIFO


# (5) FX unavailable (Decision A): an average sale carries NO trade-date FX (never mixed).
def test_average_trade_date_fx_unavailable():
    txns = [_txn(TxnType.BUY, "2024-01-01", 100, 10, fx="1.30", fx_base="SGD", ccy="EUR"),
            _txn(TxnType.SELL, "2024-03-01", 50, 20, fx="1.40", fx_base="SGD", ccy="EUR")]
    e = fifo_report(txns, base="SGD", method="average")[0][0]
    assert e.cost_fx is None and e.proceeds_fx is None     # no per-leg rate under average
    assert e.gain_base_historical is None                  # → excluded from the historical total
    # FIFO on the same data DOES carry per-leg trade-date FX.
    fifo_e = fifo_report(txns, base="SGD", method="fifo")[0][0]
    assert fifo_e.cost_fx == Decimal("1.30") and fifo_e.gain_base_historical is not None


# (6) Oversell (R9): selling more than the pool holds matches only the pool; no crash/fabrication.
def test_average_oversell_matches_only_the_pool():
    txns = [_txn(TxnType.BUY, "2024-01-01", 50, 10),
            _txn(TxnType.SELL, "2024-03-01", 100, 20)]   # sell 100 but only 50 held
    (events, lots) = fifo_report(txns, method="average")
    assert events[0].quantity == Decimal("50")     # only the matched 50
    assert events[0].cost == Decimal("500")        # 50 × 10 — no fabricated cost for the missing 50
    assert lots == []                              # pool drained
    # Selling into an empty pool → no event, no division-by-zero.
    assert fifo_report([_txn(TxnType.SELL, "2024-01-01", 10, 20)], method="average")[0] == []


# Integration: the realised-gains report applies the per-account method and (Decision A)
# excludes an average account's events from the trade-date-FX total.
async def test_realised_report_honours_average_account_and_excludes_fx(session):
    base = get_settings().base_currency
    foreign = "EUR" if base != "EUR" else "USD"
    acc = Account(name="Avg", currency=base, cost_basis_method="average")
    session.add(acc)
    await session.flush()
    instr = Instrument(symbol="AVGCO", currency=foreign)
    session.add(instr)
    await session.flush()

    def txn(ttype, m, qty, px, fx):
        return Transaction(account_id=acc.id, instrument_id=instr.id, type=ttype,
                           ts=datetime(2024, m, 1, tzinfo=UTC), quantity=Decimal(str(qty)),
                           price=Decimal(str(px)), fees=Decimal("0"), taxes=Decimal("0"),
                           amount=Decimal("0"), currency=foreign, fx_to_base=Decimal(str(fx)),
                           fx_base=base)
    session.add_all([txn(TxnType.BUY, 1, 100, 10, "1.30"),
                     txn(TxnType.BUY, 2, 100, 20, "1.35"),
                     txn(TxnType.SELL, 6, 100, 30, "1.40")])
    await session.flush()

    rep = await realised_gains_report(session, year=2024)
    # Average cost: native realised = 3000 − 100 × avg($15) = 1500 (a FIFO account would be 2000).
    assert rep["currency_groups"][0]["realised_total"] == 1500.0
    # Decision A: the average event is excluded from the trade-date-FX total, current-FX present.
    assert rep["realised_fx_events_excluded"] == 1
    assert rep["base_realised_total_historical_fx"] == 0.0
    assert rep["base_realised_total_current_fx"] != 0.0
