# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 4: Kite service + API — import the master (offline), search F&O identity,
map by exact token, and a status that never exposes credentials. No network."""

from __future__ import annotations

from pathlib import Path

CSV_BYTES = (Path(__file__).parents[1] / "fixtures" / "kite_instruments.csv").read_bytes()


def _file():
    return {"file": ("instruments.csv", CSV_BYTES, "text/csv")}


async def test_import_search_map_and_status(app_client):
    r = await app_client.post("/api/v1/kite/refresh-instruments", files=_file())
    assert r.status_code == 200 and r.json()["instruments"] == 6

    # Search surfaces F&O identity (expiry/strike/lot/type).
    res = (await app_client.get("/api/v1/kite/search", params={"q": "NIFTY"})).json()["results"]
    opt = next(x for x in res if x["tradingsymbol"] == "NIFTY26JUL25000CE")
    assert opt["instrument_type"] == "CE" and opt["expiry"] == "2026-07-31"
    assert opt["strike"] == 25000 and opt["lot_size"] == 50

    # Map a holding to an EXACT instrument token.
    await app_client.post("/api/v1/portfolio/transactions", json={
        "symbol": "NIFTYFUT", "type": "buy", "ts": "2024-01-01T10:00:00",
        "quantity": 50, "price": 24000, "currency": "INR"})
    m = await app_client.post("/api/v1/instruments/NIFTYFUT/map-kite", json={"instrument_token": 13568259})
    assert m.status_code == 200 and m.json()["instrument_type"] == "FUT"


async def test_status_never_exposes_credentials(app_client):
    await app_client.post("/api/v1/kite/refresh-instruments", files=_file())
    r = await app_client.get("/api/v1/kite/status")
    body = r.json()
    assert body["instruments"] == 6
    assert "configured" in body and body["configured"] is False   # no creds in test env
    # The response contains NO key/token/secret material.
    text = r.text.lower()
    assert "token" not in text and "api_key" not in text and "secret" not in text


async def test_refresh_without_config_or_file_is_rejected(app_client):
    r = await app_client.post("/api/v1/kite/refresh-instruments")  # no file, not configured
    assert r.status_code == 400
