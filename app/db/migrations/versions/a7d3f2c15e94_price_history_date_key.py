# SPDX-License-Identifier: AGPL-3.0-or-later
"""§14dr-25: price_history date-keying + demo-residue dedup

The `(instrument_id, interval, ts)` unique key is on the exact timestamp, so a
trading date stored under two timestamps (legacy DEMO at a non-midnight time-of-day
+ REAL alphavantage/eodhd at 00:00:00 UTC) kept TWO rows at two price levels — the
served "comb" (data-feed-routing §27).

This migration (additive + idempotent, ADR-0001 chain):
  • adds `price_history.source` (provider provenance; NULL for legacy rows), and
  • dedups existing DAILY rows to one-per-trading-date — a REAL row (midnight ts)
    supersedes a DEMO row (non-midnight ts); the kept row's ts is normalised to
    00:00:00 UTC so the existing unique index is date-effective for daily going
    forward. Intraday intervals (R-42) are untouched.

Idempotent: a fresh create_all DB (empty price_history, `source` already present)
is a no-op; a second run finds no duplicates.

Revision ID: a7d3f2c15e94
Revises: c1d4e7a90f38
Create Date: 2026-07-18
"""
from collections import defaultdict
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

import app.db.base  # noqa: F401 — registers custom column types
from app.db.base import UTCDateTime

revision = "a7d3f2c15e94"
down_revision = "c1d4e7a90f38"
branch_labels = None
depends_on = None

_DAILY = ("1d", "1w", "1mo")


def _is_midnight(dt) -> bool:
    return dt.hour == 0 and dt.minute == 0 and dt.second == 0 and (dt.microsecond or 0) == 0


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "price_history" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("price_history")}
    if "source" not in cols:
        op.add_column("price_history", sa.Column("source", sa.String(20), nullable=True))

    ph = sa.Table(
        "price_history", sa.MetaData(),
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("instrument_id", sa.Integer),
        sa.Column("interval", sa.String(10)),
        sa.Column("ts", UTCDateTime),
    )
    rows = bind.execute(
        sa.select(ph.c.id, ph.c.instrument_id, ph.c.interval, ph.c.ts).where(ph.c.interval.in_(_DAILY))
    ).fetchall()

    groups: dict = defaultdict(list)
    for r in rows:
        ts = r.ts if r.ts.tzinfo else r.ts.replace(tzinfo=UTC)
        groups[(r.instrument_id, r.interval, ts.date())].append((r.id, ts))

    to_delete: list[int] = []
    to_midnight: list[tuple[int, object]] = []
    for (_instr, _interval, d), grp in groups.items():
        mids = [gid for gid, ts in grp if _is_midnight(ts)]
        if len(grp) > 1:
            # REAL (midnight) supersedes DEMO (non-midnight). Keep one, delete the rest.
            if mids:
                keep = min(mids)
            else:
                keep = min(gid for gid, _ in grp)
                to_midnight.append((keep, d))
            to_delete += [gid for gid, _ in grp if gid != keep]
        else:
            gid, ts = grp[0]
            if not _is_midnight(ts):
                to_midnight.append((gid, d))

    for i in range(0, len(to_delete), 500):  # chunk under SQLite's bind-param limit
        bind.execute(ph.delete().where(ph.c.id.in_(to_delete[i:i + 500])))
    for gid, d in to_midnight:
        bind.execute(
            ph.update().where(ph.c.id == gid).values(ts=datetime(d.year, d.month, d.day, tzinfo=UTC))
        )

    print(f"[price_history_date_key] purged {len(to_delete)} duplicate daily candle(s); "
          f"normalised {len(to_midnight)} timestamp(s) to midnight UTC")


def downgrade() -> None:
    # The dedup/normalisation is not reversible (deleted demo residue is regenerable
    # from the demo generator; real data is preserved). Only the additive column drops.
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "price_history" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("price_history")}
        if "source" in cols:
            with op.batch_alter_table("price_history") as batch:
                batch.drop_column("source")
