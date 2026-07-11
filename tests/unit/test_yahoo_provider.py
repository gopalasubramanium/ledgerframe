# SPDX-License-Identifier: AGPL-3.0-or-later
"""Yahoo provider symbol translation + graceful degradation (no network)."""

from __future__ import annotations

import pytest

from app.providers.market import yahoo as yahoo_mod
from app.providers.market.yahoo import YahooMarketDataProvider, _range_for, to_yahoo_symbol


class _FakeResp:
    def __init__(self, status_code: int, headers: dict | None = None, data: dict | None = None) -> None:
        self.status_code = status_code
        self.headers = headers or {}
        self._data = data or {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self) -> dict:
        return self._data


def _fake_client_factory(responder):
    """Build a stand-in for httpx.AsyncClient whose .get() returns responder(call_index)."""
    state = {"calls": 0}

    class _Client:
        def __init__(self, **_kw) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_a):
            return False

        async def get(self, _url, params=None):  # noqa: ARG002
            state["calls"] += 1
            return responder(state["calls"])

    return _Client, state


@pytest.mark.parametrize(
    ("internal", "yahoo"),
    [
        ("AAPL", "AAPL"),
        ("^GSPC", "^GSPC"),
        ("BTC", "BTC-USD"),
        ("ETH", "ETH-USD"),
        ("RELIANCE.NSE", "RELIANCE.NS"),   # our .NSE -> Yahoo .NS
        ("HDFC.BSE", "HDFC.BO"),           # our .BSE -> Yahoo .BO
        ("VOD.L", "VOD.L"),                 # unchanged
        ("7203.T", "7203.T"),               # unchanged
    ],
)
def test_to_yahoo_symbol(internal, yahoo):
    assert to_yahoo_symbol(internal) == yahoo


def test_range_for_buckets():
    assert _range_for(3) == "5d"
    assert _range_for(30) == "1mo"
    assert _range_for(200) == "1y"
    assert _range_for(1000) == "5y"


async def test_quote_degrades_to_unavailable_on_error(monkeypatch):
    p = YahooMarketDataProvider()

    async def boom(url, params):
        raise RuntimeError("rate limited (429)")

    monkeypatch.setattr(p, "_get", boom)
    q = await p.get_quote("^GSPC")
    assert q.price is None
    assert q.entitlement.value == "unavailable"  # honest, never fabricated


# --- F6: provider 429 hardening (Retry-After + cooldown + honest-stale FX) -----------

async def test_fx_unavailable_is_honest_stale_not_mock(monkeypatch):
    """F6 behaviour 3: a failed Yahoo FX lookup returns an honest-stale marker (rate 0,
    is_stale) — NOT a fabricated mock rate — so fx.get_rate falls to the ECB reference."""
    p = YahooMarketDataProvider()

    async def boom(url, params):
        raise RuntimeError("429")

    monkeypatch.setattr(p, "_get", boom)
    fx = await p.get_fx_rate("USD", "SGD")
    assert fx.rate == 0
    assert fx.is_stale is True
    assert fx.source == "yahoo"  # honest provenance, no silent mock substitution


async def test_get_honours_retry_after_on_429(monkeypatch):
    """F6 behaviour 1: a 429 with Retry-After backs off by that (capped) delay before retry."""
    p = YahooMarketDataProvider()
    p._min_interval = 0.0  # ignore pacing so only the Retry-After delay is recorded
    sleeps: list[float] = []

    async def fake_sleep(secs):
        sleeps.append(secs)

    monkeypatch.setattr(yahoo_mod.asyncio, "sleep", fake_sleep)

    def responder(n):
        if n == 1:
            return _FakeResp(429, {"Retry-After": "7"})
        return _FakeResp(200, data={"ok": True})

    client_cls, _state = _fake_client_factory(responder)
    monkeypatch.setattr(yahoo_mod.httpx, "AsyncClient", client_cls)

    data = await p._get("http://x", {})
    assert data == {"ok": True}
    assert 7 in sleeps  # honoured the server's Retry-After, not the default linear backoff


async def test_provider_cools_down_after_consecutive_429s(monkeypatch):
    """F6 behaviour 2: after K consecutive 429s the provider trips a cooldown and skips the
    network entirely — a subsequent call raises without issuing a new HTTP request."""
    p = YahooMarketDataProvider()
    p._min_interval = 0.0

    async def fake_sleep(_secs):
        return None

    monkeypatch.setattr(yahoo_mod.asyncio, "sleep", fake_sleep)

    def responder(_n):
        return _FakeResp(429)  # always rate-limited

    client_cls, state = _fake_client_factory(responder)
    monkeypatch.setattr(yahoo_mod.httpx, "AsyncClient", client_cls)

    with pytest.raises(RuntimeError):
        await p._get("http://x", {})  # 3 consecutive 429s → trips the breaker
    assert p._cooldown_until > 0
    hits = state["calls"]

    with pytest.raises(RuntimeError):
        await p._get("http://x", {})  # in cooldown → must NOT touch the network
    assert state["calls"] == hits  # no new HTTP call while cooling down


async def test_streak_resets_on_success(monkeypatch):
    """A clean response ends the 429 streak so a later single 429 doesn't inherit it."""
    p = YahooMarketDataProvider()
    p._min_interval = 0.0

    async def fake_sleep(_secs):
        return None

    monkeypatch.setattr(yahoo_mod.asyncio, "sleep", fake_sleep)

    def responder(n):
        # 429, then a clean 200 (resets the streak, lifts any cooldown).
        return _FakeResp(429) if n == 1 else _FakeResp(200, data={"ok": True})

    client_cls, _state = _fake_client_factory(responder)
    monkeypatch.setattr(yahoo_mod.httpx, "AsyncClient", client_cls)

    assert await p._get("http://x", {}) == {"ok": True}
    assert p._consecutive_429 == 0
    assert p._cooldown_until == 0.0
