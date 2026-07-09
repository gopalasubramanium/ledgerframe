# SPDX-License-Identifier: AGPL-3.0-or-later
"""v2.2: fix existing mis-classified/mis-named instruments (crypto named from an
equity search), reclassify from identifiers, manual edit, and CSV asset_class column."""

from __future__ import annotations


async def _add(app_client, **kw):
    body = {"type": "buy", "ts": "2025-01-15T10:00:00", "quantity": 1, "price": 1, "currency": "USD"}
    body.update(kw)
    return await app_client.post("/api/v1/portfolio/transactions", json=body)


async def test_reclassify_fixes_crypto_class_and_wrong_name(app_client):
    # Simulate the bug: a bare "XRP" added as an equity with an equity-scraped name.
    await _add(app_client, symbol="XRP", asset_class="equity", name="Common Shares Of Beneficial Interest")
    before = (await app_client.get("/api/v1/instruments/XRP")).json()["instrument"]
    assert before["asset_class"] == "equity"

    r = (await app_client.post("/api/v1/portfolio/reclassify")).json()
    assert r["reclassified"] >= 1

    after = (await app_client.get("/api/v1/instruments/XRP")).json()["instrument"]
    assert after["asset_class"] == "crypto"           # heuristic fixed the class
    assert "Beneficial" not in (after["name"] or "")  # wrong equity name cleared


async def test_manual_edit_instrument(app_client):
    await _add(app_client, symbol="FOOBAR", asset_class="equity", name="Foobar")
    r = await app_client.patch("/api/v1/instruments/FOOBAR", json={"asset_class": "crypto", "country": "SG", "name": "Foobar Coin"})
    assert r.status_code == 200
    m = (await app_client.get("/api/v1/instruments/FOOBAR")).json()["instrument"]
    assert m["asset_class"] == "crypto" and m["country"] == "SG" and m["name"] == "Foobar Coin"


async def test_csv_template_has_asset_class_and_country():
    from app.services.csv_import import TRANSACTION_TEMPLATE

    header = TRANSACTION_TEMPLATE.splitlines()[0]
    assert "asset_class" in header and "country" in header


async def test_csv_import_classifies_from_columns(app_client):
    # Importing a crypto row via CSV should create a crypto instrument, not an equity.
    csv = (
        b"date,symbol,type,quantity,price,fees,taxes,currency,note,asset_class,country\n"
        b"2025-01-10,SOL,buy,5,150,0,0,USD,,crypto,\n"
    )
    r = await app_client.post("/api/v1/portfolio/import/commit",
                              files={"file": ("t.csv", csv, "text/csv")})
    assert r.status_code == 200
    m = (await app_client.get("/api/v1/instruments/SOL")).json()["instrument"]
    assert m["asset_class"] == "crypto"
