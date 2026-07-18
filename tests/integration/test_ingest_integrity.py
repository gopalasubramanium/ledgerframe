# SPDX-License-Identifier: AGPL-3.0-or-later
"""R-43 F-4 — ingest integrity: freshness + non-truncation, the ZIP fetch, hard timeouts.

Provenance is not integrity. ECB's own edge served a SIX-YEAR-STALE corrupt object for the legacy
``eurofxref-hist.csv`` URL (last-modified 2020; a 2010 counting-pattern nonsense row atop 2009
data) while the maintained ``.zip`` was current + genuine. The fix: ingest the ZIP, and REFUSE a
stale/corrupt or truncated series on every ingest — never persist garbage from any source.
"""

from __future__ import annotations

import io
import zipfile
from datetime import UTC, datetime, timedelta
from decimal import Decimal

# The F-4 real-file shape: newest data row is a 2010 counting-pattern nonsense line atop 2009 data.
# Newest parsed date = 2010-02-14 → six years stale relative to 2026 → must be refused.
_STALE_CORRUPT = (
    "Date, USD, INR, SGD, \n"
    "2010-02-14, 1, 2, 3, \n"        # counting-pattern nonsense (INR=2 is impossible; EUR→INR ~90)
    "2009-12-31, 1.4406, 66.90, 2.02, \n"
    "2009-12-30, 1.4331, 66.50, 2.01, \n"
)


def _fresh_csv() -> str:
    """An ECB-hist-shaped CSV whose newest date is TODAY (so the freshness gate passes)."""
    today = datetime.now(UTC).date()
    y = today - timedelta(days=1)
    return (
        "Date, USD, INR, SGD, \n"
        f"{today.isoformat()}, 1.1435, 110.1020, 1.4765, \n"
        f"{y.isoformat()}, 1.1600, 111.0000, 1.4800, \n"
    )


async def test_ingest_hist_refuses_a_stale_corrupt_series(session):
    """F-4 RED: the real 2020-served file (newest date 2010) is REFUSED and NOTHING is written —
    the store is never poisoned by a stale/corrupt file, even from the genuine authoritative source."""
    import pytest

    from app.services import fx_history
    from app.services.ingest_guard import IngestIntegrityError
    with pytest.raises(IngestIntegrityError) as ei:
        await fx_history.ingest_hist(session, _STALE_CORRUPT, max_staleness_days=7)
    assert "stale" in str(ei.value).lower()
    assert (await fx_history.status(session))["rows"] == 0  # nothing written


async def test_ingest_hist_accepts_a_fresh_series(session):
    """A genuinely fresh file (newest date today) passes the freshness gate and ingests."""
    from app.services import fx_history

    res = await fx_history.ingest_hist(session, _fresh_csv(), max_staleness_days=7)
    assert res["rows"] > 0
    assert (await fx_history.status(session))["rows"] > 0


def test_extract_hist_csv_unzips_the_maintained_zip():
    """F-4: fetch_ecb_hist ingests the ZIP — extract_hist_csv pulls the CSV member out of it."""
    from app.providers.market.ecb import extract_hist_csv

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("eurofxref-hist.csv", _fresh_csv())
    assert "Date, USD" in extract_hist_csv(buf.getvalue())


async def test_acquire_history_refuses_stale_fx_with_a_served_error(session, monkeypatch):
    """F-4 at the flow level: a stale/corrupt FX download is refused with a served error (not a
    silent bad ingest); the store is untouched and the build is retriable."""
    from types import SimpleNamespace

    from app.services import acquire, fx_history

    monkeypatch.setattr("app.services.acquire.get_settings",
                        lambda: SimpleNamespace(base_currency="SGD", is_demo=False))

    async def _stale_fetch(timeout: float = 60.0):
        return _STALE_CORRUPT
    monkeypatch.setattr("app.services.acquire.fetch_ecb_hist", _stale_fetch)

    res = await acquire.acquire_history(session, "SGD")
    assert res["ok"] is False and res["acquired"] is False
    assert "freshness" in res["message"].lower()
    assert (await fx_history.status(session))["rows"] == 0


async def test_av_client_sends_entitlement_delayed(monkeypatch):
    """F-4 (owner on-stack): the AV client carries entitlement=delayed on every call."""
    from app.providers.market import external

    sink: dict = {}

    class _Resp:
        def raise_for_status(self): pass
        def json(self): return {"ok": 1}

    class _Client:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url, params=None):
            sink.update(params or {})
            return _Resp()

    async def _fake_egress(what, **kw):
        return _Client()

    monkeypatch.setattr(external, "egress_client", _fake_egress)
    p = external.ExternalMarketDataProvider("alphavantage", "testkey")
    await p._get({"function": "TIME_SERIES_DAILY", "symbol": "TSLA", "outputsize": "full"})
    assert sink.get("entitlement") == "delayed"
    assert sink.get("outputsize") == "full"  # caller params preserved


def test_assert_not_truncated_refuses_empty():
    """The generalised truncation guard: an empty/malformed parse is refused, not trusted."""
    import pytest

    from app.services.ingest_guard import IngestIntegrityError, assert_not_truncated
    with pytest.raises(IngestIntegrityError):
        assert_not_truncated(0, source="test")
    assert_not_truncated(3, source="test")  # a plausible count passes


async def test_coingecko_ingest_verify_refuses_all_dropped(session):
    """Generalised: a CoinGecko payload whose points all drop to nothing (corrupt) is refused
    under verify, never silently stored as an empty series."""
    import pytest

    from app.models import AssetClass, Instrument
    from app.services.coingecko import ingest_history
    from app.services.ingest_guard import IngestIntegrityError
    btc = Instrument(symbol="BTC", currency="USD", pricing_currency="USD", asset_class=AssetClass.CRYPTO)
    session.add(btc)
    await session.flush()
    corrupt = {"prices": [[1, 0], [2, -5]], "total_volumes": []}  # had points, all non-positive → dropped
    with pytest.raises(IngestIntegrityError):
        await ingest_history(session, btc.id, corrupt, verify=True)
    # A healthy payload still ingests under verify.
    ok = {"prices": [[int(datetime(2026, 1, 1, tzinfo=UTC).timestamp() * 1000), 64000.0]], "total_volumes": []}
    assert await ingest_history(session, btc.id, ok, verify=True) == 1
    _ = Decimal
