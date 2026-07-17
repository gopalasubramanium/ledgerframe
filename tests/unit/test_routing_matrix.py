# SPDX-License-Identifier: AGPL-3.0-or-later
"""R-38 provider routing matrix (data-feed-routing §5/§9-RESOLVED).

Delta 1 (this block): the ``routing_matrix`` persisted model + additive migration.
The RED cause here is the **missing table/model**, not a missing endpoint — a
migration delta must fail-first on the table it introduces.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

# Import at module scope so the model registers on Base.metadata at collection time —
# before the `session` fixture's create_all runs (the repo convention, cf. test_router).
from app.models import RoutingMatrix


async def test_routing_matrix_cell_round_trips(session):
    """A cell (asset_class × listing_country → provider) persists and reads back."""
    session.add(RoutingMatrix(asset_class="equity", listing_country="US", provider="eodhd"))
    await session.flush()

    row = (
        await session.execute(
            select(RoutingMatrix).where(
                RoutingMatrix.asset_class == "equity",
                RoutingMatrix.listing_country == "US",
            )
        )
    ).scalars().one()
    assert row.provider == "eodhd"
    assert row.updated_at is not None


async def test_routing_matrix_cell_is_unique_per_class_country(session):
    """One provider per (asset_class, listing_country) — the unique cell constraint."""
    from sqlalchemy.exc import IntegrityError

    session.add(RoutingMatrix(asset_class="equity", listing_country="US", provider="eodhd"))
    await session.flush()
    session.add(RoutingMatrix(asset_class="equity", listing_country="US", provider="yahoo"))
    with pytest.raises(IntegrityError):
        await session.flush()


async def test_wildcard_country_cell_is_allowed(session):
    """``"*"`` is a valid listing_country (mirrors CAPABILITIES.regions)."""
    session.add(RoutingMatrix(asset_class="crypto", listing_country="*", provider="coingecko"))
    await session.flush()
    row = (await session.execute(select(RoutingMatrix))).scalars().one()
    assert row.listing_country == "*"


# --- Delta 2: CRUD endpoints + edit-time validation (§9-3/§9-7) -----------------
# RED cause here is the missing ENDPOINT (404), not the table.

_MATRIX = "/api/v1/system/routing-matrix"


async def test_put_then_get_round_trips_a_cell(app_client):
    """PUT upserts a cell; GET lists it back (served labels + degraded flag)."""
    r = await app_client.put(_MATRIX, json={
        "asset_class": "equity", "listing_country": "US", "provider": "yahoo"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["cell"]["provider"] == "yahoo"
    assert body["cell"]["degraded"] is False       # yahoo is keyless

    g = await app_client.get(_MATRIX)
    assert g.status_code == 200
    cells = g.json()["cells"]
    assert any(c["asset_class"] == "equity" and c["listing_country"] == "US"
               and c["provider"] == "yahoo" for c in cells)


async def test_put_is_idempotent_upsert_one_provider_per_cell(app_client):
    """A second PUT on the same cell replaces the provider (unique cell)."""
    await app_client.put(_MATRIX, json={
        "asset_class": "equity", "listing_country": "US", "provider": "yahoo"})
    await app_client.put(_MATRIX, json={
        "asset_class": "equity", "listing_country": "US", "provider": "mock"})
    cells = (await app_client.get(_MATRIX)).json()["cells"]
    us_equity = [c for c in cells if c["asset_class"] == "equity" and c["listing_country"] == "US"]
    assert len(us_equity) == 1 and us_equity[0]["provider"] == "mock"


async def test_put_unknown_source_is_a_400(app_client):
    r = await app_client.put(_MATRIX, json={
        "asset_class": "equity", "listing_country": "US", "provider": "bloomberg"})
    assert r.status_code == 400
    assert "unknown source" in r.json()["detail"].lower()


async def test_put_capability_class_mismatch_is_an_honest_400(app_client):
    """csv can't price crypto → honest 400 (§9-3)."""
    r = await app_client.put(_MATRIX, json={
        "asset_class": "crypto", "listing_country": "US", "provider": "csv"})
    assert r.status_code == 400
    assert "csv" in r.json()["detail"] and "crypto" in r.json()["detail"]


async def test_put_capability_region_mismatch_is_an_honest_400(app_client):
    """kite is IN-only → can't cover US (§9-3)."""
    r = await app_client.put(_MATRIX, json={
        "asset_class": "equity", "listing_country": "US", "provider": "kite"})
    assert r.status_code == 400
    assert "kite" in r.json()["detail"] and "US" in r.json()["detail"]


async def test_put_capable_but_unkeyed_is_accept_with_caveat(app_client):
    """eodhd is capable for US equity but needs a key; with none set the cell is
    ACCEPTED and shown degraded with a caveat — never a silent dead cell (§9-7)."""
    r = await app_client.put(_MATRIX, json={
        "asset_class": "equity", "listing_country": "US", "provider": "eodhd"})
    assert r.status_code == 200, r.text
    cell = r.json()["cell"]
    assert cell["degraded"] is True
    assert "credentials" in (cell["caveat"] or "").lower()
    # It really is stored (accept, not reject).
    cells = (await app_client.get(_MATRIX)).json()["cells"]
    assert any(c["provider"] == "eodhd" for c in cells)


async def test_put_unknown_asset_class_is_a_400(app_client):
    r = await app_client.put(_MATRIX, json={
        "asset_class": "unicorn", "listing_country": "US", "provider": "yahoo"})
    assert r.status_code == 400


async def test_delete_clears_a_cell_and_is_idempotent(app_client):
    """DELETE removes the cell; a second DELETE is a clean no-op. Shape-discriminated:
    a real JSON body with ``deleted`` — not a status-only check (SPA serves 200 HTML)."""
    await app_client.put(_MATRIX, json={
        "asset_class": "equity", "listing_country": "US", "provider": "yahoo"})
    d1 = await app_client.delete(f"{_MATRIX}/equity/US")
    assert d1.status_code == 200 and d1.json()["deleted"] is True
    d2 = await app_client.delete(f"{_MATRIX}/equity/US")
    assert d2.status_code == 200 and d2.json()["deleted"] is False
    cells = (await app_client.get(_MATRIX)).json()["cells"]
    assert not any(c["asset_class"] == "equity" and c["listing_country"] == "US" for c in cells)


async def test_delete_wildcard_country_cell(app_client):
    """A ``"*"`` cell is addressable for deletion (the '*' path segment)."""
    await app_client.put(_MATRIX, json={
        "asset_class": "crypto", "listing_country": "*", "provider": "coingecko"})
    d = await app_client.delete(f"{_MATRIX}/crypto/*")
    assert d.status_code == 200 and d.json()["deleted"] is True
