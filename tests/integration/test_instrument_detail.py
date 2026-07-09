# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 5c: per-asset instrument detail — adapter-linked facts on the detail view."""

from __future__ import annotations


async def test_crypto_detail_shows_canonical_coingecko_id(app_client):
    d = (await app_client.get("/api/v1/instruments/BTC")).json()
    meta = d["instrument"]
    assert "asset_detail" in meta
    crypto = meta["asset_detail"].get("crypto")
    assert crypto and crypto["coingecko_id"] == "bitcoin"      # canonical id, not bare symbol
    assert crypto["market_cap_usd"] is not None
    # The coingecko_id identifier is surfaced too.
    assert any(i["id_type"] == "coingecko_id" and i["value"] == "bitcoin" for i in meta["identifiers"])


async def test_equity_detail_has_empty_adapter_block(app_client):
    d = (await app_client.get("/api/v1/instruments/AAPL")).json()
    # No adapter linked → asset_detail present but empty (never fabricated).
    assert d["instrument"]["asset_detail"] == {}
