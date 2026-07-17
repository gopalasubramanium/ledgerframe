# SPDX-License-Identifier: AGPL-3.0-or-later
"""page-settings §9 / Phase 0 — the `_ALLOWED_KEYS` reconciliation (D-078).

Allow-list keys are INVISIBLE to the OpenAPI shape check (`/settings` serves a free
dict, `API-CONTRACT.md:91`), so each change is pinned here, not by the contract regen.

Delta 1 (§9-1, Amendment A): `long_term_days` SHIPS — a served-value round-trip + the
numeric validator (mirrors the route's `ge=0, le=3660`). The removed-key sweep
(delta 3, §9-2(b)/§9-6/§9-7) is pinned in the same file once those keys are gone.
"""

from __future__ import annotations

import pytest

# The seven keys removed this milestone (§9-2(b) rotation trio + §9-6 per-device
# redundancies + §9-7 no-consumer/no-home pair). Each must now be an honest 400.
REMOVED_KEYS = [
    "rotation_seconds",
    "rotation_pages",
    "focus_page",
    "reduced_motion",
    "high_contrast",
    "refresh_interval_seconds",
    "display_sleep_minutes",
]

# Keys that must SURVIVE the sweep — a served-value round-trip guards against a
# future silent delisting. `voice_enabled` / `ai_model` survive by RECORDED
# DEFERRAL (Voice R-32 / AI-surfaces D-067/D-068), exempt from the D-078 sweep —
# their presence here is the proof they were NOT swept.
SURVIVING_KEYS = {
    "privacy_mode": "true",
    "home_quote_source": "markets",
    "voice_enabled": "true",
    "ai_model": "gpt-x",
}


# --- §9-1 (Amendment A): long_term_days ships with Settings ------------------


async def test_long_term_days_is_settable_and_reads_back(app_client):
    """Served-value round-trip: the threshold PUTs and reads back as a stored row.
    RED before delta 1 on the current unknown-key-400 (`long_term_days` unlisted)."""
    r = await app_client.put("/api/v1/settings", json={"values": {"long_term_days": "500"}})
    assert r.status_code == 200, r.text
    assert r.json()["applied"]["long_term_days"] == "500"

    got = (await app_client.get("/api/v1/settings")).json()
    assert got["stored"]["long_term_days"] == "500"


async def test_long_term_days_validator_mirrors_route_bounds(app_client):
    """The numeric validator mirrors the route's `ge=0, le=3660` — a non-numeric or
    out-of-range value is an honest 400, never a silently-stored bad threshold."""
    for bad in ("abc", "-1", "3661"):
        r = await app_client.put("/api/v1/settings", json={"values": {"long_term_days": bad}})
        assert r.status_code == 400, f"{bad!r} should be rejected, got {r.status_code}"
        got = (await app_client.get("/api/v1/settings")).json()
        assert got["stored"].get("long_term_days") != bad

    # The bounds themselves are inclusive (0 and 3660 are valid).
    for ok in ("0", "3660"):
        r = await app_client.put("/api/v1/settings", json={"values": {"long_term_days": ok}})
        assert r.status_code == 200, f"{ok!r} should be accepted: {r.text}"


# --- delta 3 (§9-2(b)/§9-6/§9-7, Amendment D): removed keys are an honest 400 ---


@pytest.mark.parametrize("key", REMOVED_KEYS)
async def test_removed_key_is_unknown_400(app_client, key):
    """D-078: a removed write-only key is REFUSED, not silently skipped. RED before
    delta 3 — each key was still in `_ALLOWED_KEYS` and a PUT returned 200."""
    r = await app_client.put("/api/v1/settings", json={"values": {key: "1"}})
    assert r.status_code == 400, f"{key} should be an unknown-key 400, got {r.status_code}"
    assert key in r.json()["detail"]


# --- Amendment D: surviving keys still round-trip (delisting guard) ----------


@pytest.mark.parametrize("key,value", list(SURVIVING_KEYS.items()))
async def test_surviving_key_reads_back(app_client, key, value):
    r = await app_client.put("/api/v1/settings", json={"values": {key: value}})
    assert r.status_code == 200, r.text
    got = (await app_client.get("/api/v1/settings")).json()
    assert got["stored"][key] == value
