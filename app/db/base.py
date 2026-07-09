# SPDX-License-Identifier: AGPL-3.0-or-later
"""SQLAlchemy engine, session factory, and a Decimal-aware base.

Money is stored as TEXT and round-tripped through ``decimal.Decimal`` so we never
lose precision to SQLite's float affinity.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import TypeDecorator, event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import DateTime as SA_DateTime
from sqlalchemy.types import String

from app.core.config import get_settings


class DecimalText(TypeDecorator):
    """Exact Decimal storage across backends — stored as TEXT, round-tripped through ``str``.

    Text on *every* dialect (not NUMERIC on Postgres): the Alembic migration files create these
    money columns as ``sa.Text`` (TEXT), so a real deployment — which boots via migrations —
    stores money as text on Postgres too. Keeping the ORM type text-only means the ``create_all``
    schema matches the migrated schema exactly, and money is the identical minimal Decimal on
    SQLite and Postgres (a native NUMERIC(38,12) would come back scale-padded, e.g.
    ``68000.500000000000``, diverging from the migration path and from SQLite). The Python value
    is always a ``Decimal``.
    """

    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value if isinstance(value, Decimal) else Decimal(str(value))


class UTCDateTime(TypeDecorator):
    """Store datetimes as UTC; always return them tz-aware (UTC).

    SQLite has no native tz type and drops tzinfo on round-trip, so a value
    written aware comes back naive — mixing the two raises 'can't compare
    offset-naive and offset-aware datetimes'. Normalises the boundary:
    aware-in (converted to UTC) / naive-in (assumed UTC) on write, always
    aware-UTC on read. Mirrors DecimalText's approach for Decimal precision.
    """

    impl = SA_DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is not None:
            value = value.astimezone(UTC)
        return value.replace(tzinfo=None)  # store naive-UTC (SQLite's reality)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=UTC)  # always return aware-UTC


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


def _make_engine():
    settings = get_settings()
    # SQLite-only connect args; other backends (Postgres etc., §2.2) get driver defaults.
    if settings.is_sqlite:
        settings.db_path.parent.mkdir(parents=True, exist_ok=True)
        connect_args = {"check_same_thread": False, "timeout": 30}
    else:
        connect_args = {}
    return create_async_engine(settings.db_url, echo=False, connect_args=connect_args)


_engine = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = _make_engine()
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _sessionmaker


async def dispose_engine() -> None:
    """Dispose the cached engine and clear the singletons.

    Used by the test suite between tests: asyncpg connections are bound to the event loop
    that created them, and pytest-asyncio uses a fresh loop per test, so the pooled engine
    must be rebuilt each time. Harmless in production (a no-op unless an engine exists)."""
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _sessionmaker = None


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yields a session, commits on success, rolls back on error."""
    async with get_sessionmaker()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Enable WAL + foreign keys on every SQLite connection for concurrency & integrity.
# Guarded to SQLite (§2.2): PRAGMAs are invalid on Postgres etc.
@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _record):
    if "sqlite" not in type(dbapi_conn).__module__:
        return
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA foreign_keys=ON")
    cur.execute("PRAGMA synchronous=NORMAL")
    # Wait (don't error) when another connection holds a write lock — e.g. the API and
    # worker migrating concurrently at startup. Applies to every SQLite engine, incl. Alembic.
    cur.execute("PRAGMA busy_timeout=30000")
    cur.close()
