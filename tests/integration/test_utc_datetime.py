# SPDX-License-Identifier: AGPL-3.0-or-later
"""Issue #18 — UTCDateTime: model datetimes always round-trip as tz-aware UTC."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from app.db.base import get_sessionmaker
from app.models import AuditEvent


async def test_datetime_column_returns_aware_utc(app_client):
    async with get_sessionmaker()() as s:
        # Write an AWARE datetime …
        ev = AuditEvent(category="test", action="tz", ts=datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC))
        s.add(ev)
        await s.commit()
        eid = ev.id

    async with get_sessionmaker()() as s:
        got = (await s.execute(select(AuditEvent).where(AuditEvent.id == eid))).scalars().one()
        assert got.ts.tzinfo is not None                 # aware, not naive
        assert got.ts.utcoffset().total_seconds() == 0   # UTC
        # The #18 failure was comparing this with an aware 'now' → must not raise.
        _ = datetime.now(UTC) - got.ts
