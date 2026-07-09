# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 3.5 Unit B — soft-deleted rows (deleted_at IS NOT NULL) are invisible to every
money computation, exactly as if they had been hard-deleted. Read-exclusion only; delete
behaviour is unchanged (Unit C adds the endpoints).

Covers the sanctioned filter sites R1–R12 and the deliberately-unfiltered R13 (rebuild
preserves soft-deleted manual holdings so undo can restore them)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select

from app.models import Account, AssetClass, Holding, Instrument, Transaction, TxnType
from app.models import Quote as QuoteRow
from app.services.accounts import accounts_report
from app.services.analytics import key_stats, performance_series, time_weighted_return
from app.services.csv_import import _batch_already_imported
from app.services.portfolio import rebuild_holdings_from_transactions, value_portfolio
from app.services.statements import statements_report
from app.services.tax import realised_gains_report, tax_lots_report

UTC_ = UTC


def _txn(acc_id, instr_id, ttype, y, m, qty, px, fees="0", amount="0"):
    return Transaction(
        account_id=acc_id, instrument_id=instr_id, type=ttype,
        ts=datetime(y, m, 1, tzinfo=UTC_), quantity=Decimal(qty), price=Decimal(px),
        fees=Decimal(fees), taxes=Decimal("0"), amount=Decimal(amount), currency="USD",
    )


async def _seed(session):
    """One priced instrument with buy/buy/sell/dividend, plus a manual cash holding."""
    acc = Account(name="Broker", currency="USD")
    session.add(acc)
    await session.flush()
    aapl = Instrument(symbol="AAPL", currency="USD")
    session.add(aapl)
    await session.flush()
    session.add(QuoteRow(instrument_id=aapl.id, price=Decimal("300"), previous_close=Decimal("290"),
                         currency="USD", source="mock", entitlement="delayed",
                         received_at=datetime.now(UTC_)))
    buy1 = _txn(acc.id, aapl.id, TxnType.BUY, 2023, 1, "10", "100", "1", "-1001")
    buy2 = _txn(acc.id, aapl.id, TxnType.BUY, 2023, 6, "10", "200", "1", "-2001")
    sell = _txn(acc.id, aapl.id, TxnType.SELL, 2024, 1, "5", "250", "1", "1249")
    div = _txn(acc.id, aapl.id, TxnType.DIVIDEND, 2024, 2, "0", "0", "0", "50")
    session.add_all([buy1, buy2, sell, div])
    cash = Holding(account_id=acc.id, label="Cash", asset_class=AssetClass.CASH,
                   quantity=Decimal("1"), avg_cost=Decimal("10000"),
                   manual_value=Decimal("10000"), currency="USD")
    session.add(cash)
    await session.flush()
    await rebuild_holdings_from_transactions(session)
    return {"acc": acc, "aapl": aapl, "sell": sell, "div": div, "cash": cash}


async def _money_snapshot(session) -> dict:
    """Every money output that must ignore soft-deleted rows (R1/R3/R4/R6)."""
    val = await value_portfolio(session, "USD")
    rg = await realised_gains_report(session)
    lots = await tax_lots_report(session)
    ks = {m["label"]: m["value"] for m in (await key_stats(session, "USD"))["metrics"]}
    st = await statements_report(session)
    return {
        "net_worth": val.total_value,                                        # R1
        "realised": rg["base_realised_total_current_fx"],                    # R3
        "lot_qty": sum(x["quantity"] for x in lots["lots"]),                 # R3
        "ks_realised": ks["Realised P/L"],                                   # R4
        "ks_income": ks["Income (div/int)"],                                 # R4
        "st_fees": st["fees"]["total"],                                      # R6
        "st_income": st["income"]["total"],                                  # R6
    }


