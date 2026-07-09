# SPDX-License-Identifier: AGPL-3.0-or-later
"""§4.3 Unit 2b — stock-for-stock merger lot-transfer (A absorbed into B at ratio R).

Each vector proves one correctness checkpoint. The cross-instrument coordination is
resolve_mergers (carries A's open lots into B as synthetic buys); both FIFO engines then
replay the SAME resolved streams, so they cannot diverge.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

from app.models import TxnType
from app.services.portfolio import compute_fifo
from app.services.tax import fifo_report, resolve_mergers

A, B = 1, 2   # instrument ids: A absorbed into B


def _txn(ttype, instr, date, qty, px, target=None, fx=None, fx_base=None, ccy="USD"):
    return SimpleNamespace(
        account_id=1, instrument_id=instr, related_instrument_id=target,
        type=ttype, ts=datetime.fromisoformat(date),
        quantity=Decimal(str(qty)), price=Decimal(str(px)),
        fees=Decimal("0"), taxes=Decimal("0"), amount=Decimal("0"), currency=ccy,
        fx_to_base=(Decimal(str(fx)) if fx is not None else None), fx_base=fx_base,
        deleted_at=None)


def _by_instr(resolved):
    g: dict[int, list] = defaultdict(list)
    for t in resolved:
        g[t.instrument_id].append(t)
    return g


def _run_tax(txns, base="USD"):
    return {iid: fifo_report(grp, base) for iid, grp in _by_instr(resolve_mergers(txns, base)).items()}


def _run_val(txns, base="USD"):
    return {iid: compute_fifo(grp) for iid, grp in _by_instr(resolve_mergers(txns, base)).items()}


ACCT = 1                     # every _txn lives in account 1 (both instruments A and B)
AVG = {ACCT: "average"}      # §4.4: that account is average-cost


# (1) Cost preserved: 100 sh @ $10 ($1000) merged at R=2 → B gets 200 sh @ $5, cost still $1000.
def test_merger_preserves_total_cost():
    txns = [_txn(TxnType.BUY, A, "2023-01-01", 100, 10),
            _txn(TxnType.MERGER, A, "2024-01-01", 0, 2, target=B)]
    tax = _run_tax(txns)
    assert tax.get(A, ([], []))[1] == []                       # A terminated — no open lots
    b_lots = tax[B][1]
    assert sum(lot.quantity for lot in b_lots) == Decimal("200")            # ×2
    assert b_lots[0].unit_cost == Decimal("5")                             # 10 ÷ 2
    assert sum(lot.quantity * lot.unit_cost for lot in b_lots) == Decimal("1000")  # cost preserved


# (2) Holding period carries (R3): A bought 2y before the merger → a B sale is long-term on
#     the ORIGINAL A date, not the merger date.
def test_merger_carries_holding_period():
    txns = [_txn(TxnType.BUY, A, "2022-01-01", 100, 10),
            _txn(TxnType.MERGER, A, "2024-01-01", 0, 1, target=B),
            _txn(TxnType.SELL, B, "2024-02-01", 50, 20)]
    (events, _lots) = _run_tax(txns)[B]
    assert len(events) == 1
    assert events[0].acquired_ts == datetime(2022, 1, 1)       # original A date, not 2024 merger
    assert events[0].holding_days > 365                        # long-term


# (3) Zero gain at merger (R2): the merger emits no realised event.
def test_merger_emits_no_realised_event():
    txns = [_txn(TxnType.BUY, A, "2023-01-01", 100, 10),
            _txn(TxnType.MERGER, A, "2024-01-01", 0, 2, target=B)]
    tax = _run_tax(txns)
    all_events = [e for (events, _lots) in tax.values() for e in events]
    assert all_events == []                                    # nothing realised by the merger
    assert tax[B][1] and tax[B][1][0].quantity == Decimal("200")  # but the lot did carry into B


# (4) acq_fx carries (R7): a later B sale's cost leg uses the ORIGINAL A acquisition rate.
def test_merger_carries_acquisition_fx():
    txns = [_txn(TxnType.BUY, A, "2023-01-01", 100, 10, fx="1.30", fx_base="SGD", ccy="EUR"),
            _txn(TxnType.MERGER, A, "2024-01-01", 0, 1, target=B),
            _txn(TxnType.SELL, B, "2024-02-01", 50, 20, fx="1.40", fx_base="SGD", ccy="EUR")]
    (events, _lots) = _run_tax(txns, base="SGD")[B]
    assert events[0].cost_fx == Decimal("1.30")               # original A acquisition rate
    assert events[0].proceeds_fx == Decimal("1.40")           # the B sell rate


# (5) FIFO order on B (R1): multiple A-lots of different ages → a partial B sale consumes
#     the oldest carried lot first.
def test_merger_fifo_consumes_oldest_carried_lot_first():
    txns = [_txn(TxnType.BUY, A, "2020-01-01", 50, 10),        # oldest
            _txn(TxnType.BUY, A, "2023-01-01", 50, 30),        # newer
            _txn(TxnType.MERGER, A, "2024-01-01", 0, 1, target=B),
            _txn(TxnType.SELL, B, "2024-02-01", 50, 40)]
    (events, lots) = _run_tax(txns)[B]
    assert len(events) == 1
    assert events[0].acquired_ts == datetime(2020, 1, 1)      # oldest first
    assert events[0].cost == Decimal("500")                   # 50 @ 10 (the 2020 lot)
    assert events[0].gain == Decimal("1500")                  # 50×40 − 500
    assert len(lots) == 1 and lots[0].acquired_ts == datetime(2023, 1, 1)  # 2023 lot remains


# (6) Both engines agree (R5): identical realised gains and open lots for compute_fifo & fifo_report.
def test_both_engines_agree_on_merger():
    txns = [_txn(TxnType.BUY, A, "2020-01-01", 50, 10),
            _txn(TxnType.BUY, A, "2023-01-01", 50, 30),
            _txn(TxnType.MERGER, A, "2024-01-01", 0, 2, target=B),
            _txn(TxnType.SELL, B, "2024-02-01", 60, 25)]
    tax, val = _run_tax(txns), _run_val(txns)
    tax_events, tax_lots = tax[B]
    val_b = val[B]
    assert val_b.realised_pl == sum(e.gain for e in tax_events)                      # realised agree
    assert val_b.quantity == sum(lot.quantity for lot in tax_lots)                   # open qty agree
    assert val_b.cost_basis == sum(lot.quantity * lot.unit_cost for lot in tax_lots)  # open cost agree
    # Concrete: sell 60 of 200 post-merger → consume 60 @ 5 (2020), realised 60×25−300 = 1200.
    assert val_b.realised_pl == Decimal("1200")
    assert val_b.quantity == Decimal("140") and val_b.cost_basis == Decimal("1700")


# ── §4.4 Unit C: method-aware merger extraction ────────────────────────────────────────────
# resolve_mergers extracts the absorbed account's position under its OWN cost-basis method:
# a FIFO source carries per-lot (unchanged); an average source carries ONE pooled lot.


# (7) FIFO source unchanged (pure-superset): asking for the account's fifo method explicitly
#     produces a byte-identical resolved stream to the default (no methods) — §4.3 behaviour.
def test_fifo_source_merger_is_byte_identical():
    txns = [_txn(TxnType.BUY, A, "2020-01-01", 50, 10),
            _txn(TxnType.BUY, A, "2023-01-01", 50, 30, fx="1.30", fx_base="USD"),
            _txn(TxnType.MERGER, A, "2024-01-01", 0, 2, target=B),
            _txn(TxnType.SELL, B, "2024-02-01", 60, 25)]
    default = resolve_mergers(txns, "USD")                 # §4.3, method unspecified
    explicit = resolve_mergers(txns, "USD", {ACCT: "fifo"})  # §4.4, explicitly FIFO
    assert explicit == default                             # SimpleNamespace __dict__ equality — identical


# (8) Average source carries ONE pooled lot: A pools 100@10 + 100@20 → 200 @ avg $15 ($3000);
#     the merger (R=2) carries a SINGLE lot into B — total cost preserved, oldest date, no FX.
def test_average_source_merger_carries_single_pooled_lot():
    txns = [_txn(TxnType.BUY, A, "2020-01-01", 100, 10, fx="1.30", fx_base="USD"),
            _txn(TxnType.BUY, A, "2024-01-01", 100, 20, fx="1.35", fx_base="USD"),
            _txn(TxnType.MERGER, A, "2024-06-01", 0, 2, target=B)]
    resolved = resolve_mergers(txns, "USD", AVG)
    (_events, b_lots) = fifo_report(_by_instr(resolved)[B], "USD")
    assert len(b_lots) == 1                                # ONE pooled lot, not two per-lot carries
    lot = b_lots[0]
    assert lot.quantity == Decimal("400")                 # 200 × 2
    assert lot.unit_cost == Decimal("7.5")                # avg $15 ÷ 2
    assert lot.quantity * lot.unit_cost == Decimal("3000")   # A's total cost preserved
    assert lot.acquired_ts == datetime(2020, 1, 1)        # Decision B: oldest open lot's date
    assert lot.acq_fx is None                             # Decision A: no fabricated per-lot FX
    # Contrast: a FIFO source would carry TWO dated lots for the same portfolio.
    fifo_lots = fifo_report(_by_instr(resolve_mergers(txns, "USD", {ACCT: "fifo"}))[B], "USD")[1]
    assert len(fifo_lots) == 2


# (9) Both engines agree on the average-source merger (R5): fed the SAME resolved stream,
#     fifo_report and compute_fifo realise the same gain and hold the same open position.
def test_both_engines_agree_on_average_source_merger():
    txns = [_txn(TxnType.BUY, A, "2020-01-01", 100, 10),
            _txn(TxnType.BUY, A, "2024-01-01", 100, 20),      # pool 200 @ avg $15 ($3000)
            _txn(TxnType.MERGER, A, "2024-06-01", 0, 2, target=B),
            _txn(TxnType.SELL, B, "2024-07-01", 100, 30)]     # sell 100 of the carried 400 @ $7.5
    resolved = resolve_mergers(txns, "USD", AVG)              # resolve ONCE → both engines share it
    grp_b = _by_instr(resolved)[B]
    (tax_events, tax_lots) = fifo_report(grp_b, "USD")
    val_b = compute_fifo(grp_b)
    assert val_b.realised_pl == sum(e.gain for e in tax_events)                        # realised agree
    assert val_b.quantity == sum(lot.quantity for lot in tax_lots)                     # open qty agree
    assert val_b.cost_basis == sum(lot.quantity * lot.unit_cost for lot in tax_lots)   # open cost agree
    # Concrete: 100 @ $7.5 = cost $750, realised 100×30 − 750 = 2250; 300 @ $7.5 = $2250 remain.
    assert val_b.realised_pl == Decimal("2250")
    assert val_b.quantity == Decimal("300") and val_b.cost_basis == Decimal("2250")
