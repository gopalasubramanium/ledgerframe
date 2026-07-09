# SPDX-License-Identifier: AGPL-3.0-or-later
"""Liquidity ladder (Phase 3a) — graded 'time-to-cash' buckets of the portfolio.

Deterministic and honest: liquidity is *inferred from asset class* (an instrument's
optional ``liquidity_profile`` overrides it when set). It is indicative — a bucket says
how quickly an asset type can typically be turned to cash, not a guarantee of price or
timing. Reporting only, not advice.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.services.portfolio import value_portfolio

# Explicit override (when a user classifies an instrument) → ladder rung.
_RUNG_BY_PROFILE = {
    "listed": "immediate", "redeemable": "short", "locked": "locked", "illiquid": "illiquid",
}
# Otherwise inferred from asset class.
_RUNG_BY_CLASS = {
    "cash": "immediate", "equity": "immediate", "etf": "immediate",
    "crypto": "immediate", "commodity": "immediate",
    "mutual_fund": "short", "bond": "short",
    "fixed_deposit": "locked", "retirement": "locked",
    "property": "illiquid", "private": "illiquid",
    "liability": "liability", "other": "unclassified",
}
_ORDER = ["immediate", "short", "locked", "illiquid", "unclassified"]
_LABEL = {
    "immediate": "Immediate (cash & listed)",
    "short": "Short (funds & bonds)",
    "locked": "Locked (deposits & retirement)",
    "illiquid": "Illiquid (property & private)",
    "unclassified": "Unclassified",
}


def rung_of(hv) -> str:
    p = (getattr(hv, "liquidity_profile", None) or "").lower()
    if p in _RUNG_BY_PROFILE:
        return _RUNG_BY_PROFILE[p]
    return _RUNG_BY_CLASS.get(getattr(hv, "asset_class", "other"), "unclassified")


async def liquidity_ladder(session: AsyncSession, entity_id: int | None = None) -> dict:
    base = get_settings().base_currency
    val = await value_portfolio(session, base, entity_id=entity_id)  # §4.1
    rung_val: dict[str, Decimal] = defaultdict(lambda: Decimal(0))
    liabilities = Decimal(0)
    for h in val.holdings:
        mv = h.market_value_base
        if rung_of(h) == "liability" or mv < 0:
            liabilities += mv           # negative — kept separate from the asset ladder
            continue
        if mv <= 0:
            continue
        rung_val[rung_of(h)] += mv

    gross = sum(rung_val.values(), Decimal(0)) or Decimal(1)
    rungs = []
    cumulative = Decimal(0)
    for key in _ORDER:
        v = rung_val.get(key, Decimal(0))
        if v <= 0:
            continue
        pct = v / gross * 100
        cumulative += pct
        rungs.append({
            "key": key, "label": _LABEL[key],
            "value": float(round(v, 0)),
            "pct": float(round(pct, 1)),
            "cumulative_pct": float(round(cumulative, 1)),
        })
    liquid = rung_val.get("immediate", Decimal(0)) + rung_val.get("short", Decimal(0))
    return {
        "base_currency": base,
        "gross_assets": float(round(gross, 0)),
        "rungs": rungs,
        "liquid_pct": float(round(liquid / gross * 100, 1)),
        "liabilities": float(round(liabilities, 0)),
        "disclaimer": "Indicative liquidity by asset type — not a guarantee of sale price or timing.",
    }
