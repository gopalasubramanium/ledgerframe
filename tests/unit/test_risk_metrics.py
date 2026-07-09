# SPDX-License-Identifier: AGPL-3.0-or-later
"""§4.5 Unit B — additional risk metrics (pure core, deterministic, read-only).

Each metric needs NO risk-free rate; Sharpe/Sortino are deliberately absent. These vectors drive
`_risk_from_series` directly with fixed value series, proving known values: beta of a series vs
itself = 1, correlation of identical series = 1, downside deviation ignores positive returns, HHI
of two equal holdings = 0.5, information ratio = 0 when portfolio tracks the benchmark exactly.
Benchmark-unavailable → benchmark-relative metrics None while HHI/downside still compute.
"""

from __future__ import annotations

import statistics

from app.services.analytics import _risk_from_series

# A portfolio value series with an obvious mix of up and down days, and a differently-shaped
# benchmark, so beta/correlation are not trivially 1 unless the series are identical.
PORT = [100.0, 102.0, 101.0, 104.0, 100.0, 105.0]
BENCH = [50.0, 50.5, 50.2, 51.0, 49.5, 51.5]


def _r(port, bench, mv, benchmark_symbol="SPY"):
    return _risk_from_series(port, bench, mv, base_currency="USD", days=365,
                             benchmark_symbol=benchmark_symbol)


# (1) Beta & correlation of a series vs ITSELF = 1 (perfect sensitivity/association).
def test_beta_and_correlation_vs_self_are_one():
    rep = _r(PORT, PORT, [1.0])
    assert rep["beta"] == 1.0
    assert rep["correlation"] == 1.0


# (2) Information ratio is 0 when the portfolio tracks the benchmark exactly (no active return,
#     perfect tracking) — and tracking error is 0. Reconciles the "perfect tracking" edge cleanly.
def test_information_ratio_zero_when_port_equals_benchmark():
    rep = _r(PORT, PORT, [1.0])
    assert rep["information_ratio"] == 0.0
    assert rep["tracking_error"] == 0.0


# (3) Downside deviation uses ONLY negative returns — positive days do not affect it.
def test_downside_deviation_ignores_positive_returns():
    # Returns: +2%, −1%(→100.98/102.0? use clean values), craft exact returns.
    base = [100.0, 102.0, 100.98, 104.0088, 100.888536]   # +2%, −1%, +3%, −3%
    rets = [base[i] / base[i - 1] - 1 for i in range(1, len(base))]
    neg = [r for r in rets if r < 0]
    expected = round(statistics.pstdev(neg) * (252 ** 0.5) * 100, 2)
    rep = _r(base, [], [1.0])                       # no benchmark needed for downside
    assert rep["downside_deviation"] == expected
    # Raise every POSITIVE day; negatives unchanged → downside deviation unchanged.
    bumped = [100.0, 110.0, 108.9, 130.68, 126.7596]   # bigger +ve moves, same −1%/−3% steps
    rep2 = _r(bumped, [], [1.0])
    assert rep2["downside_deviation"] == rep["downside_deviation"]


# (4) HHI = Σ weight² — two equal holdings → 0.5; one holding → 1.0; concentration rises with skew.
def test_hhi_concentration():
    assert _r(PORT, BENCH, [1000.0, 1000.0])["hhi"] == 0.5     # two equal
    assert _r(PORT, BENCH, [1000.0])["hhi"] == 1.0             # single position
    assert _r(PORT, BENCH, [900.0, 100.0])["hhi"] == 0.82      # 0.81 + 0.01, skewed → higher


# (5) A non-identical benchmark yields finite, sensible beta/correlation (sanity, not a magic
#     number): correlation in [-1, 1], and beta is a real number.
def test_beta_correlation_finite_for_distinct_series():
    rep = _r(PORT, BENCH, [1000.0, 1000.0])
    assert rep["beta"] is not None
    assert -1.0 <= rep["correlation"] <= 1.0
    assert rep["information_ratio"] is not None      # distinct series → defined IR


# (6) Benchmark unavailable → benchmark-relative metrics None; HHI & downside still present.
def test_benchmark_unavailable_keeps_non_benchmark_metrics():
    rep = _r(PORT, [], [1000.0, 1000.0], benchmark_symbol=None)
    assert rep["available"] is True
    assert rep["beta"] is None and rep["correlation"] is None
    assert rep["information_ratio"] is None and rep["tracking_error"] is None
    assert rep["hhi"] == 0.5                          # concentration needs no benchmark
    assert rep["downside_deviation"] is not None      # downside needs no benchmark


# (7) Fully thin (no series, no holdings) → every metric None, available False, no crash.
def test_thin_data_all_none():
    rep = _r([], [], [])
    assert rep["available"] is False
    assert all(rep[k] is None for k in
               ("beta", "correlation", "downside_deviation", "information_ratio", "tracking_error", "hhi"))
