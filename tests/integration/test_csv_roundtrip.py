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


async def test_generated_template_is_comprehensive_and_importable(app_client):
    """D-096 — the downloadable template is generated from the D-090 matrix (one row
    per asset_class × permitted type) and is itself importable (round-trips clean)."""
    r = await app_client.get("/api/v1/portfolio/import/template")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    text = r.text
    assert text.splitlines()[0] == "date,symbol,type,quantity,price,fees,taxes,currency,note,asset_class,country"

    # Matches the matrix exactly (no drift): every offered combination has a row.
    matrix = (await app_client.get("/api/v1/refdata/txn-applicability")).json()
    import csv
    import io
    rows = list(csv.DictReader(io.StringIO(text)))
    combos = {(x["asset_class"], x["type"]) for x in rows}
    expected = {(ac, t) for ac, types in matrix.items() for t in types}
    assert combos == expected
    assert ("etf", "bonus") in combos          # the ratified ETF-bonus amendment
    assert ("fixed_deposit", "interest") in combos

    # The template re-imports with zero errors (round-trip contract).
    preview = (await app_client.post(
        "/api/v1/portfolio/import/preview", files={"file": ("t.csv", text.encode(), "text/csv")}
    )).json()
    assert "format_error" not in preview
    assert preview["summary"]["errors"] == 0


async def test_commit_reports_skipped_duplicates(app_client):
    """A commit of rows already in the ledger imports 0 and reports the skip count —
    the frontend uses this to warn honestly instead of a success 'Imported 0'."""
    csv_text = ("date,symbol,type,quantity,price,fees,taxes,currency,note,asset_class,country\n"
                "2022-02-02,ZDUP,buy,3,50,0,0,USD,,equity,US\n")
    first = (await app_client.post(
        "/api/v1/portfolio/import/commit", files={"file": ("t.csv", csv_text.encode(), "text/csv")}
    )).json()
    assert first["imported"] == 1
    # Re-commit the same content-as-rows (different file bytes so not the batch guard).
    csv2 = csv_text + "2022-02-03,ZNEW2,buy,1,10,0,0,USD,,equity,US\n"
    second = (await app_client.post(
        "/api/v1/portfolio/import/commit", files={"file": ("t2.csv", csv2.encode(), "text/csv")}
    )).json()
    assert second["imported"] == 1                 # only the new row
    assert second["skipped_duplicates"] == 1       # the duplicate reported, not silent
