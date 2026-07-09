# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 5b: the markets overview carries country so the UI can group region-first."""

from __future__ import annotations


async def test_overview_items_carry_country(app_client):
    data = (await app_client.get("/api/v1/markets/overview")).json()
    items = data["instruments"]
    assert items and all("country" in it for it in items)
    # Demo spans multiple regions (US equities, an India name, a Singapore name).
    countries = {(it["country"] or "").upper() for it in items}
    assert "US" in countries
    assert countries & {"IN", "SG"}  # at least one non-US region present
