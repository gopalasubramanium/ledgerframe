# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 4: AMFI service + API — refresh from a fixture, search, exact mapping, and
official-NAV provenance flowing into valuation. No network."""

from __future__ import annotations

from pathlib import Path

FIXTURE = (Path(__file__).parents[1] / "fixtures" / "amfi_navall_sample.txt").read_bytes()


def _file():
    return {"file": ("NAVAll.txt", FIXTURE, "text/plain")}


async def test_refresh_search_map_and_official_nav(app_client):
    # 1) Refresh the scheme master + NAVs from the uploaded fixture (offline).
    r = await app_client.post("/api/v1/amfi/refresh", files=_file())
    assert r.status_code == 200
    body = r.json()
    assert body["schemes"] == 5 and body["priced"] == 4      # 999999 is N.A. → unpriced

    st = (await app_client.get("/api/v1/amfi/status")).json()
    assert st["schemes"] == 5 and st["priced"] == 4

    # 2) Search: name substring, exact code, and ISIN.
    codes = {x["code"] for x in (await app_client.get("/api/v1/amfi/search", params={"q": "frontline"})).json()["results"]}
    assert "119551" in codes
    exact = (await app_client.get("/api/v1/amfi/search", params={"q": "118989"})).json()["results"]
    assert exact and exact[0]["name"].startswith("HDFC Index")
    by_isin = (await app_client.get("/api/v1/amfi/search", params={"q": "INF209K01YM2"})).json()["results"]
    assert by_isin and by_isin[0]["code"] == "119551"

    # 3) Add a mutual-fund holding and map it to an EXACT scheme code.
    await app_client.post("/api/v1/portfolio/transactions", json={
        "symbol": "MYMF", "type": "buy", "ts": "2024-01-01T10:00:00",
        "quantity": 100, "price": 400, "currency": "INR"})
    m = await app_client.post("/api/v1/instruments/MYMF/map-amfi", json={"code": "119551"})
    assert m.status_code == 200 and m.json()["published"] == 1

    # 4) The holding is now valued from the official NAV (not a market quote).
    holdings = (await app_client.get("/api/v1/portfolio/holdings")).json()["holdings"]
    mymf = next(h for h in holdings if h["symbol"] == "MYMF")
    assert mymf["valuation_method"] == "official_nav"
    assert mymf["valuation_label"] == "Official NAV"
    # NAV 512.3456 × 100 units, converted to base — a positive value from the NAV.
    assert mymf["market_value"] > 0


async def test_refresh_is_idempotent(app_client):
    await app_client.post("/api/v1/amfi/refresh", files=_file())
    r2 = await app_client.post("/api/v1/amfi/refresh", files=_file())
    # Re-running upserts the same rows — still 5 schemes, no duplicates.
    assert r2.json()["schemes"] == 5
    st = (await app_client.get("/api/v1/amfi/status")).json()
    assert st["schemes"] == 5


async def test_refresh_backfills_codenamed_mutual_fund_name(app_client):
    """§14dr-16 — a name-less mutual fund whose SYMBOL is a bare AMFI code (added from the
    master without a mapping — the owner's "103504" case) gets its display name resolved
    from the master on the next refresh. Served in the result (names_backfilled), logged,
    idempotent, never overwrites a real name."""
    # A code-named, name-less mutual fund (the dr-16 create drop: no name persisted).
    await app_client.post("/api/v1/portfolio/transactions", json={
        "symbol": "119551", "type": "buy", "ts": "2024-01-01T10:00:00",
        "quantity": 1, "price": 10, "currency": "INR", "asset_class": "mutual_fund"})
    h = (await app_client.get("/api/v1/portfolio/holdings")).json()["holdings"]
    mf = next(x for x in h if x["symbol"] == "119551")
    assert (mf["name"] or "119551") == "119551"  # identified only by the code

    # A master refresh HEALS it — a served count + the resolved scheme name.
    r = await app_client.post("/api/v1/amfi/refresh", files=_file())
    assert r.json()["names_backfilled"] >= 1

    h2 = (await app_client.get("/api/v1/portfolio/holdings")).json()["holdings"]
    mf2 = next(x for x in h2 if x["symbol"] == "119551")
    assert mf2["name"] == "Aditya Birla Sun Life Frontline Equity Fund - Direct Plan - Growth"

    # Idempotent: a second refresh backfills nothing new (the name is already real).
    r2 = await app_client.post("/api/v1/amfi/refresh", files=_file())
    assert r2.json()["names_backfilled"] == 0


async def test_status_synced_at_never_then_after_refresh(session):
    """§14dr-13 — status serves an honest last-*synced* timestamp: None until the master
    is synced (the never-synced empty the Masters card + picker read), an ISO string after.
    Uses the clean `session` fixture (no demo seed) so 'never synced' is genuinely empty."""
    from app.services import amfi as amfi_svc
    fresh = await amfi_svc.status(session)
    assert fresh["schemes"] == 0 and fresh["synced_at"] is None   # never synced
    await amfi_svc.refresh_schemes(session, FIXTURE.decode("utf-8-sig"))
    after = await amfi_svc.status(session)
    assert after["schemes"] == 5 and isinstance(after["synced_at"], str) and after["synced_at"]
