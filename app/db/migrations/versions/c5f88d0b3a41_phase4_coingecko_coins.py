# SPDX-License-Identifier: AGPL-3.0-or-later
"""phase 4: coingecko coin master

Additive only — creates the ``coingecko_coins`` table. Idempotent (create_all may
have made it already on a fresh install).

Revision ID: c5f88d0b3a41
Revises: b4e77c9a1f22
Create Date: 2026-07-03
"""
import sqlalchemy as sa
from alembic import op

import app.db.base  # noqa: F401 — registers DecimalText

revision = "c5f88d0b3a41"
down_revision = "b4e77c9a1f22"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if "coingecko_coins" in sa.inspect(bind).get_table_names():
        return
    op.create_table(
        "coingecko_coins",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("symbol", sa.String(30), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("market_cap_usd", app.db.base.DecimalText(), nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_coingecko_symbol", "coingecko_coins", ["symbol"])
    op.create_index("ix_coingecko_name", "coingecko_coins", ["name"])


def downgrade() -> None:
    op.drop_table("coingecko_coins")
