# SPDX-License-Identifier: AGPL-3.0-or-later
"""Instrument identity & taxonomy helpers (Phase 2).

Normalized identifiers (ISIN / FIGI / AMFI code / CoinGecko id / provider symbol)
live in ``instrument_identifiers`` so identity is keyed by (id_type, value), never a
bare ticker — a US/IN/SG symbol collision is impossible. Also provides sensible
taxonomy defaults so newly-created instruments are classified consistently with the
migration backfill.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import HIGH_CONFIDENCE_IDS, Instrument, InstrumentIdentifier


class DuplicateIdentifierError(ValueError):
    """A high-confidence identifier is already mapped to a different instrument."""


class OrphanRemovalError(ValueError):
    """A duplicate-instrument cleanup was refused: the row is either still in use (an active
    holding/transaction references it) or is NOT part of a duplicate group (so removing it would
    delete a legitimate lone instrument, e.g. a watchlist-only entry). R-63 F-E / I-12."""


# Sentinel so ``resolve_or_create_instrument`` can tell "caller omitted country → compute a
# default" from "caller passed country=None → leave it unknown" (§14dr-27b).
_UNSET: object = object()

# Recognised identifier namespaces.
ID_TYPES = (
    "isin", "cusip", "figi", "sedol", "amfi_code", "kite_token",
    "coingecko_id", "provider_symbol",
)


def classify_defaults(asset_class: str, *, is_manual_price: bool, currency: str) -> dict:
    """Sensible taxonomy defaults for a new instrument — mirrors the Phase 2 migration
    backfill so create_all-created rows and migrated rows agree."""
    ac = asset_class.value if hasattr(asset_class, "value") else str(asset_class)
    return {
        "asset_category": ac,
        "asset_subclass": ac,
        "pricing_currency": currency,
        "liquidity_profile": "manual" if is_manual_price else "listed",
        "valuation_method": "manual_valuation" if is_manual_price else "market_quote",
    }


async def resolve_or_create_instrument(
    session: AsyncSession,
    symbol: str,
    exchange: str | None = None,
    *,
    name: str | None = None,
    asset_class=None,
    currency: str | None = None,
    country: str | None = _UNSET,
    extra: dict | None = None,
) -> tuple[Instrument, bool]:
    """The ONE identity resolution for every instrument-create path (R-63 I-6, §9-i ADDENDUM).

    Two get-or-create paths used to key identity differently — ``market`` matched
    ``symbol.upper()`` while ``csv_import`` matched the bare (non-uppercased) symbol — so the
    same logical ticker resolved to two rows (the live TSLA id-22/id-23 pair). This collapses
    them to a single resolution whose **lookup key equals the DB uniqueness key**
    (``upper(symbol)`` + exchange, with NULL≡NULL): the F6 principle — two keys for one
    identity IS the defect.

    Case-normalizes the symbol on both lookup and create (SQLite ``=`` is case-sensitive, so the
    lookup uses ``upper(symbol)`` to catch a case-variant row). Savepoint-tolerant against a
    concurrent create: if the ``uq_instr_identity_ci`` guard rejects the flush, the winner is
    re-read rather than poisoning the outer transaction. Returns ``(instrument, created)``.
    """
    from sqlalchemy.exc import IntegrityError, OperationalError

    from app.core.symbols import country_for_symbol, currency_for_symbol
    from app.models import AssetClass

    sym = symbol.upper()
    stmt = select(Instrument).where(func.upper(Instrument.symbol) == sym)
    if exchange:
        stmt = stmt.where(Instrument.exchange == exchange)
    instrument = (await session.execute(stmt)).scalars().first()
    if instrument is not None:
        return instrument, False

    ac = asset_class if asset_class is not None else AssetClass.EQUITY
    ccy = currency or currency_for_symbol(symbol, exchange) or "USD"
    ac_val = ac.value if hasattr(ac, "value") else str(ac)
    # ``country`` is authoritative when the caller passes it (even as None — csv_import
    # deliberately leaves a non-equity's country unknown, §14dr-27b); only the _UNSET default
    # falls back to the bare-ticker heuristic (the pre-existing market.py behaviour).
    # R12 (F-G Rider A, 2026-07-24): CRYPTO is borderless — it has no listing country, so it never
    # takes the bare-ticker "US" heuristic; its country stays unknown (rendered ``—``). This is the
    # §14dr-27(b) principle applied to the crypto class specifically (MASTER-DATA §4). Both
    # ``listing_country`` (never set at create) and the legacy ``country`` stay NULL.
    if country is not _UNSET:
        ctry = country
    elif ac_val == "crypto":
        ctry = None
    else:
        ctry = country_for_symbol(symbol, exchange, ccy)
    fields: dict = dict(
        symbol=sym, exchange=exchange, name=name or sym, currency=ccy,
        country=ctry,
        asset_class=ac,
        **classify_defaults(ac, is_manual_price=False, currency=ccy),
    )
    if extra:
        fields.update(extra)
    instrument = Instrument(**fields)
    session.add(instrument)
    try:
        # Savepoint so a concurrent create (uq_instr_identity_ci) can be recovered without
        # poisoning the outer transaction — mirrors the pre-existing market.py pattern.
        async with session.begin_nested():
            await session.flush()
    except IntegrityError:
        # Our flush reached the guard and lost the race to a concurrent create — the savepoint
        # rollback has already detached the losing insert, so re-read the committed winner (the
        # pre-existing market.py pattern, unchanged).
        instrument = (await session.execute(stmt)).scalars().first()
        assert instrument is not None  # the IntegrityError means a concurrent create won
        return instrument, False
    except OperationalError:
        # Under heavy contention our INSERT could not take SQLite's writer lock within busy_timeout
        # because a still-open winning transaction of the SAME new symbol holds it — the guard made
        # the create a real serialization point. A WAL read needs no writer lock, so read the
        # committed winner; absorbing this turns a spurious 500 (and the lock it would strand for
        # the next test's DDL) into an honest resolution. Unlike the IntegrityError case the insert
        # never ran, so the pending object survives — expunge it first, else autoflush on the
        # SELECT would retry the very insert that just failed. If the row is genuinely absent the
        # lock error was NOT a lost race — re-raise it untouched.
        session.expunge(instrument)
        found = (await session.execute(stmt)).scalars().first()
        if found is not None:
            return found, False
        raise
    return instrument, True


async def _active_reference_counts(session: AsyncSession, instrument_ids: list[int]) -> dict:
    """For each instrument id, the count of ACTIVE (``deleted_at IS NULL``) holdings and
    transactions that reference it — the orphan test (R-63 F-E / I-12). An instrument with zero of
    both is an *orphan*: nothing live points at it, so a purge-then-re-add left it stranded."""
    from app.models import Holding, Transaction

    counts = {i: {"holdings": 0, "transactions": 0} for i in instrument_ids}
    if not instrument_ids:
        return counts
    for iid, n in (await session.execute(
        select(Holding.instrument_id, func.count())
        .where(Holding.instrument_id.in_(instrument_ids), Holding.deleted_at.is_(None))
        .group_by(Holding.instrument_id)
    )).all():
        counts[iid]["holdings"] = n
    for iid, n in (await session.execute(
        select(Transaction.instrument_id, func.count())
        .where(Transaction.instrument_id.in_(instrument_ids), Transaction.deleted_at.is_(None))
        .group_by(Transaction.instrument_id)
    )).all():
        counts[iid]["transactions"] = n
    return counts


async def duplicate_instruments(session: AsyncSession) -> list[dict]:
    """Instruments that share one identity — same ``upper(symbol)`` and equivalent exchange
    (NULL≡NULL) — split across more than one row. A data-quality problem the user resolves on
    Holdings; we report, never auto-merge (we never guess which row is canonical). Mirrors
    ``duplicate_identifiers``. This is the honest face of the dupe-tolerant identity migration:
    where the ``uq_instr_identity_ci`` index could not bind (a DB that already held duplicates),
    this surfaces exactly which rows to reconcile.

    R-63 F-E / I-12: each instrument now carries its ACTIVE-reference counts and a derived
    ``orphan`` flag (0 active holdings AND 0 active transactions), plus a group-level
    ``orphan_count`` — so the surface can distinguish "both rows are in use (resolve on Holdings)"
    from "one copy is unused and can be removed here" (the finding was that the counter was blind to
    orphan status, and Holdings — derived from transactions — can never show an orphan row)."""
    key_symbol = func.upper(Instrument.symbol)
    key_exch = func.coalesce(Instrument.exchange, "")
    groups = (
        await session.execute(
            select(key_symbol.label("sym"), key_exch.label("exch"), func.count().label("n"))
            .group_by(key_symbol, key_exch)
            .having(func.count() > 1)
        )
    ).all()
    out: list[dict] = []
    for sym, exch, n in groups:
        rows = (
            await session.execute(
                select(Instrument.id, Instrument.symbol, Instrument.name, Instrument.exchange)
                .where(func.upper(Instrument.symbol) == sym, func.coalesce(Instrument.exchange, "") == exch)
                .order_by(Instrument.id)
            )
        ).all()
        refs = await _active_reference_counts(session, [i for i, *_ in rows])
        instruments = []
        orphan_count = 0
        for i, s, nm, ex in rows:
            ah, at = refs[i]["holdings"], refs[i]["transactions"]
            orphan = ah == 0 and at == 0
            orphan_count += 1 if orphan else 0
            instruments.append({
                "id": i, "symbol": s, "name": nm, "exchange": ex,
                "active_holdings": ah, "active_transactions": at, "orphan": orphan,
            })
        out.append({
            "symbol": sym, "exchange": exch or None, "instrument_count": n,
            "orphan_count": orphan_count, "instruments": instruments,
        })
    return out


async def remove_orphan_instrument(session: AsyncSession, instrument_id: int) -> dict:
    """Remove one ORPHANED duplicate instrument row — the cleanup that makes the Pricing Health
    duplicate banner's promise TRUE (R-63 F-E / I-12, owner ruling R8 2026-07-24).

    Two safety gates, both refuse loudly (``OrphanRemovalError``) rather than delete the wrong row:
      1. **Non-orphan** — any ACTIVE holding/transaction references the row. The user's live data is
         on the surviving twin; a row still in use is never removable.
      2. **Non-duplicate** — the row does not share its identity (``upper(symbol)`` + equivalent
         exchange, NULL≡NULL) with at least one OTHER row. A lone instrument (e.g. a watchlist-only
         entry with no holdings) is *orphan-shaped* but is NOT a duplicate, so removing it would
         delete legitimate data — refused. This also guarantees at least one row for the identity
         always survives.

    Removes the orphan INSTRUMENT row only, first purging rows that would otherwise dangle at its id
    (quotes, price_history, identifiers, acquisitions, watchlist_items, and its own already-soft-
    deleted holdings/transactions), and nulling any ``transactions.related_instrument_id`` back-
    reference. Audit-evented. Returns ``{"removed": id, "symbol": …}``."""
    from sqlalchemy import delete, update

    from app.models import (
        AuditEvent,
        Holding,
        InstrumentAcquisition,
        InstrumentIdentifier,
        PriceHistory,
        Quote,
        Transaction,
        WatchlistItem,
    )

    instr = await session.get(Instrument, instrument_id)
    if instr is None:
        raise OrphanRemovalError(f"instrument #{instrument_id} not found")

    # Gate 1: refuse a row still in use.
    refs = (await _active_reference_counts(session, [instrument_id]))[instrument_id]
    if refs["holdings"] or refs["transactions"]:
        raise OrphanRemovalError(
            f"{instr.symbol} #{instrument_id} is in use "
            f"({refs['holdings']} holding(s), {refs['transactions']} transaction(s)) — not an orphan"
        )

    # Gate 2: refuse a row that is not part of a duplicate group (never delete a lone instrument).
    # The identity key is upper(symbol) + equivalent exchange (NULL≡''), matching the DB guard.
    twins = (await session.execute(
        select(func.count()).select_from(Instrument).where(
            func.upper(Instrument.symbol) == instr.symbol.upper(),
            func.coalesce(Instrument.exchange, "") == (instr.exchange or ""),
            Instrument.id != instrument_id,
        )
    )).scalar()
    if not twins:
        raise OrphanRemovalError(
            f"{instr.symbol} #{instrument_id} is not a duplicate — nothing to clean up"
        )

    symbol = instr.symbol
    # The surviving canonical twin (lowest OTHER id in the identity group) inherits the references
    # that carry USER INTENT — watchlist membership and merger back-refs — so the cleanup loses
    # nothing the user chose; a duplicate IS the same logical instrument, so re-pointing them is not
    # a "guess" (unlike a value merge, which we never do). Gate 2 guarantees a survivor exists.
    survivor_id = (await session.execute(
        select(Instrument.id).where(
            func.upper(Instrument.symbol) == instr.symbol.upper(),
            func.coalesce(Instrument.exchange, "") == (instr.exchange or ""),
            Instrument.id != instrument_id,
        ).order_by(Instrument.id)
    )).scalars().first()
    # Re-point watchlist membership to the survivor, de-duplicating within each watchlist (no unique
    # constraint on (watchlist_id, instrument_id), so we drop the orphan's row where the survivor is
    # already listed rather than create a visible double entry).
    for item in (await session.execute(
        select(WatchlistItem).where(WatchlistItem.instrument_id == instrument_id))).scalars().all():
        already = (await session.execute(
            select(WatchlistItem).where(
                WatchlistItem.watchlist_id == item.watchlist_id,
                WatchlistItem.instrument_id == survivor_id,
            ))).scalars().first()
        if already is not None:
            await session.delete(item)
        else:
            item.instrument_id = survivor_id
    # Merger back-references (schema-only today) follow the survivor, not null — the merger target is
    # the same logical instrument.
    await session.execute(update(Transaction)
                          .where(Transaction.related_instrument_id == instrument_id)
                          .values(related_instrument_id=survivor_id))
    # Purge the orphan's OWN pure-cache / own-metadata dependents BEFORE the instrument row (no
    # FK-cascade is declared, so a left-behind row would point at a deleted id). The active-reference
    # gate guarantees any holdings/transactions on this row are soft-deleted — deleting them loses
    # nothing live; the orphan's identifiers/quotes/history are its own and regenerable.
    for model in (Quote, PriceHistory, InstrumentIdentifier, InstrumentAcquisition,
                  Holding, Transaction):
        await session.execute(delete(model).where(model.instrument_id == instrument_id))
    await session.delete(instr)
    session.add(AuditEvent(
        category="mutation", action="remove_orphan_instrument",
        detail=f"removed orphaned duplicate instrument {symbol} #{instrument_id} (F-E/I-12)"))
    await session.flush()
    return {"removed": instrument_id, "symbol": symbol}


async def find_instrument_by_identifier(
    session: AsyncSession, id_type: str, value: str
) -> Instrument | None:
    """Resolve an instrument by a normalized identifier (e.g. an ISIN). Returns None
    if unmapped OR if the mapping is **ambiguous** (the same id points at more than one
    instrument) — we never guess which is correct; surface it via ``duplicate_identifiers``."""
    rows = (
        await session.execute(
            select(InstrumentIdentifier).where(
                InstrumentIdentifier.id_type == id_type.lower(),
                InstrumentIdentifier.value == value,
            )
        )
    ).scalars().all()
    instrument_ids = {r.instrument_id for r in rows}
    if len(instrument_ids) != 1:
        return None  # unmapped (0) or ambiguous (>1) → don't guess
    return await session.get(Instrument, next(iter(instrument_ids)))


async def duplicate_identifiers(session: AsyncSession) -> list[dict]:
    """Any (id_type, value) mapped to more than one instrument — a data-quality
    problem the user must resolve. We report, never auto-merge."""
    rows = (
        await session.execute(
            select(
                InstrumentIdentifier.id_type, InstrumentIdentifier.value,
                func.count(func.distinct(InstrumentIdentifier.instrument_id)).label("n"),
            )
            .group_by(InstrumentIdentifier.id_type, InstrumentIdentifier.value)
            .having(func.count(func.distinct(InstrumentIdentifier.instrument_id)) > 1)
        )
    ).all()
    out: list[dict] = []
    for id_type, value, n in rows:
        instrs = (
            await session.execute(
                select(Instrument.id, Instrument.symbol, Instrument.name)
                .join(InstrumentIdentifier, InstrumentIdentifier.instrument_id == Instrument.id)
                .where(InstrumentIdentifier.id_type == id_type, InstrumentIdentifier.value == value)
            )
        ).all()
        out.append({
            "id_type": id_type, "value": value, "instrument_count": n,
            "instruments": [{"id": i, "symbol": s, "name": nm} for i, s, nm in instrs],
        })
    return out


async def set_identifier(
    session: AsyncSession,
    instrument_id: int,
    id_type: str,
    value: str,
    *,
    provider: str | None = None,
    is_primary: bool = False,
) -> InstrumentIdentifier:
    """Idempotently attach an identifier to an instrument (no duplicate rows).

    Refuses to attach a **high-confidence** identifier (ISIN/CUSIP/FIGI/SEDOL/AMFI
    code/Kite token/CoinGecko id) that already belongs to a *different* instrument —
    that would create an ambiguous mapping. Raises ``DuplicateIdentifierError``.
    """
    id_type = id_type.lower()
    if id_type in HIGH_CONFIDENCE_IDS:
        clash = (
            await session.execute(
                select(InstrumentIdentifier).where(
                    InstrumentIdentifier.id_type == id_type,
                    InstrumentIdentifier.value == value,
                    InstrumentIdentifier.instrument_id != instrument_id,
                )
            )
        ).scalars().first()
        if clash is not None:
            raise DuplicateIdentifierError(
                f"{id_type} '{value}' is already mapped to instrument #{clash.instrument_id}"
            )
    existing = (
        await session.execute(
            select(InstrumentIdentifier).where(
                InstrumentIdentifier.instrument_id == instrument_id,
                InstrumentIdentifier.id_type == id_type,
                InstrumentIdentifier.value == value,
            )
        )
    ).scalars().first()
    if existing is not None:
        if provider is not None:
            existing.provider = provider
        if is_primary:
            existing.is_primary = True
        return existing
    ident = InstrumentIdentifier(
        instrument_id=instrument_id, id_type=id_type, value=value,
        provider=provider, is_primary=is_primary,
    )
    session.add(ident)
    await session.flush()
    return ident


async def identifiers_for(session: AsyncSession, instrument_id: int) -> list[dict]:
    rows = (
        await session.execute(
            select(InstrumentIdentifier).where(InstrumentIdentifier.instrument_id == instrument_id)
        )
    ).scalars().all()
    return [
        {"id_type": r.id_type, "value": r.value, "provider": r.provider, "is_primary": r.is_primary}
        for r in rows
    ]
