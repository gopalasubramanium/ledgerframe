# SPDX-License-Identifier: AGPL-3.0-or-later
"""CSV-backed market data provider for local-only / testing use.

Reads OHLCV history from ``<imports_dir>/<SYMBOL>.csv`` with a header:
    date,open,high,low,close,volume
The latest row becomes the quote (entitlement = end-of-day). Falls back to the
mock provider for any symbol without a CSV so dashboards never go blank.
"""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path

from app.core.money import D, price
from app.providers.market.mock import MockMarketDataProvider
from app.schemas.common import (
    Candle,
    EntitlementStatus,
    FailureState,
    FxRate,
    Instrument,
    MarketStatus,
    NewsItem,
    Quote,
)

MAX_CSV_BYTES = 10 * 1024 * 1024  # 10 MB safety cap


class CSVMarketDataProvider:
    name = "csv"

    def __init__(self, imports_dir: Path):
        self.imports_dir = imports_dir
        self._mock = MockMarketDataProvider()

    def _path(self, symbol: str) -> Path:
        return self.imports_dir / f"{symbol.upper()}.csv"

    def _read(self, symbol: str) -> list[Candle]:
        path = self._path(symbol)
        if not path.exists() or path.stat().st_size > MAX_CSV_BYTES:
            return []
        candles: list[Candle] = []
        with path.open(newline="") as fh:
            for row in csv.DictReader(fh):
                try:
                    candles.append(
                        Candle(
                            ts=datetime.fromisoformat(row["date"]).replace(tzinfo=UTC),
                            open=price(row["open"]),
                            high=price(row["high"]),
                            low=price(row["low"]),
                            close=price(row["close"]),
                            volume=D(row.get("volume") or 0),
                        )
                    )
                except (KeyError, ValueError):
                    continue
        candles.sort(key=lambda c: c.ts)
        return candles

    async def get_quote(self, symbol: str, exchange: str | None = None) -> Quote:
        candles = self._read(symbol)
        if len(candles) < 1:
            # R-63 F-C Option 1 (owner ruling 2026-07-24, R1): a CSV MISS returns a TYPED no-price,
            # NEVER a mock substitution. The spec never sanctioned a quote fallback here —
            # 05-PROVIDERS-AND-ROUTING §A.3 lists the mock fallback for FX/search/news only — yet
            # `self._mock.get_quote()` returned a fabricated `source="mock"` price (mock's default
            # base 100 × _walk) that the execution net persisted and confidence scored 100/high on a
            # live holding (the AARK 109.878669 defect, F-C/I-10). The class IS covered (fetch_chain
            # only walks csv for equity/etf), so the honest state is EMPTY: this source responded, it
            # simply has no price for this symbol. The net then walks on / returns a typed no-price.
            now = datetime.now(UTC)
            return Quote(
                symbol=symbol.upper(), exchange=exchange, price=None,
                currency="USD", source="csv",
                entitlement=EntitlementStatus.UNAVAILABLE, failure_state=FailureState.EMPTY,
                received_at=now, is_stale=True,
            )
        last = candles[-1]
        prev = candles[-2].close if len(candles) > 1 else last.open
        return Quote(
            symbol=symbol.upper(),
            exchange=exchange,
            price=last.close,
            previous_close=prev,
            change=price(last.close - prev),
            change_pct=D(round((last.close - prev) / prev * 100, 2)) if prev else None,
            currency="USD",
            source="csv",
            entitlement=EntitlementStatus.END_OF_DAY,
            market_time=last.ts,
            received_at=datetime.now(UTC),
        )

    async def get_history(
        self, instrument_id: str, interval: str, start: datetime, end: datetime
    ) -> list[Candle]:
        candles = self._read(instrument_id)
        if not candles:
            return await self._mock.get_history(instrument_id, interval, start, end)
        return [c for c in candles if start <= c.ts <= end]

    async def search_instruments(self, query: str) -> list[Instrument]:
        out: list[Instrument] = []
        for p in self.imports_dir.glob("*.csv"):
            sym = p.stem.upper()
            if query.upper() in sym:
                out.append(Instrument(symbol=sym, name=f"{sym} (CSV)", currency="USD"))
        return out or await self._mock.search_instruments(query)

    async def get_market_status(self, market: str) -> MarketStatus:
        return await self._mock.get_market_status(market)

    async def get_fx_rate(self, base: str, quote: str) -> FxRate:
        return await self._mock.get_fx_rate(base, quote)

    async def get_news(self, instruments: list[str]) -> list[NewsItem]:
        return []
