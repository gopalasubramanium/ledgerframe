# SPDX-License-Identifier: AGPL-3.0-or-later
"""F-G Rider A (R12, 2026-07-24) — a crypto holding's Identity reads crypto / crypto / — (unknown
country). Crypto is borderless: it has no listing country (MASTER-DATA §4), so the bare-ticker "US"
heuristic must never apply. RED before the fix: adding a crypto leaked country="US" (identity.py's
`country_for_symbol` bare-ticker default), so the Identity strip showed Country "US".
"""

from __future__ import annotations


async def test_resolver_gives_a_crypto_no_country_directly(session):
    """RED-first for the identity.py fix: the SHARED resolver chokepoint (R-63 I-6) must itself give a
    crypto asset_class an unknown country — not only the csv_import `_ensure_instrument` caller (which
    already guards via §14dr-27b). Without the fix, `country_for_symbol` bare-ticker default → "US".
    This pins the deeper guarantee so any future create path through the bare resolver stays correct."""
    from app.models import AssetClass
    from app.services.identity import resolve_or_create_instrument

    instr, created = await resolve_or_create_instrument(session, "XBTC", asset_class=AssetClass.CRYPTO)
    await session.commit()
    assert created
    assert (instr.asset_class.value if hasattr(instr.asset_class, "value") else instr.asset_class) == "crypto"
    assert instr.asset_subclass == "crypto"
    assert instr.country is None, f"the shared resolver leaked a crypto country: {instr.country!r}"
    assert instr.listing_country is None


async def test_adding_a_crypto_holding_reads_crypto_crypto_and_no_country(app_client):
    """Regression pin (already correct via `_ensure_instrument` §14dr-27b, NOT introduced here): adding
    a crypto holding through the transactions endpoint reads crypto / crypto / — (no leaked US country).
    Kept so the add-path correctness cannot silently regress alongside the identity/map fixes."""
    r = await app_client.post("/api/v1/portfolio/transactions", json={
        "symbol": "ZBTC", "type": "buy", "ts": "2024-01-01T10:00:00",
        "quantity": 1, "price": 40000, "currency": "USD", "asset_class": "crypto"})
    assert r.status_code == 200, r.text

    meta = (await app_client.get("/api/v1/instruments/ZBTC")).json()["instrument"]
    assert meta["asset_class"] == "crypto"
    assert meta["asset_subclass"] == "crypto", (
        f"crypto subclass leaked to {meta['asset_subclass']!r} (the classify_defaults subclass=class path)")
    # Borderless — no listing country, rendered "—". BOTH the authoritative field and the legacy
    # free-text one must be unknown, or the Identity strip (listing_country ?? country ?? "—") shows "US".
    assert meta["listing_country"] is None, f"crypto leaked a listing_country: {meta['listing_country']!r}"
    assert meta["country"] is None, (
        f"crypto leaked a country via the bare-ticker US heuristic: {meta['country']!r}")


async def test_mapping_an_equity_to_coingecko_clears_a_leaked_country(app_client):
    """The owner's actual path: a symbol born as an equity (country='US'), then mapped to CoinGecko.
    The map must clear the leaked country too (crypto is borderless), not just convert class/subclass."""
    import json

    from app.services import coingecko as cg

    # A symbol born as an equity (no asset_class → equity/US), then mapped to CoinGecko.
    await app_client.post("/api/v1/portfolio/transactions", json={
        "symbol": "ZETH", "type": "buy", "ts": "2024-01-01T10:00:00",
        "quantity": 1, "price": 2000, "currency": "USD"})  # NO asset_class → born equity/US
    # Confirm the leak exists pre-map.
    pre = (await app_client.get("/api/v1/instruments/ZETH")).json()["instrument"]
    assert pre["country"] == "US" and pre["asset_class"] == "equity"

    from app.db.base import get_sessionmaker
    async with get_sessionmaker()() as s:
        await cg.refresh_coins(s, json.loads('[{"id":"zeth-coin","symbol":"zeth","name":"ZEther"}]'))
        await s.commit()
    m = await app_client.post("/api/v1/instruments/ZETH/map-coingecko", json={"id": "zeth-coin"})
    assert m.status_code == 200, m.text

    post = (await app_client.get("/api/v1/instruments/ZETH")).json()["instrument"]
    assert post["asset_class"] == "crypto" and post["asset_subclass"] == "crypto"
    assert post["listing_country"] is None and post["country"] is None, (
        f"mapping to CoinGecko left a leaked country: "
        f"listing={post['listing_country']!r} country={post['country']!r}")


async def test_repair_clears_a_leaked_crypto_country_idempotently_and_audits(session):
    """R12c — the audited boot repair fixes the owner's EXISTING BTC row (crypto with a stale country
    from before the map fix). Gated/idempotent/AuditEvent-logged (repair-family precedent)."""
    from sqlalchemy import func, select

    from app.models import AssetClass, AuditEvent, Instrument
    from app.services.market import repair_crypto_country

    # A crypto row in the leaked state: class/subclass=crypto but country/listing_country="US".
    instr = Instrument(symbol="OLDBTC", name="Old BTC", asset_class=AssetClass.CRYPTO,
                       asset_subclass="crypto", currency="USD", country="US", listing_country="US")
    session.add(instr)
    await session.commit()

    r1 = await repair_crypto_country(session)
    await session.commit()
    assert r1["fixed"] == 1
    refreshed = await session.get(Instrument, instr.id)
    assert refreshed.country is None and refreshed.listing_country is None
    audits = (await session.execute(
        select(func.count()).select_from(AuditEvent).where(AuditEvent.action == "repair_crypto_country")
    )).scalar_one()
    assert audits == 1, "the repair must emit exactly one AuditEvent when it changes rows"

    # Idempotent: a second run finds nothing and adds no further audit event.
    r2 = await repair_crypto_country(session)
    await session.commit()
    assert r2["fixed"] == 0
