# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tags + contributions (W8)."""

from __future__ import annotations


async def test_holding_tags_normalise_and_allocate(app_client):
    hid = (await app_client.get("/api/v1/portfolio/holdings")).json()["holdings"][0]["id"]
    r = (await app_client.put(f"/api/v1/portfolio/holdings/{hid}/tags",
                              json={"tags": ["Core", "High Conviction", "Core"]})).json()
    assert r["ok"]
    assert r["tags"] == ["core", "high_conviction"]         # normalised + de-duped

    d = (await app_client.get("/api/v1/portfolio/tags")).json()
    by = {t["tag"]: t for t in d["tags"]}
    assert "core" in by and "high_conviction" in by
    assert any(h["tags"] == ["core", "high_conviction"] for h in d["holdings"])
    # Clearing tags removes them.
    await app_client.put(f"/api/v1/portfolio/holdings/{hid}/tags", json={"tags": []})
    assert not (await app_client.get("/api/v1/portfolio/tags")).json()["tags"]


async def test_contributions_monthly_equivalent(app_client):
    base = (await app_client.get("/api/v1/contributions")).json()["base_currency"]
    await app_client.post("/api/v1/contributions", json={"name": "SIP", "amount": 2000, "currency": base, "frequency": "monthly", "kind": "invest"})
    await app_client.post("/api/v1/contributions", json={"name": "Bonus", "amount": 12000, "currency": base, "frequency": "annual", "kind": "invest"})
    await app_client.post("/api/v1/contributions", json={"name": "Draw", "amount": 600, "currency": base, "frequency": "monthly", "kind": "withdraw"})
    d = (await app_client.get("/api/v1/contributions")).json()
    assert d["monthly_invest"] == 3000          # 2000 + 12000/12
    assert d["monthly_withdraw"] == 600
    assert d["monthly_net_investing"] == 2400
