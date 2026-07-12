# SPDX-License-Identifier: AGPL-3.0-or-later
"""ND-2 acceptance: the News readers make ZERO outbound calls under no-egress.

page-news ND-2 / SECURITY-BASELINE §7 / D-075 / Product Guarantee 5: with the no-egress
toggle (``privacy_mode``) on, news fetching (RSS + provider) must make ZERO outbound
calls — the page shows an honest empty-with-reason instead of fabricating headlines.
This mirrors the C-3 ``system/version-check`` network-trace test: spy on
``httpx.AsyncClient`` and assert it is never constructed while no-egress is on (and IS
constructed when egress is allowed, so the zero-count is not vacuous).
"""

from __future__ import annotations

import httpx


def _install_client_spy(monkeypatch) -> list[int]:
    """Replace httpx.AsyncClient with a spy that records each construction (an outbound
    attempt) and then raises, so no REAL network call leaves the suite. fetch_feeds wraps
    its client use so the raise is swallowed and the endpoint still returns a normal body."""
    constructions: list[int] = []

    class _SpyClient:
        def __init__(self, *args, **kwargs):
            constructions.append(1)
            raise RuntimeError("blocked outbound call in test")

    monkeypatch.setattr(httpx, "AsyncClient", _SpyClient)
    return constructions


async def test_news_grouped_zero_outbound_under_no_egress(app_client, monkeypatch):
    from app.db.base import get_sessionmaker
    from app.models import Setting

    async with get_sessionmaker()() as s:
        s.add(Setting(key="privacy_mode", value="true"))
        await s.commit()

    constructions = _install_client_spy(monkeypatch)

    r = await app_client.get("/api/v1/news/grouped")
    assert r.status_code == 200
    body = r.json()

    # Zero outbound calls, and an honest no-egress flag the page renders its reason from.
    assert constructions == [], "news/grouped attempted an outbound call under no-egress"
    assert body["no_egress"] is True
    assert body["groups"] == []


async def test_news_grouped_attempts_outbound_when_egress_allowed(app_client, monkeypatch):
    """Sanity foil: with no-egress OFF, the reader DOES construct the RSS client (so the
    zero-count above is meaningful). The spy blocks the real network, so nothing leaves."""
    constructions = _install_client_spy(monkeypatch)

    r = await app_client.get("/api/v1/news/grouped")
    assert r.status_code == 200
    assert r.json()["no_egress"] is False
    assert constructions, "news/grouped should attempt an outbound RSS call when egress is allowed"
