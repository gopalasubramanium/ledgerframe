# SPDX-License-Identifier: AGPL-3.0-or-later
"""Scenario / stress testing (W6) — deterministic what-if, never a forecast."""

from __future__ import annotations


async def test_scenarios_are_deterministic_downside(app_client):
    d = (await app_client.get("/api/v1/portfolio/scenarios")).json()
    assert "asset_scenarios" in d and "liquidity" in d
    nw = d["net_worth"]
    for s in d["asset_scenarios"]:
        assert s["delta"] <= 0                                   # all downside shocks
        assert abs(s["new_net_worth"] - (nw + s["delta"])) < 2.0  # new NW = NW + delta

    by = {s["id"]: s for s in d["asset_scenarios"]}
    # 20% shock is exactly twice the 10% shock (deterministic arithmetic).
    assert abs(by["equities_20"]["delta"] - 2 * by["equities_10"]["delta"]) < 2.0
    assert abs(by["equities_30"]["delta"] - 3 * by["equities_10"]["delta"]) < 2.0
    assert "not a prediction" in d["disclaimer"].lower()
