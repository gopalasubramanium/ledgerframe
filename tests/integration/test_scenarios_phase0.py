# SPDX-License-Identifier: AGPL-3.0-or-later
"""page-scenarios Phase 0 — the §9 contract deltas (9-2, 9-3, 9-4, 9-7, 9-8, 9-10)."""

from __future__ import annotations

BASE = "/api/v1"


async def _sc(client, **params):
    return (await client.get(f"{BASE}/portfolio/scenarios", params=params or None)).json()


# --------------------------------------------------------------------------- #
# 9-3 — D-105: every money figure is a SERVED display string.
# --------------------------------------------------------------------------- #


async def test_scenarios_serve_money_as_display_strings(app_client):
    d = await _sc(app_client)
    assert isinstance(d["net_worth_display"], str)
    for s in d["asset_scenarios"]:
        assert isinstance(s["exposure_display"], str)
        assert isinstance(s["delta_display"], str)
        assert isinstance(s["new_net_worth_display"], str)
        # A percentage is NOT money — it stays a number (D-105 is about money).
        assert isinstance(s["pct_change"], float)
    liq = d["liquidity"]
    assert isinstance(liq["liquid_display"], str)
    assert isinstance(liq["obligation_due"]["amount_display"], str)
    assert isinstance(liq["obligation_due"]["new_liquid_display"], str)
    for e in ("equities", "crypto", "property", "foreign_fx"):
        assert isinstance(d["exposures"][f"{e}_display"], str)


# --------------------------------------------------------------------------- #
# 9-2 — the A10 staleness annotation (a what-if is computed on today's values;
#       if those are stale, the payload must say so).
# --------------------------------------------------------------------------- #


async def test_scenarios_carry_a_staleness_annotation(app_client):
    d = await _sc(app_client)
    assert "stale_inputs" in d and "low_confidence_inputs" in d
    assert "inputs_stale" in d and "inputs_note" in d
    # Shape parity with the Policy A10 annotation, from the SAME rules (one reader's inputs).
    assert isinstance(d["stale_inputs"], int)
    assert isinstance(d["inputs_stale"], bool)


# --------------------------------------------------------------------------- #
# 9-4 — ONE DERIVATION: exposures reconcile with Portfolio's canonical allocation().
# --------------------------------------------------------------------------- #


async def test_exposures_reconcile_with_portfolio_allocation(app_client):
    d = await _sc(app_client)
    summary = (await app_client.get(f"{BASE}/portfolio/summary")).json()
    alloc = summary["allocation_by_class"]

    # crypto/property ARE Portfolio's allocation-by-class buckets — not a second derivation.
    assert abs(d["exposures"]["crypto"] - alloc.get("crypto", 0)) < 1.0
    assert abs(d["exposures"]["property"] - alloc.get("property", 0)) < 1.0
    # equities = the SUM of the three canonical class buckets.
    eq = alloc.get("equity", 0) + alloc.get("etf", 0) + alloc.get("mutual_fund", 0)
    assert abs(d["exposures"]["equities"] - eq) < 1.0
    # foreign_fx = the sum of the non-base currency buckets.
    by_ccy = summary["allocation_by_currency"]
    base = d["base_currency"]
    foreign = sum(v for k, v in by_ccy.items() if k != base)
    assert abs(d["exposures"]["foreign_fx"] - foreign) < 1.0


# --------------------------------------------------------------------------- #
# 9-7 — the shock magnitudes are NAMED CONSTANTS (no inline literals), values unchanged.
# --------------------------------------------------------------------------- #


def test_shock_magnitudes_are_named_constants():
    from app.services import scenarios as sc

    # The magnitudes live in named constants a future R-11 can make configurable — not scattered
    # inline literals. The VALUES are unchanged (the shipped scenarios must not move).
    assert sc.EQUITY_SHOCKS == (10, 20, 30)
    assert sc.RISK_SHOCK == 20
    assert sc.CRYPTO_SHOCK == 50
    assert sc.PROPERTY_SHOCK == 10
    assert sc.FX_SHOCK == 10


async def test_shocks_unchanged_after_extraction(app_client):
    """The extraction is value-preserving: the 7 shocks and their magnitudes are exactly as before."""
    d = await _sc(app_client)
    by = {s["id"]: s for s in d["asset_scenarios"]}
    assert set(by) == {"equities_10", "equities_20", "equities_30", "risk_20",
                       "crypto_50", "property_10", "fx_10"}
    nw = d["net_worth"]
    # 20% is exactly twice 10%; 30% thrice (deterministic).
    assert abs(by["equities_20"]["delta"] - 2 * by["equities_10"]["delta"]) < 2.0
    assert abs(by["equities_30"]["delta"] - 3 * by["equities_10"]["delta"]) < 2.0
    for s in by.values():
        assert s["delta"] <= 0 and abs(s["new_net_worth"] - (nw + s["delta"])) < 2.0


# --------------------------------------------------------------------------- #
# 9-8 — HOUSEHOLD-ONLY: ?entity_id is rejected, not silently mixed-scoped.
# --------------------------------------------------------------------------- #


async def test_scenarios_reject_entity_scope(app_client):
    r = await app_client.get(f"{BASE}/portfolio/scenarios", params={"entity_id": 1})
    assert r.status_code == 400
    assert "household" in r.json()["detail"].lower()
    # The household read still works.
    assert (await app_client.get(f"{BASE}/portfolio/scenarios")).status_code == 200


# --------------------------------------------------------------------------- #
# 9-10 — SN-1: the drawdown note uses the user's vocabulary ("expenses"), not "obligations".
# --------------------------------------------------------------------------- #


async def test_obligation_note_uses_expenses_vocabulary(app_client):
    d = await _sc(app_client)
    note = d["liquidity"]["obligation_due"]["note"].lower()
    assert "expenses" in note
    assert "obligation" not in note      # the model's word never reaches the user
