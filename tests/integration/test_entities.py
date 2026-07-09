# SPDX-License-Identifier: AGPL-3.0-or-later
"""§4.7 Unit A — GET /entities list reader.

Metadata enumeration only (id · name · kind), for the quarterly pack's per-entity sections —
no valuation, no recompute. One vector proves the route wiring/shape, one proves it lists the
seeded entities deterministically.
"""

from __future__ import annotations

from app.models import Entity
from app.services.accounts import list_entities


async def test_entities_endpoint_shape(app_client):
    r = await app_client.get("/api/v1/entities")
    assert r.status_code == 200
    entities = r.json()["entities"]
    assert isinstance(entities, list)
    # Metadata only — each item is exactly {id, name, kind}, no valuation/figure leaks.
    for e in entities:
        assert set(e) == {"id", "name", "kind"}
        assert isinstance(e["id"], int) and e["name"] and e["kind"]


async def test_list_entities_lists_seeded_sorted_by_name(session):
    session.add_all([
        Entity(name="Spouse", kind="spouse"),
        Entity(name="Household", kind="self"),
        Entity(name="Family Trust", kind="trust"),
    ])
    await session.flush()

    rows = await list_entities(session)
    assert [r["name"] for r in rows] == ["Family Trust", "Household", "Spouse"]   # ordered by name
    assert [r["kind"] for r in rows] == ["trust", "self", "spouse"]
    assert all(set(r) == {"id", "name", "kind"} for r in rows)                    # metadata only
    assert all(isinstance(r["id"], int) for r in rows)
