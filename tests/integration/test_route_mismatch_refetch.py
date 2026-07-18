# SPDX-License-Identifier: AGPL-3.0-or-later
"""§18-R3 (F-7a) — a route/override change invalidates the cached quote.

Owner evidence (2026-07-19): BTC/XRP were corrected to CoinGecko (Route coingecko,
Rule override, `coingecko_id` linked), yet every refresh still served the *previous*
Alpha Vantage quote — Source stayed `alphavantage`, "Delayed 04:59", stale.

Cause: :func:`app.services.market.refresh_quote` skipped whenever the routed source
was not the *active* provider and returned the cache verbatim — nothing ever compared
the cached quote's `source` to the source the route now names, and the only CoinGecko
publish path was the manual Settings "Sync now". So a corrected route could never
reach the quote store.

Ruling: a cached quote whose source is not the currently-routed source is
ROUTE-MISMATCHED — the next refresh refetches it from the new route regardless of
freshness. Pinned here: correct the override -> refresh -> Source equals Route.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest


async def _seed_crypto_on_stale_av_quote(symbol: str, coin_id: str):
    """An instrument in exactly the owner's state: routed to CoinGecko by an override,
    mapped to a canonical id, but holding a *previous-provider* cached quote."""
    from app.db.base import get_sessionmaker
    from app.models import CoingeckoCoin, Instrument
    from app.models import Quote as QuoteRow
    from app.services.identity import set_identifier

    async with get_sessionmaker()() as s:
        if await s.get(CoingeckoCoin, coin_id) is None:   # the demo master may already carry it
            s.add(CoingeckoCoin(id=coin_id, symbol=symbol.lower(), name=coin_id.title()))
        instr = Instrument(symbol=symbol.upper(), asset_class="crypto", currency="USD",
                           source_override="coingecko")
        s.add(instr)
        await s.flush()
        await set_identifier(s, instr.id, "coingecko_id", coin_id,
                             provider="coingecko", is_primary=True)
        # The stale quote from the source that owned this instrument BEFORE the correction.
        s.add(QuoteRow(instrument_id=instr.id, price=Decimal("64665.62"), currency="USD",
                       source="alphavantage", entitlement="delayed",
                       market_time=datetime(2026, 7, 18, 20, 59, tzinfo=UTC),
                       received_at=datetime(2026, 7, 18, 20, 59, tzinfo=UTC)))
        await s.commit()
        return instr.id


@pytest.fixture
def _coingecko_live(monkeypatch):
    """A reachable CoinGecko /simple/price, so the test exercises the refetch decision
    rather than the network."""
    calls: list[list[str]] = []

    async def _fake_fetch_prices(ids, timeout: float = 20.0):
        calls.append(list(ids))
        return {i: {"usd": 118250.5, "usd_market_cap": 2.3e12,
                    "last_updated_at": 1784500000} for i in ids}

    monkeypatch.setattr("app.providers.market.coingecko.fetch_prices", _fake_fetch_prices)
    return calls


async def test_corrected_route_refetches_the_cached_quote_so_source_equals_route(
    app_client, _coingecko_live,
):
    """RED before the fix: source stays 'alphavantage' forever. GREEN: one refresh
    puts the quote on the routed source."""
    from app.db.base import get_sessionmaker
    from app.services.market import refresh_quote, route_for_instrument

    await _seed_crypto_on_stale_av_quote("ZZB", "zz-bitcoinlike")

    async with get_sessionmaker()() as s:
        q = await refresh_quote(s, "ZZB")
        await s.commit()

    assert q.source == "coingecko", (
        f"route-mismatched cache was served verbatim (source={q.source!r}) — a corrected "
        "override never reaches the quote store")
    assert q.price == Decimal("118250.5")
    assert q.is_stale is False
    assert _coingecko_live == [["zz-bitcoinlike"]]

    # Source equals Route — the owner's pin.
    async with get_sessionmaker()() as s:
        from sqlalchemy import select

        from app.models import Instrument
        instr = (await s.execute(select(Instrument).where(Instrument.symbol == "ZZB"))).scalars().first()
        diag = await route_for_instrument(s, instr)
        from app.services.market import get_cached_quote
        assert (await get_cached_quote(s, "ZZB")).source == diag.source_selected == "coingecko"


async def test_an_on_route_quote_is_not_refetched(app_client, _coingecko_live):
    """The invalidation is keyed to a route MISMATCH, not to every refresh — an
    instrument already on its routed source keeps the existing cache-publish cadence
    (no per-refresh CoinGecko call, which would burn the rate budget)."""
    from app.db.base import get_sessionmaker
    from app.models import Quote as QuoteRow
    from app.services.market import refresh_quote

    iid = await _seed_crypto_on_stale_av_quote("ZZR", "zz-ripplelike")
    async with get_sessionmaker()() as s:
        row = await s.get(QuoteRow, iid)
        row.source = "coingecko"          # already on-route
        await s.commit()

    async with get_sessionmaker()() as s:
        q = await refresh_quote(s, "ZZR")
        await s.commit()

    assert _coingecko_live == [], "an on-route quote must not trigger a refetch"
    assert q.source == "coingecko"