async def test_soft_delete_excluded_from_money_equals_hard_delete(session):
    """Core proof: soft-deleting a holding AND transactions changes every money figure
    exactly as a hard delete would — the soft-deleted rows contribute nothing."""
    s = await _seed(session)
    full = await _money_snapshot(session)

    # Full portfolio is non-trivial (guards against a vacuous "0 == 0" pass).
    assert full["realised"] != 0.0
    assert full["lot_qty"] == Decimal("15")            # 20 bought − 5 sold
    assert full["net_worth"] > Decimal("10000")        # includes the 10k cash holding

    # SOFT-delete the sell, the dividend, and the manual cash holding (set deleted_at),
    # then rebuild so derived holdings recompute from the filtered ledger.
    now = datetime.now(UTC_)
    s["sell"].deleted_at = now
    s["div"].deleted_at = now
    s["cash"].deleted_at = now
    await session.flush()
    await rebuild_holdings_from_transactions(session)
    soft = await _money_snapshot(session)

    # Every computation reflects the deletion.
    assert soft["realised"] == 0.0                     # only sell removed → no realised gain
    assert soft["lot_qty"] == Decimal("20")            # no sell → all 20 shares open
    assert soft["net_worth"] < full["net_worth"]       # cash gone + qty changed
    for k in ("realised", "lot_qty", "ks_realised", "ks_income", "st_fees", "st_income", "net_worth"):
        assert soft[k] != full[k], f"{k} did not change — soft-deleted row leaked into it"

    # HARD-delete the very same rows and rebuild: outputs must be byte-identical to soft.
    await session.delete(s["sell"])
    await session.delete(s["div"])
    await session.delete(s["cash"])
    await session.flush()
    await rebuild_holdings_from_transactions(session)
    hard = await _money_snapshot(session)

    assert soft == hard, f"soft-delete diverged from hard-delete: {soft} != {hard}"


async def test_soft_delete_excluded_from_performance_series_and_twr(session):
    """R5 (time-weighted return) and R7 (net-worth history series) also exclude
    soft-deleted rows, matching a hard delete."""
    from app.providers.market import reset_provider

    reset_provider()  # deterministic mock provider (synthesises offline candle history)
    s = await _seed(session)

    async def perf_snap():
        series = (await performance_series(session, "USD", 365, "SPY", include_manual=True))["series"]
        twr = await time_weighted_return(session, "USD")
        return [p["value"] for p in series], twr

    full_series, full_twr = await perf_snap()
    assert len(full_series) > 2                          # meaningful series (not a vacuous pass)

    now = datetime.now(UTC_)
    s["sell"].deleted_at = now
    s["cash"].deleted_at = now
    await session.flush()
    await rebuild_holdings_from_transactions(session)
    soft_series, soft_twr = await perf_snap()

    await session.delete(s["sell"])
    await session.delete(s["cash"])
    await session.flush()
    await rebuild_holdings_from_transactions(session)
    hard_series, hard_twr = await perf_snap()

    # The soft-deleted manual holding drops out of the net-worth series...
    assert sum(soft_series) < sum(full_series)          # R7: cash no longer in the series
    # ...and soft-delete is indistinguishable from hard-delete for both R5 and R7.
    assert soft_series == hard_series
    assert soft_twr == hard_twr


