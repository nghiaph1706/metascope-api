.PHONY: help dev up down logs restart migrate migration db-reset seed \
        test test-unit test-integration test-cov lint format typecheck \
        worker shell clean ensure-env

# ── Prerequisites ────────────────────────────────────────────────
ensure-env:
	@test -f .env || (cp .env.example .env && echo "📋 Created .env from .env.example — edit RIOT_API_KEY")

# ── Help ─────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "MetaScope API — Available commands"
	@echo "════════════════════════════════════════"
	@echo ""
	@echo "  Development (all run inside Docker)"
	@echo "  ─────────────────────────────────────"
	@echo "  make dev          Start full stack (API + DB + Redis + Workers)"
	@echo "  make worker       Start Celery worker"
	@echo "  make shell        Python shell inside API container"
	@echo ""
	@echo "  Docker"
	@echo "  ─────────────────────────────────────"
	@echo "  make up           docker compose up -d (all services)"
	@echo "  make down         docker compose down"
	@echo "  make logs         docker compose logs -f"
	@echo "  make restart      down + up"
	@echo ""
	@echo "  Database"
	@echo "  ─────────────────────────────────────"
	@echo "  make migrate      Run pending migrations"
	@echo "  make migration    Create new migration (msg='')"
	@echo "  make db-reset     Drop + recreate DB (dev only!)"
	@echo "  make seed         Seed champion/item data from DataDragon"
	@echo ""
	@echo "  Testing"
	@echo "  ─────────────────────────────────────"
	@echo "  make test         Run all tests"
	@echo "  make test-unit    Run unit tests only"
	@echo "  make test-int     Run integration tests only"
	@echo "  make test-cov     Tests + HTML coverage report"
	@echo ""
	@echo "  Code Quality"
	@echo "  ─────────────────────────────────────"
	@echo "  make lint         ruff check"
	@echo "  make format       ruff format"
	@echo "  make typecheck    mypy strict"
	@echo "  make check        lint + typecheck (pre-commit)"
	@echo ""

# ── Development (all commands run inside Docker) ────────────────
dev: ensure-env
	docker compose up -d
	@echo "✅ Dev stack running. API: http://localhost:8000 | Flower: http://localhost:5555"

worker:
	docker compose up -d celery_worker

beat:
	docker compose up -d celery_beat

flower:
	docker compose up -d flower

shell:
	docker compose exec api python -c "import asyncio; from app.core.database import async_session_factory; import IPython; IPython.embed()"

# ── Docker ───────────────────────────────────────────────────────
up: ensure-env
	docker compose up -d
	@echo "✅ Stack started. API: http://localhost:8000 | Flower: http://localhost:5555"

down:
	docker compose down

logs:
	docker compose logs -f

logs-api:
	docker compose logs -f api

logs-worker:
	docker compose logs -f celery_worker

restart: down up

ps:
	docker compose ps

# ── Database (run inside Docker) ─────────────────────────────────
migrate:
	docker compose exec api alembic upgrade head
	@echo "✅ Migrations complete"

migration:
	@test -n "$(msg)" || (echo "❌ Usage: make migration msg='your message'" && exit 1)
	docker compose exec api alembic revision --autogenerate -m "$(msg)"

db-reset:
	@echo "⚠️  This will DROP the database. Press Ctrl+C to cancel..."
	@sleep 3
	docker compose exec api alembic downgrade base
	docker compose exec api alembic upgrade head
	$(MAKE) seed
	@echo "✅ Database reset complete"

seed:
	docker compose exec api python -m app.scripts.seed_champions
	@echo "✅ Champions and items seeded"

# ── Testing (run inside Docker) ──────────────────────────────────
test:
	docker compose exec api pytest

test-unit:
	docker compose exec api pytest tests/ -v -k "not test_router"

test-int:
	docker compose exec api pytest tests/ -v -k "test_router"

test-cov:
	docker compose exec api pytest --cov=app --cov-report=html:htmlcov --cov-report=term-missing
	@echo "📊 Coverage report: htmlcov/index.html"

test-fast:
	docker compose exec api pytest -x --no-cov -q

# ── Code Quality (run inside Docker) ─────────────────────────────
lint:
	docker compose exec api ruff check app/ tests/

lint-fix:
	docker compose exec api ruff check --fix app/ tests/

format:
	docker compose exec api ruff format app/ tests/

typecheck:
	docker compose exec api mypy app/

check: lint typecheck
	@echo "✅ All checks passed"

# ── Utilities ────────────────────────────────────────────────────
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .mypy_cache .ruff_cache .pytest_cache htmlcov .coverage

install:
	docker compose exec api pip install -e ".[dev]"

setup-hooks:
	pip install pre-commit
	pre-commit install
	pre-commit install --hook-type commit-msg
	@echo "✅ Pre-commit hooks installed"

install-prod:
	docker compose exec api pip install -e "."
