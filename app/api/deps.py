# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared API dependencies: authentication for mutating endpoints.

Auth model: a single local PIN. When no PIN is set (fresh demo install) the app
is unlocked and mutations are allowed locally — but if LAN access is enabled a
PIN is mandatory. The session token is a signed, time-limited cookie/bearer.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.base import get_session
from app.models import User
from app.services.sessions import token_is_valid

SESSION_COOKIE = "lf_session"


def _bearer(lf_session: str | None, authorization: str | None) -> str | None:
    if lf_session:
        return lf_session
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:]
    return None


def _token_scheme(authorization: str | None) -> str | None:
    """Raw API token from `Authorization: Token <raw>` — distinct from a `Bearer` session."""
    if authorization and authorization.lower().startswith("token "):
        return authorization[6:].strip() or None
    return None


async def _api_token_or_none(request: Request, session: AsyncSession, authorization: str | None):
    """Validate an `Authorization: Token` header and enforce read-only (§2.4).

    Returns the ApiToken for a valid GET/HEAD; raises 403 on any mutating method; raises 401
    if the token is invalid/revoked; returns None when no Token header is present."""
    raw = _token_scheme(authorization)
    if raw is None:
        return None
    from app.services.api_tokens import validate_token

    tok = await validate_token(session, raw)
    if tok is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or revoked API token.")
    if request.method not in ("GET", "HEAD"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This API token is read-only.")
    return tok


def _read_stays_open(path: str) -> bool:
    """Endpoints that must remain reachable even when locked, so the lock screen can
    check state and unlock. All auth endpoints; everything else under /api/v1 is gated."""
    return path.startswith("/api/v1/auth/")


_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost", "::ffff:127.0.0.1"})


async def get_db() -> AsyncIterator[AsyncSession]:  # pragma: no cover - thin wrapper
    async for s in get_session():
        yield s


async def pin_is_set(session: AsyncSession) -> bool:
    user = (await session.execute(select(User).limit(1))).scalars().first()
    return bool(user and user.pin_hash)


class PinConfirm(BaseModel):
    """Body for a D-103 irreversible action — the freshly-entered PIN (§14dr-20)."""

    pin: str = Field(min_length=6, max_length=32)


async def verify_fresh_pin(session: AsyncSession, pin: str | None) -> None:
    """D-103 (SECURITY-BASELINE §3): an irreversible purge ALWAYS demands a freshly-entered
    PIN. An unlocked/ambient session NEVER satisfies it — the submitted PIN is verified
    against the stored hash, and the session token is deliberately not accepted in its place,
    so the point of no return requires deliberate re-entry rather than ambient authority.

    Pair this with ``require_pin`` on the endpoint: the guard keeps the action off API tokens
    and unprotected installs; this checks the fresh PIN that the session can never stand in for.
    """
    from app.core.security import verify_pin

    user = (await session.execute(select(User).limit(1))).scalars().first()
    if not user or not user.pin_hash:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Set a PIN before permanently deleting data.",
        )
    if not pin or not verify_pin(pin, user.pin_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Enter your PIN to permanently delete — an unlocked session is not enough.",
        )


async def require_auth(
    request: Request,
    session: AsyncSession = Depends(get_db),
    lf_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
) -> None:
    """Guard mutating endpoints. Raises 401 when a PIN is set and no valid session token.

    A read-only API token can never mutate: if a Token header is present it is rejected here
    with 403 (§2.4)."""
    await _api_token_or_none(request, session, authorization)  # 403 on a mutation with a token
    settings = get_settings()
    token = lf_session
    if not token and authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:]

    has_pin = await pin_is_set(session)

    # If LAN access is on, a PIN must exist and a valid token is always required.
    if settings.allow_lan and not has_pin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A local PIN must be set before enabling LAN access.",
        )

    if not has_pin:
        return  # local-only, unlocked demo install

    if not token or not await token_is_valid(token, session):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Locked. Unlock with your PIN.",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_read_auth(
    request: Request,
    session: AsyncSession = Depends(get_db),
    lf_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
) -> None:
    """Gate data-bearing endpoints when a PIN is set (§1.1).

    Applied router-wide to /api/v1. When **no PIN** is set the current open behaviour is
    preserved. Auth endpoints (and CORS preflight) stay open so the lock screen can check
    state and unlock. Mutating endpoints additionally carry ``require_auth``."""
    if request.method == "OPTIONS" or _read_stays_open(request.url.path):
        return
    # §2.4 — a valid read-only API token authenticates GET/HEAD (and is rejected on any
    # mutation with 403). This applies regardless of whether a PIN is set.
    if await _api_token_or_none(request, session, authorization) is not None:
        return
    if not await pin_is_set(session):
        return  # no PIN → open, exactly as before
    token = _bearer(lf_session, authorization)
    if not token or not await token_is_valid(token, session):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Locked. Unlock with your PIN.",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_metrics_access(
    request: Request,
    session: AsyncSession = Depends(get_db),
    lf_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
) -> None:
    """/metrics gate (§2.3): allowed from loopback, or with a valid session — never
    unauthenticated over the network, consistent with the Phase-1 auth pattern."""
    if request.client and request.client.host in _LOOPBACK_HOSTS:
        return
    token = _bearer(lf_session, authorization)
    if not token or not await token_is_valid(token, session):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Metrics are restricted to loopback or an authenticated session.",
        )


async def require_session(
    session: AsyncSession = Depends(get_db),
    lf_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
) -> None:
    """Require a human session; reject API tokens outright (§2.4).

    Used for token management so a read-only API token can neither list, mint, nor revoke
    tokens. Open on a no-PIN local install, consistent with the rest of the auth model."""
    if _token_scheme(authorization) is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API tokens cannot manage tokens — use your session/PIN.",
        )
    if not await pin_is_set(session):
        return  # local unlocked
    token = _bearer(lf_session, authorization)
    if not token or not await token_is_valid(token, session):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticate with your PIN.",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_pin(
    session: AsyncSession = Depends(get_db),
    lf_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
) -> None:
    """Guard PERMANENT, irreversible actions (§3.5 hard delete / empty trash).

    Strictly stronger than ``require_auth``/``require_session``: a valid human session is
    ALWAYS required, and — because destroying data must be impossible on an unprotected
    install — it **refuses outright when no PIN has been set** (403), rather than falling
    open the way the other guards do locally. API tokens can never authorise it."""
    if _token_scheme(authorization) is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API tokens cannot permanently delete — use your session/PIN.",
        )
    if not await pin_is_set(session):
        # No PIN → no way to authorise an irreversible delete. Set a PIN first.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Set a PIN before permanently deleting data.",
        )
    token = _bearer(lf_session, authorization)
    if not token or not await token_is_valid(token, session):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticate with your PIN to permanently delete.",
            headers={"WWW-Authenticate": "Bearer"},
        )
