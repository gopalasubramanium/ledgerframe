# SPDX-License-Identifier: AGPL-3.0-or-later
"""Release hardening: routed history (§4), real auth_required (§6), briefing
percentage currency fix (§7)."""

from __future__ import annotations

from decimal import Decimal

from app.providers.market.router import ProviderAvailability, route
from app.seed.demo import seed_demo_data


def _route(**kw):
    base = {
        "instrument_id": 1, "symbol": "X", "asset_class": "equity", "asset_subclass": None,
        "listing_country": None, "mappings": set(), "active_provider": "mock", "has_manual": False,
    }
    base.update(kw)
    return route(**base)


# --- §6: auth_required is real ---------------------------------------------- #

def test_auth_required_when_preferred_source_lacks_credentials():
    av = {"kite": ProviderAvailability("kite", configured=True, has_credentials=False)}
    d = _route(asset_class="equity", listing_country="IN", availability=av)
    assert d.auth_required is True


def test_no_auth_required_when_credentialed():
    av = {"kite": ProviderAvailability("kite", configured=True, has_credentials=True)}
    d = _route(asset_class="equity", listing_country="IN", availability=av)
    assert d.auth_required is False


def test_no_auth_required_for_manual_asset():
    av = {"kite": ProviderAvailability("kite", configured=True, has_credentials=False)}
    d = _route(asset_class="property", has_manual=True, availability=av)
    assert d.auth_required is False


def test_no_auth_required_when_kite_not_configured():
    # Kite sits in the in_equity chain by default, but if the user never set it up we
    # must not nag for credentials.
    d = _route(asset_class="equity", listing_country="IN", availability={})
    assert d.auth_required is False


async def test_pricing_health_no_false_auth_chip(app_client):
    ph = (await app_client.get("/api/v1/portfolio/pricing-health")).json()
    for row in ph["holdings"]:
        assert "auth_required" in row and "mapping_required" in row
    # The demo configures no keyed provider → no false auth chips.
    assert all(not r["auth_required"] for r in ph["holdings"])
    # The unmapped demo mutual fund flags mapping_required.
    assert any(r["mapping_required"] for r in ph["holdings"])


# --- §4: routed history ----------------------------------------------------- #

def test_history_source_routing():
    from app.services.market import _history_source

    # Equity via the active provider (mock supports history) → fetch allowed.
    d = _route(asset_class="equity", listing_country="US", active_provider="mock")
    assert _history_source(d, "mock")[0] == "mock"
    # Unmapped mutual fund → no source → no history fetch.
    d = _route(asset_class="mutual_fund", listing_country="IN", active_provider="mock")
    assert _history_source(d, "mock")[0] is None
    # Mapped fund → amfi_nav owns it but NAV history isn't implemented.
    d = _route(asset_class="mutual_fund", listing_country="IN", mappings={"amfi_code"},
               cached_source="amfi_nav")
    src, reason = _history_source(d, "mock")
    assert src is None and "NAV history" in reason
    # Manual asset → never a provider fetch.
    d = _route(asset_class="property", has_manual=True)
    assert _history_source(d, "mock")[0] is None


async def test_mutual_fund_history_not_fetched_from_equity_provider(session):
    from datetime import UTC, datetime, timedelta

    from app.services.market import get_history_cached

    await seed_demo_data(session)
    await session.flush()
    end = datetime.now(UTC)
    candles = await get_history_cached(session, "HDFCNIFTY", "1d", end - timedelta(days=30), end)
    # Unmapped fund → routed to no fetchable source → empty history (never an equity feed).
    assert candles == []


# --- §7: briefing percentage never mixes currencies ------------------------- #

def test_mover_str_uses_base_percentage():
    from app.services.briefing import _mover_str

    class _H:
        label = "VOD.L"
        day_change_base = Decimal("-239")
        day_change_pct = Decimal("-2.0")

    assert _mover_str(_H(), "SGD") == "VOD.L (-239 SGD -2.0%)"


def test_mover_str_omits_pct_when_unavailable():
    from app.services.briefing import _mover_str

    class _H:
        label = "X"
        day_change_base = Decimal("10")
        day_change_pct = None

    assert _mover_str(_H(), "SGD") == "X (+10 SGD)"
