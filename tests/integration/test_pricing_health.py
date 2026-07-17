# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 3a: pricing-health diagnostics endpoint."""

from __future__ import annotations

_STATUSES = {"Fresh", "Delayed", "End-of-day", "Cached", "Manual", "Estimated", "Unavailable"}


async def test_pricing_health_reports_provenance(app_client):
    r = await app_client.get("/api/v1/portfolio/pricing-health")
    assert r.status_code == 200
    body = r.json()
    holdings = body["holdings"]
    assert holdings, "demo data should seed holdings"
    for h in holdings:
        assert h["status"] in _STATUSES
        assert "valuation_method" in h and "valuation_label" in h
        assert "source" in h and "entitlement" in h and "price_ts" in h
    # Manual demo assets (cash/property) report a Manual status.
    assert "Manual" in {h["status"] for h in holdings}
    # Summary counts are consistent with the rows.
    assert sum(body["summary"].values()) == len(holdings)
    # No secrets leak.
    blob = r.text.lower()
    assert "api_key" not in blob and "secret" not in blob


async def test_pricing_health_stale_flag_reconciles_with_summary_count(app_client):
    """§14dr-3 — the per-holding `is_stale` flag (the marker Pricing Health renders to identify WHICH
    holdings are stale) and the Stale-banner count come from ONE shared reader (value_portfolio). Pin
    the reconciliation: the number of is_stale rows in the pricing-health payload equals
    /portfolio/summary.stale_count — so "banner count == marked rows" holds by construction, never a
    second independently-computed number."""
    ph = (await app_client.get("/api/v1/portfolio/pricing-health")).json()
    summary = (await app_client.get("/api/v1/portfolio/summary")).json()
    assert "stale_count" in summary
    marked = sum(1 for h in ph["holdings"] if h["is_stale"])
    assert marked == summary["stale_count"]
