# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 3.5 Unit C — soft-delete + restore endpoints for transactions and manual holdings.

DELETE now sets deleted_at (the row survives, excluded from all money computations by Unit B);
POST .../restore clears it. These are the primitives; the 10s undo window is a client concern
(Unit E) and permanent purge is PIN-gated (Unit D)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.api.v1.routes.portfolio import (
    delete_manual_holding,
    delete_transaction,
    restore_manual_holding,
    restore_transaction,
)
from app.models import Account, AssetClass, AuditEvent, Holding, Instrument, Transaction, TxnType
from app.models import Quote as QuoteRow
from app.services.portfolio import rebuild_holdings_from_transactions, value_portfolio


async def _audit_actions(session) -> list[str]:
    return [e.action for e in (await session.execute(select(AuditEvent))).scalars().all()]


async def _seed_manual_cash(session) -> Holding:
    acc = Account(name="Broker", currency="USD")
    session.add(acc)
    await session.flush()
    cash = Holding(account_id=acc.id, label="Cash", asset_class=AssetClass.CASH,
                   quantity=Decimal("1"), avg_cost=Decimal("10000"),
                   manual_value=Decimal("10000"), currency="USD")
    session.add(cash)
    await session.flush()
    return cash


async def _seed_priced_position(session) -> tuple[Transaction, Instrument]:
    acc = Account(name="Broker", currency="USD")
    session.add(acc)
    await session.flush()
    aapl = Instrument(symbol="AAPL", currency="USD")
    session.add(aapl)
    await session.flush()
    session.add(QuoteRow(instrument_id=aapl.id, price=Decimal("300"), previous_close=Decimal("290"),
                         currency="USD", source="mock", entitlement="delayed", received_at=datetime.now(UTC)))
    buy = Transaction(account_id=acc.id, instrument_id=aapl.id, type=TxnType.BUY,
                      ts=datetime(2023, 1, 1, tzinfo=UTC), quantity=Decimal("10"), price=Decimal("100"),
                      fees=Decimal("0"), taxes=Decimal("0"), amount=Decimal("-1000"), currency="USD")
    session.add(buy)
    await session.flush()
    await rebuild_holdings_from_transactions(session)
    return buy, aapl


# --------------------------------------------------------------------------- #
# (1) DELETE soft-deletes: row survives with deleted_at set, excluded from value,
#     AuditEvent written. (2) restore clears deleted_at and the row is valued again.
# --------------------------------------------------------------------------- #
async def test_delete_manual_holding_soft_deletes_then_restore_returns_it(session):
    cash = await _seed_manual_cash(session)
    assert (await value_portfolio(session, "USD")).total_value == Decimal("10000.00")

    # DELETE → soft-delete.
    assert await delete_manual_holding(cash.id, session=session) == {"ok": True}
    row = await session.get(Holding, cash.id)
    assert row is not None and row.deleted_at is not None            # still in the DB, marked deleted
    assert row.manual_value == Decimal("10000")                      # data preserved
    assert (await value_portfolio(session, "USD")).total_value == Decimal("0.00")  # excluded from value
    assert "delete_manual_holding" in await _audit_actions(session)  # audit trail written

    # RESTORE → a specific net-worth figure returns.
    assert await restore_manual_holding(cash.id, session=session) == {"ok": True}
    assert (await session.get(Holding, cash.id)).deleted_at is None
    assert (await value_portfolio(session, "USD")).total_value == Decimal("10000.00")
    assert "restore_manual_holding" in await _audit_actions(session)


# --------------------------------------------------------------------------- #
# (4) txn delete→restore round-trip leaves derived holdings correct (rebuild ran both ways).
# --------------------------------------------------------------------------- #
async def test_delete_transaction_soft_deletes_and_restore_rebuilds_holdings(session):
    buy, _ = await _seed_priced_position(session)

    def aapl_qty(val):
        hits = [h for h in val.holdings if h.symbol == "AAPL"]
        return hits[0].quantity if hits else None

    assert aapl_qty(await value_portfolio(session, "USD")) == Decimal("10")  # derived position present

    # DELETE → soft-delete + rebuild (R2 filter excludes it, so the derived holding vanishes).
    res = await delete_transaction(buy.id, session=session)
    assert res["ok"] is True and "holdings_rebuilt" in res
    row = await session.get(Transaction, buy.id)
    assert row is not None and row.deleted_at is not None            # ledger row survives
    assert aapl_qty(await value_portfolio(session, "USD")) is None   # derived holding recomputed away
    assert "delete_transaction" in await _audit_actions(session)

    # RESTORE → rebuild brings the derived holding back exactly.
    res2 = await restore_transaction(buy.id, session=session)
    assert res2["ok"] is True and "holdings_rebuilt" in res2
    assert (await session.get(Transaction, buy.id)).deleted_at is None
    assert aapl_qty(await value_portfolio(session, "USD")) == Decimal("10")  # position restored
    assert "restore_transaction" in await _audit_actions(session)


# --------------------------------------------------------------------------- #
# (3) restore is 404 for a nonexistent id.
# --------------------------------------------------------------------------- #
async def test_restore_nonexistent_id_is_404(session):
    with pytest.raises(HTTPException) as ei:
        await restore_transaction(999999, session=session)
    assert ei.value.status_code == 404
    with pytest.raises(HTTPException) as ei:
        await restore_manual_holding(999999, session=session)
    assert ei.value.status_code == 404


async def test_restore_is_idempotent_on_a_live_row(session):
    """Restoring a row that is not soft-deleted is a harmless no-op (no error, stays live)."""
    cash = await _seed_manual_cash(session)
    assert await restore_manual_holding(cash.id, session=session) == {"ok": True}
    assert (await session.get(Holding, cash.id)).deleted_at is None
    assert (await value_portfolio(session, "USD")).total_value == Decimal("10000.00")
