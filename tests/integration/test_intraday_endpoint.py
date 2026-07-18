# SPDX-License-Identifier: AGPL-3.0-or-later
"""R-42 Phase 0.4 — the history reader carries served intraday availability + is the
range-triggered fetch (§9-3/§9-9).

The frontend sends a RANGE (never an interval); the server maps range→interval, applies
the server-side gate, and either fetches (user-triggered) or refuses with a served reason.
Every history load also carries the availability map so the range control renders its
disabled states from a served truth, never a frontend constant (closes the dr-7 gap).
"""
from __future__ import annotations


async def test_history_carries_intraday_availability_block(app_client):
    r = await app_client.get("/api/v1/instruments/AAPL/history")
    assert r.status_code == 200
    body = r.json()
    iv = body["intraday"]
    assert set(iv["ranges"]) == {"1D", "5D"}
    assert iv["ranges"]["1D"]["interval"] == "1min"
    assert iv["ranges"]["5D"]["interval"] == "5min"
    # Mock is intraday-capable → both ranges enabled on the demo instance.
    assert iv["ranges"]["1D"]["enabled"] is True
    assert iv["benchmark_reason"] == "Benchmark comparison is daily-range only."


async def test_range_1d_triggers_intraday_fetch(app_client):
    r = await app_client.get("/api/v1/instruments/AAPL/history", params={"range": "1D"})
    assert r.status_code == 200
    body = r.json()
    assert body["interval"] == "1min"          # server-side mapping, not the frontend's
    assert len(body["candles"]) > 0
    assert body["intraday"]["requested_range"] == "1D"
    assert body["intraday"]["fetch_state"] in ("fetched", "cached")
    # Intraday candles preserve time-of-day (not midnight-normalised).
    assert any(c["ts"][11:16] != "00:00" for c in body["candles"])


async def test_range_5d_maps_to_5min(app_client):
    r = await app_client.get("/api/v1/instruments/AAPL/history", params={"range": "5D"})
    body = r.json()
    assert body["interval"] == "5min"
    assert len(body["candles"]) > 0


async def test_daily_range_label_is_passthrough(app_client):
    # A non-intraday range label doesn't hijack the reader: it serves the daily series
    # (interval/days) exactly as before, and still carries the availability block.
    r = await app_client.get("/api/v1/instruments/AAPL/history", params={"range": "1M", "days": 30})
    body = r.json()
    assert body["interval"] == "1d"
    assert body["intraday"]["requested_range"] is None
    assert body["intraday"]["fetch_state"] is None
    assert len(body["candles"]) > 0


async def test_daily_history_unchanged_without_range(app_client):
    # Regression: the plain daily load still works (no range param).
    r = await app_client.get("/api/v1/instruments/AAPL/history", params={"days": 90})
    body = r.json()
    assert body["interval"] == "1d"
    assert len(body["candles"]) > 0
    assert "intraday" in body
