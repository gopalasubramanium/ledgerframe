# SPDX-License-Identifier: AGPL-3.0-or-later
"""§18-R2 (F-7b) — the refresh report is PER-INSTRUMENT HONEST.

Owner evidence (2026-07-19): "Refresh all" toasted *"Quotes & indices: Refreshed 26 of
26"* while two holdings stayed visibly stale ("Cached 18 Jul 23:39 · price is stale").

Cause: ``refresh_data`` counted a symbol as refreshed whenever the returned quote merely
*had a price* — which is true of a pure cache read, including the silent route-skip in
``refresh_quote``. A pass that fetched nothing could therefore claim N of N.

Ruling: `refreshed` counts real fetches; anything not fetched surfaces with its own
reason; and the report may never read as fully successful while a quote it covers is
still stale.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal


async def _seed_holding_with_stale_unowned_quote(symbol: str):
    """A holding routed AWAY from the active provider (a manual-lane instrument), whose
    cached quote is long stale — the shape behind the owner's two stale rows."""
    from app.db.base import get_sessionmaker
    from app.models import Account, Holding, Instrument
    from app.models import Quote as QuoteRow

    async with get_sessionmaker()() as s:
        acct = Account(name="Walk", kind="brokerage", currency="USD")
        s.add(acct)
        instr = Instrument(symbol=symbol.upper(), asset_class="property", currency="USD")
        s.add(instr)
        await s.flush()
        s.add(Holding(account_id=acct.id, instrument_id=instr.id, quantity=Decimal("1")))
        s.add(QuoteRow(instrument_id=instr.id, price=Decimal("100"), currency="USD",
                       source="alphavantage", entitlement="delayed",
                       market_time=datetime(2026, 7, 18, 15, 39, tzinfo=UTC),
                       received_at=datetime(2026, 7, 18, 15, 39, tzinfo=UTC)))
        await s.commit()
        return instr.id


async def test_refresh_never_claims_success_while_a_covered_quote_stays_stale(app_client):
    """RED before the fix: the stale, never-fetched symbol is counted in `refreshed`
    and the lane reports clean. GREEN: it is excluded, named, and given a reason."""
    sym = "ZZSTALE"
    await _seed_holding_with_stale_unowned_quote(sym)

    r = await app_client.post("/api/v1/system/refresh-data")
    assert r.status_code == 200
    data = r.json()

    assert sym not in data["succeeded"], "a cache read was counted as a refresh"
    assert sym in data["still_stale"], "a quote still stale after the pass was not surfaced"
    assert data["refreshed"] < data["total"], (
        f"claimed {data['refreshed']} of {data['total']} while {sym} stayed stale")

    reasons = {f["symbol"]: f["reason"] for f in data["failed"]}
    assert sym in reasons, "no per-instrument reason for the un-refreshed holding"
    assert reasons[sym], "the served reason must not be empty"


async def test_refreshed_counts_fetches_not_cache_reads(app_client):
    """The counter's contract, stated directly: every symbol in `succeeded` was fetched
    this pass, so none of them can still be stale."""
    r = await app_client.post("/api/v1/system/refresh-data")
    data = r.json()

    assert data["refreshed"] == len(data["succeeded"])
    assert set(data["succeeded"]).isdisjoint(set(data["still_stale"]))
