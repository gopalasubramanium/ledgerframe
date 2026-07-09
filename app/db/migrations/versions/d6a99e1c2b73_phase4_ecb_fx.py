# SPDX-License-Identifier: AGPL-3.0-or-later
"""phase 4: ecb reference fx cache

Additive only — creates the ``ecb_fx_rates`` table. Idempotent.

Revision ID: d6a99e1c2b73
Revises: c5f88d0b3a41
Create Date: 2026-07-03
"""
import sqlalchemy as sa
from alembic import op

import app.db.base  # noqa: F401 — registers DecimalText

revision = "d6a99e1c2b73"
down_revision = "c5f88d0b3a41"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if "ecb_fx_rates" in sa.inspect(bind).get_table_names():
        return
    op.create_table(
        "ecb_fx_rates",
        sa.Column("currency", sa.String(3), primary_key=True),
        sa.Column("rate", app.db.base.DecimalText(), nullable=False),
        sa.Column("as_of", sa.String(12), nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("ecb_fx_rates")
