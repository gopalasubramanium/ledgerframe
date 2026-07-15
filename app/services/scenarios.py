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
from app.core.money import format_money_display
from app.services.confidence import inputs_quality_note, portfolio_input_quality
from app.services.planning import obligations_report
from app.services.portfolio import value_portfolio
from app.services.runway import runway_report

ZERO = Decimal("0")

# The asset-class buckets that make up "equities" exposure (a superset of Portfolio's per-class
# allocation — an equity fund, an ETF and a direct equity all fall together in an equity shock).
_EQUITY_CLASSES = ("equity", "etf", "mutual_fund")

# --------------------------------------------------------------------------- #
# THE FIXED SHOCK SET (Family C — product-defined, page-scenarios §6/§9-7).
# Named constants with a rationale each, so a future R-11 (user-defined shocks) makes these
# CONFIGURABLE rather than requiring a rewrite. Downside percentages; magnitudes UNCHANGED from
# the inline literals they replace.
# --------------------------------------------------------------------------- #
EQUITY_SHOCKS = (10, 20, 30)   # standard equity drawdown steps — a normal correction, a bear market, a crash
RISK_SHOCK = 20                # risk assets (equities + crypto) fall together in a risk-off move
CRYPTO_SHOCK = 50              # crypto's characteristic high-volatility drawdown
PROPERTY_SHOCK = 10            # a property-market correction on illiquid holdings
FX_SHOCK = 10                  # the base currency strengthens 10% against your foreign holdings


def _f(x: Decimal, p: int = 0) -> float:
    return float(round(x, p))


def _money(x: Decimal) -> str | None:
    return format_money_display(x)


async def scenario_report(session: AsyncSession, entity_id: int | None = None) -> dict:
    # §9-8 — HOUSEHOLD-ONLY. `entity_id` is rejected, not ignored: scoping the ASSET shocks to one
    # entity while the liquidity what-ifs stay HOUSEHOLD (runway/obligations have no entity scope)
    # is a silently meaningless comparison — an API honesty trap (the Policy §9-21 precedent). The
    # route raises the 400; this guard is belt-and-braces for any direct caller.
    if entity_id is not None:
        raise ValueError("scenarios are household-scoped")

    base = get_settings().base_currency
    val = await value_portfolio(session, base)  # §4.1
    nw = val.total_value

    # §9-4 — ONE DERIVATION. Exposures come from Portfolio's canonical allocation reader, never a
    # private holdings loop: crypto/property ARE allocation-by-class buckets; equities is the named
    # sum of its three class buckets; foreign_fx is the sum of the non-base currency buckets. One
    # figure feeds both pages (an equality test pins them). This closes the A11 defect class.
    by_class = val.allocation("asset_class")
    by_ccy = val.allocation("native_currency")
    equities = sum((by_class.get(c, ZERO) for c in _EQUITY_CLASSES), ZERO)
    crypto = by_class.get("crypto", ZERO)
    prop = by_class.get("property", ZERO)
    foreign = sum((v for k, v in by_ccy.items() if k != base), ZERO)

    def _shock(sid: str, name: str, exposure: Decimal, pct_down: int, group: str) -> dict:
        delta = exposure * Decimal(-pct_down) / 100
        new_nw = nw + delta
        return {
            "id": sid, "name": name, "group": group,
            "exposure": _f(exposure), "exposure_display": _money(exposure),
            "delta": _f(delta), "delta_display": _money(delta),
            "new_net_worth": _f(new_nw), "new_net_worth_display": _money(new_nw),
            "pct_change": _f((delta / nw * 100) if nw else ZERO, 1),
        }

    e1, e2, e3 = EQUITY_SHOCKS
    asset_scenarios = [
        _shock("equities_10", f"Equities fall {e1}%", equities, e1, "markets"),
        _shock("equities_20", f"Equities fall {e2}%", equities, e2, "markets"),
        _shock("equities_30", f"Equities fall {e3}%", equities, e3, "markets"),
        _shock("risk_20", f"Risk assets fall {RISK_SHOCK}% (equities + crypto)", equities + crypto, RISK_SHOCK, "markets"),
        _shock("crypto_50", f"Crypto falls {CRYPTO_SHOCK}%", crypto, CRYPTO_SHOCK, "markets"),
        _shock("property_10", f"Property falls {PROPERTY_SHOCK}%", prop, PROPERTY_SHOCK, "markets"),
        _shock("fx_10", f"Your foreign currencies weaken {FX_SHOCK}% vs base", foreign, FX_SHOCK, "fx"),
    ]

    # Liquidity what-ifs (deterministic, from the CANONICAL readers — perturbed, never re-derived).
    run = await runway_report(session)
    liquid = Decimal(str(run.get("liquid", 0)))
    monthly_expense = Decimal(str(run.get("monthly_expense", 0)))
    obs = await obligations_report(session)
    next_12m = Decimal(str(obs.get("next_12m_total", 0)))

    income_stop_runway = _f(liquid / monthly_expense, 1) if monthly_expense > 0 else None
    new_liquid = liquid - next_12m
    liquidity = {
        "liquid": _f(liquid), "liquid_display": _money(liquid),
        "runway_months": run.get("runway_months"),
        "income_stop": {
            "monthly_expense": _f(monthly_expense),
            "monthly_expense_display": _money(monthly_expense),
            "runway_months": income_stop_runway,
            "note": ("If recorded income stopped, liquid assets would cover recurring expenses for this long."
                     if income_stop_runway is not None else "Add recurring expenses in Cash flow to model this."),
        },
        "obligation_due": {
            "amount": _f(next_12m), "amount_display": _money(next_12m),
            "new_liquid": _f(new_liquid), "new_liquid_display": _money(new_liquid),
            "covered": bool(liquid >= next_12m),
            # §9-10 / SN-1 — the user's vocabulary ("expenses"), not the model's word "obligations".
            # next_12m_total is expense outflows only (page-cash-flow §10-1).
            "note": "If the next 12 months of recorded expenses were paid from liquid assets now.",
        },
    }

    # §9-2 — the A10 honesty layer. What-ifs run on today's market values, which may be stale; the
    # payload says so, so a scenario is never presented as resting on fresh values when it isn't.
    stale_inputs, low_confidence_inputs = portfolio_input_quality(val)

    return {
        "base_currency": base,
        "net_worth": _f(nw), "net_worth_display": _money(nw),
        "exposures": {
            "equities": _f(equities), "equities_display": _money(equities),
            "crypto": _f(crypto), "crypto_display": _money(crypto),
            "property": _f(prop), "property_display": _money(prop),
            "foreign_fx": _f(foreign), "foreign_fx_display": _money(foreign),
        },
        "asset_scenarios": asset_scenarios,
        "liquidity": liquidity,
        "stale_inputs": stale_inputs,
        "low_confidence_inputs": low_confidence_inputs,
        "inputs_stale": bool(stale_inputs or low_confidence_inputs),
        "inputs_note": inputs_quality_note(stale_inputs, low_confidence_inputs),
        "disclaimer": "Scenario, not forecast — arithmetic on today's values, not a prediction, "
                      "probability or recommendation. Real outcomes will differ.",
    }
