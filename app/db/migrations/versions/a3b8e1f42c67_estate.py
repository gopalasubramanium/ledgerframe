# SPDX-License-Identifier: AGPL-3.0-or-later
"""estate — family readiness: profile, contacts, documents (W4)

Additive, idempotent. Three new tables; nothing existing is touched.

Revision ID: a3b8e1f42c67
Revises: f1a2c7d5e9b3
Create Date: 2026-07-05
"""
import sqlalchemy as sa
from alembic import op

revision = "a3b8e1f42c67"
down_revision = "f1a2c7d5e9b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    have = set(sa.inspect(bind).get_table_names())
    if "estate_profile" not in have:
        op.create_table(
            "estate_profile",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("will_status", sa.String(length=16), nullable=False, server_default="none"),
            sa.Column("will_location", sa.String(length=160), nullable=True),
            sa.Column("executor", sa.String(length=120), nullable=True),
            sa.Column("last_reviewed", sa.String(length=10), nullable=True),
            sa.Column("next_review_date", sa.String(length=10), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
        )
    if "estate_contact" not in have:
        op.create_table(
            "estate_contact",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("relationship", sa.String(length=60), nullable=True),
            sa.Column("roles", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("phone", sa.String(length=40), nullable=True),
            sa.Column("email", sa.String(length=120), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
    if "estate_document" not in have:
        op.create_table(
            "estate_document",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("title", sa.String(length=120), nullable=False),
            sa.Column("category", sa.String(length=24), nullable=False, server_default="other"),
            sa.Column("location", sa.String(length=160), nullable=True),
            sa.Column("status", sa.String(length=12), nullable=False, server_default="present"),
            sa.Column("review_date", sa.String(length=10), nullable=True),
            sa.Column("related_to", sa.String(length=120), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    op.drop_table("estate_document")
    op.drop_table("estate_contact")
    op.drop_table("estate_profile")
