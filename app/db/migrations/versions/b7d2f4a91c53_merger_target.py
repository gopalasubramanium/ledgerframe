# SPDX-License-Identifier: AGPL-3.0-or-later
"""merger target — transactions.related_instrument_id (§4.3 Unit 2a)

Additive, idempotent, schema-only. Adds a nullable ``related_instrument_id`` FK to
transactions: for a MERGER transaction it references the target instrument B that this
instrument is absorbed into (the price field carries the merger ratio). NULL for every
other transaction kind. Nothing reads it yet — the merger lot-transfer logic is Unit 2b.

Revision ID: b7d2f4a91c53
Revises: a1c8f34b9d62
Create Date: 2026-07-07
"""
import sqlalchemy as sa
from alembic import op

revision = "b7d2f4a91c53"
down_revision = "a1c8f34b9d62"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent: fresh DBs are create_all-bootstrapped (column already present), so add it
    # only if missing on databases adopted into Alembic. No backfill — NULL on existing rows.
    bind = op.get_bind()
    cols = {c["name"] for c in sa.inspect(bind).get_columns("transactions")}
    if "related_instrument_id" not in cols:
        with op.batch_alter_table("transactions") as batch:
            batch.add_column(sa.Column("related_instrument_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("transactions") as batch:
        batch.drop_column("related_instrument_id")
