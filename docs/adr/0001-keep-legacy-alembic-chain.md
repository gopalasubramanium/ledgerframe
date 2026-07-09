# ADR 0001 — Keep the legacy Alembic chain intact; v2 migrations build on top

- **Status:** Accepted
- **Date:** 2026-07-09
- **Context milestone:** Backend copy-in (`docs/plans/backend-copy-in.md`, Phase A)

## Context

The v2 backend is copied faithfully from the v1 source
(`~/Documents/github/LedgerFrame`, read-only). v1 ships a **single linear Alembic
chain of 24 migrations**, base `c8a035ade752` → head **`d1e7a4c02f95`**
(`instrument_annual_cost_bps`), with `script_location = app/db/migrations`.

An existing owner may already be running a v1 database. v2 must not force a
destructive re-initialisation of that data.

Two options were considered:

1. **Squash/reset** the migration history into a fresh v2 baseline (single
   `initial` migration reflecting the current schema).
2. **Keep the chain intact** and add new v2 migrations on top of the existing
   head.

## Decision

**Keep the legacy Alembic chain intact.** v2 introduces **no** history rewrite.
Every v2 schema change is a **new migration whose `down_revision` is the current
head** (initially `d1e7a4c02f95`). An existing v1 database therefore
`alembic upgrade head`s **in place**, applying only the new v2 migrations; a
fresh database replays the whole chain to the same schema.

The first v2 migration on top of the head is the Phase B prune (dropping the
tables retired by D-014..D-017), which is **additive and data-guarded** (it
fails loudly rather than dropping a non-empty table).

## Consequences

- **Upgrades in place.** A real v1 DB keeps its data and moves forward with no
  manual export/import.
- **Continuity of provenance.** The historical migrations remain the audit trail
  for how the schema reached its current shape (referenced by MASTER-DATA and
  DECISIONS, e.g. the `a3d21f7e5b10` taxonomy backfill).
- **New head discipline.** Contributors branch new migrations from the live head;
  `alembic heads` must always report exactly one head (no divergent branches).
- **Cost:** the chain is longer than a squashed baseline would be; a fresh
  install replays 24+ migrations. Acceptable for a single-user appliance.

## Alternatives rejected

- **Squash to a fresh baseline** — rejected: it would either strand existing v1
  databases or require a bespoke stamp/migration to reconcile them, adding risk
  for no benefit on a single-user appliance.
