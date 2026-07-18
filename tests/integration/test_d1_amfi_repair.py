# SPDX-License-Identifier: AGPL-3.0-or-later
"""POST-CLOSE DELTA D1-b — one-time idempotent repair for the 145834 residue.

Instruments recognised by the PRE-D1 Add-flow linker carry an ``amfi_code`` identifier
but unconverted fields (pricing_currency != INR, valuation_method != official_nav) and
no ``amfi_nav`` quote while the master has a NAV. The repair (the dr-25 cleanup pattern)
runs the D1-a helper over them: convergent, logged with counts, strictly additive
(never deletes user data) — this ships as normal product-upgrade code on the live
instance, so idempotency is load-bearing.
"""

from __future__ import annotations

from sqlalchemy import select


async def _seed_legacy_unconverted(code: str, nav) -> int:
    """Reproduce the 145834 residue: a mapped-but-unconverted MF (amfi_code attached, but
    pricing_currency USD / valuation_method market_quote, no amfi_nav quote) whose scheme
    is in the master WITH a NAV. Returns the instrument id."""
    from app.db.base import get_sessionmaker
    from app.models import AmfiScheme, AssetClass, Instrument
    from app.services.identity import set_identifier

    async with get_sessionmaker()() as s:
        s.add(AmfiScheme(code=code, name="Legacy Residue Fund", nav=nav, nav_date="2026-07-17"))
        instr = Instrument(
            symbol=code, name="Legacy Residue Fund", currency="USD",
            asset_class=AssetClass.MUTUAL_FUND, asset_subclass="mutual_fund",
            asset_category="mutual_fund", liquidity_profile="listed",
            valuation_method="market_quote", pricing_currency="USD",
        )
        s.add(instr)
        await s.flush()
        await set_identifier(s, instr.id, "amfi_code", code, provider="amfi_nav", is_primary=True)
        await s.commit()
        return instr.id


async def _read(code: str):
    from app.db.base import get_sessionmaker
    from app.models import Instrument
    from app.models import Quote as QuoteRow

    async with get_sessionmaker()() as s:
        instr = (await s.execute(
            select(Instrument).where(Instrument.symbol == code)
        )).scalars().first()
        quote = (await s.execute(
            select(QuoteRow).where(QuoteRow.instrument_id == instr.id)
        )).scalars().first()
        return instr, quote


async def test_repair_heals_unconverted_then_is_idempotent(app_client):
    # app_client boots the app (migrations + fixtures); seed the legacy residue after.
    await _seed_legacy_unconverted("145834", nav=100.5)

    from app.db.base import get_sessionmaker
    from app.services.market import recognise_unconverted_amfi_funds

    # First run heals exactly this one instrument.
    async with get_sessionmaker()() as s:
        result = await recognise_unconverted_amfi_funds(s)
        await s.commit()
    assert result["repaired"] == 1

    instr, quote = await _read("145834")
    assert instr.pricing_currency == "INR"
    assert instr.valuation_method == "official_nav"
    assert instr.asset_category == "fund"
    assert instr.liquidity_profile == "redeemable"
    assert quote is not None and quote.source == "amfi_nav"

    # Second run: nothing left to convert -> zero changes (idempotent).
    async with get_sessionmaker()() as s:
        again = await recognise_unconverted_amfi_funds(s)
        await s.commit()
    assert again["repaired"] == 0
