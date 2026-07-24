# SPDX-License-Identifier: AGPL-3.0-or-later
"""R-63 F-E (ledger I-12, owner ruling R8 2026-07-24) — orphan-duplicate cleanup.

The diagnosis (plan §F-E): a *holdings/transactions* purge is a SOFT-DELETE, so a pre-existing
duplicate INSTRUMENT pair (the legacy id-22/id-23 twins the dupe-tolerant guard KEPT) survives.
Re-adding the ticker `resolve_or_create_instrument`'s `.first()` LINKS one twin and orphans the
other (0 active holdings, 0 active transactions). The `duplicate_instruments` counter was blind to
orphan status, and the banner's "Resolve on Holdings" path was a DEAD-END for an orphan (Holdings
derives from transactions, so an orphan has no Holdings row to act on).

R8 = make the banner's promise TRUE (option 2): the orphan is removable via a working, guided action
on the surface where the finding lives. This reproduces the diagnosis shape through the REAL path,
then proves the cleanup clears it — and the refusal path is BLINDNESS-PINNED (a guard that stopped
checking would delete a live instrument and fail these tests loudly).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select, text

from app.models import (
    Account,
    Holding,
    Instrument,
    InstrumentIdentifier,
    Quote,
    Transaction,
    TxnType,
    Watchlist,
    WatchlistItem,
)
from app.services.identity import (
    OrphanRemovalError,
    duplicate_instruments,
    remove_orphan_instrument,
)

GUARD_INDEX = "uq_instr_identity_ci"


async def _legacy_pair(session):
    """The exact live shape: two (TSLA, NULL) rows — creatable only by dropping the shipped guard
    (they PRE-DATE it, which is the whole point). Returns (id_low, id_high)."""
    await session.execute(text(f"DROP INDEX IF EXISTS {GUARD_INDEX}"))
    a = Instrument(symbol="TSLA", exchange=None, name="Tesla", currency="USD")
    b = Instrument(symbol="TSLA", exchange=None, name="Tesla (dup)", currency="USD")
    session.add_all([a, b])
    await session.flush()
    lo, hi = sorted([a.id, b.id])
    return lo, hi


async def _account(session):
    acc = Account(name="Broker", currency="USD")
    session.add(acc)
    await session.flush()
    return acc


async def _link_active(session, acc_id, iid):
    """Give an instrument an ACTIVE holding + transaction (the live twin after re-add)."""
    session.add(Holding(account_id=acc_id, instrument_id=iid, asset_class="equity",
                        quantity=Decimal("10"), avg_cost=Decimal("100"), currency="USD"))
    session.add(Transaction(account_id=acc_id, instrument_id=iid, type=TxnType.BUY,
                           ts=datetime(2024, 1, 1, tzinfo=UTC), quantity=Decimal("10"),
                           price=Decimal("100"), currency="USD"))
    await session.flush()


async def _count_instruments(session, symbol="TSLA"):
    return (await session.execute(
        text("SELECT count(*) FROM instruments WHERE upper(symbol)=:s"), {"s": symbol})).scalar()


# ------------------------------------------------------------------ (b): the counter sees orphans

async def test_duplicate_instruments_surfaces_orphan_status(session):
    """The counter is no longer blind to orphan status: the linked twin reads orphan=False, the
    unreferenced twin orphan=True, and the group carries an orphan_count."""
    lo, hi = await _legacy_pair(session)
    acc = await _account(session)
    await _link_active(session, acc.id, lo)  # lo = the live twin; hi = the orphan

    dups = await duplicate_instruments(session)
    assert len(dups) == 1
    group = dups[0]
    assert group["symbol"] == "TSLA" and group["instrument_count"] == 2
    assert group["orphan_count"] == 1
    by_id = {i["id"]: i for i in group["instruments"]}
    assert by_id[lo]["orphan"] is False and by_id[lo]["active_holdings"] == 1
    assert by_id[hi]["orphan"] is True and by_id[hi]["active_holdings"] == 0
    assert by_id[hi]["active_transactions"] == 0


# --------------------------------------------------------------- R8: the cleanup makes it true

async def test_removing_the_orphan_clears_the_count_and_keeps_the_live_twin(session):
    """The RED→GREEN of the finding: pair survives purge → re-add links one → orphan → cleanup
    removes the orphan, the count clears, and the LIVE twin + its holding survive untouched."""
    lo, hi = await _legacy_pair(session)
    acc = await _account(session)
    await _link_active(session, acc.id, lo)

    out = await remove_orphan_instrument(session, hi)
    assert out["removed"] == hi

    # The orphan is gone; the live twin survives with its holding; the banner would no longer fire.
    assert await _count_instruments(session) == 1
    assert (await session.get(Instrument, hi)) is None
    assert (await session.get(Instrument, lo)) is not None
    live_holdings = (await session.execute(
        select(func.count()).select_from(Holding).where(
            Holding.instrument_id == lo, Holding.deleted_at.is_(None)))).scalar()
    assert live_holdings == 1
    assert await duplicate_instruments(session) == []


# --------------------------------------------------------------- BLINDNESS PIN: the refusal path

async def test_refuses_to_remove_a_non_orphan(session):
    """SAFETY (blindness pin): an instrument with an active holding/transaction is NOT removable —
    the guard refuses and deletes nothing. A guard that stopped checking would delete a live
    instrument here and fail loudly."""
    lo, hi = await _legacy_pair(session)
    acc = await _account(session)
    await _link_active(session, acc.id, lo)

    with pytest.raises(OrphanRemovalError):
        await remove_orphan_instrument(session, lo)  # lo is in use — must refuse
    assert await _count_instruments(session) == 2  # nothing deleted


async def test_refuses_to_remove_a_lone_non_duplicate(session):
    """SAFETY (blindness pin): a lone instrument that is NOT part of a duplicate group — e.g. a
    watchlist-only instrument with zero holdings — must never be removable through this path, or the
    cleanup would delete legitimate zero-holding instruments. It is refused even though it is
    'orphan-shaped' (0 holdings)."""
    solo = Instrument(symbol="NVDA", exchange=None, name="Nvidia", currency="USD")
    session.add(solo)
    await session.flush()

    with pytest.raises(OrphanRemovalError):
        await remove_orphan_instrument(session, solo.id)
    assert (await session.get(Instrument, solo.id)) is not None


async def test_removal_purges_dangling_dependents(session):
    """The removal takes the orphan INSTRUMENT row only, but purges rows that would dangle at its id
    — a quote, an identifier, and an already-soft-deleted transaction — so nothing points at a
    deleted instrument afterwards. The live twin's data is untouched."""
    lo, hi = await _legacy_pair(session)
    acc = await _account(session)
    await _link_active(session, acc.id, lo)
    # dangling dependents on the orphan: a cached quote, an identifier, a soft-deleted txn.
    session.add(Quote(instrument_id=hi, price=Decimal("100"), previous_close=Decimal("100"),
                     currency="USD", source="mock", entitlement="delayed",
                     received_at=datetime.now(UTC)))
    session.add(InstrumentIdentifier(instrument_id=hi, id_type="isin", value="US88160R1014"))
    session.add(Transaction(account_id=acc.id, instrument_id=hi, type=TxnType.BUY,
                           ts=datetime(2023, 1, 1, tzinfo=UTC), quantity=Decimal("1"),
                           price=Decimal("1"), currency="USD",
                           deleted_at=datetime.now(UTC)))  # soft-deleted → orphan is still orphan
    await session.flush()

    await remove_orphan_instrument(session, hi)

    for tbl in ("quotes", "instrument_identifiers", "transactions"):
        n = (await session.execute(
            text(f"SELECT count(*) FROM {tbl} WHERE instrument_id=:i"), {"i": hi})).scalar()
        assert n == 0, f"{tbl} still references the removed orphan"
    assert (await session.get(Instrument, lo)) is not None


