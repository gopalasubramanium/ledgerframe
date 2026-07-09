# SPDX-License-Identifier: AGPL-3.0-or-later
"""api_token — scoped read-only API tokens (§2.4)

Additive, idempotent. One new table; nothing existing is touched.

Revision ID: d5e2f0b83a19
Revises: c4d1e8a92f60
Create Date: 2026-07-05
"""
import sqlalchemy as sa
from alembic import op

revision = "d5e2f0b83a19"
down_revision = "c4d1e8a92f60"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if "api_token" not in set(sa.inspect(bind).get_table_names()):
        op.create_table(
            "api_token",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=80), nullable=False, server_default="API token"),
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("prefix", sa.String(length=16), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("last_used_at", sa.DateTime(), nullable=True),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("token_hash", name="uq_api_token_hash"),
        )
        op.create_index("ix_api_token_token_hash", "api_token", ["token_hash"])


def downgrade() -> None:
    op.drop_table("api_token")
