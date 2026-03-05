SHELL := /bin/bash

BACKEND_DIR := backend
FRONTEND_DIR := frontend
VENV_DIR := $(BACKEND_DIR)/venv
VENV_PY := $(VENV_DIR)/bin/python
VENV_PIP := $(VENV_DIR)/bin/pip
ALEMBIC := $(VENV_DIR)/bin/alembic

.PHONY: help venv install install-backend install-frontend \
	db-up db-down db-logs backend frontend \
	migrate migrate-local migrate-docker \
	makemigration makemigration-local makemigration-docker \
	docker-build docker-up docker-down

help:
	@echo "Available commands:"
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

# Database
db-up:
	docker compose up -d db

db-down:
	docker compose stop db

db-logs:
	docker compose logs -f db

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
	docker compose up -d db
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
	docker compose up -d db
	docker compose run --rm backend alembic revision --autogenerate -m "$(msg)"

# Docker workflow
docker-build:
	docker compose build

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down
