# SPDX-License-Identifier: AGPL-3.0-or-later
"""session revocation — revoked_token table + users.tokens_valid_after (§1.7)

Additive, idempotent. Nothing existing is touched.

Revision ID: c4d1e8a92f60
Revises: b5c9f0a71d84
Create Date: 2026-07-05
"""
import sqlalchemy as sa
from alembic import op

revision = "c4d1e8a92f60"
down_revision = "b5c9f0a71d84"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())
    if "revoked_token" not in tables:
        op.create_table(
            "revoked_token",
            sa.Column("jti", sa.String(length=64), primary_key=True),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
        )
    if "users" in tables:
        cols = {c["name"] for c in insp.get_columns("users")}
        if "tokens_valid_after" not in cols:
            op.add_column("users", sa.Column("tokens_valid_after", sa.Float(),
                                             nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("users", "tokens_valid_after")
    op.drop_table("revoked_token")
