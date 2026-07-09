# SPDX-License-Identifier: AGPL-3.0-or-later
"""entities — ownership entity table + accounts.entity_id (§4.1, Unit A)

Additive, idempotent, and number-neutral. Creates an ``entities`` table and a nullable
``accounts.entity_id`` FK, then BACKFILLS a single default entity and assigns every
existing account to it — so post-migration the whole portfolio belongs to one entity and
every computed figure is unchanged (one entity = identity). No reader filters by entity
yet (Unit B), so this is behaviour-inert on all money computations.

Revision ID: f4a9c2b71e08
Revises: e3f8a1c92d45
Create Date: 2026-07-07
"""
import sqlalchemy as sa
from alembic import op

revision = "f4a9c2b71e08"
down_revision = "e3f8a1c92d45"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent: fresh DBs are create_all-bootstrapped (table + column + index already
    # present), so only create what's missing on databases adopted into Alembic.
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if "entities" not in set(insp.get_table_names()):
        op.create_table(
            "entities",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=80), nullable=False, server_default="Household"),
            sa.Column("kind", sa.String(length=40), nullable=False, server_default="self"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )

    if "entity_id" not in {c["name"] for c in insp.get_columns("accounts")}:
        with op.batch_alter_table("accounts") as batch:
            batch.add_column(sa.Column("entity_id", sa.Integer(), nullable=True))
    if "ix_accounts_entity_id" not in {i["name"] for i in insp.get_indexes("accounts")}:
        op.create_index("ix_accounts_entity_id", "accounts", ["entity_id"])

    # Backfill (one entity = identity): ensure a single default entity exists, then assign
    # every not-yet-assigned account to it. Idempotent — re-running assigns nothing new.
    if not bind.execute(sa.text("SELECT COUNT(*) FROM entities")).scalar():
        # created_at is supplied explicitly: create_all builds this column NOT NULL, so an
        # INSERT that omits it fails on adopted databases. CURRENT_TIMESTAMP is portable.
        op.execute("INSERT INTO entities (name, kind, created_at) VALUES ('Household', 'self', CURRENT_TIMESTAMP)")
    default_id = bind.execute(sa.text("SELECT id FROM entities ORDER BY id LIMIT 1")).scalar()
    bind.execute(sa.text("UPDATE accounts SET entity_id = :eid WHERE entity_id IS NULL"),
                 {"eid": default_id})


def downgrade() -> None:
    op.drop_index("ix_accounts_entity_id", table_name="accounts")
    with op.batch_alter_table("accounts") as batch:
        batch.drop_column("entity_id")
    op.drop_table("entities")
