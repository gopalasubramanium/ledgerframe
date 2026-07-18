# SPDX-License-Identifier: AGPL-3.0-or-later
"""R-43 F-4 — ingest INTEGRITY guards (freshness + non-truncation).

Provenance is not integrity. The F-4 defect: ECB's own edge served a SIX-YEAR-STALE, corrupt object
for the legacy ``eurofxref-hist.csv`` URL (latest data 2010, a counting-pattern nonsense row) while
the maintained ``.zip`` was current and genuine — the source was authentic, the payload was rotten.
So every ingest must verify FRESHNESS (the latest date is recent) and NON-TRUNCATION (the parse
produced a plausible number of rows) before trusting a fetched series, or it silently persists
garbage. These are the shared primitives; each parser/ingest calls them.
"""

from __future__ import annotations

from datetime import date, datetime


class IngestIntegrityError(RuntimeError):
    """A fetched series failed a freshness/sanity check — refuse it rather than ingest a
    stale/corrupt or truncated payload (F-4). The caller degrades to a served error + retry, never
    a silent bad write."""

    def __init__(self, source: str, reason: str) -> None:
        super().__init__(f"{source}: {reason}")
        self.source = source
        self.reason = reason


def _as_date(d: date | datetime | str) -> date:
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, str):
        return date.fromisoformat(d[:10])
    return d


def assert_not_truncated(parsed_count: int, *, source: str, minimum: int = 1) -> None:
    """Refuse a payload that parsed to fewer than ``minimum`` rows — an empty/truncated/malformed
    response (a hung or half-served download) must never be trusted as a real series."""
    if parsed_count < minimum:
        raise IngestIntegrityError(
            source, f"parsed {parsed_count} row(s) (< {minimum}) — refusing a truncated/malformed payload")


def assert_fresh(latest: date | datetime | str | None, *, now: datetime, max_age_days: int,
                 source: str) -> None:
    """Refuse a series whose newest date is more than ``max_age_days`` older than ``now`` — the
    F-4 stale-corrupt tell (the legacy CSV's newest date was 2010). ``None`` (no dated rows) is
    also refused: an unparseable/empty payload is never a fresh one."""
    if latest is None:
        raise IngestIntegrityError(source, "no dated rows parsed — empty or malformed payload")
    ld = _as_date(latest)
    age = (_as_date(now) - ld).days
    if age > max_age_days:
        raise IngestIntegrityError(
            source, f"latest date {ld.isoformat()} is {age} days stale (> {max_age_days}) — "
                    "refusing a stale/corrupt series (provenance is not integrity)")
