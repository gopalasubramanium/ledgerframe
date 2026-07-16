# SPDX-License-Identifier: AGPL-3.0-or-later
"""institution FK re-pointing — fold accounts.institution + insurance_policy.insurer into
the master, then DROP both String columns (D-008, page-accounts §9-1 + Amendment F, commit 3)

The three-step fold (Amendment-E fold-then-drop): SEED the ``institutions`` master from the
distinct free-text values of BOTH ``accounts.institution`` and ``insurance_policy.insurer``
(trimmed, whitespace-collapsed, case-insensitive; FIRST-SEEN casing survives — the SAME
``normalize_institution_name`` the runtime write path uses, so seed keys and write keys can
never diverge) → ADD nullable ``institution_id`` FKs + RE-POINT every row by normalized key →
DROP both String columns. Values migrate IN, never destroyed.

Idempotent and number-neutral: fresh DBs are create_all-bootstrapped onto the NEW FK schema
(no String columns, nothing to fold), so this is a no-op there; it does real work only on an
adopted DB that still carries the old String columns.

Revision ID: b3e2f1a9c740
Revises: a2f1c9d47b60
Create Date: 2026-07-16
"""
import sqlalchemy as sa
from alembic import op

from app.services.institutions import normalize_institution_name

revision = "b3e2f1a9c740"
down_revision = "a2f1c9d47b60"
branch_labels = None
depends_on = None

# (table, free-text String column) pairs folded into the master.
_SOURCES = (("accounts", "institution"), ("insurance_policy", "insurer"))


def _seed_and_repoint(bind) -> None:
    """Seed the master from BOTH String columns (first-seen casing wins across the two, in
    _SOURCES order) and re-point every row's ``institution_id`` by normalized key. Assumes the
    ``institution_id`` columns already exist. Pure SQL so it is unit-testable in isolation."""
    insp = sa.inspect(bind)

    # 1. SEED — one master row per normalized key; first value seen (accounts, then policies) wins.
    existing_keys = {row[0] for row in bind.execute(sa.text("SELECT name_key FROM institutions"))}
    for table, col in _SOURCES:
        if col not in {c["name"] for c in insp.get_columns(table)}:
            continue
        for (raw,) in bind.execute(
                sa.text(f"SELECT DISTINCT {col} FROM {table} WHERE {col} IS NOT NULL")):
            display, key = normalize_institution_name(raw)
            if display and key not in existing_keys:
                bind.execute(sa.text(
                    "INSERT INTO institutions (name, name_key, created_at) "
                    "VALUES (:n, :k, CURRENT_TIMESTAMP)"), {"n": display, "k": key})
                existing_keys.add(key)

    key_to_id = {row[0]: row[1]
                 for row in bind.execute(sa.text("SELECT name_key, id FROM institutions"))}

    # 2. RE-POINT — every row's institution_id by normalized key.
    for table, col in _SOURCES:
        if col not in {c["name"] for c in insp.get_columns(table)}:
            continue
        for (rid, raw) in bind.execute(
                sa.text(f"SELECT id, {col} FROM {table} WHERE {col} IS NOT NULL")):
            _, key = normalize_institution_name(raw)
            iid = key_to_id.get(key)
            if iid is not None:
                bind.execute(sa.text(
                    f"UPDATE {table} SET institution_id = :iid WHERE id = :rid"),
                    {"iid": iid, "rid": rid})


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    acc_cols = {c["name"] for c in insp.get_columns("accounts")}
    pol_cols = {c["name"] for c in insp.get_columns("insurance_policy")}

    # No-op on a fresh create_all DB (new FK schema, no String columns to fold).
    if "institution" not in acc_cols and "insurer" not in pol_cols:
        return
    if "institutions" not in set(insp.get_table_names()):
        return  # the commit-1 migration must run first

    # ADD the FK columns + indexes (before folding, so re-point can write them). NATIVE ALTER
    # (not batch/move-and-copy): rebuilding `accounts`/`insurance_policy` under SQLite would trip
    # the child FK constraints (holdings/transactions → accounts) when those rows exist. SQLite
    # 3.35+ ADD/DROP COLUMN is native and leaves child FKs untouched.
    if "institution_id" not in acc_cols:
        op.add_column("accounts", sa.Column("institution_id", sa.Integer(), nullable=True))
        op.create_index("ix_accounts_institution_id", "accounts", ["institution_id"])
    if "institution_id" not in pol_cols:
        op.add_column("insurance_policy", sa.Column("institution_id", sa.Integer(), nullable=True))
        op.create_index("ix_insurance_policy_institution_id", "insurance_policy", ["institution_id"])

    _seed_and_repoint(bind)

    # 3. DROP the old String columns (fold-then-drop; values already migrated IN).
    if "institution" in acc_cols:
        op.drop_column("accounts", "institution")
    if "insurer" in pol_cols:
        op.drop_column("insurance_policy", "insurer")


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    acc_cols = {c["name"] for c in insp.get_columns("accounts")}
    pol_cols = {c["name"] for c in insp.get_columns("insurance_policy")}

    if "institution" not in acc_cols:
        op.add_column("accounts", sa.Column("institution", sa.String(length=120), nullable=True))
        bind.execute(sa.text("UPDATE accounts SET institution = "
                             "(SELECT name FROM institutions WHERE institutions.id = accounts.institution_id)"))
    if "insurer" not in pol_cols:
        op.add_column("insurance_policy", sa.Column("insurer", sa.String(length=120), nullable=True))
        bind.execute(sa.text("UPDATE insurance_policy SET insurer = "
                             "(SELECT name FROM institutions WHERE institutions.id = insurance_policy.institution_id)"))

    for tbl, idx in (("accounts", "ix_accounts_institution_id"),
                     ("insurance_policy", "ix_insurance_policy_institution_id")):
        if idx in {i["name"] for i in insp.get_indexes(tbl)}:
            op.drop_index(idx, table_name=tbl)
    op.drop_column("accounts", "institution_id")
    op.drop_column("insurance_policy", "institution_id")
