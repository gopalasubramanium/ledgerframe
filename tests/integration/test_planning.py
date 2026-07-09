# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 3b — goals & obligations (live progress + recurrence expansion)."""

from __future__ import annotations

from datetime import date


def test_add_months_clamps_and_rolls_over():
    from app.services.planning import _add_months
    assert _add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)     # clamp short month
    assert _add_months(date(2026, 11, 15), 3) == date(2027, 2, 15)    # year rollover


async def test_goal_crud_and_progress(app_client):
    r = await app_client.post("/api/v1/goals", json={"name": "Retire", "target_amount": 1_000_000, "basis": "net_worth"})
    assert r.status_code == 200
    gid = r.json()["id"]
    g = next(x for x in (await app_client.get("/api/v1/goals")).json()["goals"] if x["id"] == gid)
    assert g["current_base"] is not None and g["progress_pct"] is not None

    await app_client.patch(f"/api/v1/goals/{gid}", json={"name": "Retire", "target_amount": 2_000_000, "basis": "net_worth"})
    g2 = next(x for x in (await app_client.get("/api/v1/goals")).json()["goals"] if x["id"] == gid)
    assert g2["target_base"] == 2_000_000

    await app_client.delete(f"/api/v1/goals/{gid}")
    assert not any(x["id"] == gid for x in (await app_client.get("/api/v1/goals")).json()["goals"])


async def test_goal_basis_none_has_no_auto_progress(app_client):
    await app_client.post("/api/v1/goals", json={"name": "House deposit", "target_amount": 100_000, "basis": "none"})
    g = next(x for x in (await app_client.get("/api/v1/goals")).json()["goals"] if x["name"] == "House deposit")
    assert g["progress_pct"] is None and g["current_base"] is None


async def test_goal_cross_currency_target_converted(app_client):
    await app_client.post("/api/v1/goals", json={"name": "USD goal", "target_amount": 10_000, "currency": "USD", "basis": "net_worth"})
    g = next(x for x in (await app_client.get("/api/v1/goals")).json()["goals"] if x["name"] == "USD goal")
    # 10,000 USD → base at current FX (not equal to 10,000 unless base is USD).
    assert g["target_base"] > 0


async def test_obligation_recurrence_next_12m(app_client):
    # A monthly obligation anchored in the past advances into the window → ~12 occurrences.
    await app_client.post("/api/v1/obligations", json={"name": "Rent", "amount": 1000, "due_date": "2020-06-15", "recurrence": "monthly"})
    await app_client.post("/api/v1/obligations", json={"name": "Premium", "amount": 1200, "due_date": "2020-06-15", "recurrence": "annual"})
    d = (await app_client.get("/api/v1/obligations")).json()
    rent = next(o for o in d["obligations"] if o["name"] == "Rent")
    premium = next(o for o in d["obligations"] if o["name"] == "Premium")
    assert 11 <= rent["occurrences_12m"] <= 13        # monthly ≈ 12/yr
    assert premium["occurrences_12m"] == 1            # annual = 1/yr
    assert d["next_12m_total"] >= 11 * 1000 + 1200


async def test_planning_validation(app_client):
    assert (await app_client.post("/api/v1/goals", json={"name": "x", "target_amount": 1, "basis": "bogus"})).status_code == 400
    assert (await app_client.post("/api/v1/obligations", json={"name": "x", "amount": 1, "due_date": "2026-08-01", "recurrence": "weekly"})).status_code == 400
    assert (await app_client.post("/api/v1/goals", json={"name": "x", "target_amount": -5})).status_code == 422
