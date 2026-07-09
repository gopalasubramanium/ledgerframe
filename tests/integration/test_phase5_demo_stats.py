# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 5a: expanded multi-asset demo data + XIRR in the stats panel."""

from __future__ import annotations


async def test_demo_covers_the_asset_taxonomy(app_client):
    holdings = (await app_client.get("/api/v1/portfolio/holdings")).json()["holdings"]
    classes = {h["asset_class"] for h in holdings}
    # The demo now spans equities/ETFs, a mutual fund, cash, FD, bond, retirement,
    # crypto, property and a liability.
    for expected in ("equity", "etf", "mutual_fund", "cash", "fixed_deposit",
                     "bond", "retirement", "crypto", "property", "liability"):
        assert expected in classes, f"missing demo asset class: {expected}"


async def test_stats_includes_money_weighted_return(app_client):
    stats = (await app_client.get("/api/v1/portfolio/stats")).json()
    labels = {m["label"] for m in stats["metrics"]}
    assert "Money-weighted return (XIRR)" in labels
    xirr_metric = next(m for m in stats["metrics"] if m["label"].startswith("Money-weighted"))
    # Demo has real buy transactions + a current invested value → a computable XIRR.
    assert xirr_metric["value"] is not None
    assert xirr_metric["kind"] == "pct"
    # TWR is present too (value may be a number or, if history is thin, "not applicable").
    assert "Time-weighted return (TWR)" in labels
    twr_metric = next(m for m in stats["metrics"] if m["label"].startswith("Time-weighted"))
    assert twr_metric["kind"] == "pct"
