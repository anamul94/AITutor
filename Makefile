SHELL := /bin/bash

BACKEND_DIR := backend
FRONTEND_DIR := frontend
VENV_DIR := $(BACKEND_DIR)/venv
VENV_PY := $(VENV_DIR)/bin/python
VENV_PIP := $(VENV_DIR)/bin/pip
ALEMBIC := $(VENV_DIR)/bin/alembic

.PHONY: help venv install install-backend install-frontend \
	copy-env wait-db \
	db-up db-down db-logs backend frontend \
	migrate migrate-local migrate-docker \
	makemigration makemigration-local makemigration-docker \
	docker-build docker-up docker-down \
	setup setup-local

help:
	@echo "Available commands:"
	@echo "  make setup                        - Full first-time Docker setup: env, build, DB, migrations, app containers"
	@echo "  make setup-local                  - Full first-time local setup: env, deps, Postgres container, migrations"
	@echo "  make install                      - Install backend and frontend dependencies (local dev)"
	@echo "  make db-up                        - Start PostgreSQL container"
	@echo "  make db-down                      - Stop PostgreSQL container only"
	@echo "  make db-logs                      - Tail PostgreSQL logs"
	@echo "  make backend                      - Start FastAPI backend locally"
	@echo "  make frontend                     - Start Next.js frontend locally"
	@echo "  make migrate                      - Run Alembic migration (local venv if present, else Docker)"
	@echo "  make makemigration msg=\"...\"      - Create autogen migration (local venv if present, else Docker)"
	@echo "  make docker-build                 - Build all Docker images"
	@echo "  make docker-up                    - Build and start all Docker services"
	@echo "  make docker-down                  - Stop and remove all Docker services"

venv:
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "Creating Python virtualenv in $(VENV_DIR)..."; \
		python3 -m venv "$(VENV_DIR)"; \
	fi

install-backend: venv
	@echo "Installing backend dependencies..."
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install -r $(BACKEND_DIR)/requirements.txt

install-frontend:
	@echo "Installing frontend dependencies..."
	cd $(FRONTEND_DIR) && npm install

install: install-backend install-frontend

copy-env:
	@if [ ! -f "$(BACKEND_DIR)/.env" ]; then \
		cp "$(BACKEND_DIR)/.env.example" "$(BACKEND_DIR)/.env"; \
		echo "     Created backend/.env from .env.example — fill in your secrets before starting."; \
	else \
		echo "     backend/.env already exists, skipping."; \
	fi
	@if [ ! -f "$(FRONTEND_DIR)/.env.local" ]; then \
		cp "$(FRONTEND_DIR)/.env.example" "$(FRONTEND_DIR)/.env.local"; \
		echo "     Created frontend/.env.local from .env.example"; \
	else \
		echo "     frontend/.env.local already exists, skipping."; \
	fi

# Database
db-up:
	docker compose up -d db

db-down:
	docker compose stop db

db-logs:
	docker compose logs -f db

wait-db:
	@echo "     Waiting for PostgreSQL to be ready..."
	@for i in $$(seq 1 20); do \
		if docker compose exec db pg_isready -q 2>/dev/null; then \
			echo "     PostgreSQL is ready."; \
			exit 0; \
		fi; \
		echo "     ...still waiting ($$i/20)"; \
		sleep 2; \
	done; \
	echo "ERROR: PostgreSQL did not become ready in time."; \
	exit 1

# Local app runners
backend: venv
	@echo "Starting FastAPI backend..."
	cd $(BACKEND_DIR) && ./venv/bin/uvicorn app.main:app --reload

frontend:
	@echo "Starting Next.js frontend..."
	cd $(FRONTEND_DIR) && npm run dev

# Migrations
migrate:
	@if [ -x "$(ALEMBIC)" ]; then \
		$(MAKE) migrate-local; \
	else \
		$(MAKE) migrate-docker; \
	fi

migrate-local: venv
	@echo "Running Alembic migration locally..."
	cd $(BACKEND_DIR) && ./venv/bin/alembic upgrade head

migrate-docker:
	@echo "Running Alembic migration via Docker..."
	$(MAKE) db-up
	$(MAKE) wait-db
	docker compose build backend
	docker compose run --rm backend alembic upgrade head

makemigration:
	@if [ -z "$(msg)" ]; then \
		echo "Usage: make makemigration msg=\"your migration message\""; \
		exit 1; \
	fi
	@if [ -x "$(ALEMBIC)" ]; then \
		$(MAKE) makemigration-local msg="$(msg)"; \
	else \
		$(MAKE) makemigration-docker msg="$(msg)"; \
	fi

makemigration-local: venv
	@echo "Creating migration locally..."
	cd $(BACKEND_DIR) && ./venv/bin/alembic revision --autogenerate -m "$(msg)"

makemigration-docker:
	@echo "Creating migration via Docker..."
	$(MAKE) db-up
	$(MAKE) wait-db
	docker compose build backend
	docker compose run --rm backend alembic revision --autogenerate -m "$(msg)"

# Docker workflow
docker-build:
	docker compose build

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

# ── Full first-time setup ─────────────────────────────────────────────────────
setup:
	@echo ""
	@echo "==> [1/5] Copying env files (skipped if already present)..."
	$(MAKE) copy-env

	@echo ""
	@echo "==> [2/5] Starting PostgreSQL..."
	$(MAKE) db-up
	$(MAKE) wait-db

	@echo ""
	@echo "==> [3/5] Building Docker images..."
	docker compose build

	@echo ""
	@echo "==> [4/5] Running database migrations..."
	$(MAKE) migrate-docker

	@echo ""
	@echo "==> [5/5] Starting backend and frontend containers..."
	docker compose up -d backend frontend

	@echo ""
	@echo "================================================================"
	@echo "  Docker setup complete!"
	@echo ""
	@echo "    Frontend:  http://localhost:3004"
	@echo "    Backend:   http://localhost:8020"
	@echo "    Postgres:  localhost:5431"
	@echo ""
	@echo "  Useful commands:"
	@echo "    make docker-down   - stop the Docker stack"
	@echo "    make db-logs       - tail PostgreSQL logs"
	@echo "    make setup-local   - use the local backend/frontend workflow"
	@echo "================================================================"
	@echo ""

setup-local:
	@echo ""
	@echo "==> [1/5] Copying env files (skipped if already present)..."
	$(MAKE) copy-env

	@echo ""
	@echo "==> [2/5] Installing backend dependencies..."
	$(MAKE) install-backend

	@echo ""
	@echo "==> [3/5] Installing frontend dependencies..."
	$(MAKE) install-frontend

	@echo ""
	@echo "==> [4/5] Starting PostgreSQL..."
	$(MAKE) db-up
	$(MAKE) wait-db

	@echo ""
	@echo "==> [5/5] Running database migrations..."
	$(MAKE) migrate-local

	@echo ""
	@echo "================================================================"
	@echo "  Local setup complete! Run the app:"
	@echo ""
	@echo "    make backend    (in one terminal)  — FastAPI on :8000"
	@echo "    make frontend   (in another terminal) — Next.js on :3000"
	@echo ""
	@echo "  Or run everything in Docker:"
	@echo "    make setup"
	@echo "================================================================"
	@echo ""
