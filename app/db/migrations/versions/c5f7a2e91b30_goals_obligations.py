# SPDX-License-Identifier: AGPL-3.0-or-later
"""goals & obligations — planning (Phase 3b)

Additive, idempotent. Two new tables storing the user's INTENT only; progress and the
next-12-months total are computed live and never stored. Nothing existing is touched.

Revision ID: c5f7a2e91b30
Revises: b4e6c1f27a90
Create Date: 2026-07-04
"""
import sqlalchemy as sa
from alembic import op

revision = "c5f7a2e91b30"
down_revision = "b4e6c1f27a90"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())

    if "goals" not in tables:
        op.create_table(
            "goals",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=80), nullable=False),
            sa.Column("target_amount", sa.Text(), nullable=False, server_default="0"),
            sa.Column("target_date", sa.String(length=10), nullable=True),
            sa.Column("currency", sa.String(length=3), nullable=True),
            sa.Column("basis", sa.String(length=16), nullable=False, server_default="net_worth"),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )

    if "obligations" not in tables:
        op.create_table(
            "obligations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=80), nullable=False),
            sa.Column("amount", sa.Text(), nullable=False, server_default="0"),
            sa.Column("due_date", sa.String(length=10), nullable=False, server_default=""),
            sa.Column("currency", sa.String(length=3), nullable=True),
            sa.Column("recurrence", sa.String(length=12), nullable=False, server_default="once"),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    op.drop_table("obligations")
    op.drop_table("goals")
