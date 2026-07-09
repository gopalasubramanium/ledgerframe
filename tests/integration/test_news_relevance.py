# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 5 — news relevance scoring (My holdings ranked by weight × recency)."""

from __future__ import annotations


async def test_my_holdings_news_ranked_by_relevance(app_client):
    d = (await app_client.get("/api/v1/news/grouped")).json()
    mine = next((g for g in d["groups"] if g["name"] == "My holdings"), None)
    assert mine is not None and mine["items"], "expected held-symbol news in the demo"
    assert all("relevance" in it for it in mine["items"])
    rels = [it["relevance"] for it in mine["items"]]
    assert rels == sorted(rels, reverse=True)          # most relevant first
    assert max(rels) > 0                                # an actual holding scores > 0
