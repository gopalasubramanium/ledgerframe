# SPDX-License-Identifier: AGPL-3.0-or-later
"""R-38: provider routing matrix

Additive only — creates the ``routing_matrix`` table (one provider per asset-class ×
listing-country cell; data-feed-routing §5/§9). Idempotent (create_all may have made
it already on a fresh install). Full downgrade drops the table (the drop-migration
precedent, ADR-0001).

Revision ID: c1d4e7a90f38
Revises: b3e2f1a9c740
Create Date: 2026-07-18
"""
import sqlalchemy as sa
from alembic import op

import app.db.base  # noqa: F401 — registers custom column types

revision = "c1d4e7a90f38"
down_revision = "b3e2f1a9c740"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if "routing_matrix" in sa.inspect(bind).get_table_names():
        return
    op.create_table(
        "routing_matrix",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("asset_class", sa.String(20), nullable=False),
        sa.Column("listing_country", sa.String(8), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=True),
        sa.UniqueConstraint("asset_class", "listing_country", name="uq_routing_matrix_cell"),
    )


def downgrade() -> None:
    op.drop_table("routing_matrix")
