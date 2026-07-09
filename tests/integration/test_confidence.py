# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 2a — data confidence score (deterministic, explainable)."""

from __future__ import annotations

from decimal import Decimal

from app.services.confidence import score_holding, summarise


class _H:
    def __init__(self, method, stale=False, entitlement="delayed"):
        self.valuation_method = method
        self.is_stale = stale
        self.entitlement = entitlement


def test_score_by_method():
    assert score_holding(_H("market_quote"))["confidence"] == 100
    assert score_holding(_H("official_nav"))["confidence"] == 95
    assert score_holding(_H("manual_valuation"))["confidence"] == 70
    assert score_holding(_H("manual_valuation"))["confidence_band"] == "medium"


def test_penalties_stack_and_floor():
    # estimated (40) − mapping (15) − unavailable (15) = 10, low.
    r = score_holding(_H("estimated_value", entitlement="unavailable"), mapping_required=True)
    assert r["confidence"] == 10 and r["confidence_band"] == "low"
    assert any("mapping" in f for f in r["confidence_factors"])
    # A stale live quote drops from 100 to 80 (still high).
    assert score_holding(_H("market_quote", stale=True))["confidence"] == 80


def test_summarise_is_value_weighted():
    s = summarise([(Decimal("900"), 100), (Decimal("100"), 0)])
    assert s["overall"] == 90                       # (900·100 + 100·0) / 1000
    assert s["by_band"]["high"]["count"] == 1 and s["by_band"]["low"]["count"] == 1
    assert "not advice" in s["disclaimer"].lower()


async def test_pricing_health_exposes_confidence(app_client):
    d = (await app_client.get("/api/v1/portfolio/pricing-health")).json()
    assert "confidence" in d and 0 <= d["confidence"]["overall"] <= 100
    assert d["confidence"]["overall_band"] in {"high", "medium", "low"}
    for r in d["holdings"]:
        assert "confidence" in r and "confidence_band" in r and "confidence_factors" in r
    # The demo's unmapped fund is low-confidence with an explanation.
    mf = next((r for r in d["holdings"] if r["label"].startswith("HDFC")), None)
    if mf:
        assert mf["confidence_band"] == "low" and mf["confidence_factors"]
