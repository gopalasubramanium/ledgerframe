# SPDX-License-Identifier: AGPL-3.0-or-later
"""phase 4: kite instrument master

Additive only — creates the ``kite_instruments`` table. Idempotent.

Revision ID: e7b1a2c4d905
Revises: d6a99e1c2b73
Create Date: 2026-07-03
"""
import sqlalchemy as sa
from alembic import op

import app.db.base  # noqa: F401 — registers DecimalText

revision = "e7b1a2c4d905"
down_revision = "d6a99e1c2b73"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if "kite_instruments" in sa.inspect(bind).get_table_names():
        return
    op.create_table(
        "kite_instruments",
        sa.Column("instrument_token", sa.Integer, primary_key=True),
        sa.Column("exchange", sa.String(12), nullable=False),
        sa.Column("tradingsymbol", sa.String(60), nullable=False),
        sa.Column("name", sa.String(120), nullable=True),
        sa.Column("segment", sa.String(20), nullable=True),
        sa.Column("instrument_type", sa.String(6), nullable=True),
        sa.Column("lot_size", sa.Integer, nullable=True),
        sa.Column("expiry", sa.String(12), nullable=True),
        sa.Column("strike", app.db.base.DecimalText(), nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_kite_exchange", "kite_instruments", ["exchange"])
    op.create_index("ix_kite_tradingsymbol", "kite_instruments", ["tradingsymbol"])


def downgrade() -> None:
    op.drop_table("kite_instruments")
