# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 2: instrument identity + taxonomy classification."""

from __future__ import annotations

from app.models import AssetClass, Instrument
from app.services.identity import (
    classify_defaults,
    find_instrument_by_identifier,
    identifiers_for,
    set_identifier,
)


def test_classify_defaults_market_vs_manual():
    listed = classify_defaults(AssetClass.EQUITY, is_manual_price=False, currency="USD")
    assert listed == {
        "asset_category": "equity", "asset_subclass": "equity", "pricing_currency": "USD",
        "liquidity_profile": "listed", "valuation_method": "market_quote",
    }
    manual = classify_defaults(AssetClass.PROPERTY, is_manual_price=True, currency="SGD")
    assert manual["liquidity_profile"] == "manual"
    assert manual["valuation_method"] == "manual_valuation"
    assert manual["pricing_currency"] == "SGD"


async def test_identifier_resolves_across_exchanges(session):
    # Two different instruments can share the SAME ticker on different exchanges.
    us = Instrument(symbol="INFY", exchange="NYSE", name="Infosys ADR", currency="USD")
    ind = Instrument(symbol="INFY", exchange="NSE", name="Infosys Ltd", currency="INR")
    session.add_all([us, ind])
    await session.flush()

    # An ISIN uniquely resolves to the right one — not the bare ticker.
    await set_identifier(session, ind.id, "ISIN", "INE009A01021", is_primary=True)
    await set_identifier(session, us.id, "isin", "US4567881085")

    got = await find_instrument_by_identifier(session, "isin", "INE009A01021")
    assert got is not None and got.id == ind.id and got.exchange == "NSE"
    got_us = await find_instrument_by_identifier(session, "ISIN", "US4567881085")
    assert got_us is not None and got_us.id == us.id

    assert await find_instrument_by_identifier(session, "isin", "NOPE") is None

    # Idempotent: setting the same identifier again does not duplicate.
    await set_identifier(session, ind.id, "isin", "INE009A01021")
    idents = await identifiers_for(session, ind.id)
    assert len([i for i in idents if i["value"] == "INE009A01021"]) == 1
