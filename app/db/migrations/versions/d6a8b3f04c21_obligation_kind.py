# SPDX-License-Identifier: AGPL-3.0-or-later
"""obligation.kind — expense | income (Phase 4a runway)

Additive, nullable, idempotent. Lets obligations carry recurring INCOME as well as
outflows, so the runway can be a true net burn. Existing rows default to 'expense'.

Revision ID: d6a8b3f04c21
Revises: c5f7a2e91b30
Create Date: 2026-07-04
"""
import sqlalchemy as sa
from alembic import op

revision = "d6a8b3f04c21"
down_revision = "c5f7a2e91b30"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    cols = {c["name"] for c in sa.inspect(bind).get_columns("obligations")}
    if "kind" not in cols:
        op.add_column("obligations", sa.Column("kind", sa.String(length=8), nullable=False,
                                               server_default="expense"))


def downgrade() -> None:
    op.drop_column("obligations", "kind")
