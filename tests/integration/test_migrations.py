# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 2 migration safety: upgrading a *previous-release* database applies the
additive taxonomy columns + instrument_identifiers table WITHOUT data loss, and
backfills sensible defaults. This is the mandatory backward-compatible upgrade test.
"""

from __future__ import annotations

import os

from alembic import command
from sqlalchemy import create_engine, inspect, text

PREV_RELEASE_REVISION = "b2f1c7d9e004"  # v1.10.0 schema (pre Phase 2)


def _run_alembic_on(data_dir) -> str:
    """Point settings at a temp data dir and return its sync DB URL."""
    from app.core.config import get_settings, reload_settings

    (data_dir / "db").mkdir(parents=True, exist_ok=True)
    os.environ["LEDGERFRAME_DATA_DIR"] = str(data_dir)
    reload_settings()
    settings = get_settings()
    url = settings.sync_db_url
    if not settings.is_sqlite:  # Postgres shares one DB → clean public schema per test (serial)
        eng = create_engine(url)
        try:
            with eng.begin() as c:
                c.execute(text('DROP SCHEMA IF EXISTS "public" CASCADE'))
                c.execute(text('CREATE SCHEMA "public"'))
        finally:
            eng.dispose()
    return url


def test_upgrade_from_previous_release_is_additive_and_lossless(tmp_path):
    from app.core.config import reload_settings
    from app.db.migrate import _alembic_config

    old_dir = os.environ.get("LEDGERFRAME_DATA_DIR")
    try:
        url = _run_alembic_on(tmp_path / "upgrade")
        cfg = _alembic_config()

        # 1) Build a database at the PREVIOUS release schema and seed real rows.
        command.upgrade(cfg, PREV_RELEASE_REVISION)
        eng = create_engine(url)
        with eng.begin() as c:
            # boolean literals (not 0/1) so the raw SQL works on Postgres too; SQLite (>=3.23)
            # treats TRUE/FALSE as 1/0, so behaviour is identical there.
            c.execute(text(
                "INSERT INTO instruments (symbol, exchange, name, asset_class, currency, is_manual_price) "
                "VALUES ('AAPL','NASDAQ','Apple Inc.','equity','USD',false)"))
            c.execute(text(
                "INSERT INTO instruments (symbol, name, asset_class, currency, is_manual_price) "
                "VALUES ('HOME-EST','Home (est.)','property','SGD',true)"))

        # 2) Apply Phase 2 (head).
        command.upgrade(cfg, "head")

        insp = inspect(eng)
        cols = {c["name"] for c in insp.get_columns("instruments")}
        assert {
            "asset_subclass", "asset_category", "liquidity_profile", "valuation_method",
            "pricing_currency", "domicile_country", "listing_country", "exchange_mic",
            "source_override", "last_verified_at",
        } <= cols
        assert "instrument_identifiers" in insp.get_table_names()

        # 3) Data preserved + backfilled to sensible defaults.
        with eng.connect() as c:
            rows = c.execute(text(
                "SELECT symbol, pricing_currency, valuation_method, liquidity_profile, asset_category "
                "FROM instruments ORDER BY symbol")).all()
        by = {r[0]: r for r in rows}
        assert set(by) == {"AAPL", "HOME-EST"}                       # nothing lost
        assert by["AAPL"][1] == "USD"                                # pricing_currency = currency
        assert by["AAPL"][2] == "market_quote" and by["AAPL"][3] == "listed"
        assert by["HOME-EST"][2] == "manual_valuation" and by["HOME-EST"][3] == "manual"
        assert by["AAPL"][4] == "equity"                             # asset_category backfilled
        eng.dispose()
    finally:
        if old_dir is not None:
            os.environ["LEDGERFRAME_DATA_DIR"] = old_dir
        else:
            os.environ.pop("LEDGERFRAME_DATA_DIR", None)
        reload_settings()
