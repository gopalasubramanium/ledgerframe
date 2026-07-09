# SPDX-License-Identifier: AGPL-3.0-or-later
"""phase 4: amfi mutual-fund scheme master + NAV cache

Additive only — creates the ``amfi_schemes`` table. Idempotent (create_all may have
made it already on a fresh install).

Revision ID: b4e77c9a1f22
Revises: a3d21f7e5b10
Create Date: 2026-07-03
"""
import sqlalchemy as sa
from alembic import op

import app.db.base  # noqa: F401 — registers DecimalText

revision = "b4e77c9a1f22"
down_revision = "a3d21f7e5b10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if "amfi_schemes" in sa.inspect(bind).get_table_names():
        return
    op.create_table(
        "amfi_schemes",
        sa.Column("code", sa.String(12), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("isin_growth", sa.String(20), nullable=True),
        sa.Column("isin_reinvest", sa.String(20), nullable=True),
        sa.Column("fund_house", sa.String(120), nullable=True),
        sa.Column("category", sa.String(160), nullable=True),
        sa.Column("nav", app.db.base.DecimalText(), nullable=True),
        sa.Column("nav_date", sa.String(12), nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_amfi_name", "amfi_schemes", ["name"])
    op.create_index("ix_amfi_isin_growth", "amfi_schemes", ["isin_growth"])


def downgrade() -> None:
    op.drop_table("amfi_schemes")
