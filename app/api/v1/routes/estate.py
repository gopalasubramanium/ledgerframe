# SPDX-License-Identifier: AGPL-3.0-or-later
"""Estate & document readiness (W4) — family governance, never legal advice."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_auth
from app.services.estate import (
    create_contact,
    create_document,
    delete_contact,
    delete_document,
    estate_report,
    update_contact,
    update_document,
    update_profile,
)

router = APIRouter()


def reject_entity_id(entity_id: int | None = Query(default=None)) -> None:
    """page-estate §9-2 — the estate register is household-scoped (no entity FK, D-063). A scope
    param is REJECTED, not silently ignored: it could only produce a precise-looking, meaningless
    answer. Applied to EVERY estate endpoint (reads + writes) so the contract is honest everywhere;
    ordered before `require_auth` so the malformed request is rejected regardless of lock state."""
    if entity_id is not None:
        raise HTTPException(400, "the estate register is household-scoped: it cannot be filtered to one entity")


class ProfileIn(BaseModel):
    will_status: str | None = None
    will_location: str | None = Field(default=None, max_length=160)
    executor: str | None = Field(default=None, max_length=120)
    last_reviewed: str | None = None
    next_review_date: str | None = None
    notes: str | None = Field(default=None, max_length=2000)


class ContactIn(BaseModel):
    name: str = Field(max_length=120)
    # `relationship` retired (page-estate §9-5): roles is the canonical vocabulary; a stray
    # `relationship` in a request body is ignored (extra field), never persisted or served.
    roles: list[str] = Field(default_factory=list)
    phone: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=2000)


class DocumentIn(BaseModel):
    title: str = Field(max_length=120)
    category: str = "other"
    location: str | None = Field(default=None, max_length=160)
    status: str = "present"
    review_date: str | None = None
    related_to: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=2000)


@router.get("/estate", dependencies=[Depends(reject_entity_id)])
async def get_estate(session: AsyncSession = Depends(get_db)) -> dict:
    return await estate_report(session)


@router.put("/estate/profile", dependencies=[Depends(reject_entity_id), Depends(require_auth)])
async def put_profile(payload: ProfileIn, session: AsyncSession = Depends(get_db)) -> dict:
    res = await update_profile(session, payload.model_dump(exclude_none=False))
    await session.commit()
    return {"ok": True, **res}


@router.post("/estate/contacts", dependencies=[Depends(reject_entity_id), Depends(require_auth)])
async def add_contact(payload: ContactIn, session: AsyncSession = Depends(get_db)) -> dict:
    res = await create_contact(session, payload.model_dump())
    await session.commit()
    return {"ok": True, **res}


@router.patch("/estate/contacts/{cid}", dependencies=[Depends(reject_entity_id), Depends(require_auth)])
async def edit_contact(cid: int, payload: ContactIn, session: AsyncSession = Depends(get_db)) -> dict:
    try:
        res = await update_contact(session, cid, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    await session.commit()
    return {"ok": True, **res}


@router.delete("/estate/contacts/{cid}", dependencies=[Depends(reject_entity_id), Depends(require_auth)])
async def remove_contact(cid: int, session: AsyncSession = Depends(get_db)) -> dict:
    await delete_contact(session, cid)
    await session.commit()
    return {"ok": True}


@router.post("/estate/documents", dependencies=[Depends(reject_entity_id), Depends(require_auth)])
async def add_document(payload: DocumentIn, session: AsyncSession = Depends(get_db)) -> dict:
    res = await create_document(session, payload.model_dump())
    await session.commit()
    return {"ok": True, **res}


@router.patch("/estate/documents/{did}", dependencies=[Depends(reject_entity_id), Depends(require_auth)])
async def edit_document(did: int, payload: DocumentIn, session: AsyncSession = Depends(get_db)) -> dict:
    try:
        res = await update_document(session, did, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    await session.commit()
    return {"ok": True, **res}


@router.delete("/estate/documents/{did}", dependencies=[Depends(reject_entity_id), Depends(require_auth)])
async def remove_document(did: int, session: AsyncSession = Depends(get_db)) -> dict:
    await delete_document(session, did)
    await session.commit()
    return {"ok": True}
