# SPDX-License-Identifier: AGPL-3.0-or-later
"""cost-basis method — accounts.cost_basis_method (§4.4 Unit A)

Additive, idempotent, schema-only. Adds a ``cost_basis_method`` column to accounts,
defaulting to ``"fifo"``. The NOT NULL + server_default backfills every existing account to
"fifo", so the current (FIFO) behaviour and every figure are byte-identical. Nothing reads
it yet — the average-cost engine branch is Unit B.

Revision ID: c9a1e4f78b62
Revises: b7d2f4a91c53
Create Date: 2026-07-08
"""
import sqlalchemy as sa
from alembic import op

revision = "c9a1e4f78b62"
down_revision = "b7d2f4a91c53"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent: fresh DBs are create_all-bootstrapped (column already present), so add it
    # only if missing on databases adopted into Alembic. NOT NULL + server_default "fifo"
    # backfills every existing account to FIFO (no separate UPDATE needed).
    bind = op.get_bind()
    cols = {c["name"] for c in sa.inspect(bind).get_columns("accounts")}
    if "cost_basis_method" not in cols:
        with op.batch_alter_table("accounts") as batch:
            batch.add_column(sa.Column("cost_basis_method", sa.String(length=16),
                                       nullable=False, server_default="fifo"))


def downgrade() -> None:
    with op.batch_alter_table("accounts") as batch:
        batch.drop_column("cost_basis_method")
