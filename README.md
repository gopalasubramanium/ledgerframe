# LedgerFrame v2

A single-user, local-first **wealth-reporting appliance**. It consolidates an
individual's (and their household's) holdings across accounts, instruments, and
currencies into one private, honest picture — net worth, portfolio analytics,
allocation and policy drift, liquidity and cash runway, realised/unrealised P/L
for an accountant, insurance and estate readiness, and a grounded AI briefing.

**It reports; it does not act.** It never executes trades, never advises, and
never fabricates a number. See `docs/specs/PRODUCT-SPEC.md` for the normative
product definition and the seven Product Guarantees.

## Status

v2 is being rebuilt on the v1 backend, brought in under
`docs/plans/backend-copy-in.md`. The authoritative specifications live in
`docs/specs/`; product decisions in `docs/audit/DECISIONS.md`.

## Backend (development)

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'
pytest -q
```

The API is a FastAPI app (`app.main:app`); it runs headless (no frontend
required). Database migrations use Alembic (`alembic upgrade head`); the DB URL
is supplied at runtime from settings.

## Licence

AGPL-3.0-or-later.
