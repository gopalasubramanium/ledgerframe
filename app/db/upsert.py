# SPDX-License-Identifier: AGPL-3.0-or-later
"""Dialect-aware INSERT … ON CONFLICT DO UPDATE.

The SQLite and Postgres dialects expose the *same* ``on_conflict_do_update(index_elements=…,
set_=…)`` API, so callers differ only in which ``insert()`` constructor they use. SQLite
behaviour is unchanged (it still builds the SQLite construct); Postgres gets the Postgres one
(a SQLite ``OnConflictDoUpdate`` cannot be compiled by the Postgres dialect).
"""

from __future__ import annotations


def upsert(model):
    """Return ``insert(model)`` for the active dialect, ready for ``.on_conflict_do_update``."""
    from app.core.config import get_settings

    if get_settings().is_sqlite:
        from sqlalchemy.dialects.sqlite import insert
    else:
        from sqlalchemy.dialects.postgresql import insert
    return insert(model)
