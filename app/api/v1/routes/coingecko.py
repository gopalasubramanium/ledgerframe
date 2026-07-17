# SPDX-License-Identifier: AGPL-3.0-or-later
"""CoinGecko crypto endpoints (opt-in). Search + map coins by canonical id, refresh
prices, report status. No secrets; refresh + mapping are PIN-protected mutations.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_auth
from app.models import AuditEvent, Instrument
from app.services import coingecko as cg
from app.services.identity import set_identifier

router = APIRouter()


@router.get("/coingecko/status")
async def coingecko_status(session: AsyncSession = Depends(get_db)) -> dict:
    return await cg.status(session)


@router.get("/coingecko/search")
async def coingecko_search(q: str = Query(min_length=1, max_length=80),
                           session: AsyncSession = Depends(get_db)) -> dict:
    return {"results": await cg.search_coins(session, q)}


@router.post("/coingecko/refresh", dependencies=[Depends(require_auth)])
async def coingecko_refresh(
    file: UploadFile | None = File(None),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Refresh the coin master and prices. If a coins-list JSON is uploaded, only the
    master is updated (offline). Otherwise the coin master is fetched (if empty) and
    prices for mapped coins are fetched from CoinGecko (opt-in network)."""
    coins = 0
    published = 0
    if file is not None:
        try:
            data = json.loads((await file.read()).decode("utf-8-sig", errors="replace"))
        except json.JSONDecodeError as exc:
            raise HTTPException(400, f"invalid coins-list JSON: {exc}") from exc
        coins = await cg.refresh_coins(session, data)
    else:
        from app.providers.market.coingecko import fetch_coins_list, fetch_prices
        try:
            # §14dr-15 — a real Sync-now ALWAYS refetches the full coins/list and re-upserts
            # the master, mirroring amfi_refresh (which always refetches NAVAll.txt) — one
            # pattern, not two. The old `if coins == 0` guard kept a seeded/stale cache forever
            # (2 demo coins vs the real ~17k), so XRP/Ripple was unfindable. coins/list is a
            # single call (fetch_coins_list → one GET), so this stays within the rate budget.
            coins = await cg.refresh_coins(session, await fetch_coins_list())
            ids = await cg.mapped_ids(session)
            if ids:
                published = await cg.publish_prices(session, await fetch_prices(ids))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(502, f"could not reach CoinGecko: {str(exc)[:160]}") from exc
    session.add(AuditEvent(category="mutation", action="coingecko_refresh",
                           detail=f"coins={coins} published={published}"))
    result = await cg.status(session)
    result["published"] = published
    return result


class MapCoinIn(BaseModel):
    id: str


@router.post("/instruments/{symbol}/map-coingecko", dependencies=[Depends(require_auth)])
async def map_coingecko(symbol: str, payload: MapCoinIn,
                        session: AsyncSession = Depends(get_db)) -> dict:
    """Attach an exact CoinGecko canonical id to an instrument (never inferred from a
    symbol). Prices arrive on the next refresh."""
    instr = (await session.execute(
        select(Instrument).where(Instrument.symbol == symbol.upper())
    )).scalars().first()
    if instr is None:
        raise HTTPException(404, "unknown instrument")
    coin_id = payload.id.strip().lower()
    from app.models import AssetClass
    from app.services.identity import DuplicateIdentifierError
    try:
        await set_identifier(session, instr.id, "coingecko_id", coin_id, provider="coingecko", is_primary=True)
    except DuplicateIdentifierError as exc:
        raise HTTPException(409, str(exc)) from exc
    instr.asset_class = AssetClass.CRYPTO
    instr.asset_subclass = "crypto"
    instr.asset_category = "crypto"
    instr.liquidity_profile = "listed"
    instr.valuation_method = "market_quote"
    if not instr.pricing_currency:
        instr.pricing_currency = "USD"
    session.add(AuditEvent(category="mutation", action="map_coingecko",
                           detail=f"{instr.symbol}->{coin_id}"))
    return {"ok": True, "symbol": instr.symbol, "id": coin_id}
