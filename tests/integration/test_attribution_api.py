# SPDX-License-Identifier: AGPL-3.0-or-later
"""§4.5 Unit C — GET /portfolio/attribution (read-only wiring for Units A + B).

Proves the endpoint returns both the attribution decomposition and the risk metrics for the demo
portfolio, that reconciliation holds through the API, that entity_id scopes, and that a thin/empty
scope degrades to the honest 'unavailable' shape (HTTP 200), never a 500.
"""

from __future__ import annotations

_URL = "/api/v1/portfolio/attribution"
_RISK_KEYS = ("beta", "correlation", "downside_deviation", "information_ratio", "tracking_error", "hhi")


async def test_attribution_endpoint_returns_attribution_and_risk(app_client):
    r = await app_client.get(_URL)
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"attribution", "risk"}

    att = body["attribution"]
    assert att["available"] is True
    assert att["holdings"] and att["by_asset_class"] and att["by_sector"]
    # Honesty guarantee holds end-to-end: Σ contributions + residual == headline return.
    total = sum(h["contribution_pct"] for h in att["holdings"]) + att["residual_pct"]
    assert round(total, 6) == round(att["headline_return_pct"], 6)

    risk = body["risk"]
    assert all(k in risk for k in _RISK_KEYS)     # every risk metric present (value may be None)
    assert risk["hhi"] is not None                # holdings present → concentration computes


async def test_attribution_endpoint_scopes_by_entity_and_unavailable_is_not_500(app_client):
    whole = (await app_client.get(_URL)).json()
    assert whole["attribution"]["available"] is True      # whole demo portfolio attributes

    # A non-existent entity scopes to no accounts → empty → honest unavailable shape, not a 500.
    r = await app_client.get(_URL, params={"entity_id": 999999})
    assert r.status_code == 200
    body = r.json()
    assert body["attribution"]["available"] is False
    assert body["attribution"]["headline_return_pct"] is None
    assert body["risk"]["available"] is False and body["risk"]["hhi"] is None


async def test_attribution_endpoint_accepts_days_and_benchmark(app_client):
    r = await app_client.get(_URL, params={"days": 90, "benchmark": "QQQ"})
    assert r.status_code == 200
    body = r.json()
    assert body["attribution"]["window_days"] == 90        # clamped param threaded through
    assert body["risk"]["benchmark_symbol"] == "QQQ"       # benchmark threaded to risk metrics
