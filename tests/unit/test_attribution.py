# SPDX-License-Identifier: AGPL-3.0-or-later
"""§4.5 Unit A — return-attribution decomposition (pure core, deterministic, read-only).

These vectors exercise `_attribute_core` directly with HoldingValue-like namespaces, so the
decomposition math is proved with explicit values and no DB/market. The core honesty proof is
RECONCILIATION: Σ contributions + residual == the headline return, exactly — the residual is the
surfaced un-attributed remainder (income + realised + in-period closes), never a fudge. Entity
scoping (the async path) is covered in tests/integration/test_attribution.py.
"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from app.services.analytics import _attribute_core


def _h(hid, unrealised, asset_class, sector, label=None, symbol=None):
    return SimpleNamespace(holding_id=hid, unrealised_pl_base=Decimal(str(unrealised)),
                           asset_class=asset_class, sector=sector,
                           label=label or (symbol or f"#{hid}"), symbol=symbol)


# A shared, explicit portfolio: cost $1000; unrealised +200/+100/−50; realised +30, income +20.
#   contributions (pp) = unrealised / cost × 100  →  +20.0 / +10.0 / −5.0  (Σ = +25.0)
#   headline           = (250 + 30 + 20) / 1000 × 100 = +30.0
#   residual           = 30.0 − 25.0 = +5.0  ( = (30 + 20)/1000×100 — the income+realised part )
def _sample():
    holdings = [_h(1, 200, "equity", "Tech", symbol="AAA"),
                _h(2, 100, "equity", "Health", symbol="BBB"),
                _h(3, -50, "crypto", None, symbol="CCC")]   # null sector → Unclassified
    return _attribute_core(holdings, total_unrealised=Decimal("250"), total_cost=Decimal("1000"),
                           realised=Decimal("30"), income=Decimal("20"), base_currency="USD", days=365)


# (1) RECONCILIATION (the honesty guarantee): Σ contributions + residual == headline, exactly.
def test_reconciliation_contributions_plus_residual_equals_headline():
    rep = _sample()
    assert rep["available"] is True
    contribs = [h["contribution_pct"] for h in rep["holdings"]]
    assert sorted(contribs) == [-5.0, 10.0, 20.0]                 # explicit per-holding pp
    assert rep["headline_return_pct"] == 30.0
    assert rep["residual_pct"] == 5.0
    # The invariant, at display precision (round kills float-repr noise from 4dp decimals).
    assert round(sum(contribs) + rep["residual_pct"], 6) == round(rep["headline_return_pct"], 6)
    # Residual is a real remainder, not a plug: it equals the income + realised return.
    rb = rep["residual_breakdown"]
    assert rb["income_pct"] == 2.0 and rb["realised_pct"] == 3.0
    assert round(rb["income_pct"] + rb["realised_pct"], 6) == rep["residual_pct"]


# (2) ROLL-UP: per-holding contributions sum to their asset-class and sector totals.
def test_rollups_sum_from_the_same_contributions():
    rep = _sample()
    ac = {r["key"]: r["contribution_pct"] for r in rep["by_asset_class"]}
    sec = {r["key"]: r["contribution_pct"] for r in rep["by_sector"]}
    assert ac == {"equity": 30.0, "crypto": -5.0}                 # 20 + 10 ; −5
    assert sec == {"Tech": 20.0, "Health": 10.0, "Unclassified": -5.0}
    # Both roll-ups reconcile to the same attributed total (headline − residual).
    attributed = round(rep["headline_return_pct"] - rep["residual_pct"], 6)
    assert round(sum(ac.values()), 6) == attributed
    assert round(sum(sec.values()), 6) == attributed


# (3) UNCLASSIFIED bucket: a null-sector holding is bucketed, never dropped or mislabelled.
def test_null_sector_goes_to_unclassified_bucket():
    rep = _sample()
    keys = [r["key"] for r in rep["by_sector"]]
    assert "Unclassified" in keys                                 # present…
    assert None not in keys                                       # …and not a null key
    # The raw holding still carries its true (null) sector — the bucket key is the only relabel.
    ccc = next(h for h in rep["holdings"] if h["symbol"] == "CCC")
    assert ccc["sector"] is None
    # Every holding is represented (nothing silently dropped).
    assert len(rep["holdings"]) == 3


# (4) THIN DATA (R3): non-positive cost basis → a clear 'unavailable' shape, not a crash.
def test_unavailable_on_non_positive_cost_basis():
    empty = _attribute_core([], Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0"),
                            base_currency="USD", days=365)
    assert empty["available"] is False and empty["headline_return_pct"] is None
    assert empty["holdings"] == [] and empty["by_sector"] == []
    # Holdings present but zero total cost is equally unattributable (no division by zero).
    z = _attribute_core([_h(1, 5, "equity", "Tech")], Decimal("5"), Decimal("0"),
                        Decimal("0"), Decimal("0"), base_currency="USD", days=365)
    assert z["available"] is False
