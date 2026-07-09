# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.services.analytics import _carry_forward


def test_carry_forward_naive_keys_aware_axis_does_not_raise():
    # Regression (#15): Candle.ts loads NAIVE from SQLite; the performance axis is
    # tz-AWARE (built from datetime.now(UTC)). Before the fix, keys[j] <= d raised
    # "can't compare offset-naive and offset-aware datetimes".
    k = datetime(2026, 1, 1, 0, 0, 0)  # naive, like Candle.ts
    series = {k: Decimal("100"), k + timedelta(days=5): Decimal("110")}
    axis = [datetime(2026, 1, day, tzinfo=UTC) for day in (1, 3, 6, 8)]  # aware
    out = _carry_forward(axis, series)  # must not raise
    assert out == [Decimal("100"), Decimal("100"), Decimal("110"), Decimal("110")]


def test_carry_forward_homogeneous_naive_still_works():
    series = {datetime(2026, 1, 1): Decimal("5")}
    assert _carry_forward([datetime(2026, 1, 2)], series) == [Decimal("5")]


def test_carry_forward_homogeneous_aware_still_works():
    series = {datetime(2026, 1, 1, tzinfo=UTC): Decimal("7")}
    assert _carry_forward([datetime(2026, 1, 2, tzinfo=UTC)], series) == [Decimal("7")]
