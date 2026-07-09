# SPDX-License-Identifier: AGPL-3.0-or-later
"""Scoped read-only API tokens (§2.4) — create/list/revoke and per-request validation.

Only a SHA-256 hash of each token is stored; the raw value is returned once at creation and
can never be retrieved. Tokens are usable only on GET requests (enforced in deps).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import generate_api_token, hash_api_token
from app.db.base import utcnow
from app.models import ApiToken

_TOUCH_AFTER_SECONDS = 60  # throttle last_used_at writes so a GET isn't a write every time


async def create_token(session: AsyncSession, name: str | None) -> tuple[ApiToken, str]:
    raw, token_hash, prefix = generate_api_token()
    tok = ApiToken(name=(name or "API token").strip()[:80] or "API token",
                   token_hash=token_hash, prefix=prefix)
    session.add(tok)
    await session.flush()
    return tok, raw


def _serialize(t: ApiToken) -> dict:
    return {"id": t.id, "name": t.name, "prefix": t.prefix,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "last_used_at": t.last_used_at.isoformat() if t.last_used_at else None,
            "revoked": t.revoked_at is not None}


async def list_tokens(session: AsyncSession) -> list[dict]:
    rows = (await session.execute(select(ApiToken).order_by(ApiToken.created_at.desc()))).scalars().all()
    return [_serialize(t) for t in rows]  # never includes the raw token or its hash


async def revoke_token(session: AsyncSession, token_id: int) -> bool:
    t = await session.get(ApiToken, token_id)
    if t is None:
        return False
    if t.revoked_at is None:
        t.revoked_at = utcnow()
    await session.flush()
    return True


async def validate_token(session: AsyncSession, raw: str) -> ApiToken | None:
    """Return the active (non-revoked) token matching ``raw``, else None. Touches
    last_used_at (throttled). Comparison is by indexed hash lookup — constant work."""
    if not raw:
        return None
    t = (await session.execute(
        select(ApiToken).where(ApiToken.token_hash == hash_api_token(raw),
                               ApiToken.revoked_at.is_(None)))).scalars().first()
    if t is None:
        return None
    now = datetime.now(UTC)
    if t.last_used_at is None or (now - t.last_used_at).total_seconds() > _TOUCH_AFTER_SECONDS:
        t.last_used_at = now
    return t
