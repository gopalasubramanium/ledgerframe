# SPDX-License-Identifier: AGPL-3.0-or-later
"""§4.6 Unit B — cost_of_ownership reader (read-only).

Deterministic vectors that pin the honesty contract:
  R2 — two separate blocks, NO blended 'total cost of ownership' key.
  R3 — a null-expense-ratio instrument is excluded from the estimate and surfaced as
       unavailable-with-reason + a covers-N-of-M count; it never contributes 0.
  R5 — the recorded-fees total IS the statements report's fee total (single source, not a re-sum).
The reader consumes value_portfolio + statements_report outputs only — no money-path touch.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from app.core.config import get_settings
from app.models import Account, Instrument, Transaction, TxnType
from app.models import Quote as QuoteRow
from app.services.cost_of_ownership import cost_of_ownership
from app.services.portfolio import rebuild_holdings_from_transactions
from app.services.statements import statements_report


async def _instrument(session, symbol, price, ccy, bps):
    instr = Instrument(symbol=symbol, currency=ccy,
                       annual_cost_bps=(Decimal(str(bps)) if bps is not None else None))
    session.add(instr)
    await session.flush()
    session.add(QuoteRow(instrument_id=instr.id, price=Decimal(price), previous_close=Decimal(price),
                         currency=ccy, source="mock", entitlement="delayed", received_at=datetime.now(UTC)))
    return instr


def _buy(acc_id, iid, ccy, qty, px, fees):
    return Transaction(account_id=acc_id, instrument_id=iid, type=TxnType.BUY,
                       ts=datetime(2024, 1, 1, tzinfo=UTC), quantity=Decimal(qty), price=Decimal(px),
                       fees=Decimal(fees), taxes=Decimal("0"), amount=Decimal("0"), currency=ccy)


async def _seed(session):
    """AAA has a 45bps expense ratio (value 3000 → 13.5/yr); BBB has NONE (value 1000).
    Fees: 5 + 3 on the buys + a 12 FEE transaction = 20 recorded."""
    base = get_settings().base_currency
    acc = Account(name="Broker", currency=base)
    session.add(acc)
    await session.flush()
    aaa = await _instrument(session, "AAA", "300", base, 45)     # 0.45%
    bbb = await _instrument(session, "BBB", "50", base, None)    # no expense ratio
    session.add_all([
        _buy(acc.id, aaa.id, base, "10", "100", "5"),
        _buy(acc.id, bbb.id, base, "20", "40", "3"),
        Transaction(account_id=acc.id, instrument_id=None, type=TxnType.FEE,
                    ts=datetime(2024, 6, 1, tzinfo=UTC), quantity=Decimal("0"), price=Decimal("0"),
                    fees=Decimal("0"), taxes=Decimal("0"), amount=Decimal("12"), currency=base),
    ])
    await session.flush()
    await rebuild_holdings_from_transactions(session)
    return base


async def test_recorded_fees_reuse_statements_total(session):  # R5
    base = await _seed(session)
    rep = await cost_of_ownership(session, base, year=2024)
    st = await statements_report(session, year=2024)
    # Single source: the recorded total IS the statements fee total, not an independent re-sum.
    assert rep["recorded_fees"]["total"] == st["fees"]["total"]
    assert rep["recorded_fees"]["total"] == 20.0                # 5 + 3 (buy fees) + 12 (FEE txn)
    assert rep["recorded_fees"]["label"] == "fees recorded in 2024"
    # Currency-only fact — no annualised percentage on the recorded line (R4).
    assert not any("pct" in k or "percent" in k for k in rep["recorded_fees"])


async def test_null_bps_instrument_is_unavailable_never_zero(session):  # R3
    base = await _seed(session)
    est = (await cost_of_ownership(session, base, year=2024))["estimated_ongoing_cost"]
    assert est["available"] is True
    assert est["covered"] == 1 and est["total"] == 2               # AAA covered, BBB not
    assert est["coverage_label"] == "covers 1 of 2 holdings"
    assert est["estimated_annual_total"] == 13.5                   # only AAA: 3000 × 45/10000
    assert est["covered_value"] == 3000.0
    # AAA is the only priced/covered row; BBB (null rate) is surfaced with a reason, never as 0.
    assert [r["symbol"] for r in est["holdings"]] == ["AAA"]
    assert est["holdings"][0]["annual_cost_bps"] == 45.0
    bbb = [u for u in est["unavailable"] if u["symbol"] == "BBB"]
    assert len(bbb) == 1 and "no expense ratio" in bbb[0]["reason"]
    # BBB contributes nothing to the sum and appears in no covered row as a fabricated 0.
    assert all(r["symbol"] != "BBB" for r in est["holdings"])
    assert all(r["estimated_annual_cost"] != 0.0 for r in est["holdings"])


async def test_no_blended_total_cost_key(session):  # R2
    base = await _seed(session)
    rep = await cost_of_ownership(session, base, year=2024)
    # Exactly two separate blocks, plus base_currency — nothing that fuses recorded + estimated.
    assert set(rep) == {"base_currency", "recorded_fees", "estimated_ongoing_cost"}
    for block in (rep, rep["recorded_fees"], rep["estimated_ongoing_cost"]):
        for k in block:
            assert "total_cost_of_ownership" not in k
            assert not ("recorded" in k and "estimated" in k)     # no fused key


async def test_all_null_bps_estimate_is_unavailable_not_zero(session):  # R3 edge
    # A portfolio where NO instrument has a rate → the estimate is unavailable, total is None (not 0).
    base = get_settings().base_currency
    acc = Account(name="Broker", currency=base)
    session.add(acc)
    await session.flush()
    ins = await _instrument(session, "ZZZ", "100", base, None)
    session.add(_buy(acc.id, ins.id, base, "5", "80", "0"))
    await session.flush()
    await rebuild_holdings_from_transactions(session)

    est = (await cost_of_ownership(session, base))["estimated_ongoing_cost"]
    assert est["available"] is False
    assert est["estimated_annual_total"] is None                  # never a fabricated 0
    assert est["covered"] == 0 and est["total"] == 1
    assert len(est["unavailable"]) == 1
