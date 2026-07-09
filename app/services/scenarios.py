# SPDX-License-Identifier: AGPL-3.0-or-later
"""Scenario / stress testing (W6) — factual "what if", never a forecast.

Deterministic arithmetic on today's holdings: apply a hypothetical price/FX shock and show
the impact on net worth, and simple liquidity what-ifs (income stops, a large obligation
drawn now). No probabilities, no return projections, no prediction — a scenario, not advice.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.services.planning import obligations_report
from app.services.portfolio import value_portfolio
from app.services.runway import runway_report

ZERO = Decimal("0")
_EQUITY_CLASSES = {"equity", "etf", "mutual_fund"}


def _f(x: Decimal, p: int = 0) -> float:
    return float(round(x, p))


async def scenario_report(session: AsyncSession, entity_id: int | None = None) -> dict:
    base = get_settings().base_currency
    val = await value_portfolio(session, base, entity_id=entity_id)  # §4.1
    nw = val.total_value

    equities = crypto = prop = foreign = ZERO
    for h in val.holdings:
        mv = h.market_value_base
        if mv <= 0:
            continue
        if h.asset_class in _EQUITY_CLASSES:
            equities += mv
        elif h.asset_class == "crypto":
            crypto += mv
        elif h.asset_class == "property":
            prop += mv
        if h.native_currency and h.native_currency != base:
            foreign += mv

    def _shock(sid: str, name: str, exposure: Decimal, pct: float, group: str) -> dict:
        delta = exposure * Decimal(str(pct))
        new_nw = nw + delta
        return {
            "id": sid, "name": name, "group": group,
            "exposure": _f(exposure),
            "delta": _f(delta),
            "new_net_worth": _f(new_nw),
            "pct_change": _f((delta / nw * 100) if nw else ZERO, 1),
        }

    asset_scenarios = [
        _shock("equities_10", "Equities fall 10%", equities, -0.10, "markets"),
        _shock("equities_20", "Equities fall 20%", equities, -0.20, "markets"),
        _shock("equities_30", "Equities fall 30%", equities, -0.30, "markets"),
        _shock("risk_20", "Risk assets fall 20% (equities + crypto)", equities + crypto, -0.20, "markets"),
        _shock("crypto_50", "Crypto falls 50%", crypto, -0.50, "markets"),
        _shock("property_10", "Property falls 10%", prop, -0.10, "markets"),
        _shock("fx_10", "Your foreign currencies weaken 10% vs base", foreign, -0.10, "fx"),
    ]

    # Liquidity what-ifs (deterministic, from recorded planning data).
    run = await runway_report(session)
    liquid = Decimal(str(run.get("liquid", 0)))
    monthly_expense = Decimal(str(run.get("monthly_expense", 0)))
    obs = await obligations_report(session)
    next_12m = Decimal(str(obs.get("next_12m_total", 0)))

    income_stop_runway = _f(liquid / monthly_expense, 1) if monthly_expense > 0 else None
    liquidity = {
        "liquid": _f(liquid),
        "runway_months": run.get("runway_months"),
        "income_stop": {
            "monthly_expense": _f(monthly_expense),
            "runway_months": income_stop_runway,
            "note": ("If recorded income stopped, liquid assets would cover recurring expenses for this long."
                     if income_stop_runway is not None else "Add recurring expenses in Planning to model this."),
        },
        "obligation_due": {
            "amount": _f(next_12m),
            "new_liquid": _f(liquid - next_12m),
            "covered": bool(liquid >= next_12m),
            "note": "If the next 12 months of recorded obligations were paid from liquid assets now.",
        },
    }

    return {
        "base_currency": base,
        "net_worth": _f(nw),
        "exposures": {"equities": _f(equities), "crypto": _f(crypto),
                      "property": _f(prop), "foreign_fx": _f(foreign)},
        "asset_scenarios": asset_scenarios,
        "liquidity": liquidity,
        "disclaimer": "Scenario, not forecast — arithmetic on today's values, not a prediction, "
                      "probability or recommendation. Real outcomes will differ.",
    }
