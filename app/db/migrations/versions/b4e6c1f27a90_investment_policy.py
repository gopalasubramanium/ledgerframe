# SPDX-License-Identifier: AGPL-3.0-or-later
"""investment policy — target allocation, tolerance bands, risk limit

Additive, idempotent. Two new tables (investment_policy, policy_targets) storing the
user's INTENT only; drift / band status / concentration are computed live and never
stored. Nothing existing is touched.

Revision ID: b4e6c1f27a90
Revises: a9d3e5f70218
Create Date: 2026-07-04
"""
import sqlalchemy as sa
from alembic import op

revision = "b4e6c1f27a90"
down_revision = "a9d3e5f70218"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())

    if "investment_policy" not in tables:
        op.create_table(
            "investment_policy",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=80), nullable=False, server_default="Investment Policy"),
            sa.Column("base_currency", sa.String(length=3), nullable=True),
            sa.Column("default_band_pct", sa.Text(), nullable=False, server_default="5"),
            sa.Column("max_position_pct", sa.Text(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )

    if "policy_targets" not in tables:
        op.create_table(
            "policy_targets",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("policy_id", sa.Integer(), sa.ForeignKey("investment_policy.id"), nullable=False),
            sa.Column("dimension", sa.String(length=20), nullable=False),
            sa.Column("bucket", sa.String(length=40), nullable=False),
            sa.Column("target_pct", sa.Text(), nullable=False, server_default="0"),
            sa.Column("min_pct", sa.Text(), nullable=True),
            sa.Column("max_pct", sa.Text(), nullable=True),
            sa.UniqueConstraint("policy_id", "dimension", "bucket", name="uq_policy_target"),
        )
        op.create_index("ix_policy_targets_policy_id", "policy_targets", ["policy_id"])


def downgrade() -> None:
    op.drop_table("policy_targets")
    op.drop_table("investment_policy")
