repo_root = $(shell git rev-parse --show-toplevel)
include $(repo_root)/tools/makefiles/python.mk

# Python interpreter and uv settings
PYTHON ?= python
UV ?= uv
PIP = $(UV) pip

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
