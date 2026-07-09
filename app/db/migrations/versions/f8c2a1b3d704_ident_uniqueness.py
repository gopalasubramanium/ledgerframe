# SPDX-License-Identifier: AGPL-3.0-or-later
"""identifier uniqueness: high-confidence ids globally unique

Additive + best-effort. Creates a partial UNIQUE index so a high-confidence
identifier (ISIN/CUSIP/FIGI/SEDOL/AMFI code/Kite token/CoinGecko id) cannot be
attached to two different instruments. If the DB already contains such duplicates,
the index creation fails — we swallow that and leave the data untouched; the service
guard still blocks NEW duplicates and GET /system/identifier-duplicates surfaces the
existing ones for the user to resolve (we never guess which mapping is correct).

Revision ID: f8c2a1b3d704
Revises: e7b1a2c4d905
Create Date: 2026-07-03
"""
import sqlalchemy as sa
from alembic import op

revision = "f8c2a1b3d704"
down_revision = "e7b1a2c4d905"
branch_labels = None
depends_on = None

_HIGH_CONF = "('isin','cusip','figi','sedol','amfi_code','kite_token','coingecko_id')"


def upgrade() -> None:
    bind = op.get_bind()
    existing = {ix["name"] for ix in sa.inspect(bind).get_indexes("instrument_identifiers")}
    if "uq_ident_high_conf" not in existing:
        try:
            op.create_index(
                "uq_ident_high_conf", "instrument_identifiers", ["id_type", "value"],
                unique=True,
                sqlite_where=sa.text(f"id_type IN {_HIGH_CONF}"),
                postgresql_where=sa.text(f"id_type IN {_HIGH_CONF}"),  # keep it PARTIAL on PG
            )
        except Exception:  # noqa: BLE001 — pre-existing duplicates; leave data intact
            pass
    if "uq_ident_provider_symbol" not in existing:
        try:
            op.create_index(
                "uq_ident_provider_symbol", "instrument_identifiers", ["provider", "value"],
                unique=True,
                sqlite_where=sa.text("id_type = 'provider_symbol'"),
                postgresql_where=sa.text("id_type = 'provider_symbol'"),  # keep it PARTIAL on PG
            )
        except Exception:  # noqa: BLE001
            pass


def downgrade() -> None:
    for name in ("uq_ident_high_conf", "uq_ident_provider_symbol"):
        try:
            op.drop_index(name, table_name="instrument_identifiers")
        except Exception:  # noqa: BLE001
            pass
