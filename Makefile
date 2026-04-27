.PHONY: help dev build up down logs ps migrate migrate-create shell-api shell-db test lint format

help:
	@echo "ReZeb — available commands:"
	@echo "  make dev          — start full dev stack (docker-compose up --build)"
	@echo "  make up           — start stack (no rebuild)"
	@echo "  make down         — stop stack"
	@echo "  make logs         — follow all logs"
	@echo "  make logs-api     — follow API logs"
	@echo "  make ps           — show running containers"
	@echo "  make migrate      — run alembic upgrade head"
	@echo "  make migrate-create msg=<name> — create new migration"
	@echo "  make shell-api    — bash in api container"
	@echo "  make shell-db     — psql in postgres container"
	@echo "  make test         — run pytest in api container"
	@echo "  make lint         — run ruff + mypy"
	@echo "  make format       — run ruff format"
	@echo "  make seed         — seed dev data"

dev:
	cp -n .env.example .env || true
	docker compose up --build -d
	@echo "Waiting for services..."
	sleep 5
	$(MAKE) migrate
	@echo ""
	@echo "✓ API:      http://localhost:8000/docs"
	@echo "✓ Frontend: http://localhost:3000"
	@echo "✓ MinIO:    http://localhost:9001  (minioadmin / minioadmin)"

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

logs-api:
	docker compose logs -f api

ps:
	docker compose ps

migrate:
	docker compose exec api alembic upgrade head

migrate-create:
	docker compose exec api alembic revision --autogenerate -m "$(msg)"

shell-api:
	docker compose exec api bash

shell-db:
	docker compose exec postgres psql -U $${POSTGRES_USER:-rezeb} -d $${POSTGRES_DB:-rezeb}

test:
	docker compose exec api pytest tests/ -v --tb=short

lint:
	docker compose exec api ruff check app/ && docker compose exec api mypy app/

format:
	docker compose exec api ruff format app/

seed:
	docker compose exec api python -m scripts.seed_dev_data
