# SPDX-License-Identifier: AGPL-3.0-or-later
"""R-43 §12 step 7 — Build-history COVERAGE preflight (F-1).

F-1's root: ``run_backfill`` valued a 2019→2026 daily series against a price/FX store that barely
existed, with NO coverage check — so it built a square-pulse garbage line. This module reports, per
held instrument, what history actually exists on-stack: the earliest/latest real daily candle + its
count, and the per-currency FX coverage (from ``ecb_fx_history``). The trigger UI renders this
served summary so a build is never run blind, and step 8's refuse-until-coverage policy reads the
same derivation.

Every rendered value is a served display string (D-105); a genuinely-absent figure is null +
reasoned, never fabricated.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import EcbFxHistory, Holding, Instrument, PriceHistory


def _iso_date(ts) -> str | None:
    """ISO YYYY-MM-DD from a stored ts (datetime) or as_of (str)."""
    if ts is None:
        return None
    if isinstance(ts, str):
        return ts[:10]
    return ts.date().isoformat() if hasattr(ts, "date") else str(ts)[:10]


async def _fx_span(session: AsyncSession, currency: str) -> tuple[str | None, str | None]:
    """Earliest/latest ecb_fx_history as_of for a currency (as ISO strings), or (None, None)."""
    row = (await session.execute(
        select(func.min(EcbFxHistory.as_of), func.max(EcbFxHistory.as_of))
        .where(EcbFxHistory.currency == currency.upper())
    )).one()
    return _iso_date(row[0]), _iso_date(row[1])


async def coverage_summary(session: AsyncSession, base_currency: str | None = None) -> dict:
    """Per-instrument + overall coverage of the on-stack price/FX history — the served Build-history
    preflight (F-1). Numbers match the store exactly (they are read from it)."""
    base = (base_currency or get_settings().base_currency or "SGD").upper()

    instruments = (await session.execute(
        select(Instrument).join(Holding, Holding.instrument_id == Instrument.id)
        .where(Holding.deleted_at.is_(None), Instrument.id.isnot(None)).distinct()
    )).scalars().all()

    fx_cache: dict[str, tuple[str | None, str | None]] = {}
    out: list[dict] = []
    covered_count = 0
    for instr in instruments:
        ac = instr.asset_class.value if hasattr(instr.asset_class, "value") else str(instr.asset_class or "")
        prow = (await session.execute(
            select(func.min(PriceHistory.ts), func.max(PriceHistory.ts), func.count())
            .where(PriceHistory.instrument_id == instr.id, PriceHistory.interval == "1d")
        )).one()
        p_earliest, p_latest, p_days = _iso_date(prow[0]), _iso_date(prow[1]), int(prow[2] or 0)

        pricing_ccy = (instr.pricing_currency or instr.currency or base).upper()
        needs_fx = pricing_ccy != base
        fx_earliest = fx_latest = None
        if needs_fx:
            if pricing_ccy not in fx_cache:
                fx_cache[pricing_ccy] = await _fx_span(session, pricing_ccy)
            fx_earliest, fx_latest = fx_cache[pricing_ccy]

        has_price = p_days > 0
        has_fx = (not needs_fx) or (fx_earliest is not None)
        covered = has_price and has_fx
        if covered:
            covered_count += 1

        # Served human summary (D-105) — the frontend renders it verbatim.
        if not has_price:
            summary = "No price history yet — run Build history to acquire it"
        elif needs_fx and not has_fx:
            summary = f"Prices {p_earliest}→{p_latest}, but no {pricing_ccy}→{base} FX history yet"
        elif needs_fx:
            summary = f"Prices {p_earliest}→{p_latest}; {pricing_ccy} FX {fx_earliest}→{fx_latest}"
        else:
            summary = f"Prices {p_earliest}→{p_latest}"

        out.append({
            "instrument_id": instr.id, "symbol": instr.symbol,
            "name": instr.name or instr.symbol, "asset_class": ac,
            "price_earliest": p_earliest, "price_latest": p_latest, "price_days": p_days,
            "needs_fx": needs_fx, "fx_currency": pricing_ccy if needs_fx else None,
            "fx_earliest": fx_earliest, "fx_latest": fx_latest,
            "covered": covered, "summary": summary,
        })

    total = len(out)
    all_covered = total > 0 and covered_count == total
    coverage_label = (
        "History is complete for every holding." if all_covered
        else f"History covers {covered_count} of {total} holding(s) — Build history to fill the rest."
        if total else "No holdings to build history for."
    )
    return {
        "base_currency": base,
        "instruments": out,
        "total": total, "covered_count": covered_count, "all_covered": all_covered,
        "coverage_label": coverage_label,
    }
