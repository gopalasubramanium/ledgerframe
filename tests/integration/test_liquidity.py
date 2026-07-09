# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 3a — liquidity ladder (graded time-to-cash buckets)."""

from __future__ import annotations

from types import SimpleNamespace as NS

from app.services.liquidity import rung_of


def test_rung_mapping_by_class_and_override():
    assert rung_of(NS(asset_class="cash", liquidity_profile=None)) == "immediate"
    assert rung_of(NS(asset_class="equity", liquidity_profile=None)) == "immediate"
    assert rung_of(NS(asset_class="mutual_fund", liquidity_profile=None)) == "short"
    assert rung_of(NS(asset_class="fixed_deposit", liquidity_profile=None)) == "locked"
    assert rung_of(NS(asset_class="property", liquidity_profile=None)) == "illiquid"
    # An explicit profile overrides the class-based inference.
    assert rung_of(NS(asset_class="property", liquidity_profile="listed")) == "immediate"
    assert rung_of(NS(asset_class="equity", liquidity_profile="locked")) == "locked"


async def test_liquidity_ladder_endpoint(app_client):
    d = (await app_client.get("/api/v1/portfolio/liquidity")).json()
    keys = {r["key"] for r in d["rungs"]}
    assert "immediate" in keys and "illiquid" in keys
    assert 0 <= d["liquid_pct"] <= 100
    # Cumulative reaches ~100% on the last asset rung.
    assert abs(d["rungs"][-1]["cumulative_pct"] - 100) < 0.6
    assert d["liabilities"] <= 0          # liabilities are separate & negative
    assert "not a guarantee" in d["disclaimer"].lower()
