# SPDX-License-Identifier: AGPL-3.0-or-later
"""§4.6 cost-of-ownership — read-only. Two honestly-distinct blocks, deliberately never blended:

  • ``recorded_fees`` — the selected-year fee total the statements report already computes (a real
    currency fact from FEE transactions + every transaction's fee/tax fields), REUSED as the single
    source so the two surfaces can't diverge. Currency-only: annualising a historical fee would need
    a fabricated denominator, so no percentage is offered here.
  • ``estimated_ongoing_cost`` — a forward ESTIMATE: each instrument-linked holding's current value
    × its instrument's ``annual_cost_bps`` ÷ 10 000. Holdings whose instrument has NO expense ratio
    set are excluded from the sum and surfaced as unavailable-with-reason — never counted as 0 (that
    would fabricate a fact) — with a covers-N-of-M coverage count.

There is deliberately NO combined 'total cost of ownership' key: recorded (historical, realised)
and estimated (forward) sit on different footings, so fusing them would be dishonest. This reads the
OUTPUTS of ``value_portfolio`` and ``statements_report`` only — no FIFO/cost-basis or valuation math
is touched.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.money import ZERO, to_display
from app.models import Holding, Instrument
from app.services.portfolio import entity_account_filter, value_portfolio
from app.services.statements import statements_report

_BPS = Decimal(10000)   # basis-points denominator: cost = value × bps / 10 000


async def cost_of_ownership(session: AsyncSession, base: str, year: int | None = None,
                            entity_id: int | None = None) -> dict:
    """Recorded fees (currency fact) and estimated ongoing cost (expense-ratio × value), as two
    separate blocks with no blended total. ``entity_id`` scopes to one ownership entity (§4.1);
    soft-deleted holdings/transactions are excluded — both inherited from the sibling readers."""
    # (a) Recorded fees — reuse the statements report's selected-year fee total (single source, so
    # this surface can never diverge from Reports). A currency-only fact; no annualised percentage.
    st = await statements_report(session, year=year, entity_id=entity_id)
    yr = st["year"]
    fees = st["fees"]
    recorded_fees = {
        "currency": base,
        "year": yr,
        "label": f"fees recorded in {yr}",
        "total": fees["total"],              # identical object to statements' — not a re-sum (R5)
        "commissions": fees["commissions"],
        "taxes": fees["taxes"],
    }

    # (b) Estimated ongoing cost — bps × current value over instrument-linked holdings whose
    # instrument has a non-null expense ratio. value_portfolio gives the current value per holding;
    # a matching Holding query (same entity + soft-delete filters value_portfolio uses) maps each
    # holding to its instrument, whose annual_cost_bps carries the rate.
    val = await value_portfolio(session, base, entity_id=entity_id)
    hq = select(Holding).where(Holding.deleted_at.is_(None))
    ef = entity_account_filter(Holding, entity_id)  # §4.1: no-op when entity_id is None
    if ef is not None:
        hq = hq.where(ef)
    instr_of = {h.id: h.instrument_id for h in (await session.execute(hq)).scalars()}
    instruments = {i.id: i for i in (await session.execute(select(Instrument))).scalars()}

    total_est = ZERO
    covered_value = ZERO
    covered_rows: list[dict] = []
    unavailable: list[dict] = []
    for hv in val.holdings:
        iid = instr_of.get(hv.holding_id)
        if iid is None or hv.market_value_base <= ZERO:
            continue  # manual assets / non-positive positions carry no expense-ratio concept
        bps = instruments[iid].annual_cost_bps if iid in instruments else None
        if bps is None:
            # Null expense ratio → excluded from the sum and surfaced with a reason. NEVER 0.
            unavailable.append({"symbol": hv.symbol, "label": hv.label,
                                "reason": "no expense ratio (annual_cost_bps) set"})
            continue
        est = hv.market_value_base * bps / _BPS
        total_est += est
        covered_value += hv.market_value_base
        covered_rows.append({
            "symbol": hv.symbol, "label": hv.label,
            "market_value_base": to_display(hv.market_value_base),
            "annual_cost_bps": to_display(bps),
            "estimated_annual_cost": to_display(est),
        })

    covered = len(covered_rows)
    total = covered + len(unavailable)
    available = covered > 0
    estimated_ongoing_cost = {
        "currency": base,
        "available": available,
        # Forward estimate, currency-primary. None (not 0) when nothing has a rate set — an empty
        # estimate is unavailable, never a fabricated zero.
        "estimated_annual_total": to_display(total_est) if available else None,
        "covered_value": to_display(covered_value) if available else None,  # honest %-denominator
        "covered": covered,
        "total": total,
        "coverage_label": f"covers {covered} of {total} holdings",
        "holdings": covered_rows,       # only holdings WITH a rate; each carries its own bps + cost
        "unavailable": unavailable,     # null-rate holdings, surfaced with a reason (never 0)
        "note": "Estimate — the fund's expense ratio applied to today's value, not a fee you paid; "
                "excludes holdings with no expense ratio set.",
    }

    # Two separate blocks; NO combined 'total cost of ownership' key (R2 — different footings).
    return {
        "base_currency": base,
        "recorded_fees": recorded_fees,
        "estimated_ongoing_cost": estimated_ongoing_cost,
    }
