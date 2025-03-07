# Cortex Platform Developer Guidelines

## Common Commands

- Build/Install: `uv pip install -e .`
- Database Migrations: `uv run alembic upgrade head`
- Start Server: `uv run -m app.main`
- Run DB Revision: `make revision MSG="description"`
- Format: `ruff format`
- Lint: `ruff check`
- Type-check: `mypy`
- Test: `python -m pytest`
- Single test: `python -m pytest tests/test_file.py::test_function -v`

## Code Style

### Python

- Indentation: 4 spaces
- Line length: 100 characters
- Imports: Standard lib → third-party → local, grouped
- Naming: `snake_case` for variables/functions, `CamelCase` for classes, `ALL_CAPS` for constants
- Type annotations: Used consistently with Optional types
- Error handling: Uses try/except with specific exceptions, logs errors
- Documentation: Triple-quote docstrings with Args/Returns sections
- Files must end with a newline (NL at EOF)

## Architecture

- FastAPI-based API with Server-Sent Events (SSE) for real-time updates
- SQLAlchemy ORM with PostgreSQL/SQLite
- JWT-based authentication
- Redis for caching
