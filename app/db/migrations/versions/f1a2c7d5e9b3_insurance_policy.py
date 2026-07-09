# SPDX-License-Identifier: AGPL-3.0-or-later
"""insurance_policy — first-class protection register (W3)

Additive, idempotent. One new table; nothing existing is touched.

Revision ID: f1a2c7d5e9b3
Revises: e7c9d4a13b52
Create Date: 2026-07-05
"""
import sqlalchemy as sa
from alembic import op

revision = "f1a2c7d5e9b3"
down_revision = "e7c9d4a13b52"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if "insurance_policy" not in set(sa.inspect(bind).get_table_names()):
        op.create_table(
            "insurance_policy",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("insurer", sa.String(length=120), nullable=True),
            sa.Column("policy_type", sa.String(length=30), nullable=False, server_default="other"),
            sa.Column("policy_number", sa.String(length=80), nullable=True),
            sa.Column("insured_person", sa.String(length=120), nullable=True),
            sa.Column("cover_amount", sa.Text(), nullable=False, server_default="0"),
            sa.Column("currency", sa.String(length=3), nullable=False, server_default="SGD"),
            sa.Column("cash_value", sa.Text(), nullable=True),
            sa.Column("premium", sa.Text(), nullable=True),
            sa.Column("premium_frequency", sa.String(length=12), nullable=False, server_default="annual"),
            sa.Column("start_date", sa.String(length=10), nullable=True),
            sa.Column("renewal_date", sa.String(length=10), nullable=True),
            sa.Column("nominee", sa.String(length=120), nullable=True),
            sa.Column("linked_goal_id", sa.Integer(), nullable=True),
            sa.Column("documents", sa.Text(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=12), nullable=False, server_default="active"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    op.drop_table("insurance_policy")
