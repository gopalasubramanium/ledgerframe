# SPDX-License-Identifier: AGPL-3.0-or-later
"""AMFI mutual-fund NAV service: cache the scheme master, refresh official NAVs,
search/map schemes, and publish NAVs to mapped instruments as ``official_nav``
quotes so valuation flows through the normal path with honest provenance.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.money import D
from app.db.upsert import upsert
from app.models import AmfiScheme, InstrumentIdentifier
from app.models import Quote as QuoteRow
from app.providers.market.amfi import parse_nav_all


async def refresh_schemes(session: AsyncSession, text: str) -> dict:
    """Parse a NAVAll.txt payload and upsert the scheme master + latest NAV, then
    publish NAVs to any mapped instruments. Returns a summary."""
    schemes = parse_nav_all(text)
    now = datetime.now(UTC)
    priced = 0
    for s in schemes:
        stmt = upsert(AmfiScheme).values(
            code=s.code, name=s.name, isin_growth=s.isin_growth, isin_reinvest=s.isin_reinvest,
            fund_house=s.fund_house, category=s.category,
            nav=s.nav, nav_date=s.nav_date.isoformat() if s.nav_date else None, updated_at=now,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[AmfiScheme.code],
            set_={"name": s.name, "isin_growth": s.isin_growth, "isin_reinvest": s.isin_reinvest,
                  "fund_house": s.fund_house, "category": s.category,
                  "nav": s.nav, "nav_date": s.nav_date.isoformat() if s.nav_date else None,
                  "updated_at": now},
        )
        await session.execute(stmt)
        if s.nav is not None:
            priced += 1
    await session.flush()
    published = await publish_navs_to_instruments(session)
    return {"schemes": len(schemes), "priced": priced, "published": published}


async def publish_navs_to_instruments(session: AsyncSession) -> int:
    """For every instrument mapped to an AMFI scheme (via an ``amfi_code`` identifier),
    write a Quote (source=amfi_nav, entitlement=end-of-day) with the scheme's NAV, so
    the holding is valued from the official NAV. Never writes a null price."""
    now = datetime.now(UTC)
    idents = (await session.execute(
        select(InstrumentIdentifier).where(InstrumentIdentifier.id_type == "amfi_code")
    )).scalars().all()
    published = 0
    for ident in idents:
        scheme = await session.get(AmfiScheme, ident.value)
        if scheme is None or scheme.nav is None:
            continue
        values = {
            "instrument_id": ident.instrument_id, "price": D(scheme.nav),
            "previous_close": None, "currency": "INR", "source": "amfi_nav",
            "entitlement": "end-of-day", "market_time": now, "received_at": now,
        }
        stmt = upsert(QuoteRow).values(**values).on_conflict_do_update(
            index_elements=[QuoteRow.instrument_id],
            set_={k: v for k, v in values.items() if k != "instrument_id"},
        )
        await session.execute(stmt)
        published += 1
    await session.flush()
    return published


async def search_schemes(session: AsyncSession, q: str, limit: int = 20) -> list[dict]:
    """Exact code / ISIN match or name substring — for the mapping screen. Never used
    to *auto*-map (that requires an explicit user choice)."""
    q = q.strip()
    if not q:
        return []
    like = f"%{q.lower()}%"
    rows = (await session.execute(
        select(AmfiScheme).where(or_(
            AmfiScheme.code == q,
            AmfiScheme.isin_growth == q.upper(),
            AmfiScheme.isin_reinvest == q.upper(),
            func.lower(AmfiScheme.name).like(like),
        )).limit(limit)
    )).scalars().all()
    return [
        {"code": r.code, "name": r.name, "isin_growth": r.isin_growth,
         "fund_house": r.fund_house, "category": r.category,
         "nav": float(r.nav) if r.nav is not None else None, "nav_date": r.nav_date}
        for r in rows
    ]


async def status(session: AsyncSession) -> dict:
    total = (await session.execute(select(func.count()).select_from(AmfiScheme))).scalar() or 0
    priced = (await session.execute(
        select(func.count()).select_from(AmfiScheme).where(AmfiScheme.nav.isnot(None))
    )).scalar() or 0
    last = (await session.execute(select(func.max(AmfiScheme.nav_date)))).scalar()
    return {"schemes": total, "priced": priced, "as_of": last}
