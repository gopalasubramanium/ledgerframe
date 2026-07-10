# SPDX-License-Identifier: AGPL-3.0-or-later
"""C-3 acceptance: /system/version-check makes ZERO outbound calls under no-egress.

page-chrome C-3 / SECURITY-BASELINE §7 / D-075: with the no-egress toggle
(``privacy_mode``) on, the device must not reach the internet at all — the version
check included. This is the network-trace acceptance test: we spy on
``httpx.AsyncClient`` and assert it is never constructed while no-egress is on.
"""

from __future__ import annotations

import httpx


def _install_client_spy(monkeypatch) -> list[int]:
    """Replace httpx.AsyncClient with a spy that records each construction (an
    outbound attempt) and then raises, so no REAL network call is ever made in the
    test suite. version-check wraps its HTTP use in try/except, so the raise is
    swallowed and the endpoint still returns a normal body."""
    constructions: list[int] = []

    class _SpyClient:
        def __init__(self, *args, **kwargs):
            constructions.append(1)
            raise RuntimeError("blocked outbound call in test")

    monkeypatch.setattr(httpx, "AsyncClient", _SpyClient)
    return constructions


async def test_version_check_zero_outbound_under_no_egress(app_client, monkeypatch):
    from app.db.base import get_sessionmaker
    from app.models import Setting

    # Enable no-egress (privacy_mode) in the same DB the app reads.
    async with get_sessionmaker()() as s:
        s.add(Setting(key="privacy_mode", value="true"))
        await s.commit()

    constructions = _install_client_spy(monkeypatch)

    r = await app_client.get("/api/v1/system/version-check")
    assert r.status_code == 200
    body = r.json()

    # Zero outbound calls, and an honest "up to date".
    assert constructions == [], "version-check attempted an outbound call under no-egress"
    assert body["update_available"] is False
    assert body["latest"] == body["current"]


async def test_version_check_attempts_outbound_when_egress_allowed(app_client, monkeypatch):
    """Sanity foil: with no-egress OFF, the check DOES construct the HTTP client
    (so the zero-count above is meaningful, not vacuous). The spy blocks the real
    network, so no GitHub call actually leaves the suite."""
    constructions = _install_client_spy(monkeypatch)

    r = await app_client.get("/api/v1/system/version-check")
    assert r.status_code == 200
    assert constructions, "version-check should attempt an outbound call when egress is allowed"
