# SPDX-License-Identifier: AGPL-3.0-or-later
"""R-43 §17 (F-6) — CoinGecko id auto-resolution at acquisition time.

The owner's BTC/XRP carry a dr-27-era ``source_override='alphavantage'`` and NO ``coingecko_id``,
so the Build-history acquisition skipped them (coverage 4/6). Two rulings are exercised here:

- §17-R2: ``_link_coingecko_by_symbol`` resolves an AMBIGUOUS symbol to the canonical
  top-market-cap primary (BTC → bitcoin, XRP → ripple) — the stored ``market_cap_usd`` is
  unreliable (the ``/coins/list`` sync has no cap), so it fetches live caps for the candidate ids
  and links the dominant one; a genuinely ambiguous minor symbol (comparable caps) serves candidates.
- §17-R1: ``acquire_prices`` routes crypto by CLASS to CoinGecko regardless of an AV quotes-override
  — a crypto with an AV override still acquires CoinGecko history (see test_acquire_prices).
"""

from __future__ import annotations

from decimal import Decimal

import app.models  # noqa: F401 — register every table before the session fixture's create_all


async def _crypto(session, symbol: str, override: str | None = None):
    from app.models import AssetClass, Instrument

    instr = Instrument(symbol=symbol, currency="USD", pricing_currency="USD",
                       asset_class=AssetClass.CRYPTO, source_override=override)
    session.add(instr)
    await session.flush()
    return instr


async def _coin(session, cid: str, symbol: str, name: str, cap=None):
    from app.models import CoingeckoCoin

    session.add(CoingeckoCoin(id=cid, symbol=symbol, name=name,
                              market_cap_usd=Decimal(cap) if cap is not None else None))


async def _has_id(session, instrument_id: int) -> str | None:
    from sqlalchemy import select

    from app.models import InstrumentIdentifier

    return (await session.execute(
        select(InstrumentIdentifier.value).where(
            InstrumentIdentifier.instrument_id == instrument_id,
            InstrumentIdentifier.id_type == "coingecko_id"))).scalars().first()


async def test_ambiguous_btc_resolves_to_dominant_market_cap(session, monkeypatch):
    """§17-R2: 'btc' matches bitcoin + scam tokens; only bitcoin has a dominant cap → linked.
    The dominant cap here is the STORED one (bitcoin was enriched once) — resolves even offline."""
    from app.services.market import _link_coingecko_by_symbol

    await _coin(session, "bitcoin", "btc", "Bitcoin", cap="1275382680099")
    await _coin(session, "batcat", "btc", "batcat")
    await _coin(session, "big-tom-coin", "btc", "Big Tom Coin")
    btc = await _crypto(session, "BTC", override="alphavantage")
    await session.flush()

    err = await _link_coingecko_by_symbol(session, btc)
    assert err is None, f"expected a clean link, got served error: {err}"
    assert await _has_id(session, btc.id) == "bitcoin"


async def test_ambiguous_xrp_resolves_via_live_market_cap(session, monkeypatch):
    """§17-R2: 'xrp' matches ripple + scam tokens, NONE with a stored cap (the owner's real state).
    The linker fetches live caps for the candidate ids and links the dominant one (ripple)."""
    from app.providers.market import coingecko as cg
    from app.services.market import _link_coingecko_by_symbol

    await _coin(session, "ripple", "xrp", "XRP")                 # stored cap = None (real state)
    await _coin(session, "binance-peg-xrp", "xrp", "Binance-Peg XRP")
    await _coin(session, "harrypotterobamapacman8inu", "xrp", "HPOP8Inu")
    xrp = await _crypto(session, "XRP", override="alphavantage")
    await session.flush()

    async def _fake_prices(ids, timeout=20.0):
        assert set(ids) >= {"ripple", "binance-peg-xrp"}
        return {"ripple": {"usd": 1.09, "usd_market_cap": 64_000_000_000},
                "binance-peg-xrp": {"usd": 1.09, "usd_market_cap": 0},
                "harrypotterobamapacman8inu": {"usd": 0.0001}}
    monkeypatch.setattr(cg, "fetch_prices", _fake_prices)

    err = await _link_coingecko_by_symbol(session, xrp)
    assert err is None, f"expected a clean link, got served error: {err}"
    assert await _has_id(session, xrp.id) == "ripple"


async def test_genuinely_ambiguous_minor_symbol_serves_candidates(session, monkeypatch):
    """§17-R2: two comparable-cap tokens sharing a symbol → NO dominant primary → served
    candidates (never a silent guess). Preserves the dr-27 ambiguous-symbol behaviour."""
    from app.providers.market import coingecko as cg
    from app.services.market import _link_coingecko_by_symbol

    await _coin(session, "dupcoin-a", "dup", "Dup A")
    await _coin(session, "dupcoin-b", "dup", "Dup B")
    dup = await _crypto(session, "DUP")
    await session.flush()

    async def _fake_prices(ids, timeout=20.0):
        return {"dupcoin-a": {"usd_market_cap": 5_000_000},
                "dupcoin-b": {"usd_market_cap": 4_000_000}}   # comparable → not dominant
    monkeypatch.setattr(cg, "fetch_prices", _fake_prices)

    err = await _link_coingecko_by_symbol(session, dup)
    assert err is not None and "multiple" in err.lower()
    assert "dupcoin-a" in err and "dupcoin-b" in err
    assert await _has_id(session, dup.id) is None
