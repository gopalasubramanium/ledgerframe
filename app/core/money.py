# SPDX-License-Identifier: AGPL-3.0-or-later
"""Decimal-based money helpers.

Rule enforced project-wide: monetary amounts are :class:`decimal.Decimal`, never
``float``. Floats are only acceptable at the very edge (chart pixels, JSON for the
browser) and are produced explicitly via :func:`to_display`.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Context, Decimal, InvalidOperation

ZERO = Decimal("0")
CENTS = Decimal("0.01")
PRICE_Q = Decimal("0.000001")  # quote precision (6dp) covers FX & crypto

# D-105: quote-price DISPLAY precision by asset class, formatted in the backend so the frontend
# renders the string verbatim (money = served display strings; no client formatting). Stored native
# precision is unchanged — this is display only. Equities / ETFs / funds / indices → 2dp; crypto →
# up to 6 significant digits (so sub-cent tokens aren't truncated to "0.00").
_SIG6 = Context(prec=6, rounding=ROUND_HALF_UP)
_CRYPTO_CLASSES = frozenset({"crypto"})


def format_price_display(value: Decimal | None, asset_class: object = None) -> str | None:
    """A served display string for a QUOTE price at class-appropriate precision (D-105). None passes
    through (never a fabricated 0). Grouped thousands; crypto keeps 6 significant digits (trailing
    zeros trimmed), everything else is 2dp."""
    if value is None:
        return None
    p = D(value)
    ac = (asset_class.value if hasattr(asset_class, "value") else str(asset_class or "")).lower()
    if ac in _CRYPTO_CLASSES:
        return format(_SIG6.create_decimal(p), ",f")  # 6 significant digits, fixed notation
    return format(p.quantize(CENTS, rounding=ROUND_HALF_UP), ",.2f")


def format_money_display(value: Decimal | None) -> str | None:
    """A served display string for a MONEY amount: grouped thousands, 2dp (page-heatmap §12hm1-1,
    D-105 posture — the frontend renders it verbatim and formats nothing). None passes through, so
    an unpriced field stays honestly empty and is never a fabricated 0 (Guarantee 3)."""
    if value is None:
        return None
    return format(D(value).quantize(CENTS, rounding=ROUND_HALF_UP), ",.2f")


def format_signed_pct_display(value: Decimal | None) -> str | None:
    """A served display string for a SIGNED percentage change: explicit +/− (U+2212 minus, matching
    the app's signed-figure convention), 2dp, trailing '%'. None passes through (never a fabricated
    0% — a missing Today's change is shown as an em dash with a reason)."""
    if value is None:
        return None
    p = D(value).quantize(CENTS, rounding=ROUND_HALF_UP)
    sign = "+" if p > ZERO else "−" if p < ZERO else ""
    return f"{sign}{format(abs(p), ',.2f')}%"


def D(value: object) -> Decimal:
    """Coerce anything reasonable to a Decimal. Raises ValueError on garbage."""
    if isinstance(value, Decimal):
        return value
    if value is None or value == "":
        return ZERO
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"cannot interpret {value!r} as a decimal") from exc


def money(value: object) -> Decimal:
    """Quantize to 2 decimal places for stored monetary amounts."""
    return D(value).quantize(CENTS, rounding=ROUND_HALF_UP)


def price(value: object) -> Decimal:
    """Quantize to 6 decimal places for quotes / FX rates."""
    return D(value).quantize(PRICE_Q, rounding=ROUND_HALF_UP)


def to_display(value: Decimal | None) -> float | None:
    """Convert a Decimal to float at the JSON boundary only. None passes through."""
    return None if value is None else float(value)


def pct_change(current: Decimal, previous: Decimal) -> Decimal | None:
    """Percentage change, or None when the base is zero (avoid division by zero)."""
    if previous == ZERO:
        return None
    return ((current - previous) / previous * Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
