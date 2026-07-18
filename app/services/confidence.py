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
    if getattr(hv, "fx_unavailable", False):
        # W-1b: a native price exists but no FX rate to state it in base — the value is
        # not converted (never a fabricated 1.0), so it is heavily penalised and named.
        score -= 30
        factors.append("FX rate unavailable — value not converted to base (−30)")
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


def portfolio_input_quality(val) -> tuple[int, int]:
    """(stale, low-confidence) counts over the positive-value holdings a figure is computed FROM.

    The rules every reader honours (the Gate-A10 shape): a stale priced holding, and the ``< 50``
    low-confidence band (PRODUCT-SPEC §5). Extracted here so a derived-figure reader (drift,
    scenarios) can flag that its inputs may not be fresh — Guarantee 3 does not exempt a derived
    figure. (Policy/Review still carry their own copies; consolidating them onto this is recorded
    in 08-TECH-DEBT — not rewired mid-build on accepted pages.)
    """
    priced = [h for h in val.holdings if h.market_value_base > 0]
    stale = sum(1 for h in priced if h.is_stale and h.symbol)
    low = sum(1 for h in priced if score_holding(h)["confidence"] < 50)
    return stale, low


def inputs_quality_note(stale: int, low: int) -> str | None:
    """An honest, SERVED reason a derived figure may be off — or None when there is nothing to
    warn about. States a FACT about the inputs; names no trade, no field, no endpoint (copy
    hygiene). PROPOSED copy — the owner ratifies the wording."""
    if not stale and not low:
        return None
    parts = []
    if stale:
        parts.append(f"{stale} {'price is' if stale == 1 else 'prices are'} stale")
    if low:
        parts.append(f"{low} {'holding is' if low == 1 else 'holdings are'} low-confidence")
    return f"{' and '.join(parts)} — these figures may not reflect current values."
