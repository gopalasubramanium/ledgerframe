# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 4: Kite adapter — parsers, symbol mapping, and the READ-ONLY security guard
(no order/trading endpoint is reachable). Deterministic; no network."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from app.providers.market.kite import (
    _ALLOWED_PREFIXES,
    KiteProvider,
    _is_allowed,
    parse_instruments_csv,
    parse_quote,
    to_kite_symbol,
)
from app.schemas.common import EntitlementStatus

CSV = (Path(__file__).parents[1] / "fixtures" / "kite_instruments.csv").read_text()


def test_parse_instruments_master_including_fno():
    by_sym = {i.tradingsymbol: i for i in parse_instruments_csv(CSV)}
    assert len(by_sym) == 6
    eq = by_sym["INFY"]
    assert eq.instrument_type == "EQ" and eq.exchange == "NSE" and eq.lot_size == 1
    opt = by_sym["NIFTY26JUL25000CE"]
    assert opt.instrument_type == "CE" and opt.expiry == "2026-07-31"
    assert opt.strike == 25000 and opt.lot_size == 50 and opt.segment == "NFO-OPT"
    fut = by_sym["GOLD26AUGFUT"]
    assert fut.instrument_type == "FUT" and fut.exchange == "MCX" and fut.lot_size == 100


def test_symbol_mapping():
    assert to_kite_symbol("RELIANCE.NSE") == "NSE:RELIANCE"
    assert to_kite_symbol("HDFCBANK.BSE") == "BSE:HDFCBANK"
    assert to_kite_symbol("INFY") == "NSE:INFY"
    assert to_kite_symbol("NIFTY26JULFUT.NFO") == "NFO:NIFTY26JULFUT"
    assert to_kite_symbol("GOLD26AUGFUT.MCX") == "MCX:GOLD26AUGFUT"
    assert to_kite_symbol("NSE:INFY") == "NSE:INFY"          # already qualified


def test_parse_quote_and_unavailable():
    q = parse_quote({"last_price": 1500.5, "ohlc": {"close": 1490.0}}, "INFY.NSE", "NSE")
    assert q.price == Decimal("1500.5") and q.previous_close == Decimal("1490")
    assert q.entitlement is EntitlementStatus.DELAYED and q.currency == "INR"
    na = parse_quote({"last_price": 0}, "X.NSE", "NSE")
    assert na.price is None and na.entitlement is EntitlementStatus.UNAVAILABLE


def test_requires_credentials():
    with pytest.raises(ValueError):
        KiteProvider("", "")
    p = KiteProvider("api-key", "access-token")
    assert p.name == "kite"


async def test_order_and_trading_endpoints_are_refused():
    # The allow-list is READ-ONLY market data only — no trading terms anywhere.
    banned = ("order", "gtt", "position", "holding", "margin", "fund", "trades")
    for pre in _ALLOWED_PREFIXES:
        assert not any(b in pre for b in banned), pre
    # Read-only endpoints allowed; anything else refused.
    assert _is_allowed("quote") and _is_allowed("quote?i=NSE:INFY") and _is_allowed("instruments")
    for forbidden in ("orders", "orders/regular", "gtt/triggers", "portfolio/holdings",
                      "portfolio/positions", "user/margins", "user/profile"):
        assert _is_allowed(forbidden) is False

    p = KiteProvider("api-key", "access-token")
    with pytest.raises(ValueError):
        await p._get("orders")            # guard trips BEFORE any network call
    with pytest.raises(ValueError):
        await p._get("portfolio/positions")
