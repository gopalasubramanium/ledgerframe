# SPDX-License-Identifier: AGPL-3.0-or-later
"""Goals & obligations (Phase 3b).

Stores intent only; **progress and the next-12-months total are computed live** from the
current valuation and never stored. Deterministic and factual — it states progress and
totals, never "on track" (a projection) and never advice. Cross-currency targets/amounts
are converted to base at **current** FX, clearly caveated.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import Goal, Obligation
from app.services import fx
from app.services.liquidity import rung_of
from app.services.portfolio import value_portfolio

GOAL_BASES = ("net_worth", "liquid", "none")
RECURRENCES = ("once", "monthly", "quarterly", "annual")
OBLIGATION_KINDS = ("expense", "income")
_STEP_MONTHS = {"monthly": 1, "quarterly": 3, "annual": 12}
# Recurring amount normalised to a monthly figure (one-offs are not a steady burn).
MONTHLY_FACTOR = {"monthly": Decimal(1), "quarterly": Decimal(1) / 3, "annual": Decimal(1) / 12}


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def _add_months(d: date, n: int) -> date:
    m = d.month - 1 + n
    y = d.year + m // 12
    m = m % 12 + 1
    # clamp day to the target month's length
    for day in (d.day, 28, 29, 30, 31):
        try:
            return date(y, m, min(day, 31))
        except ValueError:
            continue
    return date(y, m, 28)


async def _basis_values(session: AsyncSession) -> tuple[str, Decimal, Decimal]:
    """(base_currency, net_worth, liquid) in base currency."""
    base = get_settings().base_currency
    val = await value_portfolio(session, base)
    net_worth = val.total_value
    liquid = sum((h.market_value_base for h in val.holdings
                  if h.market_value_base > 0 and rung_of(h) in ("immediate", "short")), Decimal(0))
    return base, net_worth, liquid


def _q(v: Decimal, dp: int = 0) -> float:
    return float(round(v, dp))


async def goals_report(session: AsyncSession) -> dict:
    base, net_worth, liquid = await _basis_values(session)
    goals = (await session.execute(select(Goal).order_by(Goal.target_date.is_(None), Goal.target_date))).scalars().all()
    today = datetime.now(UTC).date()
    out = []
    for g in goals:
        ccy = g.currency or base
        target_base = await fx.convert(Decimal(g.target_amount), ccy, base)
        current = {"net_worth": net_worth, "liquid": liquid}.get(g.basis)  # None basis → no auto progress
        row = {
            "id": g.id, "name": g.name, "basis": g.basis,
            "currency": ccy, "target_amount": _q(Decimal(g.target_amount), 2),
            "target_base": _q(target_base, 0), "target_date": g.target_date, "note": g.note,
            "current_base": None, "progress_pct": None, "remaining_base": None, "days_to_target": None,
        }
        if current is not None and target_base > 0:
            row["current_base"] = _q(current, 0)
            row["progress_pct"] = float(round(current / target_base * 100, 1))
            row["remaining_base"] = _q(target_base - current, 0)
        td = _parse_date(g.target_date)
        if td is not None:
            row["days_to_target"] = (td - today).days
        out.append(row)
    return {
        "base_currency": base, "goals": out,
        "disclaimer": "Progress is a fact against your target — not a forecast or advice. "
                      "Cross-currency targets use today's FX (approximate).",
    }


async def obligations_report(session: AsyncSession) -> dict:
    base = get_settings().base_currency
    obs = (await session.execute(select(Obligation).order_by(Obligation.due_date))).scalars().all()
    today = datetime.now(UTC).date()
    horizon = _add_months(today, 12)

    def _occurrences(due: date, recurrence: str) -> list[date]:
        if recurrence == "once":
            return [due] if today <= due <= horizon else []
        step = _STEP_MONTHS.get(recurrence)
        if not step:
            return [due] if today <= due <= horizon else []
        d = due
        while d < today:            # advance to the first occurrence from now
            d = _add_months(d, step)
        out = []
        while d <= horizon:
            out.append(d)
            d = _add_months(d, step)
        return out

    rows, next_12m = [], Decimal(0)
    for o in obs:
        ccy = o.currency or base
        amt_base = await fx.convert(Decimal(o.amount), ccy, base)
        due = _parse_date(o.due_date)
        occ = _occurrences(due, o.recurrence) if due else []
        kind = getattr(o, "kind", "expense") or "expense"
        if kind == "expense":                     # only outflows count toward the total
            next_12m += amt_base * len(occ)
        rows.append({
            "id": o.id, "name": o.name, "amount": _q(Decimal(o.amount), 2), "currency": ccy,
            "amount_base": _q(amt_base, 0), "due_date": o.due_date, "recurrence": o.recurrence,
            "kind": kind, "note": o.note, "occurrences_12m": len(occ),
            "next_due": occ[0].isoformat() if occ else o.due_date,
        })
    return {
        "base_currency": base, "obligations": rows,
        "next_12m_total": _q(next_12m, 0),
        "disclaimer": "Known future cash flows you've entered; outflow total uses today's FX (approximate). Not advice.",
    }
