# SPDX-License-Identifier: AGPL-3.0-or-later
"""page-heatmap Phase 0 (ND-8) — the HoldingView reshape: per-holding `country` +
server-derived D-083 `region`, so the Heatmap's region filter reads served values (no
client region map, the Markets rule).

Fail-first: RED on the pre-reshape shape (HoldingView had neither field).
"""
from __future__ import annotations

import re

from app.core.regions import REGIONS


async def test_holdings_serve_country_and_region(app_client):
    d = (await app_client.get("/api/v1/portfolio/holdings")).json()
    assert d["holdings"], "demo should have holdings"
    for h in d["holdings"]:
        # Both fields are present on every row (reshape applied).
        assert "country" in h and "region" in h
        # region is TOTAL — always one of the six D-083 buckets (never null, never "Global").
        assert h["region"] in REGIONS, h["region"]
        assert h["region"] != "Global"


async def test_region_is_derived_from_country_server_side(app_client):
    """Every served region matches the canonical derivation of its served country — proving the
    server derived it (the client is never expected to map country → region)."""
    from app.core.regions import region_of

    d = (await app_client.get("/api/v1/portfolio/holdings")).json()
    for h in d["holdings"]:
        assert h["region"] == region_of(h["country"])
    # The demo spans multiple regions (US equities + an India + a Singapore name, per markets tests).
    regions = {h["region"] for h in d["holdings"]}
    assert len(regions) >= 2, f"expected a multi-region demo, got {regions}"


# --- §12hm1-1 (owner walk, ND-7c REVERSAL): the tile readout is built from SERVED display strings.
# Fail-first: RED before the reader served `market_value_display` / `day_change_pct_display`.


async def test_holdings_serve_display_strings_for_the_tile_readout(app_client):
    """The reader serves the readout's figures as display STRINGS (D-105 posture), so the frontend
    renders them verbatim and formats nothing."""
    d = (await app_client.get("/api/v1/portfolio/holdings")).json()
    priced = [h for h in d["holdings"] if h["is_priced"] and (h["market_value"] or 0) > 0]
    assert priced, "demo should have priced holdings"
    for h in priced:
        assert isinstance(h["market_value_display"], str), h
        # 2dp money, grouped thousands — the served string, not a float.
        assert re.fullmatch(r"-?[\d,]+\.\d{2}", h["market_value_display"]), h["market_value_display"]
        pct = h["day_change_pct_display"]
        # Signed percent, or an HONEST null (rendered as an em dash + reason) — never a made-up 0%.
        assert pct is None or re.fullmatch(r"[+−]?[\d,]+\.\d{2}%", pct), pct


async def test_display_strings_are_null_when_the_figure_does_not_exist(app_client):
    """An absent figure stays absent — the reader never fabricates a 0 (Guarantee 3)."""
    d = (await app_client.get("/api/v1/portfolio/holdings")).json()
    for h in d["holdings"]:
        if h["market_value"] is None:
            assert h["market_value_display"] is None
        if h["day_change_pct"] is None:
            assert h["day_change_pct_display"] is None
