# SPDX-License-Identifier: AGPL-3.0-or-later
"""Durable audit for security events (§1.2/§1.3).

Auth failure handlers raise HTTPException, which makes the request-scoped session roll
back — so an AuditEvent added to it would be lost. Security-relevant events are therefore
written in their own committed session so the trail is real even when the request fails.
"""

from __future__ import annotations

from app.db.base import get_sessionmaker
from app.models import AuditEvent


async def record_security_event(action: str, detail: str | None = None) -> None:
    try:
        async with get_sessionmaker()() as s:
            s.add(AuditEvent(category="security", action=action, detail=detail))
            await s.commit()
    except Exception:  # noqa: BLE001 — auditing must never break the auth flow
        pass
