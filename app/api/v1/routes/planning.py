# SPDX-License-Identifier: AGPL-3.0-or-later
"""Goals & obligations endpoints (Phase 3b). Reads open; mutations PIN-protected.
Progress/totals are computed live and are reporting only — never advice."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_auth
from app.models import Goal, Obligation
from app.services.planning import (
    GOAL_BASES,
    OBLIGATION_KINDS,
    RECURRENCES,
    goals_report,
    obligations_report,
)

router = APIRouter()


class GoalIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    target_amount: float = Field(gt=0)
    target_date: str | None = Field(default=None, max_length=10)
    currency: str | None = Field(default=None, max_length=3)
    basis: str = "net_worth"
    note: str | None = Field(default=None, max_length=1000)


class ObligationIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    amount: float = Field(gt=0)
    due_date: str = Field(min_length=10, max_length=10)
    currency: str | None = Field(default=None, max_length=3)
    recurrence: str = "once"
    kind: str = "expense"
    note: str | None = Field(default=None, max_length=1000)


def _check_kind(kind: str) -> None:
    if kind not in OBLIGATION_KINDS:
        raise HTTPException(400, f"kind must be one of {OBLIGATION_KINDS}")


def _norm_ccy(c: str | None) -> str | None:
    c = (c or "").strip().upper()
    return c or None


# --- goals ------------------------------------------------------------------ #

@router.get("/goals")
async def get_goals(session: AsyncSession = Depends(get_db)) -> dict:
    return await goals_report(session)


@router.post("/goals", dependencies=[Depends(require_auth)])
async def create_goal(payload: GoalIn, session: AsyncSession = Depends(get_db)) -> dict:
    if payload.basis not in GOAL_BASES:
        raise HTTPException(400, f"basis must be one of {GOAL_BASES}")
    g = Goal(name=payload.name.strip()[:80], target_amount=Decimal(str(payload.target_amount)),
             target_date=(payload.target_date or None), currency=_norm_ccy(payload.currency),
             basis=payload.basis, note=(payload.note or None))
    session.add(g)
    await session.flush()
    return {"id": g.id}


@router.patch("/goals/{goal_id}", dependencies=[Depends(require_auth)])
async def update_goal(goal_id: int, payload: GoalIn, session: AsyncSession = Depends(get_db)) -> dict:
    if payload.basis not in GOAL_BASES:
        raise HTTPException(400, f"basis must be one of {GOAL_BASES}")
    g = await session.get(Goal, goal_id)
    if g is None:
        raise HTTPException(404, "goal not found")
    g.name = payload.name.strip()[:80]
    g.target_amount = Decimal(str(payload.target_amount))
    g.target_date = payload.target_date or None
    g.currency = _norm_ccy(payload.currency)
    g.basis = payload.basis
    g.note = payload.note or None
    await session.flush()
    return {"id": g.id}


@router.delete("/goals/{goal_id}", dependencies=[Depends(require_auth)])
async def delete_goal(goal_id: int, session: AsyncSession = Depends(get_db)) -> dict:
    g = await session.get(Goal, goal_id)
    if g is not None:
        await session.delete(g)
    return {"ok": True}


# --- obligations ------------------------------------------------------------ #

@router.get("/obligations")
async def get_obligations(session: AsyncSession = Depends(get_db)) -> dict:
    return await obligations_report(session)


@router.post("/obligations", dependencies=[Depends(require_auth)])
async def create_obligation(payload: ObligationIn, session: AsyncSession = Depends(get_db)) -> dict:
    if payload.recurrence not in RECURRENCES:
        raise HTTPException(400, f"recurrence must be one of {RECURRENCES}")
    _check_kind(payload.kind)
    o = Obligation(name=payload.name.strip()[:80], amount=Decimal(str(payload.amount)),
                   due_date=payload.due_date, currency=_norm_ccy(payload.currency),
                   recurrence=payload.recurrence, kind=payload.kind, note=(payload.note or None))
    session.add(o)
    await session.flush()
    return {"id": o.id}


@router.patch("/obligations/{obligation_id}", dependencies=[Depends(require_auth)])
async def update_obligation(obligation_id: int, payload: ObligationIn, session: AsyncSession = Depends(get_db)) -> dict:
    if payload.recurrence not in RECURRENCES:
        raise HTTPException(400, f"recurrence must be one of {RECURRENCES}")
    _check_kind(payload.kind)
    o = await session.get(Obligation, obligation_id)
    if o is None:
        raise HTTPException(404, "obligation not found")
    o.name = payload.name.strip()[:80]
    o.amount = Decimal(str(payload.amount))
    o.due_date = payload.due_date
    o.currency = _norm_ccy(payload.currency)
    o.recurrence = payload.recurrence
    o.kind = payload.kind
    o.note = payload.note or None
    await session.flush()
    return {"id": o.id}


@router.delete("/obligations/{obligation_id}", dependencies=[Depends(require_auth)])
async def delete_obligation(obligation_id: int, session: AsyncSession = Depends(get_db)) -> dict:
    o = await session.get(Obligation, obligation_id)
    if o is not None:
        await session.delete(o)
    return {"ok": True}


# --- Contributions (W8) --------------------------------------------------- #
class ContributionIn(BaseModel):
    name: str = Field(max_length=120)
    amount: float = 0
    currency: str | None = Field(default=None, max_length=3)
    frequency: str = "monthly"
    kind: str = "invest"
    target_goal_id: int | None = None
    start_date: str | None = None
    active: bool = True
    note: str | None = Field(default=None, max_length=2000)


@router.get("/contributions")
async def get_contributions(session: AsyncSession = Depends(get_db)) -> dict:
    from app.services.contributions import contributions_report

    return await contributions_report(session)


@router.post("/contributions", dependencies=[Depends(require_auth)])
async def add_contribution(payload: ContributionIn, session: AsyncSession = Depends(get_db)) -> dict:
    from app.services.contributions import create_contribution

    res = await create_contribution(session, payload.model_dump())
    await session.commit()
    return {"ok": True, **res}


@router.patch("/contributions/{cid}", dependencies=[Depends(require_auth)])
async def edit_contribution(cid: int, payload: ContributionIn, session: AsyncSession = Depends(get_db)) -> dict:
    from app.services.contributions import update_contribution

    try:
        res = await update_contribution(session, cid, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    await session.commit()
    return {"ok": True, **res}


@router.delete("/contributions/{cid}", dependencies=[Depends(require_auth)])
async def remove_contribution(cid: int, session: AsyncSession = Depends(get_db)) -> dict:
    from app.services.contributions import delete_contribution

    await delete_contribution(session, cid)
    await session.commit()
    return {"ok": True}
