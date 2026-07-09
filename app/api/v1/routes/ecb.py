# SPDX-License-Identifier: AGPL-3.0-or-later
"""ECB reference-FX endpoints (opt-in). Refresh/status + an FX conversion diagnostic
that records whether a reference rate is direct, inverse or triangulated.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_auth
from app.models import AuditEvent
from app.services import ecb_fx, fx

router = APIRouter()


@router.get("/fx/ecb/status")
async def ecb_status(session: AsyncSession = Depends(get_db)) -> dict:
    return await ecb_fx.status(session)


@router.post("/fx/ecb/refresh", dependencies=[Depends(require_auth)])
async def ecb_refresh(
    file: UploadFile | None = File(None),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Refresh the ECB reference rates from an uploaded XML (offline) or the official
    daily feed (opt-in network)."""
    if file is not None:
        text = (await file.read()).decode("utf-8-sig", errors="replace")
    else:
        from app.providers.market.ecb import fetch_ecb_daily
        try:
            text = await fetch_ecb_daily()
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(502, f"could not fetch ECB rates: {str(exc)[:160]}") from exc
    result = await ecb_fx.refresh(session, text)
    session.add(AuditEvent(category="mutation", action="ecb_refresh",
                           detail=f"currencies={result['currencies']} as_of={result['as_of']}"))
    return result


@router.get("/fx/convert")
async def fx_convert(
    from_: str = Query(alias="from", min_length=3, max_length=3),
    to: str = Query(min_length=3, max_length=3),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Diagnostic: the effective FX rate plus the ECB reference rate and its method
    (direct / inverse / triangulated)."""
    ref_rate, method = ecb_fx.reference_rate(from_, to)
    effective = await fx.get_rate(from_, to)
    return {
        "from": from_.upper(), "to": to.upper(),
        "effective_rate": float(effective),
        "ecb_rate": float(ref_rate) if ref_rate is not None else None,
        "ecb_method": method,          # direct | inverse | triangulated | identity | unavailable
        "source": "ecb_reference" if method != "unavailable" else "provider",
    }
