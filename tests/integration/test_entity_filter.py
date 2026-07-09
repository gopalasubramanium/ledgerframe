# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 4.1 Unit B — the optional entity filter.

Two proofs: (1) NUMBER-NEUTRAL — with a single default entity owning everything (the
post-migration state), filtering by it is identical to not filtering (one entity =
identity); (2) PARTITION — with two entities, filtering by each partitions the portfolio
and the parts reconcile to the unfiltered whole, proving the filter actually restricts.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from app.models import Account, AssetClass, Entity, Holding, Instrument, Transaction, TxnType
from app.models import Quote as QuoteRow
from app.services.accounts import accounts_report
from app.services.analytics import key_stats
from app.services.portfolio import rebuild_holdings_from_transactions, value_portfolio
from app.services.statements import statements_report
from app.services.tax import realised_gains_report

UTC_ = UTC


async def _instrument(session, symbol="AAPL", price="300"):
    instr = Instrument(symbol=symbol, currency="USD")
    session.add(instr)
    await session.flush()
    session.add(QuoteRow(instrument_id=instr.id, price=Decimal(price), previous_close=Decimal(price),
                         currency="USD", source="mock", entitlement="delayed", received_at=datetime.now(UTC_)))
    return instr


def _txn(acc_id, instr_id, ttype, y, m, qty, px, amount="0"):
    return Transaction(account_id=acc_id, instrument_id=instr_id, type=ttype,
                       ts=datetime(y, m, 1, tzinfo=UTC_), quantity=Decimal(qty), price=Decimal(px),
                       fees=Decimal("0"), taxes=Decimal("0"), amount=Decimal(amount), currency="USD")


def _cash(acc_id, value):
    return Holding(account_id=acc_id, label="Cash", asset_class=AssetClass.CASH,
                   quantity=Decimal("1"), avg_cost=Decimal(value), manual_value=Decimal(value), currency="USD")


async def test_default_entity_is_identity(session):
    """One default entity owns everything → unfiltered == filtered-by-default == expected."""
    ent = Entity(name="Household", kind="self")
    session.add(ent)
    await session.flush()
    acc = Account(name="Broker", currency="USD", entity_id=ent.id)
    session.add(acc)
    await session.flush()
    aapl = await _instrument(session)
    session.add_all([
        _txn(acc.id, aapl.id, TxnType.BUY, 2023, 1, "10", "100", "-1000"),
        _txn(acc.id, aapl.id, TxnType.SELL, 2024, 1, "5", "250", "1250"),
        _txn(acc.id, aapl.id, TxnType.DIVIDEND, 2024, 2, "0", "0", "50"),
        _cash(acc.id, "10000"),
    ])
    await session.flush()
    await rebuild_holdings_from_transactions(session)

    async def figures(eid):
        val = await value_portfolio(session, "USD", entity_id=eid)
        rg = await realised_gains_report(session, entity_id=eid)
        ks = {m["label"]: m["value"] for m in (await key_stats(session, "USD", entity_id=eid))["metrics"]}
        st = await statements_report(session, entity_id=eid)
        return {
            "net_worth": val.total_value,
            "realised": rg["base_realised_total_current_fx"],
            "ks_realised": ks["Realised P/L"],
            "st_income": st["income"]["total"],
        }

    unfiltered = await figures(None)
    filtered = await figures(ent.id)

    # Non-trivial (guards against a vacuous pass), and byte-identical either way.
    assert unfiltered["net_worth"] > Decimal("10000") and unfiltered["realised"] != 0.0
    assert unfiltered == filtered


async def test_two_entities_partition_and_reconcile(session):
    """Two entities partition the portfolio; each part is a strict subset and the parts
    sum back to the unfiltered whole — proving the filter restricts, not no-ops."""
    a = Entity(name="Self", kind="self")
    b = Entity(name="Spouse", kind="spouse")
    session.add_all([a, b])
    await session.flush()
    acc_a = Account(name="A-Broker", currency="USD", entity_id=a.id)
    acc_b = Account(name="B-Broker", currency="USD", entity_id=b.id)
    session.add_all([acc_a, acc_b])
    await session.flush()
    aapl = await _instrument(session)
    session.add_all([
        # Entity A: a realised sale + cash.
        _txn(acc_a.id, aapl.id, TxnType.BUY, 2023, 1, "10", "100", "-1000"),
        _txn(acc_a.id, aapl.id, TxnType.SELL, 2024, 1, "5", "250", "1250"),
        _cash(acc_a.id, "10000"),
        # Entity B: a buy-only position (no realised) + cash.
        _txn(acc_b.id, aapl.id, TxnType.BUY, 2023, 3, "20", "50", "-1000"),
        _cash(acc_b.id, "5000"),
    ])
    await session.flush()
    await rebuild_holdings_from_transactions(session)

    nw_all = (await value_portfolio(session, "USD")).total_value
    nw_a = (await value_portfolio(session, "USD", entity_id=a.id)).total_value
    nw_b = (await value_portfolio(session, "USD", entity_id=b.id)).total_value
    rg_all = (await realised_gains_report(session))["base_realised_total_current_fx"]
    rg_a = (await realised_gains_report(session, entity_id=a.id))["base_realised_total_current_fx"]
    rg_b = (await realised_gains_report(session, entity_id=b.id))["base_realised_total_current_fx"]

    # The filter genuinely restricts (each part is a strict subset of the whole)...
    assert nw_a < nw_all and nw_b < nw_all and nw_a > 0 and nw_b > 0
    # ...and the parts reconcile exactly to the unfiltered whole.
    assert nw_a + nw_b == nw_all
    # Realised gains partition: only A sold, so A carries all of it, B none.
    assert rg_a != 0.0 and rg_b == 0.0 and rg_a == rg_all

    # accounts_report is scoped too: each entity sees only its own account.
    accs_a = {x["name"] for x in (await accounts_report(session, entity_id=a.id))["accounts"]}
    accs_b = {x["name"] for x in (await accounts_report(session, entity_id=b.id))["accounts"]}
    assert accs_a == {"A-Broker"} and accs_b == {"B-Broker"}
