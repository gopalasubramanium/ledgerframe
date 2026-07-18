# SPDX-License-Identifier: AGPL-3.0-or-later
"""§14dr-27 (owner order) — the regression net for the whole R-38 routing surface.

A parametrised matrix over EVERY asset class × EVERY provider in the capability table,
asserting (1) matrix-cell capability accept/reject, and (2) route() rule outcome WITH and
WITHOUT a matrix cell — including the precedence guarantees (override > manual-only lane >
cache-publish NAV/coingecko > matrix cell > active provider) and AMENDMENT-A (an incapable /
degraded cell can never price LESS than today — it falls through unchanged).

Expected values are hand-authored from the routing spec (not re-derived from the code under
test); the class×provider capability map is the ground truth an owner would read off
CAPABILITIES.
"""

from __future__ import annotations

import pytest

from app.providers.market.router import ProviderAvailability, route
from app.services.market import validate_matrix_provider

ASSET_CLASSES = [
    "equity", "etf", "mutual_fund", "bond", "cash", "fixed_deposit", "commodity",
    "crypto", "property", "private", "retirement", "liability", "other",
]
PROVIDERS = ["alphavantage", "amfi_nav", "coingecko", "csv", "ecb_fx", "eodhd", "kite", "mock", "yahoo"]

# Ground truth: which providers can price each class (read off CAPABILITIES.asset_classes).
CLASS_CAPABLE: dict[str, set[str]] = {
    "equity": {"alphavantage", "csv", "eodhd", "kite", "mock", "yahoo"},
    "etf": {"alphavantage", "csv", "eodhd", "mock", "yahoo"},
    "mutual_fund": {"amfi_nav", "eodhd"},
    "bond": set(),
    "cash": set(),
    "fixed_deposit": set(),
    "commodity": {"kite", "mock", "yahoo"},
    "crypto": {"alphavantage", "coingecko", "eodhd", "mock", "yahoo"},
    "property": set(),
    "private": set(),
    "retirement": set(),
    "liability": set(),
    "other": set(),
}

_EODHD_KEYED = {"eodhd": ProviderAvailability(name="eodhd", configured=True, has_credentials=True)}


def _route(ac, country, **kw):
    return route(
        instrument_id=1, symbol="X", asset_class=ac, asset_subclass=None,
        listing_country=country, mappings=set(kw.pop("mappings", set())),
        active_provider="mock", has_manual=kw.pop("has_manual", False),
        cached_source=kw.pop("cached", None), matrix_provider=kw.pop("matrix", None),
        availability=kw.pop("avail", None),
    )


# --- (1) capability accept/reject: the class gate, for the full class × provider grid ----- #
@pytest.mark.parametrize("ac", ASSET_CLASSES)
@pytest.mark.parametrize("prov", PROVIDERS)
def test_matrix_cell_class_capability(ac, prov):
    _norm, err, _deg, _cav = validate_matrix_provider(ac, "*", prov)
    if prov in CLASS_CAPABLE[ac]:
        # The class gate passes; a region/key objection may remain, but never "can't price".
        assert not (err and "can't price" in err), (ac, prov, err)
    else:
        # A provider that can't price this class is rejected with the honest served reason.
        assert err and f"can't price a {ac}" in err, (ac, prov, err)


# --- (2a) route() WITHOUT a cell — the baseline per class ---------------------------------- #
NO_CELL = {
    "equity": ("US", "mock", "active"), "etf": ("US", "mock", "active"),
    "mutual_fund": ("US", "mock", "active"), "bond": ("US", "mock", "active"),
    "crypto": (None, "mock", "active"), "retirement": ("IN", "mock", "active"),
    "cash": (None, None, "lane"), "fixed_deposit": (None, None, "lane"),
    "commodity": (None, None, "lane"), "property": (None, None, "lane"),
    "private": (None, None, "lane"), "liability": (None, None, "lane"),
    "other": (None, None, "lane"),
}


@pytest.mark.parametrize("ac", ASSET_CLASSES)
def test_route_without_a_cell(ac):
    country, exp_source, exp_rule = NO_CELL[ac]
    d = _route(ac, country)
    assert (d.source_selected, d.route_rule) == (exp_source, exp_rule), (ac, d.source_selected, d.route_rule)


# --- (2b) route() WITH a capable cell — only classes that reach slot 3.5 route rule=matrix - #
# (ac -> country, provider, availability, expected source). Every provider here is genuinely
# capable for the class×country, keyed and live.
MATRIX_CELL = {
    "equity": ("US", "yahoo", None, "yahoo"),
    "etf": ("US", "yahoo", None, "yahoo"),
    "crypto": (None, "coingecko", None, "coingecko"),   # unmapped crypto falls through to the cell
    "mutual_fund": ("US", "eodhd", _EODHD_KEYED, "eodhd"),  # a GLOBAL (non-IN) fund, no AMFI owner
}


@pytest.mark.parametrize("ac", list(MATRIX_CELL))
def test_route_with_a_capable_cell_is_rule_matrix(ac):
    country, prov, avail, exp_source = MATRIX_CELL[ac]
    d = _route(ac, country, matrix=prov, avail=avail)
    assert (d.source_selected, d.route_rule) == (exp_source, "matrix"), (ac, d.source_selected, d.route_rule)


# --- (2c) precedence: cache-publish NAV / coingecko own the price BEFORE any matrix cell --- #
def test_amfi_nav_owns_india_mf_over_a_matrix_cell():
    # A mapped India MF is owned by amfi_nav (cache-publish) — a matrix cell for the same
    # class never overwrites the NAV (returns at step 3, before slot 3.5).
    d = _route("mutual_fund", "IN", mappings={"amfi_code"}, matrix="eodhd", avail=_EODHD_KEYED)
    assert d.source_selected == "amfi_nav" and d.route_rule != "matrix"


def test_coingecko_owns_mapped_crypto_over_a_matrix_cell():
    d = _route("crypto", None, mappings={"coingecko_id"}, cached="coingecko", matrix="alphavantage")
    assert d.source_selected == "coingecko" and d.route_rule != "matrix"


# --- (2d) precedence: a manual-only lane ignores any cell --------------------------------- #
@pytest.mark.parametrize("ac", ["cash", "fixed_deposit", "commodity", "property", "private", "liability", "other"])
def test_manual_only_lane_ignores_a_cell(ac):
    d = _route(ac, None, matrix="mock")   # even a hypothetical cell is inert
    assert d.route_rule != "matrix" and d.source_selected is None


# --- (2e) AMENDMENT-A: an INCAPABLE cell can never price less than today ------------------- #
@pytest.mark.parametrize("ac,country,bad_provider", [
    ("bond", "US", "eodhd"),        # eodhd can't price a bond
    ("equity", "IN", "kite"),       # kite covers IN but needs a key it doesn't have here
    ("retirement", "IN", "eodhd"),  # nothing covers retirement
])
def test_incapable_or_unkeyed_cell_falls_through_unchanged(ac, country, bad_provider):
    # With the (incapable/unkeyed) cell, resolution CONTINUES down the chain exactly as if the
    # cell were absent — never rule=matrix, never a worse result than no cell.
    with_cell = _route(ac, country, matrix=bad_provider)
    no_cell = _route(ac, country)
    assert with_cell.route_rule != "matrix"
    assert (with_cell.source_selected, with_cell.route_rule) == (no_cell.source_selected, no_cell.route_rule)
