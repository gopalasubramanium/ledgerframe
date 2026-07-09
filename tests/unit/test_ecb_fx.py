# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 4: ECB reference FX — parser, direct/inverse/triangulated derivation, and
the provider→ECB fallback. Deterministic, fixture-driven."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from app.providers.market.ecb import parse_ecb_daily
from app.services import ecb_fx

FIXTURE = (Path(__file__).parents[1] / "fixtures" / "ecb_eurofxref_daily.xml").read_text()


def _load():
    as_of, rates = parse_ecb_daily(FIXTURE)
    ecb_fx._set_cache(rates, as_of)
    return as_of, rates


def test_parse_ecb_daily():
    as_of, rates = parse_ecb_daily(FIXTURE)
    assert as_of == "2026-07-03"
    assert rates["EUR"] == Decimal("1")
    assert rates["USD"] == Decimal("1.0850")
    assert rates["SGD"] == Decimal("1.4600")
    assert rates["INR"] == Decimal("90.5000")


def test_reference_rate_direct_inverse_triangulated():
    _load()
    # EUR is the base of the file → EUR->X is direct.
    r, m = ecb_fx.reference_rate("EUR", "USD")
    assert m == "direct" and r == Decimal("1.0850")
    # X->EUR is inverse.
    r, m = ecb_fx.reference_rate("USD", "EUR")
    assert m == "inverse" and abs(r - (Decimal("1") / Decimal("1.0850"))) < Decimal("1e-9")
    # X->Y is triangulated via EUR.
    r, m = ecb_fx.reference_rate("USD", "SGD")
    assert m == "triangulated" and abs(r - (Decimal("1.46") / Decimal("1.085"))) < Decimal("1e-9")
    # Identity + unavailable.
    assert ecb_fx.reference_rate("USD", "USD") == (Decimal("1"), "identity")
    assert ecb_fx.reference_rate("USD", "ZZZ") == (None, "unavailable")


async def test_fx_falls_back_to_ecb_when_provider_fails(monkeypatch):
    from app.services import fx

    _load()
    fx.clear_cache()

    class _Down:
        async def get_fx_rate(self, base, quote):
            raise RuntimeError("provider unavailable")

    monkeypatch.setattr(fx, "get_provider", lambda: _Down())
    rate = await fx.get_rate("USD", "SGD")
    # Falls back to the ECB triangulated rate (1.46 / 1.085), not a crash or 1.0.
    assert abs(rate - (Decimal("1.46") / Decimal("1.085"))) < Decimal("1e-6")
    fx.clear_cache()
