# SPDX-License-Identifier: AGPL-3.0-or-later
"""page-settings §9-1 / Phase 0 delta 2 — the ONE default-resolution helper (Amendment A).

Amendment A binds:
  - ONE place resolves the stored `long_term_days` (A11 — `tax.resolve_long_term_days`,
    shared by BOTH readers and every long_term_days-taking route; no per-route re-reads);
  - PARAM-WINS — an explicit query param overrides the stored default;
  - existing export behaviour must not silently change — absent row → served 365.

Parametrised over BOTH reader-backed endpoints so a single failure proves the helper is
NOT shared (the whole point of A11).

RED-first status against pre-delta-2 code (routes hard-default 365, no stored resolution):
  (a) RED — real cause: the route sends 365 and the stored row is never read.
  (b) GREEN guardrail — explicit param already wins; it must STAY winning after the
      stored-default path lands (a naive "stored always wins" would break it).
  (c) GREEN guardrail — 365 is today's served default; Amendment A forbids changing it
      when no row exists.
"""

from __future__ import annotations

import pytest

# Both endpoints echo the resolved threshold as `long_term_days` in their report body.
LTD_ENDPOINTS = [
    "/api/v1/portfolio/realised-gains",
    "/api/v1/portfolio/tax-lots",
]


# --- (a) stored value honoured when the param is absent ---------------------


@pytest.mark.parametrize("endpoint", LTD_ENDPOINTS)
async def test_stored_threshold_is_the_default_when_param_absent(app_client, endpoint):
    """RED before delta 2: a stored non-365 threshold is IGNORED because the route
    hard-defaults 365 and nothing reads the setting. GREEN after: the report reflects
    the stored value with NO query param."""
    put = await app_client.put("/api/v1/settings", json={"values": {"long_term_days": "1"}})
    assert put.status_code == 200, put.text

    d = (await app_client.get(endpoint)).json()
    assert d["long_term_days"] == 1


# --- (b) an explicit param still overrides (PARAM-WINS) ----------------------


@pytest.mark.parametrize("endpoint", LTD_ENDPOINTS)
async def test_explicit_param_overrides_the_stored_default(app_client, endpoint):
    """PARAM-WINS guardrail: with a stored 1, an explicit `?long_term_days=3660` still
    wins — the stored default only fills the gap when the caller passes nothing."""
    put = await app_client.put("/api/v1/settings", json={"values": {"long_term_days": "1"}})
    assert put.status_code == 200, put.text

    d = (await app_client.get(f"{endpoint}?long_term_days=3660")).json()
    assert d["long_term_days"] == 3660


# --- (c) absent row → served 365 unchanged ----------------------------------


@pytest.mark.parametrize("endpoint", LTD_ENDPOINTS)
async def test_absent_row_serves_365_unchanged(app_client, endpoint):
    """No stored row (fresh instance) and no param → the served default stays 365.
    Amendment A: existing export behaviour must not silently change."""
    got = (await app_client.get("/api/v1/settings")).json()
    assert "long_term_days" not in got["stored"]  # fresh instance → unset

    d = (await app_client.get(endpoint)).json()
    assert d["long_term_days"] == 365
