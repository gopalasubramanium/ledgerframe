# SPDX-License-Identifier: AGPL-3.0-or-later
"""POST-CLOSE DELTA D1 (data-feed-routing) — one India-MF recognition derivation.

The owner's 145834 finding: a scheme present in the synced master with a valid NAV,
added via the Add/buy flow, was MAPPED-BUT-NEVER-CONVERTED — ``_link_amfi_by_symbol``
attached ``amfi_code`` + stamped IN but left ``pricing_currency=USD`` /
``valuation_method=market_quote`` and never published the known NAV. The full
conversion lived only on the ``map_amfi`` route. D1-a extracts ONE helper
(``recognise_amfi_fund``) both paths call, so the two paths cannot drift.
"""

from __future__ import annotations

from sqlalchemy import select


async def _sync_scheme(code: str, name: str, nav) -> None:
    from app.db.base import get_sessionmaker
    from app.models import AmfiScheme

    async with get_sessionmaker()() as s:
        s.add(AmfiScheme(code=code, name=name, nav=nav, nav_date="2026-07-17"))
        await s.commit()


async def _add_mf(app_client, symbol: str):
    # The D-089 listed Add flow: one POST with the scheme code as the symbol.
    return await app_client.post("/api/v1/portfolio/transactions", json={
        "symbol": symbol, "type": "buy", "ts": "2025-01-15T10:00:00",
        "quantity": 10, "price": 50, "currency": "INR", "asset_class": "mutual_fund"})


async def _instr_and_quote(symbol: str):
    from app.db.base import get_sessionmaker
    from app.models import Instrument
    from app.models import Quote as QuoteRow

    async with get_sessionmaker()() as s:
        instr = (await s.execute(
            select(Instrument).where(Instrument.symbol == symbol.upper())
        )).scalars().first()
        quote = (await s.execute(
            select(QuoteRow).where(QuoteRow.instrument_id == instr.id)
        )).scalars().first() if instr is not None else None
        return instr, quote


# The converted field-set both recognition paths must produce (the anti-drift contract).
def _fieldset(instr) -> dict:
    return {
        "pricing_currency": instr.pricing_currency,
        "valuation_method": instr.valuation_method,
        "asset_category": instr.asset_category,
        "liquidity_profile": instr.liquidity_profile,
        "asset_subclass": instr.asset_subclass,
        "listing_country": instr.listing_country,
        "asset_class": getattr(instr.asset_class, "value", instr.asset_class),
    }


async def test_add_flow_fully_converts_and_publishes_nav_immediately(app_client):
    # D1-a: scheme present in the master WITH a NAV → the Add/buy flow recognises the
    # India MF end-to-end: full conversion AND an amfi_nav quote row exists immediately,
    # no master refresh needed. RED before the helper: pricing_currency stays None/USD,
    # valuation_method stays market_quote, and NO quote row is written.
    await _sync_scheme("145834", "Franklin India Test Fund", nav=100.5)
    assert (await _add_mf(app_client, "145834")).status_code == 200

    instr, quote = await _instr_and_quote("145834")
    assert instr is not None
    fs = _fieldset(instr)
    assert fs["pricing_currency"] == "INR"
    assert fs["valuation_method"] == "official_nav"
    assert fs["asset_category"] == "fund"
    assert fs["liquidity_profile"] == "redeemable"
    assert fs["listing_country"] == "IN"
    # The known NAV is published inline — the holding is valued immediately.
    assert quote is not None and quote.source == "amfi_nav"


async def test_two_recognition_paths_produce_byte_equal_fieldset(app_client):
    # D1-a anti-drift pin: for the SAME scheme, the Add-flow path and the map_amfi route
    # produce an identical converted instrument field-set — the two paths cannot diverge
    # because they call the one helper. RED before: the Add-flow path under-converts.
    # Two distinct schemes (one amfi_code maps to exactly one instrument); the converted
    # field-set is scheme-independent (all constants), so equality is the anti-drift test.
    await _sync_scheme("145834", "Franklin India Test Fund", nav=100.5)
    await _sync_scheme("119551", "HDFC Top 100", nav=880.0)

    # Path 1 — Add flow (symbol IS the scheme code).
    assert (await _add_mf(app_client, "145834")).status_code == 200
    add_instr, _ = await _instr_and_quote("145834")

    # Path 2 — a bare instrument mapped via the map_amfi route.
    await app_client.post("/api/v1/portfolio/transactions", json={
        "symbol": "MYFUND", "type": "buy", "ts": "2025-01-15T10:00:00",
        "quantity": 10, "price": 50, "currency": "USD", "asset_class": "mutual_fund"})
    r = await app_client.post("/api/v1/instruments/MYFUND/map-amfi", json={"code": "119551"})
    assert r.status_code == 200, r.text
    map_instr, _ = await _instr_and_quote("MYFUND")

    assert _fieldset(add_instr) == _fieldset(map_instr)
