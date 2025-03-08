# Semantic Workbench Developer Guidelines

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
- Install Dev Dependencies: `uv add --dev <package>` (e.g., for type stubs: `uv add --dev types-python-jose`)

## Important Development Practices

- Never work around missing packages or type stubs - always ask to have them properly installed as dev dependencies
- For type checking issues, install the appropriate type stubs rather than modifying code to bypass errors

## Code Style

### Python

- Indentation: 4 spaces
- Line length: 100 characters
- Imports: Standard lib → third-party → local, grouped
- Naming: `snake_case` for variables/functions, `CamelCase` for classes, `ALL_CAPS` for constants
- Type annotations: Used consistently with Optional types
- Error handling: Uses try/except with specific exceptions, logs errors
- Documentation: Triple-quote docstrings with Args/Returns sections

## Architecture

- FastAPI-based API with Server-Sent Events (SSE) for real-time updates
- SQLAlchemy ORM with PostgreSQL/SQLite
  - Always use ORM models directly instead of raw SQL
  - For migrations and schema changes, use Alembic
- JWT-based authentication
- Redis for caching

## Development Notes

- This is a modern platform focused on clean design and maintainability
- Always consider scalability and performance in your implementation
- Follow established patterns in the codebase for consistency

## Project Documentation Guidelines

When exploring any project, always check for these documentation files:

### Core Documentation
- `README.md` - Project overview, setup instructions, and basic usage
- `ARCHITECTURE.md` - System architecture, design patterns, and component interactions
- `DEVELOPMENT.md` - Development workflow, tools, and practices
- `CONTRIBUTING.md` - Guidelines for contributing to the project

### Technical Documentation
- `docs/` directory - Detailed documentation for various aspects of the system
- `API.md` or `API_REFERENCE.md` - API documentation
- `DEPLOYMENT.md` - Deployment procedures and environments
- `TESTING.md` - Testing strategies and procedures

### Configuration and Setup
- `.env.example` - Example environment variables
- `docker-compose.yml` - Container configuration
- `pyproject.toml` / `package.json` - Dependencies and project metadata

### Standards and Conventions
- `STYLE_GUIDE.md` - Code style guidelines
- `CODE_OF_CONDUCT.md` - Community standards

Always prioritize official project documentation over assumptions. Reference these files when making design decisions to ensure alignment with project standards.

## Testing Best Practices

- Use dependency overrides for FastAPI tests, not patching:
  ```python
  # Good approach (use this)
  app.dependency_overrides[get_db] = lambda: mock_db
  
  # Bad approach (avoid this)
  with patch("app.api.auth.get_db", return_value=mock_db):
      ...
  ```
- Create fixtures that properly clean up resources
- Always use `@pytest.mark.asyncio` for testing async functions
- Test fastAPI endpoints using TestClient with dependency overrides
- Clear all overrides after tests using try/finally or yield fixtures
- Mock database sessions, not individual queries
- Create test-specific fixtures for commonly used dependencies
