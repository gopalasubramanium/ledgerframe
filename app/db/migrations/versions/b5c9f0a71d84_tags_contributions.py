# SPDX-License-Identifier: AGPL-3.0-or-later
"""tags + contributions (W8)

Additive, idempotent. Two new tables; nothing existing is touched.

Revision ID: b5c9f0a71d84
Revises: a3b8e1f42c67
Create Date: 2026-07-05
"""
import sqlalchemy as sa
from alembic import op

revision = "b5c9f0a71d84"
down_revision = "a3b8e1f42c67"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    have = set(sa.inspect(bind).get_table_names())
    if "holding_tag" not in have:
        op.create_table(
            "holding_tag",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("account_id", sa.Integer(), nullable=False),
            sa.Column("holding_key", sa.String(length=200), nullable=False),
            sa.Column("tags", sa.Text(), nullable=False, server_default="[]"),
            sa.UniqueConstraint("account_id", "holding_key", name="uq_holding_tag"),
        )
        op.create_index("ix_holding_tag_account_id", "holding_tag", ["account_id"])
    if "contribution" not in have:
        op.create_table(
            "contribution",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("amount", sa.Text(), nullable=False, server_default="0"),
            sa.Column("currency", sa.String(length=3), nullable=False, server_default="SGD"),
            sa.Column("frequency", sa.String(length=12), nullable=False, server_default="monthly"),
            sa.Column("kind", sa.String(length=12), nullable=False, server_default="invest"),
            sa.Column("target_goal_id", sa.Integer(), nullable=True),
            sa.Column("start_date", sa.String(length=10), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    op.drop_table("contribution")
    op.drop_table("holding_tag")
