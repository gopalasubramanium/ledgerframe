# SPDX-License-Identifier: AGPL-3.0-or-later
"""Valuation provenance: concise, honest labels for HOW a value was derived.

Kept separate from *entitlement* (recency/rights). A holding always shows one
label from this module so the user can see at a glance whether a number is a live
market quote, an official NAV, a manual value, a stale cache, or unavailable.
"""

from __future__ import annotations

from app.schemas.common import EntitlementStatus, ValuationMethod

# The canonical, user-facing labels (per the product spec). ESTIMATED_VALUE and
# FX_REFERENCE are internal honest states shown where relevant.
_METHOD_LABELS: dict[ValuationMethod, str] = {
    ValuationMethod.MARKET_QUOTE: "Live / delayed market quote",
    ValuationMethod.OFFICIAL_NAV: "Official NAV",
    ValuationMethod.BROKER_QUOTE: "Broker quote",
    ValuationMethod.MANUAL_VALUATION: "Manual value",
    ValuationMethod.STATEMENT_IMPORT: "Statement value",
    ValuationMethod.CALCULATED_ACCRUAL: "Accrued estimate",
    ValuationMethod.ESTIMATED_VALUE: "Estimated value",
    ValuationMethod.FX_REFERENCE: "Reference FX",
    ValuationMethod.UNAVAILABLE: "Price unavailable",
}


def valuation_label(
    method: ValuationMethod,
    *,
    entitlement: EntitlementStatus | str | None = None,
    is_stale: bool = False,
    price_available: bool = True,
) -> str:
    """Concise label for a holding's current value.

    Precedence: genuinely-unavailable → "Price unavailable"; a stale/cached market
    quote → "Stale cached value"; otherwise the method's own label. Manual, NAV and
    statement values are never overridden by staleness — their freshness is conveyed
    by their own valuation date, not the market-cache clock.
    """
    if not price_available or method is ValuationMethod.UNAVAILABLE:
        return _METHOD_LABELS[ValuationMethod.UNAVAILABLE]
    ent = entitlement.value if isinstance(entitlement, EntitlementStatus) else entitlement
    if method is ValuationMethod.MARKET_QUOTE and (is_stale or ent == EntitlementStatus.CACHED.value):
        return "Stale cached value"
    return _METHOD_LABELS.get(method, _METHOD_LABELS[ValuationMethod.MARKET_QUOTE])


def method_for_quote(entitlement: EntitlementStatus, price_available: bool) -> ValuationMethod:
    """Default valuation method for a provider quote (market data). Unavailable when
    there's no price; otherwise a market quote — the common case."""
    if not price_available:
        return ValuationMethod.UNAVAILABLE
    return ValuationMethod.MARKET_QUOTE


def health_status(
    method: ValuationMethod,
    *,
    entitlement: EntitlementStatus | str | None = None,
    is_stale: bool = False,
    price_available: bool = True,
) -> str:
    """A single concise status word for the Pricing Health view. One of:
    Fresh · Delayed · End-of-day · Cached · Manual · Estimated · Unavailable.
    (Mapping-required / Authentication-required come from provider adapters.)"""
    if not price_available or method is ValuationMethod.UNAVAILABLE:
        return "Unavailable"
    if method in (ValuationMethod.MANUAL_VALUATION, ValuationMethod.STATEMENT_IMPORT):
        return "Manual"
    if method in (ValuationMethod.ESTIMATED_VALUE, ValuationMethod.CALCULATED_ACCRUAL):
        return "Estimated"
    if method is ValuationMethod.OFFICIAL_NAV:
        return "End-of-day"
    ent = entitlement.value if isinstance(entitlement, EntitlementStatus) else entitlement
    if is_stale or ent == EntitlementStatus.CACHED.value:
        return "Cached"
    if ent == EntitlementStatus.REALTIME.value:
        return "Fresh"
    if ent == EntitlementStatus.END_OF_DAY.value:
        return "End-of-day"
    return "Delayed"
