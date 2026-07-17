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
