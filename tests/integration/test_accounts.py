# SPDX-License-Identifier: AGPL-3.0-or-later
"""Account / institution view (W7) — grouping and management."""

from __future__ import annotations


async def test_accounts_group_totals_and_crud(app_client):
    d = (await app_client.get("/api/v1/accounts")).json()
    assert d["count"] >= 1 and d["accounts"]
    # Account values roll up to the portfolio total (within rounding).
    assert abs(d["total"] - sum(a["value"] for a in d["accounts"])) < 5
    a0 = d["accounts"][0]
    assert {"asset_classes", "holdings", "last_activity", "institution"} <= set(a0)

    r = (await app_client.post("/api/v1/accounts", json={
        "name": "IBKR", "institution": "Interactive Brokers", "kind": "brokerage", "currency": "USD"})).json()
    assert r["ok"]
    nid = r["id"]
    lst = (await app_client.get("/api/v1/accounts/list")).json()
    assert any(x["name"] == "IBKR" for x in lst["accounts"])

    # An empty account deletes fine.
    assert (await app_client.delete(f"/api/v1/accounts/{nid}")).status_code == 200

    # An account WITH transactions is protected from deletion.
    with_txns = next((a for a in d["accounts"] if a["last_activity"]), None)
    if with_txns:
        assert (await app_client.delete(f"/api/v1/accounts/{with_txns['id']}")).status_code == 400
