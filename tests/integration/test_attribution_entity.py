# SPDX-License-Identifier: AGPL-3.0-or-later
"""§4.5 Unit A — return attribution, entity scoping (async, read-only).

Proves the async `attribution` reader partitions by ownership entity exactly like its siblings:
each entity's attribution covers only its own holdings; entity_id=None attributes the whole
portfolio. Values are deterministic (seeded quotes + manual-free rebuilt holdings); the pure
decomposition math is covered in tests/unit/test_attribution.py. Read-only: no money-path change.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from app.models import Account, Entity, Instrument, Transaction, TxnType
from app.models import Quote as QuoteRow
from app.services.analytics import attribution
from app.services.portfolio import rebuild_holdings_from_transactions


async def _instrument(session, symbol, price, sector):
    instr = Instrument(symbol=symbol, currency="USD", sector=sector)
    session.add(instr)
    await session.flush()
    session.add(QuoteRow(instrument_id=instr.id, price=Decimal(price), previous_close=Decimal(price),
                         currency="USD", source="mock", entitlement="delayed", received_at=datetime.now(UTC)))
    return instr


def _buy(acc_id, instr_id, qty, px):
    return Transaction(account_id=acc_id, instrument_id=instr_id, type=TxnType.BUY,
                       ts=datetime(2023, 1, 1, tzinfo=UTC), quantity=Decimal(qty), price=Decimal(px),
                       fees=Decimal("0"), taxes=Decimal("0"), amount=Decimal("0"), currency="USD")


async def test_attribution_partitions_by_entity(session):
    # Two entities, one account each. E1: AAA cost 1000 → value 3000 (unrealised +2000, Tech).
    #                                E2: BBB cost 800  → value 1000 (unrealised +200,  Energy).
    e1 = Entity(name="Alice", kind="self")
    e2 = Entity(name="Bob", kind="self")
    session.add_all([e1, e2])
    await session.flush()
    a1 = Account(name="A1", currency="USD", entity_id=e1.id)
    a2 = Account(name="A2", currency="USD", entity_id=e2.id)
    session.add_all([a1, a2])
    await session.flush()
    aaa = await _instrument(session, "AAA", "300", "Tech")
    bbb = await _instrument(session, "BBB", "50", "Energy")
    session.add_all([_buy(a1.id, aaa.id, "10", "100"),     # E1
                     _buy(a2.id, bbb.id, "20", "40")])      # E2
    await session.flush()
    await rebuild_holdings_from_transactions(session)

    whole = await attribution(session, "USD", 365, entity_id=None)
    r1 = await attribution(session, "USD", 365, entity_id=e1.id)
    r2 = await attribution(session, "USD", 365, entity_id=e2.id)

    # Whole portfolio sees both holdings; each entity sees only its own.
    assert {h["symbol"] for h in whole["holdings"]} == {"AAA", "BBB"}
    assert {h["symbol"] for h in r1["holdings"]} == {"AAA"}
    assert {h["symbol"] for h in r2["holdings"]} == {"BBB"}

    # E1 in isolation: cost 1000, unrealised +2000 → +200pp contribution, no income/realised.
    assert r1["holdings"][0]["contribution_pct"] == 200.0
    assert r1["headline_return_pct"] == 200.0 and r1["residual_pct"] == 0.0
    assert {r["key"] for r in r1["by_sector"]} == {"Tech"}

    # E2 in isolation: cost 800, unrealised +200 → +25pp.
    assert r2["holdings"][0]["contribution_pct"] == 25.0
    assert {r["key"] for r in r2["by_sector"]} == {"Energy"}

    # Reconciliation holds under every scope (the honesty invariant is scope-independent).
    for rep in (whole, r1, r2):
        s = sum(h["contribution_pct"] for h in rep["holdings"]) + rep["residual_pct"]
        assert round(s, 6) == round(rep["headline_return_pct"], 6)
