# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 2.2 — injectable database URL (Postgres-ready), SQLite by default."""

from __future__ import annotations

from app.core.config import _to_sync_url, get_settings, reload_settings


def test_defaults_to_local_sqlite(monkeypatch):
    # Assert the DEFAULT (no injected URL) is local SQLite — independent of any
    # LEDGERFRAME_DB_URL the environment may set (e.g. the Postgres CI job). A fresh Settings
    # under a cleared env avoids mutating the global singleton other tests rely on.
    monkeypatch.delenv("LEDGERFRAME_DB_URL", raising=False)
    from app.core.config import Settings

    s = Settings()
    assert s.db_url.startswith("sqlite+aiosqlite:///")
    assert s.sync_db_url.startswith("sqlite:///")
    assert s.is_sqlite is True


def test_db_url_injectable_via_env(monkeypatch):
    monkeypatch.setenv("LEDGERFRAME_DB_URL", "postgresql+asyncpg://u:p@h:5432/lf")
    reload_settings()
    try:
        s = get_settings()
        assert s.db_url == "postgresql+asyncpg://u:p@h:5432/lf"
        assert s.sync_db_url == "postgresql+psycopg://u:p@h:5432/lf"   # sync driver for Alembic
        assert s.is_sqlite is False
    finally:
        monkeypatch.delenv("LEDGERFRAME_DB_URL", raising=False)
        reload_settings()


def test_sync_url_derivation():
    assert _to_sync_url("sqlite+aiosqlite:////tmp/x.db") == "sqlite:////tmp/x.db"
    assert _to_sync_url("postgresql+asyncpg://u@h/db") == "postgresql+psycopg://u@h/db"
    assert _to_sync_url("postgresql://u@h/db") == "postgresql://u@h/db"  # already sync


def test_decimaltext_is_text_on_every_dialect():
    # Money is stored as TEXT on both dialects, matching the migration files (sa.Text) so the
    # create_all schema equals the migrated schema on Postgres, and money is the identical
    # minimal Decimal everywhere (no NUMERIC scale-padding on Postgres).
    from decimal import Decimal

    from sqlalchemy.dialects import postgresql, sqlite

    from app.db.base import DecimalText

    dt = DecimalText()
    for dialect in (postgresql.dialect(), sqlite.dialect()):
        impl = str(dt.load_dialect_impl(dialect)).upper()
        assert "NUMERIC" not in impl and ("VARCHAR" in impl or "TEXT" in impl or "STRING" in impl)
    # Bind is always a plain string (never a native Decimal handed to the driver).
    assert dt.process_bind_param(Decimal("68000.5"), postgresql.dialect()) == "68000.5"


def test_partial_unique_indexes_survive_on_postgres():
    from sqlalchemy.dialects import postgresql
    from sqlalchemy.schema import CreateIndex

    from app.models import InstrumentIdentifier

    for name in ("uq_ident_high_conf", "uq_ident_provider_symbol"):
        idx = next(i for i in InstrumentIdentifier.__table__.indexes if i.name == name)
        ddl = str(CreateIndex(idx).compile(dialect=postgresql.dialect()))
        assert "WHERE" in ddl.upper(), f"{name} lost its partial predicate on Postgres"
