.DEFAULT_GOAL := help

# Run everything against the project's own venv only. This neutralises a
# polluted PYTHONPATH (e.g. a globally sourced ROS install) that would
# otherwise leak system packages and pytest plugins into our environment.
export PYTHONPATH :=

.PHONY: help install run dev lint format typecheck test test-cov check \
        migration migrate downgrade seed db-create db-shell clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Create the virtualenv and install all dependencies
	uv sync

run: ## Run the API server
	uv run institute-admin-api

dev: ## Run the API server with autoreload
	uv run uvicorn institute_administration.main:app --reload --host 0.0.0.0 --port 8000

lint: ## Lint the codebase
	uv run ruff check .

format: ## Auto-format and fix imports
	uv run ruff format .
	uv run ruff check --fix .

typecheck: ## Run static type checks
	uv run mypy src

test: ## Run the test suite
	uv run pytest

test-cov: ## Run tests with a coverage report
	uv run pytest --cov --cov-report=term-missing

check: lint typecheck test ## Run all quality gates

migration: ## Autogenerate a migration: make migration m="add users table"
	uv run alembic revision --autogenerate -m "$(m)"

migrate: ## Apply all pending migrations
	uv run alembic upgrade head

downgrade: ## Revert the last migration
	uv run alembic downgrade -1

seed: ## Create the bootstrap super-admin user (idempotent)
	uv run institute-admin-seed

db-create: ## Create the local Postgres role and database (requires a running server)
	createdb $(POSTGRES_DB) 2>/dev/null || true

db-shell: ## Open a psql shell against the configured database
	psql "postgresql://$(POSTGRES_USER):$(POSTGRES_PASSWORD)@$(POSTGRES_HOST):$(POSTGRES_PORT)/$(POSTGRES_DB)"

clean: ## Remove caches and build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov dist build
