# SPDX-License-Identifier: AGPL-3.0-or-later
"""Holding tags (W8) — a personal lens (Core / Satellite / Emergency…) on top of asset
class. Tags key on (account_id, holding_key) where holding_key is the instrument symbol or
the manual label — stable across the holding rebuild. Reporting only; overlaps are honest
(a holding counts under every tag it carries).
"""

from __future__ import annotations

import json
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import Holding, HoldingTag, Instrument
from app.services.portfolio import value_portfolio

ZERO = Decimal("0")
SUGGESTED_TAGS = ["core", "satellite", "speculative", "income", "emergency",
                  "child_education", "retirement", "high_conviction", "watch_closely"]


def _clean_tags(tags: list[str]) -> list[str]:
    out: list[str] = []
    for t in tags or []:
        s = str(t).strip().lower().replace(" ", "_")[:24]
        if s and s not in out:
            out.append(s)
    return out[:8]


async def _holding_key(session: AsyncSession, h: Holding) -> str:
    instrument = await session.get(Instrument, h.instrument_id) if h.instrument_id else None
    return (instrument.symbol if instrument and instrument.symbol else None) or h.label or f"#{h.id}"


async def set_holding_tags(session: AsyncSession, holding_id: int, tags: list[str]) -> dict:
    h = await session.get(Holding, holding_id)
    if h is None:
        raise ValueError("holding not found")
    key = await _holding_key(session, h)
    clean = _clean_tags(tags)
    row = (await session.execute(select(HoldingTag).where(
        HoldingTag.account_id == h.account_id, HoldingTag.holding_key == key))).scalars().first()
    if row is None:
        row = HoldingTag(account_id=h.account_id, holding_key=key, tags=json.dumps(clean))
        session.add(row)
    else:
        row.tags = json.dumps(clean)
    await session.flush()
    return {"account_id": h.account_id, "holding_key": key, "tags": clean}


async def _lookup(session: AsyncSession) -> dict[tuple[int, str], list[str]]:
    rows = (await session.execute(select(HoldingTag))).scalars().all()
    out: dict[tuple[int, str], list[str]] = {}
    for r in rows:
        try:
            out[(r.account_id, r.holding_key)] = json.loads(r.tags)
        except (ValueError, TypeError):
            out[(r.account_id, r.holding_key)] = []
    return out


async def tag_allocation(session: AsyncSession, entity_id: int | None = None) -> dict:
    base = get_settings().base_currency
    val = await value_portfolio(session, base, entity_id=entity_id)  # §4.1
    lookup = await _lookup(session)

    by_tag: dict[str, dict] = defaultdict(lambda: {"value": ZERO, "count": 0})
    holdings = []
    # Denominator = GROSS assets (positive holdings); liabilities are never allocation weight
    # (GLOSSARY 'Allocation weight'; page-portfolio ND-4). Tag weights are a share of gross.
    gross = ZERO
    for hv in val.holdings:
        key = hv.symbol or hv.label
        # account-less holdings (account_id None) can't carry tags → same as the [] default.
        tags = lookup.get((hv.account_id, key), []) if hv.account_id is not None else []
        holdings.append({"holding_id": hv.holding_id, "label": hv.label, "symbol": hv.symbol,
                         "value": float(round(hv.market_value_base, 0)), "tags": tags})
        if hv.market_value_base <= 0:
            continue  # liabilities/zeros are excluded from allocation weight (never a tag slice)
        gross += hv.market_value_base
        for t in tags:
            by_tag[t]["value"] += hv.market_value_base
            by_tag[t]["count"] += 1

    total = gross
    tags_list = sorted(
        ({"tag": t, "value": float(round(v["value"], 0)), "count": v["count"],
          "pct": float(round(v["value"] / total * 100, 1)) if total else 0.0}
         for t, v in by_tag.items()),
        key=lambda x: x["value"], reverse=True)
    return {"base_currency": base, "total": float(round(total, 0)),
            "tags": tags_list, "holdings": holdings, "suggested": SUGGESTED_TAGS,
            "disclaimer": "Your own labels — a lens on top of asset class. A holding counts under "
                          "every tag it carries, so tag totals can overlap. Reporting only."}
