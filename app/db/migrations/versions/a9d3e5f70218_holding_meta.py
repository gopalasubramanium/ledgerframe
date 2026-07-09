# SPDX-License-Identifier: AGPL-3.0-or-later
"""holding.meta — optional per-asset metadata (JSON)

Additive, nullable, idempotent. Holds optional structured detail for manual assets
(fixed deposit, bond, property, retirement, insurance, private) without complicating
the simple "just a value" flow.

Revision ID: a9d3e5f70218
Revises: f8c2a1b3d704
Create Date: 2026-07-03
"""
import sqlalchemy as sa
from alembic import op

revision = "a9d3e5f70218"
down_revision = "f8c2a1b3d704"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    cols = {c["name"] for c in sa.inspect(bind).get_columns("holdings")}
    if "meta" not in cols:
        op.add_column("holdings", sa.Column("meta", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("holdings", "meta")
