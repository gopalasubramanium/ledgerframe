# SPDX-License-Identifier: AGPL-3.0-or-later
"""soft-delete — holdings.deleted_at + transactions.deleted_at (§3.5, Unit A)

Additive, idempotent, schema-only. Adds a nullable, indexed ``deleted_at`` timestamp
to both tables. Nothing reads or writes it yet (Unit B onward), so this is a no-op on
all existing behaviour.

Revision ID: e3f8a1c92d45
Revises: d5e2f0b83a19
Create Date: 2026-07-07
"""
import sqlalchemy as sa
from alembic import op

revision = "e3f8a1c92d45"
down_revision = "d5e2f0b83a19"
branch_labels = None
depends_on = None

_TABLES = ("holdings", "transactions")


def upgrade() -> None:
    # Idempotent: the app bootstraps fresh DBs with create_all(), which already includes
    # the model's deleted_at column + ix_<table>_deleted_at index — so only add what is
    # missing on databases adopted into Alembic before this revision.
    bind = op.get_bind()
    insp = sa.inspect(bind)
    for table in _TABLES:
        cols = {c["name"] for c in insp.get_columns(table)}
        if "deleted_at" not in cols:
            with op.batch_alter_table(table) as batch:
                batch.add_column(sa.Column("deleted_at", sa.DateTime(), nullable=True))
        idx = {i["name"] for i in insp.get_indexes(table)}
        if f"ix_{table}_deleted_at" not in idx:
            op.create_index(f"ix_{table}_deleted_at", table, ["deleted_at"])


def downgrade() -> None:
    for table in _TABLES:
        op.drop_index(f"ix_{table}_deleted_at", table_name=table)
        with op.batch_alter_table(table) as batch:
            batch.drop_column("deleted_at")
