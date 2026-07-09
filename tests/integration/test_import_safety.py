# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 3a: safe CSV import — preview (no mutation), validation, duplicate
detection, and idempotent commit."""

from __future__ import annotations

_CSV = (
    b"date,symbol,type,quantity,price,fees,taxes,currency,note\n"
    b"2024-02-01,TESTX,buy,10,50,1,0,USD,phase3\n"
    b"2024-02-02,TESTX,sell,5,60,1,0,USD,trim\n"
    b"notadate,TESTX,buy,1,1,0,0,USD,bad row\n"
)


def _file(content: bytes):
    return {"file": ("import.csv", content, "text/csv")}


async def _txn_count(client) -> int:
    r = await client.get("/api/v1/portfolio/transactions")
    return len(r.json()["transactions"])


async def test_preview_validates_without_mutating(app_client):
    before = await _txn_count(app_client)
    r = await app_client.post("/api/v1/portfolio/import/preview", files=_file(_CSV))
    assert r.status_code == 200
    body = r.json()
    assert body["summary"]["valid"] == 2
    assert body["summary"]["errors"] == 1          # the 'notadate' row
    assert body["already_imported"] is False
    # Preview writes nothing.
    assert await _txn_count(app_client) == before


async def test_commit_is_idempotent_by_content_hash(app_client):
    before = await _txn_count(app_client)
    r1 = await app_client.post("/api/v1/portfolio/import/commit", files=_file(_CSV))
    assert r1.status_code == 200
    assert r1.json()["imported"] == 2
    after_first = await _txn_count(app_client)
    assert after_first == before + 2

    # Re-importing the exact same file is a no-op.
    r2 = await app_client.post("/api/v1/portfolio/import/commit", files=_file(_CSV))
    assert r2.json().get("skipped") is True
    assert r2.json()["imported"] == 0
    assert await _txn_count(app_client) == after_first


async def test_duplicate_rows_flagged_against_existing(app_client):
    await app_client.post("/api/v1/portfolio/import/commit", files=_file(_CSV))
    # A DIFFERENT file (new hash) that repeats one already-imported row.
    dup_csv = (
        b"date,symbol,type,quantity,price,fees,taxes,currency,note\n"
        b"2024-02-01,TESTX,buy,10,50,1,0,USD,dup\n"
    )
    r = await app_client.post("/api/v1/portfolio/import/preview", files=_file(dup_csv))
    body = r.json()
    assert body["already_imported"] is False       # different content hash
    assert body["summary"]["duplicates"] == 1      # but the row already exists
    assert body["summary"]["new"] == 0
