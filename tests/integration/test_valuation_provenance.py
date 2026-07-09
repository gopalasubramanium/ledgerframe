# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 1 API surface: holdings carry valuation provenance; providers endpoint
exposes capability metadata (no secrets)."""

from __future__ import annotations


async def test_holdings_expose_valuation_provenance(app_client):
    r = await app_client.get("/api/v1/portfolio/holdings")
    assert r.status_code == 200
    holdings = r.json()["holdings"]
    assert holdings, "demo data should seed holdings"

    labels = set()
    for h in holdings:
        assert "valuation_method" in h and "valuation_label" in h
        labels.add(h["valuation_label"])
        assert h["valuation_label"] in {
            "Live / delayed market quote", "Official NAV", "Broker quote",
            "Manual value", "Statement value", "Accrued estimate",
            "Estimated value", "Stale cached value", "Price unavailable",
        }

    # The demo set includes manual assets (cash/property), which are always a
    # "Manual value" regardless of which market provider is active.
    assert "Manual value" in labels, sorted(labels)


async def test_providers_endpoint_exposes_capabilities_without_secrets(app_client):
    r = await app_client.get("/api/v1/system/providers")
    assert r.status_code == 200
    body = r.json()
    assert body["active"] == "mock"
    assert set(body["capabilities"]) >= {"mock", "csv", "yahoo", "alphavantage"}
    assert body["capabilities"]["yahoo"]["fetch_on_demand"] is False
    assert "in_mutual_fund" in body["default_priority"]
    # No secret-ish keys leak from capability metadata.
    blob = r.text.lower()
    assert "api_key" not in blob and "token" not in blob and "secret" not in blob
