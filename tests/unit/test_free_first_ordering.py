# SPDX-License-Identifier: AGPL-3.0-or-later
"""R-63 Phase 3 — free-first chain ordering (§9-6): free/keyless sources precede key-gated/paid
ones within capability, so no core price REQUIRES payment. The HEAD (override/matrix/active) still
wins over free-first — that pair is proven in test_execution_net.py."""

from __future__ import annotations

from app.providers.market.router import DEFAULT_PRIORITY, capabilities_for

# Free LIVE market sources (keyless). csv is keyless too but a LOCAL import fallback, not a live
# source, so it is excluded from the "free live source leads" assertions.
_KEYLESS_LIVE = {"yahoo", "coingecko", "ecb_fx", "amfi_nav"}
_PAID = {"alphavantage", "eodhd", "kite"}
_TERMINAL = {"manual", "statement", "accrual", "cache", "csv"}


def test_no_paid_source_precedes_a_capable_free_live_source():
    """§9-6: in every lane, no paid/keyed provider comes before the first free/keyless live source."""
    for lane, chain in DEFAULT_PRIORITY.items():
        first_paid = next((i for i, p in enumerate(chain) if p in _PAID), None)
        first_free = next((i for i, p in enumerate(chain) if p in _KEYLESS_LIVE), None)
        if first_paid is not None and first_free is not None:
            assert first_free < first_paid, (
                f"{lane}: paid '{chain[first_paid]}' precedes free '{chain[first_free]}' — not free-first")


def test_ruled_us_equity_pattern():
    """The exact pattern the owner ruled at the §9 one-pass."""
    assert DEFAULT_PRIORITY["us_equity"] == ["yahoo", "alphavantage", "eodhd", "csv", "manual"]


def test_core_market_lanes_lead_with_a_keyless_source():
    """Core function never requires payment: the first live (non-terminal, non-csv) source in each
    core market lane is keyless."""
    for lane in ("us_equity", "sg_equity", "in_equity", "crypto", "fx", "global_fund"):
        first_live = next(p for p in DEFAULT_PRIORITY[lane] if p not in _TERMINAL)
        assert not capabilities_for(first_live).needs_key, (
            f"{lane} leads with a paid source '{first_live}' — a core price would require a key")
