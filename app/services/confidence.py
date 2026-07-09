# SPDX-License-Identifier: AGPL-3.0-or-later
"""Data confidence score (Phase 2a) — a transparent, deterministic 0–100 signal for
*how well-sourced* each holding's value is. Pure data-quality reporting: it says nothing
about whether a holding is good or bad to own, only how trustworthy the number is.

Base score by valuation method, then honest penalties. Every deduction is listed so the
score is explainable, never a black box.
"""

from __future__ import annotations

from decimal import Decimal

# Base confidence by how the value was established.
_BASE = {
    "market_quote": 100,
    "official_nav": 95,
    "calculated_accrual": 85,
    "manual_valuation": 70,
    "estimated_value": 40,
    "unavailable": 20,
}
# Explanatory (non-penalty) note for lower-base methods, so <100 is understandable.
_METHOD_NOTE = {
    "official_nav": "official NAV",
    "calculated_accrual": "modelled accrual (principal + interest)",
    "manual_valuation": "user-maintained value",
    "estimated_value": "valued from cost — no live price",
    "unavailable": "no value from any source",
}


def band_of(score: int) -> str:
    return "high" if score >= 80 else "medium" if score >= 50 else "low"


def score_holding(hv, mapping_required: bool = False) -> dict:
    """Confidence for one holding. ``hv`` is a HoldingValue; ``mapping_required`` comes
    from the router (an unmapped fund/crypto)."""
    method = getattr(hv, "valuation_method", "market_quote")
    score = _BASE.get(method, 60)
    factors: list[str] = []
    note = _METHOD_NOTE.get(method)
    if note:
        factors.append(note)
    if getattr(hv, "is_stale", False):
        score -= 20
        factors.append("price is stale (−20)")
    if mapping_required:
        score -= 15
        factors.append("needs identifier mapping (−15)")
    if (getattr(hv, "entitlement", None) or "") == "unavailable":
        score -= 15
        factors.append("no source could price it (−15)")
    score = max(0, min(100, score))
    return {"confidence": score, "confidence_band": band_of(score), "confidence_factors": factors}


def summarise(scored: list[tuple[Decimal, int]]) -> dict:
    """Portfolio confidence from ``(abs_value_base, score)`` pairs. Value-weighted so a
    tiny unpriced holding doesn't tank the headline, and a big manual asset counts."""
    gross = sum((v for v, _ in scored), Decimal(0)) or Decimal(1)
    weighted = sum((v * s for v, s in scored), Decimal(0))
    overall = int(round(weighted / gross))
    by_band: dict[str, dict[str, int | Decimal]] = {
        b: {"count": 0, "value": Decimal(0)} for b in ("high", "medium", "low")}
    for v, s in scored:
        b = band_of(s)
        by_band[b]["count"] += 1
        by_band[b]["value"] += v
    return {
        "overall": overall,
        "overall_band": band_of(overall),
        "by_band": {
            b: {"count": d["count"], "value_pct": float(round(d["value"] / gross * 100, 1))}
            for b, d in by_band.items()
        },
        "disclaimer": "Data-quality signal only — how well-sourced each value is. Not advice.",
    }
