# SPDX-License-Identifier: AGPL-3.0-or-later
"""News headlines (free RSS + provider) and AI briefing."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_auth
from app.providers.market import get_provider
from app.services.briefing import get_briefing, refresh_briefing
from app.services.feeds import (
    DEFAULT_FEEDS,
    fetch_feeds,
    get_feed_urls,
    set_feed_urls,
    test_feeds,
)

router = APIRouter()


@router.get("/news")
async def news(session: AsyncSession = Depends(get_db)) -> dict:
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.models import Watchlist

    wl = (
        await session.execute(
            select(Watchlist).options(selectinload(Watchlist.items)).limit(1)
        )
    ).scalars().first()
    symbols = []
    if wl:
        from app.models import Instrument

        for it in wl.items[:8]:
            instr = await session.get(Instrument, it.instrument_id)
            if instr:
                symbols.append(instr.symbol)

    # Free RSS feeds first (no key needed), then any provider news. The RSS fetch
    # is capped so a slow/blocked feed can never stall the News page; on timeout we
    # simply show provider headlines.
    import asyncio

    try:
        rss = await asyncio.wait_for(fetch_feeds(session, limit=30), timeout=12)
    except (TimeoutError, Exception):  # noqa: BLE001
        rss = []
    provider_items = await get_provider().get_news(symbols or ["AAPL", "MSFT", "NVDA"])
    items = rss + list(provider_items)
    return {
        "items": [i.model_dump(mode="json") for i in items],
        "rss_count": len(rss),
    }


@router.get("/news/grouped")
async def grouped_news(session: AsyncSession = Depends(get_db)) -> dict:
    """News grouped by area (B10): My holdings · India · Singapore · US · Global ·
    Macro/FX. Deduplicated by headline and recency-sorted. Only summarises retrieved
    headlines — never invents causation. Headlines are sanitised (untrusted input)."""
    import asyncio
    import re
    from datetime import UTC, datetime

    from app.ai.safety import sanitize_untrusted
    from app.models import Instrument, WatchlistItem

    held = {
        s for s in (
            await session.execute(select(Instrument.symbol).join(
                WatchlistItem, WatchlistItem.instrument_id == Instrument.id, isouter=True))
        ).scalars().all() if s
    }
    from app.models import Holding
    held |= {
        i.symbol for i in (
            await session.execute(select(Instrument).join(Holding, Holding.instrument_id == Instrument.id))
        ).scalars().all() if i.symbol
    }

    # Portfolio weights → relevance scoring for "My holdings" news (bigger position = more
    # relevant), combined with recency. Deterministic; only ranks retrieved headlines.
    from app.core.config import get_settings
    from app.services.portfolio import value_portfolio

    val = await value_portfolio(session, get_settings().base_currency)
    _gross = sum((h.market_value_base for h in val.holdings if h.market_value_base > 0), 0) or 1
    weights = {h.symbol: float(h.market_value_base / _gross)
               for h in val.holdings if h.symbol and h.market_value_base > 0}

    try:
        items = list(await asyncio.wait_for(fetch_feeds(session, limit=40), timeout=12))
    except (TimeoutError, Exception):  # noqa: BLE001
        items = []
    # Provider news carries per-symbol tags (RSS usually doesn't), so it's what actually
    # populates "My holdings". Best-effort — never blocks the page.
    try:
        # sorted() so the held-symbol selection (and thus the feed) is deterministic.
        items += list(await get_provider().get_news(sorted(held)[:12] or ["AAPL", "MSFT", "NVDA"]))
    except Exception:  # noqa: BLE001
        pass
    now = datetime.now(UTC)
    items.sort(key=lambda x: x.published_at or now, reverse=True)

    def _recency(published_at) -> float:
        if not published_at:
            return 0.3
        pa = published_at if published_at.tzinfo else published_at.replace(tzinfo=UTC)
        age_h = (now - pa).total_seconds() / 3600
        return max(0.05, 1 - age_h / (14 * 24))    # ~linear decay over 14 days

    seen: set[str] = set()
    groups: dict[str, list] = {k: [] for k in ("My holdings", "India", "Singapore", "US", "Global", "Macro / FX")}
    for it in items:
        key = re.sub(r"\W+", "", (it.headline or "").lower())[:64]
        if not key or key in seen:
            continue
        seen.add(key)
        h = (it.headline or "").lower()
        compact: dict[str, Any] = {"headline": sanitize_untrusted(it.headline), "source": it.source,
                   "url": it.url, "published_at": it.published_at.isoformat() if it.published_at else None,
                   "symbols": it.symbols or []}
        matched = set(it.symbols or []) & held
        if matched:
            w = max((weights.get(s, 0.0) for s in matched), default=0.0)
            compact["relevance"] = round(w * _recency(it.published_at), 4)
            groups["My holdings"].append(compact)
        elif re.search(r"\b(fed|inflation|interest rate|central bank|dollar|rupee|currency|bond yield|gdp|recession)\b", h):
            groups["Macro / FX"].append(compact)
        elif re.search(r"\b(india|nifty|sensex|\brbi\b|rupee|mumbai|adani|reliance)\b", h):
            groups["India"].append(compact)
        elif re.search(r"\b(singapore|straits times|\bsti\b|\bmas\b|\bsgx\b|dbs|ocbc)\b", h):
            groups["Singapore"].append(compact)
        elif re.search(r"\b(wall street|s&p|nasdaq|dow|nyse|u\.s\.|\bus\b|federal reserve)\b", h):
            groups["US"].append(compact)
        else:
            groups["Global"].append(compact)
    # Rank "My holdings" by relevance (weight × recency) — most relevant to you first.
    groups["My holdings"].sort(key=lambda c: c.get("relevance", 0.0), reverse=True)
    return {"groups": [{"name": k, "items": v[:6]} for k, v in groups.items() if v],
            "total": len(seen)}


@router.get("/news/feeds")
async def get_feeds(session: AsyncSession = Depends(get_db)) -> dict:
    return {"feeds": await get_feed_urls(session), "defaults": DEFAULT_FEEDS}


class FeedsIn(BaseModel):
    feeds: list[str]


@router.put("/news/feeds", dependencies=[Depends(require_auth)])
async def put_feeds(payload: FeedsIn, session: AsyncSession = Depends(get_db)) -> dict:
    await set_feed_urls(session, payload.feeds)
    return {"ok": True, "feeds": await get_feed_urls(session)}


@router.get("/news/feeds/test")
async def test_news_feeds(session: AsyncSession = Depends(get_db)) -> dict:
    return {"results": await test_feeds(session)}


@router.get("/briefing")
async def briefing(session: AsyncSession = Depends(get_db)) -> dict:
    return await get_briefing(session)


@router.post("/briefing/refresh", dependencies=[Depends(require_auth)])
async def briefing_refresh(session: AsyncSession = Depends(get_db)) -> dict:
    # Writes derived briefing text to settings → PIN-protected like other mutations
    # (require_auth is a no-op until a PIN is set, so first-run UX is unaffected).
    text = await refresh_briefing(session)
    return {"text": text}
