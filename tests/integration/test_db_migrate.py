# SPDX-License-Identifier: AGPL-3.0-or-later
"""The migration runner is safe for create_all-bootstrapped databases.

Reproduces the Pi failure ("table accounts already exists"): a DB created by
create_all() has no Alembic stamp (or an empty alembic_version table from a prior
failed upgrade), so a plain `alembic upgrade head` re-runs the initial migration.
``run_migrations`` must instead stamp + upgrade cleanly. Runs in-process (fast).
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text

import app.models  # noqa: F401 — register models on Base.metadata
from app.core.config import get_settings, reload_settings
from app.db.base import Base
from app.db.migrate import run_migrations


def _reset_namespace(sync_url: str, schema: str = "public") -> None:
    """Give a migration test a clean slate. SQLite isolates via a fresh temp file (tmp_path),
    so this is a no-op there; on Postgres the tests share one database, so drop+recreate the
    schema (the suite runs serially, so a clean schema is sufficient isolation)."""
    if sync_url.startswith("sqlite"):
        return
    eng = create_engine(sync_url)
    try:
        with eng.begin() as c:
            c.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
            c.execute(text(f'CREATE SCHEMA "{schema}"'))
    finally:
        eng.dispose()


@pytest.fixture
def db_url(tmp_path, monkeypatch):
    """Point settings at an isolated temp database, restoring afterwards."""
    monkeypatch.setenv("LEDGERFRAME_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("LEDGERFRAME_SECRET_KEY", "x" * 32)
    reload_settings()
    settings = get_settings()
    url = settings.sync_db_url
    if settings.is_sqlite:
        settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        _reset_namespace(url)  # clean public schema per test on Postgres
    yield url
    reload_settings()  # restore the normal (test) settings for other tests


def _version(url: str) -> str | None:
    eng = create_engine(url)
    try:
        with eng.connect() as c:
            row = c.execute(text("SELECT version_num FROM alembic_version")).first()
            return row[0] if row else None
    finally:
        eng.dispose()


def _create_all(url: str):
    eng = create_engine(url)
    try:
        Base.metadata.create_all(eng)
    finally:
        eng.dispose()


def test_fresh_database(db_url):
    status = run_migrations(log=lambda *a: None)
    assert status in ("upgraded", "adopted")
    assert _version(db_url)  # stamped at head


def test_adopts_create_all_schema(db_url):
    _create_all(db_url)  # full schema, no alembic_version
    status = run_migrations(log=lambda *a: None)
    assert status == "adopted"
    assert _version(db_url)


def test_recovers_empty_alembic_version(db_url):
    # The Pi's exact broken state: full create_all schema + EMPTY alembic_version.
    _create_all(db_url)
    eng = create_engine(db_url)
    with eng.connect() as c:
        c.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        c.commit()
    eng.dispose()
    status = run_migrations(log=lambda *a: None)
    assert status in ("adopted", "reconciled")
    assert _version(db_url)


def test_idempotent_second_run(db_url):
    run_migrations(log=lambda *a: None)
    # Running again must be a clean no-op.
    run_migrations(log=lambda *a: None)
    assert _version(db_url)


def test_session_revocation_schema_present_after_migrations(db_url):
    from sqlalchemy import inspect

    run_migrations(log=lambda *a: None)
    eng = create_engine(db_url)
    try:
        insp = inspect(eng)
        assert "revoked_token" in insp.get_table_names()
        assert "tokens_valid_after" in {c["name"] for c in insp.get_columns("users")}
    finally:
        eng.dispose()


def test_upgrade_from_prior_head_adds_revocation_additively(db_url):
    """§1.7 migration is additive and preserves data (upgrade-from-previous-head)."""
    from alembic import command
    from sqlalchemy import inspect

    from app.db.migrate import _alembic_config

    cfg = _alembic_config()
    command.upgrade(cfg, "b5c9f0a71d84")  # the head BEFORE session revocation
    eng = create_engine(db_url)
    try:
        insp = inspect(eng)
        assert "revoked_token" not in insp.get_table_names()
        with eng.begin() as c:
            c.execute(text("INSERT INTO users (name, pin_hash, created_at) VALUES ('Owner', 'x', '2026-01-01')"))
    finally:
        eng.dispose()

    command.upgrade(cfg, "head")
    eng = create_engine(db_url)
    try:
        insp = inspect(eng)
        assert "revoked_token" in insp.get_table_names()
        assert "tokens_valid_after" in {c["name"] for c in insp.get_columns("users")}
        with eng.connect() as c:
            row = c.execute(text("SELECT name, tokens_valid_after FROM users")).first()
        assert row[0] == "Owner" and float(row[1]) == 0.0  # data preserved, column defaulted
    finally:
        eng.dispose()


def _schema_map(insp, schema: str | None = None) -> dict[str, set[str]]:
    return {t: {c["name"] for c in insp.get_columns(t, schema=schema)}
            for t in insp.get_table_names(schema=schema)}


def test_migrated_head_matches_create_all(db_url):
    """§2.1 — the full migration chain produces exactly the create_all schema
    (tables + columns), so migrations are the single source of truth."""
    from sqlalchemy import create_engine, inspect

    from app.core.config import get_settings
    from app.db.base import Base

    run_migrations(log=lambda *a: None)
    meng = create_engine(db_url)
    migrated = _schema_map(inspect(meng))
    meng.dispose()
    migrated.pop("alembic_version", None)

    if get_settings().is_sqlite:
        ca_url = db_url.replace("ledgerframe.db", "ca_equiv.db")
        ceng = create_engine(ca_url)
        Base.metadata.create_all(ceng)
        created = _schema_map(inspect(ceng))
        ceng.dispose()
    else:
        # Postgres shares one database — build create_all into a separate schema and compare.
        ceng = create_engine(db_url)
        with ceng.begin() as c:
            c.execute(text('DROP SCHEMA IF EXISTS "ca_equiv" CASCADE'))
            c.execute(text('CREATE SCHEMA "ca_equiv"'))
        with ceng.connect() as c:
            c.exec_driver_sql("SET search_path TO ca_equiv")
            Base.metadata.create_all(bind=c)
            c.commit()
            created = _schema_map(inspect(c), schema="ca_equiv")
        with ceng.begin() as c:
            c.execute(text('DROP SCHEMA "ca_equiv" CASCADE'))
        ceng.dispose()

    assert set(migrated) == set(created), f"table set differs: {set(migrated) ^ set(created)}"
    for table in created:
        assert migrated[table] == created[table], (
            f"columns differ in {table}: {migrated[table] ^ created[table]}")


def test_concurrent_run_migrations_is_serialised(db_url):
    """§2.1 — two callers migrating the same DB at once are serialised by the file lock
    and both converge on a valid head stamp (no 'database is locked', no corruption)."""
    import concurrent.futures as cf

    with cf.ThreadPoolExecutor(max_workers=2) as ex:
        results = list(ex.map(lambda _: run_migrations(log=lambda *a: None), range(2)))
    assert all(r in ("upgraded", "adopted", "reconciled") for r in results)
    assert _version(db_url)  # stamped, schema intact


def test_api_token_schema_present_after_migrations(db_url):
    from sqlalchemy import inspect

    run_migrations(log=lambda *a: None)
    eng = create_engine(db_url)
    try:
        insp = inspect(eng)
        assert "api_token" in insp.get_table_names()
        cols = {c["name"] for c in insp.get_columns("api_token")}
        assert {"token_hash", "prefix", "revoked_at", "last_used_at", "created_at"} <= cols
    finally:
        eng.dispose()


def test_upgrade_from_prior_head_adds_api_token_additively(db_url):
    """§2.4 migration is additive and preserves data (upgrade-from-previous-head)."""
    from alembic import command
    from sqlalchemy import inspect

    from app.db.migrate import _alembic_config

    cfg = _alembic_config()
    command.upgrade(cfg, "c4d1e8a92f60")  # head BEFORE api_token
    eng = create_engine(db_url)
    try:
        assert "api_token" not in inspect(eng).get_table_names()
        with eng.begin() as c:
            c.execute(text("INSERT INTO accounts (name, kind, currency, created_at) "
                           "VALUES ('A','brokerage','SGD','2026-01-01 00:00:00')"))
    finally:
        eng.dispose()

    command.upgrade(cfg, "head")
    eng = create_engine(db_url)
    try:
        assert "api_token" in inspect(eng).get_table_names()
        with eng.connect() as c:
            assert c.execute(text("SELECT count(*) FROM accounts")).scalar() == 1  # data preserved
    finally:
        eng.dispose()


def test_soft_delete_columns_present_after_migrations(db_url):
    """§3.5 Unit A — the full chain adds deleted_at to holdings + transactions. The
    schema-equivalence with create_all is asserted by test_migrated_head_matches_create_all;
    this pins the new column explicitly on both tables."""
    from sqlalchemy import inspect

    run_migrations(log=lambda *a: None)
    eng = create_engine(db_url)
    try:
        insp = inspect(eng)
        assert "deleted_at" in {c["name"] for c in insp.get_columns("holdings")}
        assert "deleted_at" in {c["name"] for c in insp.get_columns("transactions")}
    finally:
        eng.dispose()


def test_upgrade_from_prior_head_adds_soft_delete_additively(db_url):
    """§3.5 Unit A migration is additive and lossless (upgrade-from-previous-head).

    Build the DB at the pre-soft-delete head, seed real holdings + transactions, upgrade
    to head, and assert deleted_at now exists, is NULL on every pre-existing row, and no
    prior data was lost."""
    from alembic import command
    from sqlalchemy import inspect

    from app.db.migrate import _alembic_config

    cfg = _alembic_config()
    command.upgrade(cfg, "d5e2f0b83a19")  # head BEFORE soft-delete (api_token)
    eng = create_engine(db_url)
    try:
        insp = inspect(eng)
        assert "deleted_at" not in {c["name"] for c in insp.get_columns("holdings")}
        assert "deleted_at" not in {c["name"] for c in insp.get_columns("transactions")}
        with eng.begin() as c:
            c.execute(text("INSERT INTO accounts (name, kind, currency, created_at) "
                           "VALUES ('Broker','brokerage','SGD','2026-01-01 00:00:00')"))
            aid = c.execute(text("SELECT id FROM accounts")).scalar()
            c.execute(text(
                "INSERT INTO holdings (account_id, asset_class, quantity, avg_cost, currency, label) "
                "VALUES (:a,'equity','10','100','USD','Test holding')"), {"a": aid})
            c.execute(text(
                "INSERT INTO transactions (account_id, type, ts, quantity, price, fees, taxes, amount, currency) "
                "VALUES (:a,'buy','2026-01-02 00:00:00','10','100','0','0','1000','USD')"), {"a": aid})
    finally:
        eng.dispose()

    command.upgrade(cfg, "head")
    eng = create_engine(db_url)
    try:
        insp = inspect(eng)
        assert "deleted_at" in {c["name"] for c in insp.get_columns("holdings")}
        assert "deleted_at" in {c["name"] for c in insp.get_columns("transactions")}
        with eng.connect() as c:
            assert c.execute(text("SELECT count(*) FROM holdings")).scalar() == 1       # nothing lost
            assert c.execute(text("SELECT count(*) FROM transactions")).scalar() == 1
            h = c.execute(text("SELECT label, deleted_at FROM holdings")).first()
            tx = c.execute(text("SELECT currency, deleted_at FROM transactions")).first()
        assert h[0] == "Test holding" and h[1] is None    # data preserved, new column NULL
        assert tx[0] == "USD" and tx[1] is None
    finally:
        eng.dispose()


def test_entities_schema_present_after_migrations(db_url):
    """§4.1 Unit A — the full chain adds the entities table + accounts.entity_id. The
    create_all-schema equivalence (incl. the new table + FK column) is asserted by
    test_migrated_head_matches_create_all; this pins them explicitly."""
    from sqlalchemy import inspect

    run_migrations(log=lambda *a: None)
    eng = create_engine(db_url)
    try:
        insp = inspect(eng)
        assert "entities" in insp.get_table_names()
        assert "entity_id" in {c["name"] for c in insp.get_columns("accounts")}
    finally:
        eng.dispose()


def test_upgrade_from_prior_head_adds_entities_with_backfill(db_url):
    """§4.1 Unit A migration is additive, lossless, and NUMBER-NEUTRAL: it creates one
    default entity and assigns every pre-existing account to it (one entity = identity).

    Build the DB at the pre-entities head, seed accounts + holdings + transactions, upgrade,
    and assert: entities exists, exactly one default entity was created, every account now
    points at it (no NULLs/orphans), and all prior data is preserved."""
    from alembic import command
    from sqlalchemy import inspect

    from app.db.migrate import _alembic_config

    cfg = _alembic_config()
    command.upgrade(cfg, "e3f8a1c92d45")  # head BEFORE entities (soft-delete)
    eng = create_engine(db_url)
    try:
        insp = inspect(eng)
        assert "entities" not in insp.get_table_names()
        assert "entity_id" not in {c["name"] for c in insp.get_columns("accounts")}
        with eng.begin() as c:
            for nm in ("Broker", "Bank"):
                c.execute(text("INSERT INTO accounts (name, kind, currency, created_at) "
                               "VALUES (:n,'brokerage','SGD','2026-01-01 00:00:00')"), {"n": nm})
            aid = c.execute(text("SELECT id FROM accounts ORDER BY id LIMIT 1")).scalar()
            c.execute(text(
                "INSERT INTO holdings (account_id, asset_class, quantity, avg_cost, currency, label) "
                "VALUES (:a,'equity','10','100','USD','Test holding')"), {"a": aid})
            c.execute(text(
                "INSERT INTO transactions (account_id, type, ts, quantity, price, fees, taxes, amount, currency) "
                "VALUES (:a,'buy','2026-01-02 00:00:00','10','100','0','0','1000','USD')"), {"a": aid})
    finally:
        eng.dispose()

    command.upgrade(cfg, "head")
    eng = create_engine(db_url)
    try:
        insp = inspect(eng)
        assert "entities" in insp.get_table_names()
        assert "entity_id" in {c["name"] for c in insp.get_columns("accounts")}
        with eng.connect() as c:
            assert c.execute(text("SELECT COUNT(*) FROM entities")).scalar() == 1   # one default entity
            default_id = c.execute(text("SELECT id FROM entities LIMIT 1")).scalar()
            # Backfill: every account assigned to the default entity — no orphans/NULLs left.
            assert c.execute(text("SELECT COUNT(*) FROM accounts WHERE entity_id IS NULL")).scalar() == 0
            owners = [r[0] for r in c.execute(text("SELECT entity_id FROM accounts")).all()]
            assert owners and all(o == default_id for o in owners)
            # Prior data preserved.
            assert c.execute(text("SELECT COUNT(*) FROM accounts")).scalar() == 2
            assert c.execute(text("SELECT COUNT(*) FROM holdings")).scalar() == 1
            assert c.execute(text("SELECT COUNT(*) FROM transactions")).scalar() == 1
            names = {r[0] for r in c.execute(text("SELECT name FROM accounts")).all()}
            assert names == {"Broker", "Bank"}
    finally:
        eng.dispose()


def test_trade_date_fx_columns_present_after_migrations(db_url):
    """§4.2 Unit A — the full chain adds fx_to_base + fx_base to transactions. The
    create_all-schema equivalence is asserted by test_migrated_head_matches_create_all;
    this pins the two new columns explicitly."""
    from sqlalchemy import inspect

    run_migrations(log=lambda *a: None)
    eng = create_engine(db_url)
    try:
        cols = {c["name"] for c in inspect(eng).get_columns("transactions")}
        assert {"fx_to_base", "fx_base"} <= cols
    finally:
        eng.dispose()


def test_upgrade_from_prior_head_adds_trade_date_fx_as_null(db_url):
    """§4.2 Unit A migration is additive and lossless, and the honest-unavailable backfill
    is NULL (never a fabricated historical rate).

    Build the DB at the pre-4.2 head, seed transactions (incl. a foreign-currency one),
    upgrade, and assert both columns exist, are NULL on every pre-existing row, and all
    prior data is preserved."""
    from alembic import command
    from sqlalchemy import inspect

    from app.db.migrate import _alembic_config

    cfg = _alembic_config()
    command.upgrade(cfg, "f4a9c2b71e08")  # head BEFORE trade-date FX (entities)
    eng = create_engine(db_url)
    try:
        cols = {c["name"] for c in inspect(eng).get_columns("transactions")}
        assert "fx_to_base" not in cols and "fx_base" not in cols
        with eng.begin() as c:
            c.execute(text("INSERT INTO accounts (name, kind, currency, created_at) "
                           "VALUES ('Broker','brokerage','SGD','2026-01-01 00:00:00')"))
            aid = c.execute(text("SELECT id FROM accounts")).scalar()
            # A domestic and a FOREIGN-currency transaction — both must end up NULL.
            c.execute(text(
                "INSERT INTO transactions (account_id, type, ts, quantity, price, fees, taxes, amount, currency) "
                "VALUES (:a,'buy','2019-03-01 00:00:00','10','100','0','0','1000','USD')"), {"a": aid})
            c.execute(text(
                "INSERT INTO transactions (account_id, type, ts, quantity, price, fees, taxes, amount, currency) "
                "VALUES (:a,'buy','2020-06-01 00:00:00','5','2000','0','0','10000','INR')"), {"a": aid})
    finally:
        eng.dispose()

    command.upgrade(cfg, "head")
    eng = create_engine(db_url)
    try:
        cols = {c["name"] for c in inspect(eng).get_columns("transactions")}
        assert {"fx_to_base", "fx_base"} <= cols
        with eng.connect() as c:
            assert c.execute(text("SELECT COUNT(*) FROM transactions")).scalar() == 2  # nothing lost
            # Honest-unavailable: NO row got a fabricated rate — both columns NULL everywhere.
            assert c.execute(text(
                "SELECT COUNT(*) FROM transactions WHERE fx_to_base IS NOT NULL OR fx_base IS NOT NULL")).scalar() == 0
            rows = c.execute(text("SELECT currency, amount, fx_to_base, fx_base FROM transactions "
                                  "ORDER BY ts")).all()
        assert {r[0] for r in rows} == {"USD", "INR"}                 # prior data preserved
        assert all(r[2] is None and r[3] is None for r in rows)       # unavailable on all
    finally:
        eng.dispose()


def test_merger_target_column_present_after_migrations(db_url):
    """§4.3 Unit 2a — the full chain adds transactions.related_instrument_id. The create_all
    equivalence is asserted by test_migrated_head_matches_create_all; this pins it explicitly."""
    from sqlalchemy import inspect

    run_migrations(log=lambda *a: None)
    eng = create_engine(db_url)
    try:
        cols = {c["name"] for c in inspect(eng).get_columns("transactions")}
        assert "related_instrument_id" in cols
    finally:
        eng.dispose()


def test_upgrade_from_prior_head_adds_merger_target_as_null(db_url):
    """§4.3 Unit 2a migration is additive and lossless: related_instrument_id is added
    nullable and left NULL on every pre-existing transaction."""
    from alembic import command
    from sqlalchemy import inspect

    from app.db.migrate import _alembic_config

    cfg = _alembic_config()
    command.upgrade(cfg, "a1c8f34b9d62")  # head BEFORE merger target (trade-date FX)
    eng = create_engine(db_url)
    try:
        cols = {c["name"] for c in inspect(eng).get_columns("transactions")}
        assert "related_instrument_id" not in cols
        with eng.begin() as c:
            c.execute(text("INSERT INTO accounts (name, kind, currency, created_at) "
                           "VALUES ('Broker','brokerage','SGD','2026-01-01 00:00:00')"))
            aid = c.execute(text("SELECT id FROM accounts")).scalar()
            c.execute(text(
                "INSERT INTO transactions (account_id, type, ts, quantity, price, fees, taxes, amount, currency) "
                "VALUES (:a,'buy','2026-01-02 00:00:00','10','100','0','0','1000','USD')"), {"a": aid})
    finally:
        eng.dispose()

    command.upgrade(cfg, "head")
    eng = create_engine(db_url)
    try:
        cols = {c["name"] for c in inspect(eng).get_columns("transactions")}
        assert "related_instrument_id" in cols
        with eng.connect() as c:
            assert c.execute(text("SELECT COUNT(*) FROM transactions")).scalar() == 1  # nothing lost
            row = c.execute(text("SELECT currency, related_instrument_id FROM transactions")).first()
        assert row[0] == "USD" and row[1] is None    # data preserved, new column NULL
    finally:
        eng.dispose()


def test_cost_basis_method_column_present_after_migrations(db_url):
    """§4.4 Unit A — the full chain adds accounts.cost_basis_method. The create_all
    equivalence is asserted by test_migrated_head_matches_create_all; this pins it explicitly."""
    from sqlalchemy import inspect

    run_migrations(log=lambda *a: None)
    eng = create_engine(db_url)
    try:
        cols = {c["name"] for c in inspect(eng).get_columns("accounts")}
        assert "cost_basis_method" in cols
    finally:
        eng.dispose()


def test_upgrade_from_prior_head_defaults_cost_basis_method_to_fifo(db_url):
    """§4.4 Unit A migration is additive and the backfill defaults every existing account to
    'fifo' (pure superset — current FIFO behaviour unchanged)."""
    from alembic import command
    from sqlalchemy import inspect

    from app.db.migrate import _alembic_config

    cfg = _alembic_config()
    command.upgrade(cfg, "b7d2f4a91c53")  # head BEFORE cost-basis method (merger target)
    eng = create_engine(db_url)
    try:
        cols = {c["name"] for c in inspect(eng).get_columns("accounts")}
        assert "cost_basis_method" not in cols
        with eng.begin() as c:
            for nm in ("Broker", "Bank"):
                c.execute(text("INSERT INTO accounts (name, kind, currency, created_at) "
                               "VALUES (:n,'brokerage','SGD','2026-01-01 00:00:00')"), {"n": nm})
    finally:
        eng.dispose()

    command.upgrade(cfg, "head")
    eng = create_engine(db_url)
    try:
        cols = {c["name"] for c in inspect(eng).get_columns("accounts")}
        assert "cost_basis_method" in cols
        with eng.connect() as c:
            assert c.execute(text("SELECT COUNT(*) FROM accounts")).scalar() == 2  # nothing lost
            rows = c.execute(text("SELECT name, cost_basis_method FROM accounts ORDER BY name")).all()
        assert {r[0] for r in rows} == {"Bank", "Broker"}          # data preserved
        assert all(r[1] == "fifo" for r in rows)                   # every existing account → FIFO
    finally:
        eng.dispose()


def test_annual_cost_bps_column_present_after_migrations(db_url):
    """§4.6 Unit A — the full chain adds instruments.annual_cost_bps. The create_all equivalence
    is asserted by test_migrated_head_matches_create_all; this pins it explicitly."""
    from sqlalchemy import inspect

    run_migrations(log=lambda *a: None)
    eng = create_engine(db_url)
    try:
        cols = {c["name"] for c in inspect(eng).get_columns("instruments")}
        assert "annual_cost_bps" in cols
    finally:
        eng.dispose()


def test_upgrade_from_prior_head_adds_annual_cost_bps_null(db_url):
    """§4.6 Unit A migration is additive and lossless: the column is absent before the upgrade,
    present after, and an existing instrument is preserved with annual_cost_bps NULL — 'not set',
    never a fabricated 0."""
    from alembic import command
    from sqlalchemy import inspect

    from app.db.migrate import _alembic_config

    cfg = _alembic_config()
    command.upgrade(cfg, "c9a1e4f78b62")  # head BEFORE instrument ongoing-cost
    eng = create_engine(db_url)
    try:
        cols = {c["name"] for c in inspect(eng).get_columns("instruments")}
        assert "annual_cost_bps" not in cols
        with eng.begin() as c:
            c.execute(text("INSERT INTO instruments (symbol, name, asset_class, currency, is_manual_price) "
                           "VALUES ('VWRA','Vanguard All-World','etf','USD',false)"))  # boolean: portable Postgres+SQLite
    finally:
        eng.dispose()

    command.upgrade(cfg, "head")
    eng = create_engine(db_url)
    try:
        cols = {c["name"] for c in inspect(eng).get_columns("instruments")}
        assert "annual_cost_bps" in cols
        with eng.connect() as c:
            assert c.execute(text("SELECT COUNT(*) FROM instruments")).scalar() == 1  # nothing lost
            row = c.execute(text("SELECT symbol, annual_cost_bps FROM instruments")).one()
        assert row[0] == "VWRA"          # data preserved
        assert row[1] is None            # existing instrument stays 'not set' (NULL, not 0)
    finally:
        eng.dispose()
