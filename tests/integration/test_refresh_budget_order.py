# SPDX-License-Identifier: AGPL-3.0-or-later
"""R-63 Phase 3 — the refresh budget spends HOLDINGS before overview proxies (§9-6).

`refresh_data` walks the symbol list in order and stops when the time budget is reached, so the
ORDER decides who gets a call when the budget is tight. A user's own holdings must come first —
a call must never be spent on an overview proxy while a holding goes unrefreshed. Proven by
recording the actual refresh call ORDER (a counted-calls test), not merely that a price appeared.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal


async def _seed_equity_holding(symbol: str) -> None:
    from app.db.base import get_sessionmaker
    from app.models import Account, Holding, Instrument

    async with get_sessionmaker()() as s:
        acct = Account(name="Budget", kind="brokerage", currency="USD")
        s.add(acct)
        instr = Instrument(symbol=symbol.upper(), asset_class="equity",
                           listing_country="US", currency="USD")
        s.add(instr)
        await s.flush()
        s.add(Holding(account_id=acct.id, instrument_id=instr.id, quantity=Decimal("1")))
        await s.commit()


async def test_refresh_spends_holdings_before_overview_proxies(app_client, monkeypatch):
    import app.services.market as market_mod
    from app.api.v1.routes.markets import _DEFAULT_OVERVIEW
    from app.schemas.common import EntitlementStatus, Quote
    from app.services.market import QuoteRefresh

    hold_sym = "MYHOLD"
    await _seed_equity_holding(hold_sym)

    order: list[str] = []

    async def fake_refresh(session, sym, exchange=None):
        order.append(sym.upper())
        q = Quote(symbol=sym.upper(), price=Decimal("1"), currency="USD", source="yahoo",
                  entitlement=EntitlementStatus.DELAYED, received_at=datetime.now(UTC))
        return QuoteRefresh(q, "fetched")

    async def _noop(*a, **k):
        return None

    monkeypatch.setattr(market_mod, "refresh_quote_detailed", fake_refresh)
    monkeypatch.setattr(market_mod, "backfill_instrument_name", _noop)

    r = await app_client.post("/api/v1/system/refresh-data")
    assert r.status_code == 200
    assert hold_sym in order, "the seeded holding was never refreshed"

    # Some overview symbols (e.g. AAPL/NVDA) are ALSO demo holdings and correctly ride the holdings
    # block; the invariant is that no PURE proxy (overview-only, not held) precedes a holding.
    from sqlalchemy import select

    from app.db.base import get_sessionmaker
    from app.models import Holding, Instrument

    async with get_sessionmaker()() as s:
        held = {
            r0 for r0 in (await s.execute(
                select(Instrument.symbol).join(Holding, Holding.instrument_id == Instrument.id)
                .where(Holding.deleted_at.is_(None)))).scalars().all() if r0}
    pure_proxies = [order.index(p) for p in _DEFAULT_OVERVIEW if p in order and p not in held]
    assert pure_proxies, "expected overview-only proxies in the refresh set"
    assert order.index(hold_sym) < min(pure_proxies), (
        "a holding was refreshed AFTER an overview-only proxy — the budget priority is wrong")
