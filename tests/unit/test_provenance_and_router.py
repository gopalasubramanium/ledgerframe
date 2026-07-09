# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 1: valuation provenance labels + the price-source router seam.

Deterministic, no network — the router wraps the conftest-forced mock provider.
"""

from __future__ import annotations

from app.core.provenance import method_for_quote, valuation_label
from app.providers.market.router import (
    CAPABILITIES,
    DEFAULT_PRIORITY,
    PriceSourceRouter,
    capabilities_for,
    get_router,
)
from app.schemas.common import EntitlementStatus, ValuationMethod


def test_valuation_label_canonical_methods():
    assert valuation_label(ValuationMethod.MARKET_QUOTE) == "Live / delayed market quote"
    assert valuation_label(ValuationMethod.OFFICIAL_NAV) == "Official NAV"
    assert valuation_label(ValuationMethod.BROKER_QUOTE) == "Broker quote"
    assert valuation_label(ValuationMethod.MANUAL_VALUATION) == "Manual value"
    assert valuation_label(ValuationMethod.STATEMENT_IMPORT) == "Statement value"
    assert valuation_label(ValuationMethod.CALCULATED_ACCRUAL) == "Accrued estimate"


def test_valuation_label_stale_and_unavailable():
    # A stale/cached market quote reads as stale; manual/NAV are NOT overridden by staleness.
    assert valuation_label(ValuationMethod.MARKET_QUOTE, is_stale=True) == "Stale cached value"
    assert valuation_label(ValuationMethod.MARKET_QUOTE, entitlement=EntitlementStatus.CACHED) == "Stale cached value"
    assert valuation_label(ValuationMethod.MANUAL_VALUATION, is_stale=True) == "Manual value"
    assert valuation_label(ValuationMethod.MARKET_QUOTE, price_available=False) == "Price unavailable"
    assert valuation_label(ValuationMethod.UNAVAILABLE) == "Price unavailable"


def test_method_for_quote():
    assert method_for_quote(EntitlementStatus.DELAYED, price_available=True) is ValuationMethod.MARKET_QUOTE
    assert method_for_quote(EntitlementStatus.DELAYED, price_available=False) is ValuationMethod.UNAVAILABLE


def test_capabilities_registry():
    for name in ("mock", "csv", "yahoo", "alphavantage"):
        assert CAPABILITIES[name].name == name
        assert CAPABILITIES[name].quote is True
    # Rate-limited providers are declared fetch_on_demand=False.
    assert CAPABILITIES["yahoo"].fetch_on_demand is False
    assert CAPABILITIES["alphavantage"].needs_key is True
    # Unknown provider → safe quote-only default, never a KeyError.
    unknown = capabilities_for("does-not-exist")
    assert unknown.quote is True and unknown.history is False


def test_default_priority_lanes_end_in_honest_fallback():
    for lane in ("in_equity", "in_mutual_fund", "crypto", "deposit", "derivative"):
        chain = DEFAULT_PRIORITY[lane]
        assert chain, lane
        assert chain[-1] in {"manual", "accrual", "cache"}, (lane, chain)


async def test_router_delegates_to_active_provider():
    from app.providers.market import get_provider

    router = get_router()
    assert isinstance(router, PriceSourceRouter)
    active = getattr(get_provider(), "name", "unknown")
    # The router wraps the active provider 1:1 (name + capabilities track it).
    assert router.name == active
    assert router.capabilities.name == active
    q = await router.get_quote("AAPL")
    assert q.symbol == "AAPL"  # delegation returns the provider's own quote object
