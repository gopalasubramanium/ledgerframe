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
    # Clearing THIS holding's tags removes them — "high_conviction" (unique to it) disappears
    # from the totals; other demo-seeded tags (page-portfolio §12b-6) are unaffected.
    await app_client.put(f"/api/v1/portfolio/holdings/{hid}/tags", json={"tags": []})
    d2 = (await app_client.get("/api/v1/portfolio/tags")).json()
    assert all(h["tags"] == [] for h in d2["holdings"] if h["holding_id"] == hid)
    assert "high_conviction" not in {t["tag"] for t in d2["tags"]}


async def test_contributions_monthly_equivalent(app_client):
    base = (await app_client.get("/api/v1/contributions")).json()["base_currency"]
    await app_client.post("/api/v1/contributions", json={"name": "SIP", "amount": 2000, "currency": base, "frequency": "monthly", "kind": "invest"})
    await app_client.post("/api/v1/contributions", json={"name": "Bonus", "amount": 12000, "currency": base, "frequency": "annual", "kind": "invest"})
    await app_client.post("/api/v1/contributions", json={"name": "Draw", "amount": 600, "currency": base, "frequency": "monthly", "kind": "withdraw"})
    d = (await app_client.get("/api/v1/contributions")).json()
    assert d["monthly_invest"] == 3000          # 2000 + 12000/12
    assert d["monthly_withdraw"] == 600
    assert d["monthly_net_investing"] == 2400
