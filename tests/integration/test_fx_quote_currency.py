# SPDX-License-Identifier: AGPL-3.0-or-later
"""W-1 (R-42 Phase 3b): a live-quoted holding's market value must convert FROM the
QUOTE's currency — the authoritative currency of the fetched price — not the
holding's stored currency, which drifts (an AMFI scheme code has no exchange
suffix, so the FIFO builder defaults holding.currency to the account/txn currency).

Reproduces the owner-walk data exactly: an India mutual fund priced in INR
(quote.currency='INR') held in an SGD account (holding.currency='SGD'). Before the
fix native_ccy resolved to 'SGD' and fx.convert same-currency short-circuited to
rate 1.0, so the INR NAV magnitude rendered as a raw SGD figure (100 × 14.8131 =
"SGD 1,481.31"). After the fix it converts INR→SGD.
"""

from __future__ import annotations

from decimal import Decimal

import app.services.portfolio as pf
from app.models import Account, AssetClass, Holding, Instrument
from app.models import Quote as QuoteRow
from app.services import ecb_fx, fx


class _NoFxProvider:
    """A provider that can serve no FX at all (every pair unavailable)."""
    name = "stub"
    fetch_on_demand = False

    async def get_fx_rate(self, base, quote):
        return None


async def _fixed_rates(monkeypatch):
    # Patch the ONE lookup both convert_checked (market value) and the get_rate wrapper
    # (cost/day) resolve through, so figures are deterministic (the mock FX has a ±1% wobble).
    async def fake_get_rate_or_none(base: str, quote: str):
        base, quote = base.upper(), quote.upper()
        if base == quote:
            return Decimal("1")
        table = {("INR", "SGD"): Decimal("0.016"), ("USD", "SGD"): Decimal("1.35")}
        return table.get((base, quote))

    fx.clear_cache()
    monkeypatch.setattr(fx, "get_rate_or_none", fake_get_rate_or_none)


async def test_inr_fund_in_sgd_account_converts_from_quote_currency(session, monkeypatch):
    await _fixed_rates(monkeypatch)
    acc = Account(name="Broker", currency="SGD")
    session.add(acc)
    await session.flush()
    # AMFI fund: pricing_currency INR, but the legacy currency field left USD (W-2
    # divergence) and the holding defaulted to the account currency (SGD).
    fund = Instrument(
        symbol="145834", name="Motilal Oswal Liquid Fund - Direct Growth",
        asset_class=AssetClass.MUTUAL_FUND, currency="USD", pricing_currency="INR",
        valuation_method="official_nav", listing_country="IN",
    )
    session.add(fund)
    await session.flush()
    session.add(QuoteRow(
        instrument_id=fund.id, price=Decimal("14.8131"), currency="INR",
        source="amfi_nav", entitlement="end-of-day",
    ))
    session.add(Holding(
        account_id=acc.id, instrument_id=fund.id, asset_class=AssetClass.MUTUAL_FUND,
        quantity=Decimal("100"), avg_cost=Decimal("6"), currency="SGD",
    ))
    await session.commit()

    val = await pf.value_portfolio(session, "SGD", warm=False)
    hv = next(h for h in val.holdings if h.symbol == "145834")

    # 100 × 14.8131 INR × 0.016 (INR→SGD) = 23.70096 → ~SGD 23.70, NOT the raw INR magnitude.
    assert hv.market_value_base != Decimal("1481.31"), "raw INR magnitude leaked into base"
    assert abs(hv.market_value_base - Decimal("23.70")) < Decimal("0.02")


async def test_usd_holding_conversion_unchanged(session, monkeypatch):
    await _fixed_rates(monkeypatch)
    acc = Account(name="Broker", currency="SGD")
    session.add(acc)
    await session.flush()
    tsla = Instrument(symbol="TSLA", name="Tesla", asset_class=AssetClass.EQUITY,
                      currency="USD", pricing_currency="USD")
    session.add(tsla)
    await session.flush()
    session.add(QuoteRow(instrument_id=tsla.id, price=Decimal("380.84"),
                         currency="USD", source="mock", entitlement="delayed"))
    session.add(Holding(account_id=acc.id, instrument_id=tsla.id,
                        asset_class=AssetClass.EQUITY, quantity=Decimal("10"),
                        avg_cost=Decimal("300"), currency="USD"))
    await session.commit()

    val = await pf.value_portfolio(session, "SGD", warm=False)
    hv = next(h for h in val.holdings if h.symbol == "TSLA")
    # 10 × 380.84 USD × 1.35 (USD→SGD) = 5141.34 — the correct-today path, unchanged.
    assert abs(hv.market_value_base - Decimal("5141.34")) < Decimal("0.02")


