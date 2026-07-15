# SPDX-License-Identifier: AGPL-3.0-or-later
"""Insurance page-build Phase 0 — the §9 contract/behaviour deltas, fail-first.

Each test is written to be RED on the pre-delta code and GREEN after the delta it guards
(page-insurance §9). Grouped by the ruling number it pins.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta


async def _base(app_client) -> str:
    return (await app_client.get("/api/v1/insurance")).json()["base_currency"]


# --------------------------------------------------------------------------- #
# 9-10 + 9-4 (Amendment A) — count is ACTIVE-only, and money is served as display strings.
# --------------------------------------------------------------------------- #
async def test_count_and_totals_count_active_only(app_client):
    """`count` must agree with the totals it rides beside on Net worth's D-081 line (active only).
    RED today: `count` = len(all rows) = 2 while the totals sum 1 active policy (Amendment A cause i)."""
    base = await _base(app_client)
    await app_client.post("/api/v1/insurance", json={
        "name": "Active Term", "policy_type": "term_life", "cover_amount": 100000,
        "currency": base, "cash_value": 5000, "premium_frequency": "annual", "status": "active"})
    await app_client.post("/api/v1/insurance", json={
        "name": "Lapsed Whole", "policy_type": "whole_life", "cover_amount": 200000,
        "currency": base, "cash_value": 9000, "premium_frequency": "annual", "status": "lapsed"})
    rep = (await app_client.get("/api/v1/insurance")).json()
    assert rep["count"] == 1                    # active-only — RED today (== 2)
    assert rep["total_cover"] == 100000         # lapsed excluded from totals
    assert rep["total_cash_value"] == 5000
    assert len(rep["policies"]) == 2            # both still visible in the records table


async def test_money_served_as_display_strings(app_client):
    """D-105: every money figure is served as a display string (Amendment A cause ii).
    RED today: the `*_display` keys do not exist."""
    base = await _base(app_client)
    await app_client.post("/api/v1/insurance", json={
        "name": "Term Life", "policy_type": "term_life", "cover_amount": 500000,
        "currency": base, "cash_value": 12000, "premium": 1200,
        "premium_frequency": "annual", "status": "active"})
    rep = (await app_client.get("/api/v1/insurance")).json()
    assert rep["total_cover_display"] == "500,000.00"
    assert rep["total_cash_value_display"] == "12,000.00"
    assert rep["total_annual_premium_display"] == "1,200.00"
    pol = rep["policies"][0]
    assert pol["cover_amount_display"] == "500,000.00"
    assert pol["cash_value_display"] == "12,000.00"
    assert pol["premium_display"] == "1,200.00"
    # a missing money figure stays honestly empty, never a fabricated 0 (Guarantee 3)
    await app_client.post("/api/v1/insurance", json={
        "name": "No Cash", "policy_type": "health", "cover_amount": 50000,
        "currency": base, "premium_frequency": "annual", "status": "active"})
    rep = (await app_client.get("/api/v1/insurance")).json()
    no_cash = next(p for p in rep["policies"] if p["name"] == "No Cash")
    assert no_cash["cash_value_display"] is None
    assert no_cash["premium_display"] is None
