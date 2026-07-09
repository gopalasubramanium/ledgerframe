# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 4: ECB reference-FX API — refresh from fixture, status, and the FX
conversion diagnostic (records direct/inverse/triangulated). No network."""

from __future__ import annotations

from pathlib import Path

FIXTURE = (Path(__file__).parents[1] / "fixtures" / "ecb_eurofxref_daily.xml").read_bytes()


def _file():
    return {"file": ("eurofxref-daily.xml", FIXTURE, "application/xml")}


async def test_ecb_refresh_status_and_convert(app_client):
    r = await app_client.post("/api/v1/fx/ecb/refresh", files=_file())
    assert r.status_code == 200
    assert r.json()["currencies"] == 6 and r.json()["as_of"] == "2026-07-03"  # +EUR

    st = (await app_client.get("/api/v1/fx/ecb/status")).json()
    assert st["currencies"] == 6 and st["as_of"] == "2026-07-03"

    # Direct (EUR base).
    d = (await app_client.get("/api/v1/fx/convert", params={"from": "EUR", "to": "USD"})).json()
    assert d["ecb_method"] == "direct" and abs(d["ecb_rate"] - 1.0850) < 1e-6

    # Triangulated cross.
    t = (await app_client.get("/api/v1/fx/convert", params={"from": "USD", "to": "SGD"})).json()
    assert t["ecb_method"] == "triangulated" and t["ecb_rate"] is not None
    assert t["source"] == "ecb_reference"

    # Unknown currency → reference unavailable (provider still gives an effective rate).
    u = (await app_client.get("/api/v1/fx/convert", params={"from": "USD", "to": "INR"})).json()
    assert u["ecb_method"] == "triangulated"  # INR is in the fixture
