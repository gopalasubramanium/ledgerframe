# SPDX-License-Identifier: AGPL-3.0-or-later
"""§14dr-27(c/d): India mutual funds created via the Add flow are recognised as
India-listed AMFI schemes (so the routing matrix / NAV owner prices them and the
scheme code persists for the edit form), instead of falling through as unclassified
US instruments. The Add flow sends the AMFI scheme code as the transaction *symbol*
and never maps it; creation (and, later, source-correction) recover the mapping."""

from __future__ import annotations


async def _sync_scheme(code: str, name: str) -> None:
    from app.db.base import get_sessionmaker
    from app.models import AmfiScheme

    async with get_sessionmaker()() as s:
        s.add(AmfiScheme(code=code, name=name, nav=None))
        await s.commit()


async def _add_mf(app_client, symbol: str):
    # Mirror the D-089 listed Add flow: one POST with the scheme code as the symbol.
    return await app_client.post("/api/v1/portfolio/transactions", json={
        "symbol": symbol, "type": "buy", "ts": "2025-01-15T10:00:00",
        "quantity": 10, "price": 50, "currency": "INR", "asset_class": "mutual_fund"})


async def _route(symbol: str):
    from sqlalchemy import select

    from app.db.base import get_sessionmaker
    from app.models import Instrument
    from app.services.market import route_for_instrument

    async with get_sessionmaker()() as s:
        instr = (await s.execute(
            select(Instrument).where(Instrument.symbol == symbol.upper())
        )).scalars().first()
        return await route_for_instrument(s, instr)


async def test_india_mf_add_flow_auto_links_amfi_and_routes_nav(app_client):
    # §14dr-27(c): when the symbol is a synced AMFI scheme code, creation links it and stamps
    # listing_country=IN, so the fund is owned by amfi_nav (source no longer 'none'/active)
    # and lands in the in_mutual_fund lane. RED before: country US, lane global_fund, active.
    await _sync_scheme("119551", "HDFC Top 100")
    assert (await _add_mf(app_client, "119551")).status_code == 200

    m = (await app_client.get("/api/v1/instruments/119551")).json()["instrument"]
    assert m["listing_country"] == "IN"
    assert any(i["id_type"] == "amfi_code" and i["value"] == "119551" for i in m["identifiers"])

    diag = await _route("119551")
    assert diag.source_selected == "amfi_nav" and diag.lane == "in_mutual_fund"
    assert diag.route_rule != "active"


async def test_india_mf_source_correction_links_amfi_when_synced_later(app_client):
    # §14dr-27(c): correction-time attach (symmetric to coingecko). An MF added before the
    # master was synced stays unmapped at create; after syncing, correcting the source to
    # amfi_nav links the scheme and stamps IN — no dead end.
    assert (await _add_mf(app_client, "120505")).status_code == 200
    m0 = (await app_client.get("/api/v1/instruments/120505")).json()["instrument"]
    assert not any(i["id_type"] == "amfi_code" for i in m0["identifiers"])

    await _sync_scheme("120505", "Parag Parikh Flexi Cap")
    r = await app_client.patch("/api/v1/instruments/120505", json={"source_override": "amfi_nav"})
    assert r.status_code == 200, r.text
    assert r.json()["source_override"] == "amfi_nav"

    m = (await app_client.get("/api/v1/instruments/120505")).json()["instrument"]
    assert m["listing_country"] == "IN"
    assert any(i["id_type"] == "amfi_code" and i["value"] == "120505" for i in m["identifiers"])


async def test_amfi_correction_no_scheme_match_served_error(app_client):
    # §14dr-27(c): correcting an MF whose symbol is not a synced scheme code → served string
    # (D-105) directing to the picker / sync, never a silent success.
    assert (await _add_mf(app_client, "NOTASCHEME")).status_code == 200
    r = await app_client.patch("/api/v1/instruments/NOTASCHEME", json={"source_override": "amfi_nav"})
    assert r.status_code == 400
    assert "no amfi scheme" in r.json()["detail"].lower()
