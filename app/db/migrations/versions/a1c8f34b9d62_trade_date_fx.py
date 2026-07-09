# SPDX-License-Identifier: AGPL-3.0-or-later
"""trade-date FX — transactions.fx_to_base + transactions.fx_base (§4.2, Unit A)

Additive, idempotent, schema-only. Adds two nullable columns to persist the native→base FX
rate captured at commit (Unit B): ``fx_to_base`` (the rate) and ``fx_base`` (which base it
was captured against). Nothing reads or writes them yet (Unit C), so this is behaviour-inert.

CRITICAL — the backfill is **NULL, not a default**. Unlike the §4.1 entity backfill, there
is deliberately NO ``UPDATE``: a pre-existing (possibly years-old) trade has no historical
FX rate, and using today's rate for it would be a wrong number. NULL means "trade-date FX
unavailable", which is the honest state. New rows populate the rate live at commit (Unit B).

Revision ID: a1c8f34b9d62
Revises: f4a9c2b71e08
Create Date: 2026-07-07
"""
import sqlalchemy as sa
from alembic import op

import app.db.base  # noqa: F401 — DecimalText custom column type

revision = "a1c8f34b9d62"
down_revision = "f4a9c2b71e08"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent: fresh DBs are create_all-bootstrapped (columns already present), so only
    # add what is missing on databases adopted into Alembic. No backfill — existing rows stay
    # NULL ("trade-date FX unavailable"); we never fabricate a historical rate.
    bind = op.get_bind()
    cols = {c["name"] for c in sa.inspect(bind).get_columns("transactions")}
    with op.batch_alter_table("transactions") as batch:
        if "fx_to_base" not in cols:
            batch.add_column(sa.Column("fx_to_base", app.db.base.DecimalText(), nullable=True))
        if "fx_base" not in cols:
            batch.add_column(sa.Column("fx_base", sa.String(length=3), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("transactions") as batch:
        batch.drop_column("fx_base")
        batch.drop_column("fx_to_base")
