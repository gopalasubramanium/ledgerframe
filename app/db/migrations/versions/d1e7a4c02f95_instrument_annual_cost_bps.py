# SPDX-License-Identifier: AGPL-3.0-or-later
"""instrument ongoing-cost — instruments.annual_cost_bps (§4.6 Unit A)

Additive, idempotent, schema-only. Adds a nullable ``annual_cost_bps`` column (basis points)
to instruments — the fund's expense ratio, a property of the instrument, not the lot, so it is
never touched by the holdings rebuild. NULLABLE with NO server_default and NO backfill: null
means 'not set' (NOT zero — zero would be a fabricated fact). Nothing reads it yet — the
cost-of-ownership reader is Unit B.

Revision ID: d1e7a4c02f95
Revises: c9a1e4f78b62
Create Date: 2026-07-08
"""
import sqlalchemy as sa
from alembic import op

import app.db.base  # noqa: F401 — registers the DecimalText custom column type

revision = "d1e7a4c02f95"
down_revision = "c9a1e4f78b62"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent: fresh DBs are create_all-bootstrapped (column already present), so add it only
    # if missing on databases adopted into Alembic. Nullable with no server_default — existing
    # instruments keep annual_cost_bps NULL ('not set'), never backfilled to a fabricated 0.
    bind = op.get_bind()
    cols = {c["name"] for c in sa.inspect(bind).get_columns("instruments")}
    if "annual_cost_bps" not in cols:
        with op.batch_alter_table("instruments") as batch:
            batch.add_column(sa.Column("annual_cost_bps", app.db.base.DecimalText(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("instruments") as batch:
        batch.drop_column("annual_cost_bps")
