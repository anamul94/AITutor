.PHONY: help install db-up db-down backend frontend all migrate makemigration docker-up docker-down docker-build

help:
	@echo "Available commands:"
	@echo "  make install         - Install backend and frontend dependencies (local dev)"
	@echo "  make db-up           - Start the PostgreSQL database only (Docker)"
	@echo "  make db-down         - Stop all Docker services"
	@echo "  make backend         - Start the FastAPI backend server (local dev, requires venv)"
	@echo "  make frontend        - Start the Next.js frontend server (local dev)"
	@echo "  make migrate         - Run Alembic migrations inside the backend Docker container"
	@echo "  make makemigration   - Auto-generate a migration inside the backend Docker container"
	@echo "  make docker-build    - Build all Docker images"
	@echo "  make docker-up       - Build and start all services (db + backend + frontend)"
	@echo "  make docker-down     - Stop and remove all Docker services"

# Install dependencies for both frontend and backend (local dev only)
install:
	@echo "Installing Backend Dependencies..."
	cd backend && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
	@echo "Installing Frontend Dependencies..."
	cd frontend && npm install

# Start database only
db-up:
	docker compose up -d db

# Stop all services
db-down:
	docker compose down

# Start FastAPI backend (local dev)
backend:
	@echo "Starting FastAPI Backend..."
	cd backend && ./venv/bin/uvicorn app.main:app --reload

# Start Next.js frontend (local dev)
frontend:
	@echo "Starting Next.js Frontend..."
	cd frontend && npm run dev

# Run Alembic migrations inside the running backend container
migrate:
	@echo "Running Database Migrations inside container..."
	docker compose exec backend alembic upgrade head

# Auto-generate a new migration inside the running backend container
# Usage: make makemigration msg="your migration message"
makemigration:
	@echo "Creating migration inside container..."
	docker compose exec backend alembic revision --autogenerate -m "$(msg)"

# Build all Docker images
docker-build:
	docker compose build

# Build and start all Docker services
docker-up:
	docker compose up --build -d

# Stop and remove all Docker services
docker-down:
	docker compose down