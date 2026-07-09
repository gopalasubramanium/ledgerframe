# SPDX-License-Identifier: AGPL-3.0-or-later
"""Scoped read-only API tokens (§2.4) — PIN-gated management.

Create/revoke require an authenticated session (require_session), so a read-only API token can
neither mint nor revoke tokens (it is rejected with 403 on those mutating calls). The raw
token is returned once at creation and is never retrievable afterwards.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_session
from app.models import AuditEvent
from app.services.api_tokens import create_token, list_tokens, revoke_token

router = APIRouter()


class TokenIn(BaseModel):
    name: str = Field(default="API token", max_length=80)


@router.get("/tokens", dependencies=[Depends(require_session)])
async def get_tokens(session: AsyncSession = Depends(get_db)) -> dict:
    """List token metadata (never the raw token or its hash)."""
    return {"tokens": await list_tokens(session)}


@router.post("/tokens", dependencies=[Depends(require_session)])
async def create(payload: TokenIn, session: AsyncSession = Depends(get_db)) -> dict:
    tok, raw = await create_token(session, payload.name)
    session.add(AuditEvent(category="security", action="api_token_created", detail=tok.prefix))
    await session.commit()
    return {"id": tok.id, "name": tok.name, "prefix": tok.prefix, "token": raw,
            "note": "Store this now — it is shown only once and cannot be retrieved. "
                    "Use it read-only: Authorization: Token <token> on GET requests."}


@router.delete("/tokens/{token_id}", dependencies=[Depends(require_session)])
async def revoke(token_id: int, session: AsyncSession = Depends(get_db)) -> dict:
    if not await revoke_token(session, token_id):
        raise HTTPException(404, "token not found")
    session.add(AuditEvent(category="security", action="api_token_revoked", detail=str(token_id)))
    await session.commit()
    return {"ok": True}
