# SPDX-License-Identifier: AGPL-3.0-or-later
"""A5 (legacy CSV → safe v2 + optional metadata), A6 (manual-asset metadata),
A7 (Pricing Health actions: source override + per-holding refresh)."""

from __future__ import annotations

# --- A5: legacy CSV import routes through the safe v2 path -------------------- #

async def test_legacy_csv_classifies_and_dedupes(app_client):
    csv = (
        b"date,symbol,type,quantity,price,fees,taxes,currency,note,asset_class,country\n"
        b"2025-02-01,SOL,buy,5,150,0,0,USD,,crypto,\n"
    )
    r1 = await app_client.post("/api/v1/portfolio/import/csv", files={"file": ("t.csv", csv, "text/csv")})
    assert r1.status_code == 200 and r1.json()["imported"] == 1
    # Classified (not defaulted to equity) via the shared v2 path.
    m = (await app_client.get("/api/v1/instruments/SOL")).json()["instrument"]
    assert m["asset_class"] == "crypto"
    # Idempotent: same file again imports nothing (content-hash / fingerprint dedup).
    r2 = await app_client.post("/api/v1/portfolio/import/csv", files={"file": ("t.csv", csv, "text/csv")})
    assert r2.json()["imported"] == 0


async def test_csv_optional_identifier_and_injection_guard(app_client):
    csv = (
        b"date,symbol,type,quantity,price,fees,taxes,currency,note,asset_class,identifier_type,identifier_value\n"
        b"2025-03-01,INFY.NSE,buy,3,1500,0,0,INR,=cmd|calc,equity,isin,INE009A01021\n"
    )
    r = await app_client.post("/api/v1/portfolio/import/csv", files={"file": ("t.csv", csv, "text/csv")})
    assert r.status_code == 200 and r.json()["imported"] == 1
    m = (await app_client.get("/api/v1/instruments/INFY.NSE")).json()["instrument"]
    assert any(i["id_type"] == "isin" and i["value"] == "INE009A01021" for i in m["identifiers"])


# --- A6: manual asset metadata (optional, whitelisted) ----------------------- #

async def test_manual_holding_meta_roundtrip_and_whitelist(app_client):
    r = await app_client.post("/api/v1/portfolio/manual-holdings", json={
        "label": "OCBC 12-month FD", "asset_class": "fixed_deposit", "value": 50000, "currency": "SGD",
        "meta": {"rate": "3.4%", "maturity_date": "2026-01-15", "issuer": "OCBC", "evil": "x" * 999},
    })
    assert r.status_code == 200
    rows = (await app_client.get("/api/v1/portfolio/manual-holdings")).json()["holdings"]
    fd = next(h for h in rows if h["label"] == "OCBC 12-month FD")
    assert fd["meta"]["rate"] == "3.4%" and fd["meta"]["issuer"] == "OCBC"
    assert "evil" not in fd["meta"]                 # non-whitelisted key dropped


async def test_manual_value_still_works_without_meta(app_client):
    r = await app_client.post("/api/v1/portfolio/manual-holdings", json={
        "label": "Emergency cash 2", "asset_class": "cash", "value": 1000, "currency": "SGD"})
    assert r.status_code == 200


# --- A7: pricing-health actions --------------------------------------------- #

async def test_source_override_set_and_clear(app_client):
    # A keyless source valid for a US equity is accepted (§5).
    r = await app_client.patch("/api/v1/instruments/AAPL", json={"source_override": "yahoo"})
    assert r.status_code == 200 and r.json()["source_override"] == "yahoo"
    r2 = await app_client.patch("/api/v1/instruments/AAPL", json={"source_override": "auto"})
    assert r2.json()["source_override"] is None


async def test_source_override_validation(app_client):
    # Unknown provider → rejected.
    bad = await app_client.patch("/api/v1/instruments/AAPL", json={"source_override": "not-a-provider"})
    assert bad.status_code == 400
    # A credentialed provider without credentials (demo has no EODHD key) → rejected.
    auth = await app_client.patch("/api/v1/instruments/AAPL", json={"source_override": "eodhd"})
    assert auth.status_code == 400 and "credential" in auth.json()["detail"].lower()
    # Kite (India-only) on a US equity → rejected.
    region = await app_client.patch("/api/v1/instruments/AAPL", json={"source_override": "kite"})
    assert region.status_code == 400
    # AMFI on a non-fund → rejected.
    amfi = await app_client.patch("/api/v1/instruments/AAPL", json={"source_override": "amfi_nav"})
    assert amfi.status_code == 400


async def test_refresh_holding_action(app_client):
    holdings = (await app_client.get("/api/v1/portfolio/holdings")).json()["holdings"]
    market = next(h for h in holdings if h["symbol"] == "AAPL")
    manual = next(h for h in holdings if h["symbol"] is None)
    rm = await app_client.post(f"/api/v1/portfolio/pricing-health/{market['id']}/refresh")
    assert rm.status_code == 200 and rm.json()["refreshed"] is True
    ru = await app_client.post(f"/api/v1/portfolio/pricing-health/{manual['id']}/refresh")
    assert ru.status_code == 200 and ru.json()["refreshed"] is False
