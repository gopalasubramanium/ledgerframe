# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase A1: the per-instrument price-source routing decision (pure policy)."""

from __future__ import annotations

from app.providers.market.router import lane_for, route


def _route(**kw):
    base = {
        "instrument_id": 1, "symbol": "X", "asset_class": "equity", "asset_subclass": None,
        "listing_country": None, "mappings": set(), "active_provider": "yahoo", "has_manual": False,
    }
    base.update(kw)
    return route(**base)


def test_lane_selection():
    assert lane_for("equity", None, "IN") == "in_equity"
    assert lane_for("equity", None, "SG") == "sg_equity"
    assert lane_for("equity", None, "US") == "us_equity"
    assert lane_for("mutual_fund", None, "IN") == "in_mutual_fund"
    assert lane_for("mutual_fund", None, "US") == "global_fund"
    assert lane_for("crypto", None, None) == "crypto"
    assert lane_for("equity", "derivative", "IN") == "derivative"
    assert lane_for("property", None, None) == "manual_only"


def test_equity_routes_to_active_provider():
    d = _route(asset_class="equity", listing_country="US", active_provider="yahoo")
    assert d.source_selected == "yahoo" and d.valuation_method == "market_quote"


def test_mutual_fund_needs_amfi_never_a_market_feed():
    # Unmapped MF → mapping required, NOT the active equity provider.
    d = _route(asset_class="mutual_fund", listing_country="IN", active_provider="yahoo")
    assert d.mapping_required and d.source_selected != "yahoo"
    # Mapped MF with a published NAV → AMFI owns it.
    d2 = _route(asset_class="mutual_fund", listing_country="IN", mappings={"amfi_code"},
                cached_source="amfi_nav")
    assert d2.source_selected == "amfi_nav" and d2.valuation_method == "official_nav"
    # Mapped MF, NAV not yet published → still AMFI (awaiting), never the equity feed.
    d3 = _route(asset_class="mutual_fund", listing_country="IN", mappings={"amfi_code"},
                cached_source="mock", active_provider="mock")
    assert d3.source_selected == "amfi_nav" and d3.source_selected != "mock"


def test_crypto_prefers_coingecko_but_falls_back_to_active():
    # Mapped + published coingecko quote → coingecko owns it.
    d = _route(asset_class="crypto", mappings={"coingecko_id"}, cached_source="coingecko")
    assert d.source_selected == "coingecko"
    # Mapped but not yet published → active provider prices it (no dead holding).
    d2 = _route(asset_class="crypto", mappings={"coingecko_id"}, cached_source="mock",
                active_provider="mock")
    assert d2.source_selected == "mock"
    # Unmapped crypto still prices via the active provider by symbol.
    d3 = _route(asset_class="crypto", active_provider="yahoo")
    assert d3.source_selected == "yahoo"


def test_manual_only_never_uses_a_feed():
    d = _route(asset_class="property", has_manual=True)
    assert d.source_selected == "manual" and d.valuation_method == "manual_valuation"
    d2 = _route(asset_class="cash", has_manual=False)
    assert d2.source_selected is None and d2.valuation_method == "unavailable"


def test_source_override_wins():
    d = _route(asset_class="equity", source_override="eodhd")
    assert d.source_selected == "eodhd"
