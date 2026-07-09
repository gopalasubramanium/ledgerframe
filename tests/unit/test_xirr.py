# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 5a: XIRR (money-weighted return)."""

from __future__ import annotations

from datetime import date

from app.core.xirr import xirr


def test_simple_one_year_10pct():
    r = xirr([(date(2023, 1, 1), -1000.0), (date(2024, 1, 1), 1100.0)])
    assert r is not None and abs(r - 10.0) < 0.2


def test_doubling_in_a_year_is_100pct():
    r = xirr([(date(2023, 1, 1), -1000.0), (date(2024, 1, 1), 2000.0)])
    assert r is not None and abs(r - 100.0) < 0.5


def test_multiple_contributions():
    # -1000 at t0, -1000 at +6mo, worth 2200 at +1yr → a positive, sensible IRR.
    r = xirr([
        (date(2023, 1, 1), -1000.0),
        (date(2023, 7, 1), -1000.0),
        (date(2024, 1, 1), 2200.0),
    ])
    assert r is not None and 5.0 < r < 40.0


def test_insufficient_or_no_sign_change_is_none():
    assert xirr([(date(2023, 1, 1), -1000.0)]) is None            # one flow
    assert xirr([]) is None
    assert xirr([(date(2023, 1, 1), -1000.0), (date(2024, 1, 1), -500.0)]) is None  # all outflow
