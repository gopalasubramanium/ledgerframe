# SPDX-License-Identifier: AGPL-3.0-or-later
"""review_log — recorded reviews over time (W1)

Additive, idempotent. One new table storing a snapshot each time a review is recorded.
Nothing existing is touched.

Revision ID: e7c9d4a13b52
Revises: d6a8b3f04c21
Create Date: 2026-07-05
"""
import sqlalchemy as sa
from alembic import op

revision = "e7c9d4a13b52"
down_revision = "d6a8b3f04c21"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if "review_log" not in set(sa.inspect(bind).get_table_names()):
        op.create_table(
            "review_log",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("reviewed_at", sa.DateTime(), nullable=True),
            sa.Column("net_worth", sa.Text(), nullable=False, server_default="0"),
            sa.Column("base_currency", sa.String(length=3), nullable=False, server_default="SGD"),
            sa.Column("confidence", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("drift_flags", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("attention_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("next_review_date", sa.String(length=10), nullable=True),
        )
        op.create_index("ix_review_log_reviewed_at", "review_log", ["reviewed_at"])


def downgrade() -> None:
    op.drop_table("review_log")
