# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round-trip contract: the app's own transactions export must be its import's
cleanest input. Export → import preview → ZERO errors, ZERO fixes. This is the
permanent guard for the final-walk bug (holdings snapshot ≠ transactions ledger).

Rule (page-holdings.md + TEMPLATE-page-build.md): any surface that both exports and
imports a format must have a lossless round-trip test."""

from __future__ import annotations


def _file(content: bytes):
    return {"file": ("roundtrip.csv", content, "text/csv")}


async def _seed(app_client) -> None:
    for payload in [
        {"symbol": "AAPL", "type": "buy", "ts": "2024-01-15T09:30:00", "quantity": 10,
         "price": 185.50, "fees": 1, "currency": "USD", "asset_class": "equity", "country": "US"},
        {"symbol": "BTC", "type": "buy", "ts": "2024-05-10T09:30:00", "quantity": 0.1,
         "price": 64000, "fees": 5, "currency": "USD", "asset_class": "crypto"},
        {"symbol": "AAPL", "type": "sell", "ts": "2024-06-20T09:30:00", "quantity": 5,
         "price": 210, "fees": 1, "taxes": 0.5, "currency": "USD", "note": "Trim"},
    ]:
        assert (await app_client.post("/api/v1/portfolio/transactions", json=payload)).status_code == 200


async def test_transactions_export_reimports_losslessly(app_client):
    await _seed(app_client)

    exported = (await app_client.get("/api/v1/portfolio/transactions.csv"))
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/csv")
    text = exported.text
    # Header is exactly the import schema.
    assert text.splitlines()[0] == "date,symbol,type,quantity,price,fees,taxes,currency,note,asset_class,country"

    preview = (await app_client.post(
        "/api/v1/portfolio/import/preview", files=_file(text.encode())
    )).json()
    # The whole point: the app's own export parses with zero errors and zero fixes.
    assert "format_error" not in preview
    assert preview["summary"]["errors"] == 0
    assert preview["summary"]["total"] > 0
    assert all(r["ok"] for r in preview["rows"])
    # Dates parsed, types selected, symbols present (the exact symptoms that failed).
    ours = [r for r in preview["rows"] if r["symbol"] in ("AAPL", "BTC")]
    assert ours, "the seeded rows must survive the round-trip"
    for r in ours:
        assert r["type"] in ("buy", "sell")
        assert r["date"] and r["symbol"]


async def test_holdings_snapshot_is_guided_not_garbled(app_client):
    """The holdings snapshot is a REPORT, not an import file. Re-importing it must
    yield one honest message — never 14 cryptic per-cell errors."""
    await _seed(app_client)
    snapshot = (await app_client.get("/api/v1/portfolio/holdings.csv")).text
    preview = (await app_client.post(
        "/api/v1/portfolio/import/preview", files=_file(snapshot.encode())
    )).json()
    assert "format_error" in preview
    assert "snapshot" in preview["format_error"].lower()
    assert preview["rows"] == []
    assert preview["summary"]["errors"] == 0  # no per-row garbage
