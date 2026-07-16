# SPDX-License-Identifier: AGPL-3.0-or-later
"""estate — retire estate_contact.relationship, folding it into notes (page-estate §9-5)

D-010/D-063 + MASTER-DATA say `relationship` is DROPPED (roles is the fixed vocabulary;
relationship was free text that never mapped into it). But free text cannot be re-keyed into
the fixed `roles` vocab, so the drop must not destroy it — **AMENDMENT E** (owner, 2026-07-16):

    before the drop, every contact with a non-empty `relationship` gets it FOLDED into its
    `notes` field, prefixed `Relationship: «value»` (newline-appended if notes already exist).

Data-preserving and idempotent (guarded on the column's presence, so a create_all-bootstrapped
DB that never had the column is a clean no-op). The downgrade re-adds the column empty — the fold
is one-way (the original free text now lives inside notes and is not machine-separable back out).

Revision ID: f2b7c1a9e304
Revises: f9e1a2b3c4d5
Create Date: 2026-07-16
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "f2b7c1a9e304"
down_revision = "f9e1a2b3c4d5"
branch_labels = None
depends_on = None


def _has_column(conn, table: str, column: str) -> bool:
    return column in {c["name"] for c in sa.inspect(conn).get_columns(table)}


def upgrade() -> None:
    conn = op.get_bind()
    if not _has_column(conn, "estate_contact", "relationship"):
        return  # already dropped / adopted from create_all — nothing to fold.

    # Fold every non-empty relationship into notes BEFORE the column is dropped (Amendment E).
    rows = conn.execute(sa.text(
        "SELECT id, relationship, notes FROM estate_contact "
        "WHERE relationship IS NOT NULL AND TRIM(relationship) <> ''"
    )).fetchall()
    for rid, rel, notes in rows:
        folded = f"Relationship: {(rel or '').strip()}"
        new_notes = f"{notes}\n{folded}" if (notes and str(notes).strip()) else folded
        conn.execute(sa.text("UPDATE estate_contact SET notes = :n WHERE id = :i"),
                     {"n": new_notes, "i": rid})

    # SQLite cannot DROP COLUMN in place — batch mode recreates the table portably.
    with op.batch_alter_table("estate_contact") as batch:
        batch.drop_column("relationship")


def downgrade() -> None:
    conn = op.get_bind()
    if _has_column(conn, "estate_contact", "relationship"):
        return
    # Re-add empty; the fold is one-way (the value now lives inside notes).
    op.add_column("estate_contact", sa.Column("relationship", sa.String(length=60), nullable=True))
