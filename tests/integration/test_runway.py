# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 4a — cash runway (liquid ÷ recurring net burn; honest when no data)."""

from __future__ import annotations


async def test_runway_no_data_is_honest(app_client):
    d = (await app_client.get("/api/v1/portfolio/runway")).json()
    assert d["status"] == "no_data" and d["runway_months"] is None
    assert "add recurring" in d["note"].lower()


async def test_runway_finite_expenses_only(app_client):
    await app_client.post("/api/v1/obligations", json={
        "name": "Rent", "amount": 2000, "due_date": "2026-08-01", "recurrence": "monthly", "kind": "expense"})
    d = (await app_client.get("/api/v1/portfolio/runway")).json()
    assert d["status"] == "finite"
    assert d["monthly_expense"] == 2000 and d["net_monthly_burn"] == 2000
    assert d["runway_months"] > 0 and d["runway_date"]


async def test_runway_positive_when_income_covers(app_client):
    await app_client.post("/api/v1/obligations", json={
        "name": "Rent", "amount": 2000, "due_date": "2026-08-01", "recurrence": "monthly", "kind": "expense"})
    await app_client.post("/api/v1/obligations", json={
        "name": "Salary", "amount": 5000, "due_date": "2026-08-01", "recurrence": "monthly", "kind": "income"})
    d = (await app_client.get("/api/v1/portfolio/runway")).json()
    assert d["status"] == "positive" and d["net_monthly_burn"] < 0 and d["runway_months"] is None


async def test_recurrence_normalised_to_monthly(app_client):
    # Annual 12,000 → 1,000/month.
    await app_client.post("/api/v1/obligations", json={
        "name": "Insurance", "amount": 12000, "due_date": "2026-08-01", "recurrence": "annual", "kind": "expense"})
    d = (await app_client.get("/api/v1/portfolio/runway")).json()
    assert abs(d["monthly_expense"] - 1000) < 1


async def test_obligation_kind_validation(app_client):
    r = await app_client.post("/api/v1/obligations", json={
        "name": "x", "amount": 1, "due_date": "2026-08-01", "kind": "bogus"})
    assert r.status_code == 400
