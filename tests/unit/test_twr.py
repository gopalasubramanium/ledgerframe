# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 5d: time-weighted return (pure chain-linking math)."""

from __future__ import annotations

from app.core.twr import twr_from_flows


def test_simple_growth_no_flows():
    # 100 -> 110 over two days with no flows -> +10%.
    assert twr_from_flows([100.0, 105.0, 110.0], [0.0, 0.0, 0.0]) is not None
    r = twr_from_flows([100.0, 110.0, 121.0], [0.0, 0.0, 0.0])
    assert r is not None and abs(r - 21.0) < 0.1   # 1.1 * 1.1 - 1


def test_flow_is_removed_from_the_return():
    # Day 1: value 210 but 100 of that is a fresh deposit -> the investment return is
    # (210 - 100 - 100)/100 = +10%, NOT +110%. Next day flat.
    r = twr_from_flows([100.0, 210.0, 210.0], [0.0, 100.0, 0.0])
    assert r is not None and abs(r - 10.0) < 0.1


def test_insufficient_or_bad_series_is_none():
    assert twr_from_flows([100.0], [0.0]) is None          # one point
    assert twr_from_flows([], []) is None
    assert twr_from_flows([0.0, 0.0, 0.0], [0.0, 0.0, 0.0]) is None  # never a positive base
    assert twr_from_flows([100.0, 110.0], [0.0]) is None    # misaligned
