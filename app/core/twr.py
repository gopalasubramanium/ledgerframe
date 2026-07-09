# SPDX-License-Identifier: AGPL-3.0-or-later
"""Time-weighted return (TWR).

TWR removes the distorting effect of the *timing and size* of your own
contributions/withdrawals — it measures how the investments themselves performed.
It's computed by chain-linking each period's return with that period's external
cash flow removed, so a big deposit right before a rally doesn't flatter the number
(that's what XIRR captures instead).

This is the pure math over an aligned ``(values, flows)`` daily series. Returns
``None`` when there isn't enough valid history to be meaningful, so the caller can
show "not applicable" rather than a fabricated figure.
"""

from __future__ import annotations


def twr_from_flows(values: list[float], flows: list[float]) -> float | None:
    """Cumulative TWR (percent) over the series, or ``None`` if not derivable.

    ``values[t]`` is the portfolio market value at the end of day ``t``; ``flows[t]``
    is the net external capital added on day ``t`` (buys positive, sells negative),
    assumed to occur within that day. Each day's investment return is
    ``(V[t] - flow[t] - V[t-1]) / V[t-1]`` and the daily returns are chain-linked.
    """
    if len(values) < 2 or len(values) != len(flows):
        return None
    prod = 1.0
    n = 0
    for t in range(1, len(values)):
        v0 = values[t - 1]
        if v0 <= 0:
            continue
        r = (values[t] - flows[t] - v0) / v0
        if r <= -1.0:      # a full wipeout / bad data point — don't chain a negative base
            continue
        prod *= 1.0 + r
        n += 1
    if n < 2:
        return None
    return round((prod - 1.0) * 100.0, 2)
