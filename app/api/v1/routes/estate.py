# SPDX-License-Identifier: AGPL-3.0-or-later
"""Estate & document readiness (W4) — family governance, never legal advice."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
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


class ProfileIn(BaseModel):
    will_status: str | None = None
    will_location: str | None = Field(default=None, max_length=160)
    executor: str | None = Field(default=None, max_length=120)
    last_reviewed: str | None = None
    next_review_date: str | None = None
    notes: str | None = Field(default=None, max_length=2000)


class ContactIn(BaseModel):
    name: str = Field(max_length=120)
    relationship: str | None = Field(default=None, max_length=60)
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


@router.get("/estate")
async def get_estate(session: AsyncSession = Depends(get_db)) -> dict:
    return await estate_report(session)


@router.put("/estate/profile", dependencies=[Depends(require_auth)])
async def put_profile(payload: ProfileIn, session: AsyncSession = Depends(get_db)) -> dict:
    res = await update_profile(session, payload.model_dump(exclude_none=False))
    await session.commit()
    return {"ok": True, **res}


@router.post("/estate/contacts", dependencies=[Depends(require_auth)])
async def add_contact(payload: ContactIn, session: AsyncSession = Depends(get_db)) -> dict:
    res = await create_contact(session, payload.model_dump())
    await session.commit()
    return {"ok": True, **res}


@router.patch("/estate/contacts/{cid}", dependencies=[Depends(require_auth)])
async def edit_contact(cid: int, payload: ContactIn, session: AsyncSession = Depends(get_db)) -> dict:
    try:
        res = await update_contact(session, cid, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    await session.commit()
    return {"ok": True, **res}


@router.delete("/estate/contacts/{cid}", dependencies=[Depends(require_auth)])
async def remove_contact(cid: int, session: AsyncSession = Depends(get_db)) -> dict:
    await delete_contact(session, cid)
    await session.commit()
    return {"ok": True}


@router.post("/estate/documents", dependencies=[Depends(require_auth)])
async def add_document(payload: DocumentIn, session: AsyncSession = Depends(get_db)) -> dict:
    res = await create_document(session, payload.model_dump())
    await session.commit()
    return {"ok": True, **res}


@router.patch("/estate/documents/{did}", dependencies=[Depends(require_auth)])
async def edit_document(did: int, payload: DocumentIn, session: AsyncSession = Depends(get_db)) -> dict:
    try:
        res = await update_document(session, did, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    await session.commit()
    return {"ok": True, **res}


@router.delete("/estate/documents/{did}", dependencies=[Depends(require_auth)])
async def remove_document(did: int, session: AsyncSession = Depends(get_db)) -> dict:
    await delete_document(session, did)
    await session.commit()
    return {"ok": True}
