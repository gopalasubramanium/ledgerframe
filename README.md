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

## Development

**One command runs everything:**

```bash
make dev            # backend (uvicorn :8321) + frontend (Vite :5173), prefixed logs, Ctrl+C stops both
```

On first run `make dev` (`scripts/dev.sh`) creates a dev `.env` from
`.env.example` with local defaults — a data dir **under your home**
(`~/.local/share/ledgerframe-dev`, never the appliance `/mnt/...`) and a
generated strong `SECRET_KEY` — and tells you it did. Real deployments keep
their own `.env` (and the `/mnt` data dir) unchanged.

> The frontend calls the backend through a Vite dev proxy, so **both must be
> running** — starting only Vite yields 500s from the API. `make dev` starts
> both.

### One-time setup

```bash
uv venv .venv && uv pip install -e '.[dev]'   # backend deps (or: python -m venv + pip)
( cd frontend && npm install )                # frontend deps
```

### Useful targets

```bash
make test              # backend test suite (pytest)
make lint              # ruff
make api-contract-check # fail if the frozen OpenAPI contract is stale
make migrate           # alembic upgrade head
( cd frontend && npm run check )   # frontend lint + typecheck + token-drift + tests
```

The API is a FastAPI app (`app.main:app`); it runs headless (no frontend
required). Migrations use Alembic; the DB URL comes from settings at runtime.

## Licence

AGPL-3.0-or-later.
