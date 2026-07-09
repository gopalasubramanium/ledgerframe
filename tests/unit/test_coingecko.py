# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 4: CoinGecko parser — canonical ids, symbol collisions, multi-currency,
and unavailable (zero) prices. Deterministic, fixture-driven."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from app.providers.market.coingecko import parse_coins_list, parse_simple_price

_FX = Path(__file__).parents[1] / "fixtures"
COINS = json.loads((_FX / "coingecko_coins_list.json").read_text())
PRICES = json.loads((_FX / "coingecko_simple_price.json").read_text())


def test_symbol_collision_kept_distinct_by_canonical_id():
    coins = parse_coins_list(COINS)
    by_id = {c.id: c for c in coins}
    # Two different canonical ids share the symbol "btc" — never merged.
    btc_ids = {c.id for c in coins if c.symbol == "btc"}
    assert btc_ids == {"bitcoin", "binance-peg-bitcoin"}
    assert by_id["bitcoin"].name == "Bitcoin"
    assert by_id["binance-peg-bitcoin"].name == "Binance-Peg Bitcoin"


def test_simple_price_multi_currency_and_unavailable():
    prices = parse_simple_price(PRICES)
    btc = prices["bitcoin"]
    assert btc.prices["usd"] == Decimal("68000.5")
    assert btc.prices["sgd"] == Decimal("92000.1")
    assert btc.prices["inr"] == Decimal("5680000.0")
    assert btc.market_cap_usd == Decimal("1340000000000.0")
    assert btc.last_updated is not None
    # Solana is all-zero in the fixture → no prices (unavailable), never fabricated.
    assert prices["solana"].prices == {}
