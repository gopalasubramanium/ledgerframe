# SPDX-License-Identifier: AGPL-3.0-or-later
"""Zerodha Kite endpoints (opt-in, READ-ONLY). Instrument-master import + search +
mapping and a status that NEVER exposes credentials. No order/trading endpoints exist.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_auth
from app.core.config import get_settings
from app.models import AuditEvent, Instrument
from app.services import kite as kite_svc
from app.services.identity import set_identifier

router = APIRouter()


@router.get("/kite/status")
async def kite_status(session: AsyncSession = Depends(get_db)) -> dict:
    """Whether Kite is configured + the cached master size. NEVER returns the key or
    token — only booleans and counts."""
    s = get_settings()
    st = await kite_svc.status(session)
    st["configured"] = bool(s.kite_api_key and s.kite_access_token)
    return st


@router.get("/kite/search")
async def kite_search(q: str = Query(min_length=1, max_length=80),
                      session: AsyncSession = Depends(get_db)) -> dict:
    return {"results": await kite_svc.search(session, q)}


@router.post("/kite/refresh-instruments", dependencies=[Depends(require_auth)])
async def kite_refresh(
    file: UploadFile | None = File(None),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Import the read-only instrument master. Uses an uploaded CSV (offline) or, if
    Kite is configured, downloads it (read-only; no trading access)."""
    if file is not None:
        text = (await file.read()).decode("utf-8-sig", errors="replace")
    else:
        s = get_settings()
        if not (s.kite_api_key and s.kite_access_token):
            raise HTTPException(400, "Kite not configured — set LEDGERFRAME_KITE_API_KEY / "
                                     "LEDGERFRAME_KITE_ACCESS_TOKEN, or upload the instruments CSV.")
        from app.providers.market.kite import KiteProvider, KiteSessionExpired
        try:
            text = await KiteProvider(s.kite_api_key, s.kite_access_token).fetch_instruments()
        except KiteSessionExpired as exc:
            raise HTTPException(401, "Kite session expired — regenerate your access token.") from exc
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(502, f"could not reach Kite: {str(exc)[:160]}") from exc
    count = await kite_svc.import_instruments(session, text)
    session.add(AuditEvent(category="mutation", action="kite_refresh", detail=f"instruments={count}"))
    return {"instruments": count}


class MapKiteIn(BaseModel):
    instrument_token: int


@router.post("/instruments/{symbol}/map-kite", dependencies=[Depends(require_auth)])
async def map_kite(symbol: str, payload: MapKiteIn,
                   session: AsyncSession = Depends(get_db)) -> dict:
    """Attach an exact Kite instrument token to an instrument (never inferred)."""
    from app.models import KiteInstrument as KiteRow

    instr = (await session.execute(
        select(Instrument).where(Instrument.symbol == symbol.upper())
    )).scalars().first()
    if instr is None:
        raise HTTPException(404, "unknown instrument")
    krow = await session.get(KiteRow, payload.instrument_token)
    if krow is None:
        raise HTTPException(404, "unknown Kite instrument token (refresh the master first)")
    from app.models import AssetClass
    from app.services.identity import DuplicateIdentifierError
    try:
        await set_identifier(session, instr.id, "kite_token", str(payload.instrument_token),
                             provider="kite", is_primary=True)
    except DuplicateIdentifierError as exc:
        raise HTTPException(409, str(exc)) from exc
    # Derivative is a *subclass*, not a broad AssetClass (the enum has none) — the broad
    # class is the underlying's market (MCX commodity vs NSE/BSE equity). See ASSUMPTIONS.
    is_deriv = krow.instrument_type in ("FUT", "CE", "PE")
    if is_deriv:
        instr.asset_class = AssetClass.COMMODITY if (krow.exchange or "").upper() == "MCX" else AssetClass.EQUITY
        instr.asset_subclass = "derivative"
    else:
        instr.asset_class = AssetClass.EQUITY
        instr.asset_subclass = "equity"
    instr.exchange_mic = krow.exchange
    instr.listing_country = "IN"
    instr.valuation_method = "market_quote"
    session.add(AuditEvent(category="mutation", action="map_kite",
                           detail=f"{instr.symbol}->{payload.instrument_token}"))
    return {"ok": True, "symbol": instr.symbol, "instrument_token": payload.instrument_token,
            "instrument_type": krow.instrument_type, "asset_subclass": instr.asset_subclass}
