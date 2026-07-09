# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 1.8 — RFC 9116 security.txt is served."""

from __future__ import annotations


async def test_security_txt_served(app_client):
    r = await app_client.get("/.well-known/security.txt")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    body = r.text
    assert "Contact:" in body and "Expires:" in body and "Policy:" in body