async def test_guard_readers_exclude_soft_deleted(session):
    """Guard for the display / dedup / targeting readers (R8–R12): each excludes
    soft-deleted rows. A future query that forgets the filter fails here."""
    from app.api.v1.routes.dashboard import _holding_currencies
    from app.api.v1.routes.portfolio import list_manual_holdings, list_transactions

    s = await _seed(session)
    # A second manual holding in EUR, to exercise the currency reader (R12).
    eur = Holding(account_id=s["acc"].id, label="Euro cash", asset_class=AssetClass.CASH,
                  quantity=Decimal("1"), avg_cost=Decimal("500"),
                  manual_value=Decimal("500"), currency="EUR")
    session.add(eur)
    await session.flush()

    # Baselines (everything visible).
    assert len((await list_manual_holdings(session=session))["holdings"]) == 2          # R8
    txn_ids_full = {t["id"] for t in (await list_transactions(session=session))["transactions"]}
    assert len(txn_ids_full) == 4                                                        # R9
    assert await _batch_already_imported(session, "BATCH-X") is False                    # R10 (setup)
    s["sell"].import_batch = "BATCH-X"
    await session.flush()
    assert await _batch_already_imported(session, "BATCH-X") is True                     # R10
    accs = {a["id"]: a for a in (await accounts_report(session))["accounts"]}
    assert accs[s["acc"].id]["last_activity"] is not None                                # R11
    assert "EUR" in await _holding_currencies(session)                                   # R12

    # Soft-delete one of each and re-read.
    now = datetime.now(UTC_)
    s["cash"].deleted_at = now
    eur.deleted_at = now
    s["sell"].deleted_at = now
    s["div"].deleted_at = now
    for t in (await session.execute(select(Transaction))).scalars().all():
        if t.instrument_id is not None:
            t.deleted_at = now  # soft-delete ALL transactions to zero out last-activity
    await session.flush()

    manual = (await list_manual_holdings(session=session))["holdings"]                   # R8
    assert manual == [], "soft-deleted manual holdings still listed in the editor"        # both were soft-deleted
    txn_ids_soft = {t["id"] for t in (await list_transactions(session=session))["transactions"]}
    assert s["sell"].id not in txn_ids_soft and len(txn_ids_soft) == 0                   # R9
    assert await _batch_already_imported(session, "BATCH-X") is False                    # R10: re-import unblocked
    accs2 = {a["id"]: a for a in (await accounts_report(session))["accounts"]}
    assert accs2.get(s["acc"].id, {}).get("last_activity") is None                       # R11
    assert "EUR" not in await _holding_currencies(session)                               # R12


async def test_soft_deleted_transaction_can_be_reimported(session):
    """R10 end-to-end: after soft-deleting an imported transaction, re-importing the
    identical CSV row SUCCEEDS. Both dedup guards (batch-hash AND row fingerprint) ignore
    soft-deleted rows, so undo→re-import is no longer blocked."""
    from app.services.csv_import import import_transactions_csv

    csv_bytes = (
        b"date,symbol,type,quantity,price,fees,currency,note\n"
        b"2024-01-01,AAPL,buy,10,100,1,USD,first\n"
    )
    # First import lands the row; re-importing the identical file is correctly deduplicated.
    assert (await import_transactions_csv(session, csv_bytes))["imported"] == 1
    assert (await import_transactions_csv(session, csv_bytes))["imported"] == 0  # dedup is active

    # Soft-delete the imported transaction.
    txn = (await session.execute(select(Transaction))).scalars().one()
    txn.deleted_at = datetime.now(UTC_)
    await session.flush()

    # The identical file now re-imports successfully — neither the batch guard nor the
    # fingerprint set sees the soft-deleted row anymore.
    assert (await import_transactions_csv(session, csv_bytes))["imported"] == 1
    live = (await session.execute(
        select(Transaction).where(Transaction.deleted_at.is_(None))
    )).scalars().all()
    assert len(live) == 1  # exactly one live copy (plus the soft-deleted original)


async def test_r13_manual_holding_preserved_through_rebuild_then_restored(session):
    """R13: rebuild must NOT hard-delete a soft-deleted manual holding (it carries
    manual_value), so undo can restore it — but valuation still excludes it while
    soft-deleted, and includes it again once restored."""
    s = await _seed(session)
    cash = s["cash"]
    assert (await value_portfolio(session, "USD")).total_value > Decimal("10000")  # cash counted

    # Soft-delete the manual holding, then rebuild (the rebuild path R13 is unfiltered).
    cash.deleted_at = datetime.now(UTC_)
    await session.flush()
    await rebuild_holdings_from_transactions(session)

    # The row still exists (rebuild preserved it because manual_value is set)...
    row = await session.get(Holding, cash.id)
    assert row is not None and row.manual_value == Decimal("10000") and row.deleted_at is not None
    # ...but it contributes nothing to valuation while soft-deleted.
    nw_deleted = (await value_portfolio(session, "USD")).total_value

    # Restore (undo) and rebuild: it is valued again.
    row.deleted_at = None
    await session.flush()
    await rebuild_holdings_from_transactions(session)
    nw_restored = (await value_portfolio(session, "USD")).total_value

    assert nw_restored - nw_deleted == Decimal("10000.00")  # exactly the cash holding, back
