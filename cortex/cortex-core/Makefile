# Cortex Core Makefile

.PHONY: help setup dev start migrate revision test clean

# Python interpreter and uv settings
PYTHON ?= python
UV ?= uv
PIP = $(UV) pip

# Default target
help:
	@echo "Cortex Core"
	@echo ""
	@echo "Usage:"
	@echo "  make <target>"
	@echo ""
	@echo "Targets:"
	@echo "  setup           Install dependencies"
	@echo "  dev             Run development server with auto-reload"
	@echo "  start           Start the application"
	@echo "  migrate         Run database migrations"
	@echo "  revision MSG=x  Create a new migration (MSG is required)"
	@echo "  test            Run tests"
	@echo "  clean           Clean build artifacts and cache files"

# Set up the project
setup:
	$(UV) venv
	$(PIP) install -e ".[dev]"

# Run the development server
dev:
	$(PYTHON) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 4000

# Start the application
start:
	$(PYTHON) -m app.main

# Run database migrations
migrate:
	$(PYTHON) -m alembic upgrade head

# Create a new migration
revision:
	@if [ -z "$(MSG)" ]; then \
		echo "Error: MSG is required. Usage: make revision MSG='description'"; \
		exit 1; \
	fi
	$(PYTHON) -m alembic revision --autogenerate -m "$(MSG)"

# Run tests
test:
	$(PYTHON) -m pytest

# Check for outdated dependencies
check-deps:
	$(PIP) list --outdated

# Clean build artifacts and cache files
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name "*.pyc" -delete
