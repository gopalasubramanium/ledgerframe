# SPDX-License-Identifier: AGPL-3.0-or-later
"""phase 2: instrument identity + taxonomy

Additive only. Adds classification columns to ``instruments`` and a normalized
``instrument_identifiers`` table (ISIN / FIGI / AMFI code / CoinGecko id / provider
symbol …). Idempotent: the app bootstraps fresh DBs with ``create_all()``, so a
column/table may already exist on a database being adopted into Alembic — we add
only what's missing, then backfill sensible defaults for existing rows.

Revision ID: a3d21f7e5b10
Revises: b2f1c7d9e004
Create Date: 2026-07-03
"""
from collections.abc import Callable

import sqlalchemy as sa
from alembic import op

import app.db.base  # noqa: F401 — registers the DecimalText custom type

revision = "a3d21f7e5b10"
down_revision = "b2f1c7d9e004"
branch_labels = None
depends_on = None

# name -> column factory (nullable, additive)
_NEW_COLUMNS: dict[str, Callable[[], sa.Column]] = {
    "asset_subclass": lambda: sa.Column("asset_subclass", sa.String(40), nullable=True),
    "asset_category": lambda: sa.Column("asset_category", sa.String(40), nullable=True),
    "liquidity_profile": lambda: sa.Column("liquidity_profile", sa.String(20), nullable=True),
    "valuation_method": lambda: sa.Column("valuation_method", sa.String(30), nullable=True),
    "pricing_currency": lambda: sa.Column("pricing_currency", sa.String(3), nullable=True),
    "domicile_country": lambda: sa.Column("domicile_country", sa.String(2), nullable=True),
    "listing_country": lambda: sa.Column("listing_country", sa.String(2), nullable=True),
    "exchange_mic": lambda: sa.Column("exchange_mic", sa.String(10), nullable=True),
    "source_override": lambda: sa.Column("source_override", sa.String(40), nullable=True),
    "last_verified_at": lambda: sa.Column("last_verified_at", sa.DateTime, nullable=True),
}


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    existing = {c["name"] for c in insp.get_columns("instruments")}
    for name, factory in _NEW_COLUMNS.items():
        if name not in existing:
            op.add_column("instruments", factory())

    if "instrument_identifiers" not in insp.get_table_names():
        op.create_table(
            "instrument_identifiers",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("instrument_id", sa.Integer, sa.ForeignKey("instruments.id"), nullable=False),
            sa.Column("id_type", sa.String(24), nullable=False),
            sa.Column("value", sa.String(64), nullable=False),
            sa.Column("provider", sa.String(40), nullable=True),
            # sa.false() renders "0" on SQLite (byte-identical to the old text("0")) and "false"
            # on Postgres, which rejects an integer default on a boolean column.
            sa.Column("is_primary", sa.Boolean, nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime, nullable=True),
            sa.UniqueConstraint("instrument_id", "id_type", "value", name="uq_ident_instr_type_value"),
        )
        op.create_index("ix_ident_instrument_id", "instrument_identifiers", ["instrument_id"])
        op.create_index("ix_ident_type_value", "instrument_identifiers", ["id_type", "value"])

    # Backfill existing instruments to sensible, non-destructive defaults.
    op.execute("UPDATE instruments SET pricing_currency = currency WHERE pricing_currency IS NULL")
    op.execute("UPDATE instruments SET asset_category = asset_class WHERE asset_category IS NULL")
    op.execute("UPDATE instruments SET asset_subclass = asset_class WHERE asset_subclass IS NULL")
    # Compare the boolean per dialect: SQLite keeps its exact original `= 1` (stored as 0/1);
    # Postgres needs `= true` since `boolean = integer` is a type error there. SQLite behaviour
    # is byte-for-byte unchanged.
    manual = "is_manual_price = true" if bind.dialect.name == "postgresql" else "is_manual_price = 1"
    op.execute(
        "UPDATE instruments SET liquidity_profile = "
        f"CASE WHEN {manual} THEN 'manual' ELSE 'listed' END "
        "WHERE liquidity_profile IS NULL"
    )
    op.execute(
        "UPDATE instruments SET valuation_method = "
        f"CASE WHEN {manual} THEN 'manual_valuation' ELSE 'market_quote' END "
        "WHERE valuation_method IS NULL"
    )


def downgrade() -> None:
    op.drop_table("instrument_identifiers")
    for name in _NEW_COLUMNS:
        with op.batch_alter_table("instruments") as batch:
            batch.drop_column(name)
