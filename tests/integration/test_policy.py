# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 1 — Investment Policy: stored targets + live drift/band/concentration."""

from __future__ import annotations


async def test_default_policy_is_created(app_client):
    p = (await app_client.get("/api/v1/policy")).json()
    assert p["name"] == "Investment Policy"
    assert p["default_band_pct"] == 5.0 and p["targets"] == []


async def test_set_targets_all_dimensions(app_client):
    r = await app_client.put("/api/v1/policy/targets", json={"targets": [
        {"dimension": "asset_class", "bucket": "equity", "target_pct": 30},
        {"dimension": "asset_class", "bucket": "property", "target_pct": 40, "min_pct": 30, "max_pct": 50},
        {"dimension": "currency", "bucket": "SGD", "target_pct": 60},
        {"dimension": "region", "bucket": "India", "target_pct": 20},
    ]})
    assert r.status_code == 200 and len(r.json()["targets"]) == 4


async def test_target_validation(app_client):
    # Unknown dimension.
    bad = await app_client.put("/api/v1/policy/targets", json={"targets": [
        {"dimension": "sector_x", "bucket": "tech", "target_pct": 10}]})
    assert bad.status_code == 400
    # Out-of-range target.
    oob = await app_client.put("/api/v1/policy/targets", json={"targets": [
        {"dimension": "asset_class", "bucket": "equity", "target_pct": 150}]})
    assert oob.status_code == 400
    # Duplicate bucket in a dimension.
    dup = await app_client.put("/api/v1/policy/targets", json={"targets": [
        {"dimension": "currency", "bucket": "SGD", "target_pct": 10},
        {"dimension": "currency", "bucket": "SGD", "target_pct": 20}]})
    assert dup.status_code == 400


async def test_drift_reports_band_status_and_gap(app_client):
    await app_client.put("/api/v1/policy/targets", json={"targets": [
        {"dimension": "asset_class", "bucket": "equity", "target_pct": 30},
        {"dimension": "asset_class", "bucket": "property", "target_pct": 40, "min_pct": 30, "max_pct": 50},
    ]})
    d = (await app_client.get("/api/v1/policy/drift")).json()
    assert d["has_targets"] is True and "not financial advice" in d["disclaimer"].lower()
    ac = next(x for x in d["dimensions"] if x["dimension"] == "asset_class")
    buckets = {r["bucket"]: r for r in ac["rows"]}
    # Demo is property-heavy → property over its band, equity under.
    assert buckets["property"]["status"] == "over"
    assert buckets["equity"]["status"] == "under"
    # Every row carries a factual base-currency gap and a band.
    for r in ac["rows"]:
        assert "gap_base" in r and "lower_pct" in r and "upper_pct" in r
    # Held-but-untargeted classes are surfaced honestly.
    assert ac["untargeted"]
    assert ac["coverage_pct"] == 70.0


async def test_concentration_flag(app_client):
    r = await app_client.put("/api/v1/policy", json={"max_position_pct": 25})
    assert r.status_code == 200 and r.json()["max_position_pct"] == 25.0
    d = (await app_client.get("/api/v1/policy/drift")).json()
    # The demo property dominates → it breaches a 25% single-position limit.
    assert d["concentration"] and d["concentration"][0]["weight_pct"] > 25


async def test_clear_concentration_limit(app_client):
    await app_client.put("/api/v1/policy", json={"max_position_pct": 25})
    cleared = await app_client.put("/api/v1/policy", json={"max_position_pct": 0})
    assert cleared.json()["max_position_pct"] is None
    d = (await app_client.get("/api/v1/policy/drift")).json()
    assert d["concentration"] == []
