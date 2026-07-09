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
