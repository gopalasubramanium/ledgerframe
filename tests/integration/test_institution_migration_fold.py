# SPDX-License-Identifier: AGPL-3.0-or-later
"""Isolated proof of the commit-3 migration's data fold (page-accounts §9-1 + Amendment F).

The integration suite runs on create_all (the NEW FK schema), where the migration is a no-op,
so the fold logic is proven here directly against a throwaway SQLite DB carrying the OLD
free-text columns: the seed collapses "DBS "/"dbs" to ONE row with first-seen casing, and every
row is re-pointed by normalized key across BOTH source columns.
"""

from __future__ import annotations

import sqlalchemy as sa

from app.db.migrations.versions.b3e2f1a9c740_institution_fk import _seed_and_repoint


def test_fold_collapses_case_whitespace_and_repoints_both_tables():
    eng = sa.create_engine("sqlite://")  # in-memory
    with eng.begin() as conn:
        conn.execute(sa.text(
            "CREATE TABLE institutions (id INTEGER PRIMARY KEY, name TEXT, name_key TEXT, created_at TEXT)"))
        conn.execute(sa.text(
            "CREATE TABLE accounts (id INTEGER PRIMARY KEY, institution TEXT, institution_id INTEGER)"))
        conn.execute(sa.text(
            "CREATE TABLE insurance_policy (id INTEGER PRIMARY KEY, insurer TEXT, institution_id INTEGER)"))
        # First-seen casing is "DBS " (trimmed → "DBS"); the "dbs" variant must collapse onto it.
        conn.execute(sa.text("INSERT INTO accounts (id, institution) VALUES (1, 'DBS '), (2, 'dbs'), (3, NULL)"))
        # The policy references the SAME institution by another casing → one shared master row.
        conn.execute(sa.text("INSERT INTO insurance_policy (id, insurer) VALUES (10, 'DBS')"))

        _seed_and_repoint(conn)

        insts = conn.execute(sa.text("SELECT name, name_key FROM institutions")).all()
        # Exactly one master row, first-seen casing preserved.
        assert [(n, k) for n, k in insts] == [("DBS", "dbs")]
        iid = conn.execute(sa.text("SELECT id FROM institutions")).scalar_one()

        # Both accounts (any casing) re-point to it; the NULL account stays NULL.
        acc = dict(conn.execute(sa.text("SELECT id, institution_id FROM accounts")).all())
        assert acc == {1: iid, 2: iid, 3: None}
        # The policy re-points to the SAME shared row (one master, both FK columns).
        pol = conn.execute(sa.text("SELECT institution_id FROM insurance_policy WHERE id = 10")).scalar_one()
        assert pol == iid
