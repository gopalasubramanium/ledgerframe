# SPDX-License-Identifier: AGPL-3.0-or-later
"""Session-token validation with server-side revocation (§1.7).

Layered on top of the signed-token check in ``core.security``:
  * per-token revocation — /auth/lock records the presented token's ``jti``;
  * revoke-all — a PIN change bumps ``users.tokens_valid_after`` so every token issued
    at/before that instant becomes invalid.
"""

from __future__ import annotations

import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.models import RevokedToken, User


async def token_is_valid(token: str, session: AsyncSession) -> bool:
    payload = decode_token(token)
    if not payload:
        return False
    iat = float(payload.get("iat", 0))
    user = (await session.execute(select(User).limit(1))).scalars().first()
    if user and float(user.tokens_valid_after or 0) > float(iat):
        return False  # revoked-all cutoff (PIN change)
    jti = payload.get("jti")
    if jti:
        revoked = (await session.execute(
            select(RevokedToken).where(RevokedToken.jti == jti))).scalars().first()
        if revoked is not None:
            return False  # individually revoked (lock)
    return True


async def revoke_token(token: str | None, session: AsyncSession) -> None:
    """Revoke a single token by its jti (idempotent)."""
    if not token:
        return
    payload = decode_token(token)
    jti = payload.get("jti") if payload else None
    if not jti:
        return
    exists = (await session.execute(
        select(RevokedToken).where(RevokedToken.jti == jti))).scalars().first()
    if exists is None:
        session.add(RevokedToken(jti=jti))


async def revoke_all(session: AsyncSession) -> None:
    """Invalidate every existing token (bump the cutoff). New tokens issued after this
    instant remain valid."""
    user = (await session.execute(select(User).limit(1))).scalars().first()
    if user is not None:
        user.tokens_valid_after = time.time()
