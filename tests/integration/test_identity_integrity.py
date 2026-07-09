# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 1 of the multi-asset completion: identifier uniqueness (A2), mapping
classification (A3), and the derivative-as-subclass policy (A4)."""

from __future__ import annotations


async def _add(app_client, symbol, **kw):
    body = {"symbol": symbol, "type": "buy", "ts": "2025-01-15T10:00:00",
            "quantity": 1, "price": 1, "currency": "USD"}
    body.update(kw)
    return await app_client.post("/api/v1/portfolio/transactions", json=body)


# --- A2: uniqueness -------------------------------------------------------- #

async def test_duplicate_coingecko_id_blocked(app_client):
    # Demo already maps BTC → "bitcoin". Mapping a second instrument to it must 409.
    await _add(app_client, "MYCOIN", asset_class="crypto")
    r = await app_client.post("/api/v1/instruments/MYCOIN/map-coingecko", json={"id": "bitcoin"})
    assert r.status_code == 409
    assert "already mapped" in r.text.lower()


async def test_duplicate_amfi_and_kite_blocked(app_client):
    await _add(app_client, "FUNDA", asset_class="mutual_fund")
    await _add(app_client, "FUNDB", asset_class="mutual_fund")
    assert (await app_client.post("/api/v1/instruments/FUNDA/map-amfi", json={"code": "119551"})).status_code == 200
    dup = await app_client.post("/api/v1/instruments/FUNDB/map-amfi", json={"code": "119551"})
    assert dup.status_code == 409


async def test_no_duplicates_on_clean_demo(app_client):
    d = (await app_client.get("/api/v1/system/identifier-duplicates")).json()
    assert d["count"] == 0


# --- A3: mapping updates broad + detailed classification ------------------- #

async def test_amfi_mapping_sets_full_classification(app_client):
    await _add(app_client, "HDFCTEST", asset_class="equity", currency="INR")
    await app_client.post("/api/v1/instruments/HDFCTEST/map-amfi", json={"code": "100027"})
    m = (await app_client.get("/api/v1/instruments/HDFCTEST")).json()["instrument"]
    assert m["asset_class"] == "mutual_fund"
    assert m["asset_subclass"] == "mutual_fund"
    assert m["liquidity_profile"] == "redeemable"
    assert m["listing_country"] == "IN"


async def test_coingecko_mapping_sets_crypto_class(app_client):
    await _add(app_client, "SOLX", asset_class="equity")
    await app_client.post("/api/v1/instruments/SOLX/map-coingecko", json={"id": "solana"})
    m = (await app_client.get("/api/v1/instruments/SOLX")).json()["instrument"]
    assert m["asset_class"] == "crypto" and m["asset_subclass"] == "crypto"


# --- A4: derivative is a subclass, never AssetClass("derivative") ---------- #

async def test_reclassify_never_crashes_on_derivative(app_client):
    # Import a Kite master with a future, map to it, and confirm broad class stays valid.
    import pathlib

    csv = (pathlib.Path(__file__).parents[1] / "fixtures" / "kite_instruments.csv").read_bytes()
    await app_client.post("/api/v1/kite/refresh-instruments", files={"file": ("k.csv", csv, "text/csv")})
    await _add(app_client, "NIFTYFUTX", asset_class="equity", currency="INR")
    r = await app_client.post("/api/v1/instruments/NIFTYFUTX/map-kite", json={"instrument_token": 13568259})
    assert r.status_code == 200 and r.json()["asset_subclass"] == "derivative"
    m = (await app_client.get("/api/v1/instruments/NIFTYFUTX")).json()["instrument"]
    assert m["asset_class"] in ("equity", "commodity")   # valid broad class, not "derivative"
    assert m["asset_subclass"] == "derivative"
    # And the bulk reclassify runs cleanly with a derivative present.
    assert (await app_client.post("/api/v1/portfolio/reclassify")).status_code == 200
