PYTHON ?= .venv/bin/python

.PHONY: help dev test lint api-contract api-contract-check migrate

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN{FS=":.*?## "}{printf "  %-20s %s\n", $$1, $$2}'

dev: ## Run backend + frontend together (dev; creates a local .env on first run)
	@bash scripts/dev.sh

test: ## Run the backend test suite
	$(PYTHON) -m pytest -q

lint: ## Ruff lint
	$(PYTHON) -m ruff check .

api-contract: ## Re-freeze the OpenAPI contract (docs/specs/API-CONTRACT.json)
	$(PYTHON) scripts/check_api_contract.py --write

api-contract-check: ## Fail if the committed OpenAPI contract is stale (drift check)
	$(PYTHON) scripts/check_api_contract.py

migrate: ## Upgrade the database to the latest migration
	$(PYTHON) -m alembic upgrade head
