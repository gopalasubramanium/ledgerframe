# SPDX-License-Identifier: AGPL-3.0-or-later
"""AMFI mutual-fund NAV endpoints (opt-in). Search + map schemes, refresh official
NAVs, and report status. No secrets; refresh + mapping are PIN-protected mutations.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_auth
from app.models import AuditEvent, Instrument
from app.services import amfi as amfi_svc
from app.services.identity import set_identifier

router = APIRouter()


@router.get("/amfi/status")
async def amfi_status(session: AsyncSession = Depends(get_db)) -> dict:
    return await amfi_svc.status(session)


@router.get("/amfi/search")
async def amfi_search(q: str = Query(min_length=1, max_length=80),
                      session: AsyncSession = Depends(get_db)) -> dict:
    return {"results": await amfi_svc.search_schemes(session, q)}


@router.post("/amfi/refresh", dependencies=[Depends(require_auth)])
async def amfi_refresh(
    file: UploadFile | None = File(None),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Refresh the scheme master + latest NAVs. Uses an uploaded NAVAll.txt if
    provided (offline), else downloads the official AMFI file (opt-in network)."""
    if file is not None:
        text = (await file.read()).decode("utf-8-sig", errors="replace")
    else:
        from app.providers.market.amfi import fetch_nav_all
        try:
            text = await fetch_nav_all()
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(502, f"could not fetch AMFI NAVs: {str(exc)[:160]}") from exc
    result = await amfi_svc.refresh_schemes(session, text)
    session.add(AuditEvent(category="mutation", action="amfi_refresh",
                           detail=f"schemes={result['schemes']} priced={result['priced']}"))
    return result


class MapAmfiIn(BaseModel):
    code: str


@router.post("/instruments/{symbol}/map-amfi", dependencies=[Depends(require_auth)])
async def map_amfi(symbol: str, payload: MapAmfiIn,
                   session: AsyncSession = Depends(get_db)) -> dict:
    """Attach an exact AMFI scheme code to an instrument (the only way NAV mapping
    happens — never inferred). Publishes the NAV immediately if known."""
    instr = (await session.execute(
        select(Instrument).where(Instrument.symbol == symbol.upper())
    )).scalars().first()
    if instr is None:
        raise HTTPException(404, "unknown instrument")
    from app.models import AssetClass
    from app.services.identity import DuplicateIdentifierError
    try:
        await set_identifier(session, instr.id, "amfi_code", payload.code.strip(), provider="amfi_nav", is_primary=True)
    except DuplicateIdentifierError as exc:
        raise HTTPException(409, str(exc)) from exc
    # Broad + detailed classification (an AMFI-mapped fund is an official-NAV mutual fund).
    instr.asset_class = AssetClass.MUTUAL_FUND
    instr.asset_subclass = "mutual_fund"
    instr.asset_category = "fund"
    instr.liquidity_profile = "redeemable"
    instr.valuation_method = "official_nav"
    instr.pricing_currency = "INR"
    instr.listing_country = "IN"
    published = await amfi_svc.publish_navs_to_instruments(session)
    session.add(AuditEvent(category="mutation", action="map_amfi",
                           detail=f"{instr.symbol}->{payload.code}"))
    return {"ok": True, "symbol": instr.symbol, "code": payload.code.strip(), "published": published}