async def test_mixed_currency_book_net_worth(session, monkeypatch):
    await _fixed_rates(monkeypatch)
    acc = Account(name="Broker", currency="SGD")
    session.add(acc)
    await session.flush()
    fund = Instrument(symbol="145834", name="Motilal Liquid",
                      asset_class=AssetClass.MUTUAL_FUND, currency="USD",
                      pricing_currency="INR", valuation_method="official_nav",
                      listing_country="IN")
    tsla = Instrument(symbol="TSLA", name="Tesla", asset_class=AssetClass.EQUITY,
                      currency="USD", pricing_currency="USD")
    session.add_all([fund, tsla])
    await session.flush()
    session.add_all([
        QuoteRow(instrument_id=fund.id, price=Decimal("14.8131"), currency="INR",
                 source="amfi_nav", entitlement="end-of-day"),
        QuoteRow(instrument_id=tsla.id, price=Decimal("380.84"), currency="USD",
                 source="mock", entitlement="delayed"),
        Holding(account_id=acc.id, instrument_id=fund.id,
                asset_class=AssetClass.MUTUAL_FUND, quantity=Decimal("100"),
                avg_cost=Decimal("6"), currency="SGD"),
        Holding(account_id=acc.id, instrument_id=tsla.id,
                asset_class=AssetClass.EQUITY, quantity=Decimal("10"),
                avg_cost=Decimal("300"), currency="USD"),
    ])
    await session.commit()

    val = await pf.value_portfolio(session, "SGD", warm=False)
    # Net worth = 23.70 (fund, converted) + 5141.34 (TSLA) — the fund contributes its
    # converted value, not 1481.31 of unconverted INR magnitude.
    assert abs(val.total_value - Decimal("5165.04")) < Decimal("0.05")
    assert val.total_value < Decimal("6000"), "unconverted INR magnitude inflating net worth"


async def _no_fx_anywhere(monkeypatch):
    """No provider FX and no ECB reference — every non-identity pair is unavailable."""
    fx.clear_cache()
    monkeypatch.setattr(fx, "get_provider", lambda: _NoFxProvider())
    monkeypatch.setattr(ecb_fx, "reference_rate", lambda base, quote: (None, "unavailable"))


async def test_missing_rate_is_flagged_never_fabricated_one(app_client, session, monkeypatch):
    """W-1b: when a rate is genuinely unavailable, the holding surfaces an HONEST
    flagged state (served reason + confidence penalty) — never a silent 1.0 that leaks
    the raw native magnitude into net worth."""
    await _no_fx_anywhere(monkeypatch)
    acc = Account(name="Broker", currency="SGD")
    session.add(acc)
    await session.flush()
    fund = Instrument(symbol="145834", name="Motilal Liquid",
                      asset_class=AssetClass.MUTUAL_FUND, currency="USD",
                      pricing_currency="INR", valuation_method="official_nav",
                      listing_country="IN")
    session.add(fund)
    await session.flush()
    session.add(QuoteRow(instrument_id=fund.id, price=Decimal("14.8131"), currency="INR",
                         source="amfi_nav", entitlement="end-of-day"))
    session.add(Holding(account_id=acc.id, instrument_id=fund.id,
                        asset_class=AssetClass.MUTUAL_FUND, quantity=Decimal("100"),
                        avg_cost=Decimal("6"), currency="SGD"))
    await session.commit()

    val = await pf.value_portfolio(session, "SGD", warm=False)
    hv = next(h for h in val.holdings if h.symbol == "145834")
    # Never the fabricated 1.0 conversion (raw INR magnitude) in a base-currency value.
    assert hv.market_value_base != Decimal("1481.31")
    assert hv.market_value_base == Decimal("0")
    assert getattr(hv, "fx_unavailable", False) is True
    # Net worth does not include the unconverted magnitude.
    assert val.total_value == Decimal("0")

    # The reason is SERVED (D-105) on the pricing-health row, distinct from "no quote".
    ph = (await app_client.get("/api/v1/portfolio/pricing-health")).json()
    row = next(r for r in ph["holdings"] if r["symbol"] == "145834")
    assert row["failure_reason"] and "convert" in row["failure_reason"].lower()
    assert any("fx" in f.lower() or "convert" in f.lower() for f in row["confidence_factors"])
