# SPDX-License-Identifier: AGPL-3.0-or-later
"""ECB reference-FX service.

Caches the ECB daily euro reference rates (DB + a small in-process map) and derives
any pair with explicit **direct / inverse / triangulated** logic. Consumed by
``app.services.fx`` as a *fallback* only — it never overrides a working, entitled
provider rate. All arithmetic is ``Decimal``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.money import D
from app.db.upsert import upsert
from app.models import EcbFxRate
from app.providers.market.ecb import parse_ecb_daily

# In-process EUR-based rates (EUR -> CCY) so the session-less FX path can use them.
_RATES: dict[str, Decimal] = {}
_ASOF: str | None = None


def _set_cache(rates: dict[str, Decimal], as_of: str | None) -> None:
    global _ASOF
    _RATES.clear()
    _RATES.update(rates)
    _ASOF = as_of


async def refresh(session: AsyncSession, xml_text: str) -> dict:
    """Parse the ECB daily XML, upsert the cache table, and refresh the in-process map."""
    as_of, rates = parse_ecb_daily(xml_text)
    now = datetime.now(UTC)
    for ccy, rate in rates.items():
        stmt = upsert(EcbFxRate).values(
            currency=ccy, rate=D(rate), as_of=as_of, updated_at=now,
        ).on_conflict_do_update(
            index_elements=[EcbFxRate.currency],
            set_={"rate": D(rate), "as_of": as_of, "updated_at": now},
        )
        await session.execute(stmt)
    await session.flush()
    _set_cache(rates, as_of)
    return {"currencies": len(rates), "as_of": as_of}


async def load_from_db(session: AsyncSession) -> int:
    """Populate the in-process map from the cache table (called at startup)."""
    rows = (await session.execute(select(EcbFxRate))).scalars().all()
    if not rows:
        return 0
    _set_cache({r.currency: D(r.rate) for r in rows},
               next((r.as_of for r in rows if r.as_of), None))
    return len(rows)


def reference_rate(base: str, quote: str) -> tuple[Decimal | None, str]:
    """Reference rate for base→quote from the ECB (EUR-based) cache, with the method.

    Returns ``(rate, method)`` where method ∈ {identity, direct, inverse,
    triangulated, unavailable}. ``(None, "unavailable")`` if a needed leg is missing.
    """
    base, quote = base.upper(), quote.upper()
    if base == quote:
        return Decimal("1"), "identity"
    if not _RATES:
        return None, "unavailable"
    rb, rq = _RATES.get(base), _RATES.get(quote)   # EUR->base, EUR->quote
    if base == "EUR" and rq is not None:
        return rq, "direct"                        # EUR -> quote
    if quote == "EUR" and rb is not None and rb != 0:
        return Decimal("1") / rb, "inverse"        # base -> EUR
    if rb is not None and rq is not None and rb != 0:
        return rq / rb, "triangulated"             # base -> EUR -> quote
    return None, "unavailable"


async def status(session: AsyncSession) -> dict:
    total = (await session.execute(select(func.count()).select_from(EcbFxRate))).scalar() or 0
    as_of = (await session.execute(select(func.max(EcbFxRate.as_of)))).scalar()
    return {"currencies": total, "as_of": as_of, "loaded": len(_RATES)}
