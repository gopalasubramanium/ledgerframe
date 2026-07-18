# SPDX-License-Identifier: AGPL-3.0-or-later
"""R-43 §12 — the Build-history ACQUISITION preflight.

Before the backfill reconstructs the net-worth series (``app.services.backfill.run_backfill``),
the inputs it values from must actually exist on-stack. F-1/F-2/F-3 all traced to the same root:
step-6 acquisition never ran, so ``ecb_fx_history`` was empty and ``price_history`` was
sparse/wrong-instrument — and the orchestrator valued a garbage series anyway. This module is the
preflight that acquires those inputs first.

Step 2 acquires the ECB ``eurofxref-hist`` per-date FX (one keyless fetch = the whole daily
reference history back to 1999), ingested idempotently. Later steps grow this preflight with the
per-instrument price acquisition (crypto via CoinGecko, funds via the AMFI archive, equities via AV
``outputsize=full``) behind the class-aware capability gate.

Honesty (Product Guarantee 5): under no-egress this makes **ZERO** outbound calls and returns a
served refusal — building history requires the exchange-rate download; a garbage-from-nothing
series is never fabricated in its place.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.egress import egress_allowed
from app.providers.market.amfi import chunk_date_ranges, fetch_nav_history
from app.providers.market.coingecko import fetch_market_chart_range
from app.providers.market.ecb import fetch_ecb_hist
from app.services.fx_history import ingest_hist
from app.services.ingest_guard import IngestIntegrityError

log = logging.getLogger("ledgerframe")

# F-4: hard wall on the FX download (no stage may spin indefinitely) + the FX staleness ceiling.
ECB_FETCH_TIMEOUT_S = 90
FX_MAX_STALENESS_DAYS = 7
# Hard per-instrument fetch wall for the price-acquisition stages (crypto/fund history).
PRICE_FETCH_TIMEOUT_S = 60

# The served refusal shown when no-egress blocks the exchange-rate download (D-105).
NO_EGRESS_MESSAGE = (
    "Building history requires an exchange-rate download — no-egress is on. "
    "The device makes zero outbound calls in this mode (Product Guarantee 5)."
)


async def acquire_history(session: AsyncSession, base_currency: str | None = None) -> dict:
    """Fetch + ingest the historical inputs the backfill values from, BEFORE reconstructing the
    series. Returns a served summary ``{ok, acquired, message, fx?}``.

    ``ok`` is False + ``acquired`` False under no-egress (the honest refusal) — the caller must not
    proceed to value a coverage-poor series. Idempotent: re-running re-ingests in place (the ECB
    upsert), so a warm store is refreshed, not duplicated."""
    settings = get_settings()
    base = (base_currency or settings.base_currency)

    if not await egress_allowed():
        # Guarantee 5 (takes precedence over everything below): never construct a client, never make
        # the call — refuse honestly. Building history requires the exchange-rate download.
        return {"ok": False, "acquired": False, "message": NO_EGRESS_MESSAGE}

    if settings.is_demo:
        # Offline demo posture (mock provider): the demo seed generates ecb_fx_history
        # deterministically (app/seed/demo_history.py) — a real ECB fetch is neither needed nor
        # wanted. Report OK so the build proceeds from the seeded history; acquired=False (no fetch).
        return {"ok": True, "acquired": False,
                "message": "Demo history is generated offline — no download needed."}

    # §12-R3: purge wrong-instrument candles (crypto rows cached from AV's equity endpoint) BEFORE
    # valuing, so the backfill never reads garbage. Idempotent — a second build finds nothing.
    from app.services.market import repair_wrong_class_candles
    purge = await repair_wrong_class_candles(session)

    # ECB per-date FX — one fetch of the MAINTAINED zip (F-4). Hard timeout so no stage can spin
    # indefinitely (the F-4 hang); a stale/corrupt or truncated file is REFUSED (integrity gate),
    # not ingested — both degrade to a served error the caller shows, and the build is retriable.
    try:
        csv_text = await asyncio.wait_for(fetch_ecb_hist(), timeout=ECB_FETCH_TIMEOUT_S)
    except TimeoutError:  # asyncio.TimeoutError is TimeoutError on 3.11+
        return {"ok": False, "acquired": False,
                "message": "Exchange-rate download timed out — retry Build history."}
    try:
        fx = await ingest_hist(session, csv_text, max_staleness_days=FX_MAX_STALENESS_DAYS)
    except IngestIntegrityError as exc:
        await session.rollback()
        return {"ok": False, "acquired": False,
                "message": f"Exchange-rate data failed the freshness check — {exc.reason}. "
                           "Not ingested; retry Build history."}
    await session.commit()
    # Per-instrument price history — each class routed to the provider that can serve it (§12-R3).
    prices = await acquire_prices(session, base)
    await session.commit()

    log.info("acquire_history: ECB FX %s dates; purged %s garbage candle(s); prices %s (base %s)",
             fx.get("dates"), purge.get("purged"), prices, base)
    return {"ok": True, "acquired": True, "fx": fx, "purged": purge.get("purged", 0),
            "prices": prices,
            "message": f"Exchange-rate history downloaded — {fx.get('dates', 0)} publication days."}


async def _held_instruments(session: AsyncSession) -> list:
    """The distinct instruments the book holds (non-manual, not soft-deleted) — the acquisition set."""
    from app.models import Holding, Instrument

    return (await session.execute(
        select(Instrument).join(Holding, Holding.instrument_id == Instrument.id)
        .where(Holding.deleted_at.is_(None), Instrument.id.isnot(None)).distinct()
    )).scalars().all()


async def _identifier(session: AsyncSession, instrument_id: int, id_type: str) -> str | None:
    from app.models import InstrumentIdentifier

    return (await session.execute(
        select(InstrumentIdentifier.value)
        .where(InstrumentIdentifier.instrument_id == instrument_id,
               InstrumentIdentifier.id_type == id_type)
    )).scalars().first()


async def acquire_prices(session: AsyncSession, base_currency: str | None = None) -> dict:
    """§12 steps 4/5/6: acquire per-instrument price history for the held book, routing each class
    to the provider that can serve it (§12-R3):

      • equity / etf  → the active provider's daily history (Alpha Vantage ``outputsize=full`` for a
        >100-day range = ONE call = the full 20+yr series; the 12h freshness marker prevents a
        refetch within the window). Served via ``get_history_cached`` (the routed, cached path).
      • crypto        → CoinGecko ``market_chart/range`` (never AV — its crypto history is garbage).
      • mutual_fund   → the AMFI history archive in ≤90-day chunks.

    An instrument whose provider mapping cannot be resolved (no coingecko_id / amfi_code) is skipped
    HONESTLY (logged) — never fabricated. A per-instrument failure degrades (logged), never aborts
    the whole build. Returns per-class counts for the served summary."""
    from app.models import Transaction as Txn
    from app.services.amfi import ingest_nav_history
    from app.services.coingecko import ingest_history as ingest_crypto_history
    from app.services.market import get_history_cached

    earliest = (await session.execute(
        select(func.min(Txn.ts)).where(Txn.deleted_at.is_(None), Txn.instrument_id.isnot(None))
    )).scalar()
    if earliest is None:
        return {"equity": 0, "crypto": 0, "mutual_fund": 0, "skipped": 0}
    start = datetime(earliest.year, earliest.month, earliest.day, tzinfo=UTC)
    end = datetime.now(UTC)
    counts = {"equity": 0, "crypto": 0, "mutual_fund": 0, "skipped": 0}

    for instr in await _held_instruments(session):
        ac = instr.asset_class.value if hasattr(instr.asset_class, "value") else str(instr.asset_class or "")
        try:
            if ac in ("equity", "etf"):
                # AV outputsize=full is auto-selected for a >100-day range → 1 call/instrument.
                await get_history_cached(session, instr.symbol, "1d", start, end)
                counts["equity"] += 1
            elif ac == "crypto":
                cid = await _identifier(session, instr.id, "coingecko_id")
                if not cid:
                    # §17-R1/R2 (F-6): history acquisition routes by CLASS to CoinGecko — the
                    # quotes-lane source_override (e.g. the owner's dr-27 AV override on BTC/XRP)
                    # never blocks it. Auto-resolve the canonical id at acquisition time, reusing
                    # the ONE linker (top-market-cap disambiguation, §17-R2); an unresolvable symbol
                    # (no match / genuinely ambiguous) is skipped HONESTLY with the served reason.
                    from app.services.market import _link_coingecko_by_symbol
                    link_err = await _link_coingecko_by_symbol(session, instr)
                    if link_err:
                        counts["skipped"] += 1
                        log.info("acquire_prices: %s crypto unmapped — %s", instr.symbol, link_err)
                        continue
                    cid = await _identifier(session, instr.id, "coingecko_id")
                chart = await asyncio.wait_for(
                    fetch_market_chart_range(cid, "usd", start, end), timeout=PRICE_FETCH_TIMEOUT_S)
                counts["crypto"] += await ingest_crypto_history(session, instr.id, chart, verify=True)
            elif ac == "mutual_fund":
                code = await _identifier(session, instr.id, "amfi_code") or (
                    instr.symbol if (instr.symbol or "").isdigit() else None)
                if not code:
                    counts["skipped"] += 1
                    log.info("acquire_prices: %s fund has no amfi_code — skipped (honest)", instr.symbol)
                    continue
                for a, b in chunk_date_ranges(start.date(), end.date()):
                    text = await asyncio.wait_for(fetch_nav_history(a, b), timeout=PRICE_FETCH_TIMEOUT_S)
                    counts["mutual_fund"] += await ingest_nav_history(session, instr.id, str(code), text, verify=True)
            else:
                counts["skipped"] += 1
        except Exception as exc:  # noqa: BLE001 — one instrument's failure never aborts the build
            counts["skipped"] += 1
            log.warning("acquire_prices: %s (%s) history unavailable — degrading honestly: %s",
                        instr.symbol, ac, exc)
    return counts
