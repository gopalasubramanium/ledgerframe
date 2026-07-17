# SPDX-License-Identifier: AGPL-3.0-or-later
"""Clearing demo data, seed-once behaviour, and live-data refresh endpoint."""

from __future__ import annotations


async def test_reset_without_pin_is_refused(app_client):
    # D-103 (page-settings System tab): reset-data is require_pin — a destructive, irreversible
    # wipe must be impossible on a no-PIN install. No PIN set → 403, and nothing is deleted.
    before = (await app_client.get("/api/v1/portfolio/holdings")).json()["holdings"]
    assert len(before) > 0
    r = await app_client.post("/api/v1/system/reset-data")
    assert r.status_code == 403, r.text
    # Data is untouched.
    after = (await app_client.get("/api/v1/portfolio/holdings")).json()["holdings"]
    assert len(after) == len(before)


async def test_reset_clears_holdings_and_blocks_reseed(app_client):
    # Demo data is present initially.
    before = (await app_client.get("/api/v1/portfolio/holdings")).json()["holdings"]
    assert len(before) > 0
    # D-103: set a PIN → the returned cookie authenticates the client for the PIN-gated reset.
    assert (await app_client.post("/api/v1/auth/set-pin", json={"pin": "009753"})).status_code == 200
    # Clear it — §14dr-20/D-103: the fresh PIN is threaded through (an unlocked session alone
    # does NOT satisfy the wipe).
    r = await app_client.post("/api/v1/system/reset-data", json={"pin": "009753"})
    assert r.status_code == 200
    after = (await app_client.get("/api/v1/portfolio/holdings")).json()["holdings"]
    assert after == []
    # Transactions gone too.
    txns = (await app_client.get("/api/v1/portfolio/transactions")).json()["transactions"]
    assert txns == []


async def test_reset_demands_a_fresh_pin_not_the_ambient_session(app_client):
    # §14dr-20 / D-103: reset-data, like purge, always demands a freshly-entered PIN — an
    # unlocked/ambient session never satisfies it (RED before the fix: the PIN was discarded).
    before = (await app_client.get("/api/v1/portfolio/holdings")).json()["holdings"]
    assert len(before) > 0
    assert (await app_client.post("/api/v1/auth/set-pin", json={"pin": "024680"})).status_code == 200
    # Unlocked session but the WRONG fresh PIN → refused, and nothing is wiped.
    wrong = await app_client.post("/api/v1/system/reset-data", json={"pin": "111111"})
    assert wrong.status_code == 401
    after = (await app_client.get("/api/v1/portfolio/holdings")).json()["holdings"]
    assert len(after) == len(before)
    # The correct fresh PIN → the reset proceeds.
    ok = await app_client.post("/api/v1/system/reset-data", json={"pin": "024680"})
    assert ok.status_code == 200


async def test_seed_runs_once(session):
    from app.seed.demo import seed_demo_data

    assert await seed_demo_data(session) is True       # first time seeds
    assert await seed_demo_data(session) is False       # flag set → no re-seed


async def test_refresh_data_endpoint(app_client):
    r = await app_client.post("/api/v1/system/refresh-data")
    assert r.status_code == 200
    body = r.json()
    assert "refreshed" in body and "total" in body


async def test_data_source_switch_applies_in_process(app_client, tmp_path, monkeypatch):
    import app.core.envfile as envfile

    monkeypatch.setattr(envfile, "ENV_PATH", tmp_path / ".env")
    r = await app_client.put("/api/v1/system/data-source", json={"provider": "csv"})
    assert r.status_code == 200
    assert r.json()["applied"] is True
