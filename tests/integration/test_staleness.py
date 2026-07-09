# SPDX-License-Identifier: AGPL-3.0-or-later
"""One-click stale-refresh prompt: the read-only /system/staleness signal."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


async def test_staleness_shape_and_fresh_demo(app_client):
    r = (await app_client.get("/api/v1/system/staleness")).json()
    assert set(r) == {"stale", "count", "refreshable"}
    # Freshly-seeded demo quotes are current → nothing stale → no banner.
    assert r["stale"] is False and r["count"] == 0 and r["refreshable"] is False


async def test_staleness_detects_old_quotes(app_client):
    from sqlalchemy import update

    from app.db.base import get_sessionmaker
    from app.models import Quote

    # Populate quote rows (they're created lazily), then age them past the threshold.
    await app_client.post("/api/v1/system/refresh-data")
    async with get_sessionmaker()() as s:
        await s.execute(update(Quote).values(received_at=datetime.now(UTC) - timedelta(days=30)))
        await s.commit()

    r = (await app_client.get("/api/v1/system/staleness")).json()
    assert r["stale"] is True and r["count"] > 0
    # mock provider fetches on demand → a refresh could help.
    assert r["refreshable"] is True


async def test_staleness_is_read_only_and_needs_no_auth(app_client):
    # No PIN set yet; the signal is a plain GET with no side effects.
    before = (await app_client.get("/api/v1/system/staleness")).json()
    after = (await app_client.get("/api/v1/system/staleness")).json()
    assert before == after


def test_eod_quotes_are_not_stale_within_the_day():
    """(i) An end-of-day / NAV quote is the day's authoritative value — not 'stale' 15
    minutes later; only after it misses a full day's publish."""
    from datetime import UTC, datetime, timedelta

    from app.services.market import _is_stale

    six_hours = datetime.now(UTC) - timedelta(hours=6)
    assert _is_stale(six_hours, "delayed") is True          # intraday delayed → stale
    assert _is_stale(six_hours, "end-of-day") is False       # daily value → still fresh
    assert _is_stale(six_hours, "official_nav") is False
    forty_hours = datetime.now(UTC) - timedelta(hours=40)
    assert _is_stale(forty_hours, "end-of-day") is True      # missed a day → stale
