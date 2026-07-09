# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 4: EODHD adapter — symbol mapping + parsers. Deterministic, fixture-driven;
the network methods are never exercised here."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from app.providers.market.eodhd import (
    EodhdProvider,
    parse_eod,
    parse_search,
    realtime_to_quote,
    to_eodhd_symbol,
)
from app.schemas.common import EntitlementStatus

_FX = Path(__file__).parents[1] / "fixtures"


def test_symbol_mapping_across_venues():
    assert to_eodhd_symbol("AAPL") == "AAPL.US"
    assert to_eodhd_symbol("AAPL", "NASDAQ") == "AAPL.US"
    assert to_eodhd_symbol("RELIANCE.NSE") == "RELIANCE.NSE"
    assert to_eodhd_symbol("HDFCBANK.BSE") == "HDFCBANK.BSE"
    assert to_eodhd_symbol("D05.SI") == "D05.SG"        # SGX suffix mapped
    assert to_eodhd_symbol("VOD.L") == "VOD.LSE"
    assert to_eodhd_symbol("7203.T") == "7203.TSE"
    assert to_eodhd_symbol("BTC") == "BTC-USD.CC"
    assert to_eodhd_symbol("^GSPC") == "GSPC.INDX"


def test_realtime_to_quote_and_unavailable():
    data = json.loads((_FX / "eodhd_realtime.json").read_text())
    q = realtime_to_quote(data, "AAPL", None)
    assert q.price == Decimal("211.75")
    assert q.previous_close == Decimal("209.90")
    assert q.entitlement is EntitlementStatus.DELAYED
    assert q.currency == "USD"
    assert q.change_pct is not None and abs(q.change_pct - Decimal("0.8813")) < Decimal("0.01")

    # A missing/NA close is unavailable — never fabricated.
    na = realtime_to_quote({"code": "X.US", "close": "NA"}, "X", None)
    assert na.price is None and na.entitlement is EntitlementStatus.UNAVAILABLE


def test_parse_eod():
    candles = parse_eod(json.loads((_FX / "eodhd_eod.json").read_text()))
    assert len(candles) == 2
    assert candles[-1].close == Decimal("211.75")
    assert candles[0].volume == Decimal("40000000")


def test_parse_search_maps_type_and_venue():
    results = parse_search(json.loads((_FX / "eodhd_search.json").read_text()))
    by_name = {i.name: i for i in results}
    assert by_name["Apple Inc"].symbol == "AAPL"           # US → bare ticker
    assert by_name["Apple Inc"].asset_class == "equity"
    r = by_name["Reliance Industries Ltd"]
    assert r.symbol == "RELIANCE.NSE" and r.currency == "INR"


def test_provider_requires_key():
    with pytest.raises(ValueError):
        EodhdProvider("eodhd", "")
    p = EodhdProvider("eodhd", "fake-key")     # constructs; no network call
    assert p.name == "eodhd" and p.fetch_on_demand is False
