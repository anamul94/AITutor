.PHONY: help install db-up db-down backend frontend all

help:
	@echo "Available commands:"
	@echo "  make install    - Install backend and frontend dependencies"
	@echo "  make db-up      - Start the PostgreSQL database using Docker"
	@echo "  make db-down    - Stop the PostgreSQL database"
	@echo "  make backend    - Start the FastAPI backend server"
	@echo "  make frontend   - Start the Next.js frontend server"
	@echo "  make all        - Start db, backend, and frontend (ensure you use separate terminals for backend/frontend)"

# Install dependencies for both frontend and backend
install:
	@echo "Installing Backend Dependencies..."
	cd backend && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
	@echo "Installing Frontend Dependencies..."
	cd frontend && npm install

# Start database
db-up:
	docker compose up -d

# Stop database
db-down:
	docker compose down

# Start FastAPI backend
backend:
	@echo "Starting FastAPI Backend..."
	cd backend && ./venv/bin/uvicorn app.main:app --reload

# Start Next.js frontend
frontend:
	@echo "Starting Next.js Frontend..."
	cd frontend && npm run dev
	
# Setup step (migrations)
migrate:
	@echo "Running Database Migrations..."
	cd backend && ./venv/bin/alembic upgrade head
