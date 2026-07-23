# SPDX-License-Identifier: AGPL-3.0-or-later
"""R-63 F-C (I-10) — a demo/synthetic price must never be served, nor scored high, for a REAL
holding on a live instance. Three independent fixes (owner rulings 2026-07-24):

* Option 1 — the CSV lane no longer substitutes mock on a miss (`csv_provider.py`).
* Option 3 — a STANDING net guard refuses any mock/demo-sourced quote on a live instance.
* Option 2 — the confidence law caps a mock/demo-sourced price below "high" outside demo mode.

The Phase A repro reproduced the owner's exact live number (109.878669) as a mock price laundered
through the net at confidence 100/high; these are the fail-first REDs that turn it typed-no-price.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.providers.market import build_provider
from app.providers.market.csv_provider import CSVMarketDataProvider
from app.providers.market.router import ProviderAvailability
from app.schemas.common import EntitlementStatus, FailureState, Quote
from app.services import market
from app.services.confidence import score_holding


# ---- Option 1 — the CSV lane returns a TYPED no-price on a miss, never a mock price ----

async def test_csv_miss_returns_typed_no_price_never_mock():
    csv_prov = build_provider("csv")
    assert isinstance(csv_prov, CSVMarketDataProvider)
    q = await csv_prov.get_quote("AARK")  # no AARK.csv in the temp imports dir
    assert q.price is None, "a CSV miss must NOT fabricate a mock price (the AARK 109.878669 defect)"
    assert q.source != "mock"
    assert q.failure_state is FailureState.EMPTY


class _FailingHead:
    name = "alphavantage"
    fetch_on_demand = False

    async def get_quote(self, symbol, exchange=None):
        return Quote(symbol=symbol.upper(), price=None, currency="USD", source="alphavantage",
                     entitlement=EntitlementStatus.UNAVAILABLE, failure_state=FailureState.EMPTY,
                     received_at=datetime.now(UTC), is_stale=True)


class _FailingYahoo:
    name = "yahoo"
    fetch_on_demand = False

    async def get_quote(self, symbol, exchange=None):
        return Quote(symbol=symbol.upper(), price=None, currency="USD", source="yahoo",
                     entitlement=EntitlementStatus.UNAVAILABLE, failure_state=FailureState.EMPTY,
                     received_at=datetime.now(UTC), is_stale=True)


async def test_net_no_longer_launders_mock_through_the_csv_lane(session, monkeypatch):
    """THE PHASE A REPRO, now GREEN: AV head fails, yahoo fails, the REAL csv lane is walked —
    and the net returns a TYPED no-price, never a stored source='mock' price at confidence 100."""
    monkeypatch.setattr(market, "provider_availability", lambda: {
        "alphavantage": ProviderAvailability("alphavantage", True, True, True)})
    monkeypatch.setattr(market, "get_provider", lambda: _FailingHead())

    def fake_build(name):
        if name == "yahoo":
            return _FailingYahoo()
        if name == "csv":
            return build_provider("csv")  # the REAL csv provider (empty imports dir)
        return None
    monkeypatch.setattr("app.providers.market.build_provider", fake_build, raising=False)

    r = await market.refresh_quote_detailed(session, "AARK", None)
    assert not r.fetched, "the net must not report a fabricated price as fetched"
    assert r.priced_by != "mock"
    assert r.failure_state is FailureState.EMPTY
    cached = await market.get_cached_quote(session, "AARK")
    assert cached.source != "mock", "no mock quote may be persisted for a real holding"


# ---- Option 3 — the STANDING net guard refuses a mock-sourced price (blindness pin) ----

class _MockLane:
    """A lane that DOES price, but with source='mock' — the leak the guard must refuse."""

    name = "csv"
    fetch_on_demand = False

    async def get_quote(self, symbol, exchange=None):
        return Quote(symbol=symbol.upper(), price="109.878669", currency="USD", source="mock",
                     entitlement=EntitlementStatus.DELAYED,
                     market_time=datetime.now(UTC), received_at=datetime.now(UTC))


async def test_net_guard_refuses_a_mock_sourced_price_on_a_live_instance(session, monkeypatch):
    """Blindness pin: force a lane to return a mock-priced quote on a live instance. The guard
    must refuse it (outcome no_data, nothing persisted). Remove the guard and this FAILS loudly
    (the net would store source='mock' at a real price) — so the guard provably protects something."""
    monkeypatch.setattr(market, "provider_availability", lambda: {
        "alphavantage": ProviderAvailability("alphavantage", True, True, True)})
    monkeypatch.setattr(market, "get_provider", lambda: _FailingHead())  # active provider = alphavantage (live)

    def fake_build(name):
        if name == "yahoo":
            return _FailingYahoo()
        if name == "csv":
            return _MockLane()  # a lane that prices with source='mock'
        return None
    monkeypatch.setattr("app.providers.market.build_provider", fake_build, raising=False)

    r = await market.refresh_quote_detailed(session, "AARK", None)
    assert not r.fetched and r.outcome == "no_data"
    cached = await market.get_cached_quote(session, "AARK")
    assert cached.source != "mock"


async def test_net_allows_mock_in_demo_mode(session, monkeypatch):
    """The guard is scoped to LIVE instances: in demo mode (active provider IS mock) a mock price
    is legitimate and must still be served — the guard must not break the demo."""
    class _MockActive(_MockLane):
        name = "mock"

    monkeypatch.setattr(market, "provider_availability", lambda: {})
    monkeypatch.setattr(market, "get_provider", lambda: _MockActive())
    monkeypatch.setattr("app.providers.market.build_provider", lambda name: None)

    r = await market.refresh_quote_detailed(session, "AAPL", None)
    assert r.fetched and r.priced_by == "mock"


# ---- Option 2 — the confidence law caps a mock/demo price below "high" outside demo mode ----

class _HV:
    def __init__(self, source, method="market_quote", is_stale=False, entitlement="delayed"):
        self.source = source
        self.valuation_method = method
        self.is_stale = is_stale
        self.entitlement = entitlement
        self.fx_unavailable = False


def test_confidence_caps_a_mock_price_below_high_on_a_live_instance():
    # demo_mode=False (a live instance): a mock-sourced market_quote can NOT read 100/high.
    scored = score_holding(_HV(source="mock"), demo_mode=False)
    assert scored["confidence"] <= 40
    assert scored["confidence_band"] != "high"
    assert any("synthetic" in f for f in scored["confidence_factors"])


def test_confidence_leaves_a_real_source_at_full_marks():
    # a genuine live source is untouched — the cap is scoped to mock/demo only.
    scored = score_holding(_HV(source="alphavantage"), demo_mode=False)
    assert scored["confidence"] == 100 and scored["confidence_band"] == "high"


def test_confidence_preserves_mock_high_in_demo_mode():
    # in demo mode a mock price is legitimate — full marks, no cap (the demo must feel populated).
    scored = score_holding(_HV(source="mock"), demo_mode=True)
    assert scored["confidence"] == 100 and scored["confidence_band"] == "high"


# ---- Migration rider — the quotes-table repair removes stored mock rows on a live instance ----

class _LiveProvider:
    name = "alphavantage"
    fetch_on_demand = False


async def _seed_mock_quote(session, symbol="AARK"):
    from app.models import Quote as QuoteRow
    from app.services.identity import resolve_or_create_instrument
    instr, _ = await resolve_or_create_instrument(session, symbol=symbol, exchange=None)
    session.add(QuoteRow(
        instrument_id=instr.id, price="109.878669", currency="USD", source="mock",
        entitlement="delayed", received_at=datetime.now(UTC)))
    await session.flush()
    return instr


async def test_quote_repair_removes_a_stored_mock_row_on_a_live_instance(session, monkeypatch):
    await _seed_mock_quote(session, "AARK")
    monkeypatch.setattr(market, "get_provider", lambda: _LiveProvider())  # a LIVE instance
    out = await market.repair_quote_demo_residue(session)
    assert out["purged"] == 1
    cached = await market.get_cached_quote(session, "AARK")
    assert cached.source != "mock", "the fabricated mock quote must be gone (falls to Estimated)"
    # Idempotent: a second run finds nothing.
    assert (await market.repair_quote_demo_residue(session))["purged"] == 0


async def test_quote_repair_is_a_noop_in_demo_mode(session, monkeypatch):
    """The guard is scoped to LIVE instances: in demo mode a mock quote is legitimate seed data
    and must survive — the repair must not wipe the demo."""
    await _seed_mock_quote(session, "AAPL")

    class _MockProvider:
        name = "mock"
    monkeypatch.setattr(market, "get_provider", lambda: _MockProvider())
    out = await market.repair_quote_demo_residue(session)
    assert out["purged"] == 0 and out.get("skipped") == "demo instance"
    cached = await market.get_cached_quote(session, "AAPL")
    assert cached.source == "mock", "demo seed data must survive in demo mode"
