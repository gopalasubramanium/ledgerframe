# SPDX-License-Identifier: AGPL-3.0-or-later
"""§4.5 Unit B — risk_metrics async wiring (read-only).

Proves the async reader sources its series from performance_series and its holdings from
value_portfolio, and degrades honestly: with holdings present but NO benchmark history available,
the benchmark-relative metrics come back None while HHI still computes from current holdings.
Pure metric math is covered in tests/unit/test_risk_metrics.py.
"""

from __future__ import annotations

from decimal import Decimal

from app.models import Account, AssetClass, Holding
from app.services.analytics import risk_metrics


async def test_risk_metrics_benchmark_unavailable_still_gives_hhi(session):
    acc = Account(name="Broker", currency="USD")
    session.add(acc)
    await session.flush()
    # A single manual holding: deterministic value, no market/benchmark history in the test DB.
    session.add(Holding(account_id=acc.id, label="Cash", asset_class=AssetClass.CASH,
                        quantity=Decimal("1"), avg_cost=Decimal("1000"),
                        manual_value=Decimal("1000"), currency="USD"))
    await session.flush()

    rep = await risk_metrics(session, "USD", 365)
    assert rep["available"] is True
    assert rep["benchmark_symbol"] == "SPY"                 # the same benchmark the siblings use
    # No benchmark series → benchmark-relative metrics are honestly None (not fabricated).
    assert rep["beta"] is None and rep["correlation"] is None
    assert rep["information_ratio"] is None and rep["tracking_error"] is None
    # HHI needs no series/benchmark: a single position is fully concentrated (Σ weight² = 1).
    assert rep["hhi"] == 1.0
