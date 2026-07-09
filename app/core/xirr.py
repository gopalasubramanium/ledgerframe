# SPDX-License-Identifier: AGPL-3.0-or-later
"""XIRR — the money-weighted (internal) rate of return of dated cash flows.

Deterministic; robust bisection so it never diverges. Returns ``None`` when the
cash-flow history is insufficient (fewer than two flows, or no sign change) so the
caller can honestly show "not applicable" rather than a misleading number.
"""

from __future__ import annotations

from datetime import date


def _npv(rate: float, days: list[int], amounts: list[float]) -> float:
    base = 1.0 + rate
    return sum(cf / base ** (t / 365.0) for cf, t in zip(amounts, days, strict=False))


def xirr(flows: list[tuple[date, float]]) -> float | None:
    """XIRR as an annual percentage, or ``None`` if it can't be computed honestly.

    Convention: money *invested* is negative, money/value *returned* is positive
    (so the final portfolio value is a positive flow dated today).
    """
    if len(flows) < 2:
        return None
    flows = sorted(flows, key=lambda f: f[0])
    amounts = [float(cf) for _, cf in flows]
    if not (any(a > 0 for a in amounts) and any(a < 0 for a in amounts)):
        return None  # need at least one inflow and one outflow
    d0 = flows[0][0]
    days = [(d - d0).days for d, _ in flows]

    lo, hi = -0.999999, 10.0
    f_lo, f_hi = _npv(lo, days, amounts), _npv(hi, days, amounts)
    if f_lo * f_hi > 0:               # widen once for very high returns
        hi = 1000.0
        f_hi = _npv(hi, days, amounts)
        if f_lo * f_hi > 0:
            return None               # no sign change → no reliable root
    for _ in range(200):
        mid = (lo + hi) / 2.0
        f_mid = _npv(mid, days, amounts)
        if abs(f_mid) < 1e-7 or (hi - lo) < 1e-10:
            return round(mid * 100.0, 2)
        if f_lo * f_mid < 0:
            hi, f_hi = mid, f_mid
        else:
            lo, f_lo = mid, f_mid
    return round((lo + hi) / 2.0 * 100.0, 2)