async def test_watchlisted_orphan_is_repointed_not_dropped(session):
    """A duplicate IS the same logical instrument, so removing the orphan must NOT silently drop the
    user's watchlist entry — it is RE-POINTED to the surviving canonical twin (lossless cleanup)."""
    lo, hi = await _legacy_pair(session)
    acc = await _account(session)
    await _link_active(session, acc.id, lo)  # lo = live twin; hi = orphan, but watchlisted
    wl = Watchlist(name="Watch")
    session.add(wl)
    await session.flush()
    session.add(WatchlistItem(watchlist_id=wl.id, instrument_id=hi))
    await session.flush()

    await remove_orphan_instrument(session, hi)

    # The watchlist entry survives, now pointing at the live twin — not deleted, not dangling.
    items = (await session.execute(
        select(WatchlistItem).where(WatchlistItem.watchlist_id == wl.id))).scalars().all()
    assert len(items) == 1 and items[0].instrument_id == lo


# ------------------------------------------------------------------------ HTTP wiring + 409 path

async def test_endpoint_removes_orphan_and_refuses_non_orphan(app_client):
    """The HTTP surface: POST /system/instrument-duplicates/{id}/remove clears an orphan (200) and
    refuses a non-orphan (409). Seeded by dropping the guard on the app's own DB (a legacy pair)."""
    from app.db.base import get_sessionmaker

    async with get_sessionmaker()() as s:
        await s.execute(text(f"DROP INDEX IF EXISTS {GUARD_INDEX}"))
        a = Instrument(symbol="ZQZQ", exchange=None, name="Z", currency="USD")
        b = Instrument(symbol="ZQZQ", exchange=None, name="Z dup", currency="USD")
        s.add_all([a, b])
        await s.flush()
        lo, hi = sorted([a.id, b.id])
        acc = Account(name="B", currency="USD")
        s.add(acc)
        await s.flush()
        s.add(Holding(account_id=acc.id, instrument_id=lo, asset_class="equity",
                     quantity=Decimal("1"), avg_cost=Decimal("1"), currency="USD"))
        s.add(Transaction(account_id=acc.id, instrument_id=lo, type=TxnType.BUY,
                         ts=datetime(2024, 1, 1, tzinfo=UTC), quantity=Decimal("1"),
                         price=Decimal("1"), currency="USD"))
        await s.commit()

    listed = (await app_client.get("/api/v1/system/instrument-duplicates")).json()
    grp = next(g for g in listed["duplicates"] if g["symbol"] == "ZQZQ")
    assert grp["orphan_count"] == 1

    ok = await app_client.post(f"/api/v1/system/instrument-duplicates/{hi}/remove")
    assert ok.status_code == 200

    refuse = await app_client.post(f"/api/v1/system/instrument-duplicates/{lo}/remove")
    assert refuse.status_code == 409

    after = (await app_client.get("/api/v1/system/instrument-duplicates")).json()
    assert not any(g["symbol"] == "ZQZQ" for g in after["duplicates"])
