# SPDX-License-Identifier: AGPL-3.0-or-later
"""Kite instrument-master service: import + cache the master (read-only metadata),
and search it for exact exchange+tradingsymbol matching and F&O identity.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.money import D
from app.db.upsert import upsert
from app.models import KiteInstrument as KiteRow
from app.providers.market.kite import parse_instruments_csv


async def import_instruments(session: AsyncSession, csv_text: str) -> int:
    """Upsert the Kite instrument master from the CSV dump. Metadata only."""
    rows = parse_instruments_csv(csv_text)
    now = datetime.now(UTC)
    for r in rows:
        stmt = upsert(KiteRow).values(
            instrument_token=r.instrument_token, exchange=r.exchange, tradingsymbol=r.tradingsymbol,
            name=r.name, segment=r.segment, instrument_type=r.instrument_type, lot_size=r.lot_size,
            expiry=r.expiry, strike=D(str(r.strike)) if r.strike is not None else None, updated_at=now,
        ).on_conflict_do_update(
            index_elements=[KiteRow.instrument_token],
            set_={"exchange": r.exchange, "tradingsymbol": r.tradingsymbol, "name": r.name,
                  "segment": r.segment, "instrument_type": r.instrument_type, "lot_size": r.lot_size,
                  "expiry": r.expiry, "strike": D(str(r.strike)) if r.strike is not None else None,
                  "updated_at": now},
        )
        await session.execute(stmt)
    await session.flush()
    return len(rows)


async def search(session: AsyncSession, q: str, limit: int = 20) -> list[dict]:
    """Search the master by exact tradingsymbol or name substring — for mapping."""
    q = q.strip()
    if not q:
        return []
    like = f"%{q.lower()}%"
    rows = (await session.execute(
        select(KiteRow).where(or_(
            func.upper(KiteRow.tradingsymbol) == q.upper(),
            func.lower(KiteRow.tradingsymbol).like(like),
            func.lower(KiteRow.name).like(like),
        )).limit(limit)
    )).scalars().all()
    return [
        {"instrument_token": r.instrument_token, "exchange": r.exchange,
         "tradingsymbol": r.tradingsymbol, "name": r.name, "segment": r.segment,
         "instrument_type": r.instrument_type, "lot_size": r.lot_size,
         "expiry": r.expiry, "strike": float(r.strike) if r.strike is not None else None}
        for r in rows
    ]


async def status(session: AsyncSession) -> dict:
    total = (await session.execute(select(func.count()).select_from(KiteRow))).scalar() or 0
    by_seg = {}
    for seg, n in (await session.execute(
        select(KiteRow.exchange, func.count()).group_by(KiteRow.exchange)
    )).all():
        by_seg[seg] = n
    return {"instruments": total, "by_exchange": by_seg}
