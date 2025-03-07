# Cortex Developer Guidelines

## Common Commands
* Build/Install: `uv pip install -e ".[dev]"` (backend)
* Start backend: `uv run uvicorn cortex_core.main:app --reload`
* Start frontend: `cd cortex-chat && pnpm dev`
* Install frontend deps: `cd cortex-chat && pnpm install`
* Build frontend: `cd cortex-chat && pnpm build`
* Format: `uv run black .` (backend), `cd cortex-chat && pnpm format` (frontend)
* Sort imports: `uv run isort .` (backend)
* Lint: `uv run flake8` (backend), `cd cortex-chat && pnpm lint` (frontend)
* Type-check: `uv run mypy` (backend), `cd cortex-chat && pnpm type-check` (frontend)
* Test: `uv run pytest` (backend), `cd cortex-chat && pnpm test` (frontend)
* Single test: `uv run pytest tests/test_file.py::test_function`
* Test coverage: `uv run pytest --cov=cortex_core --cov-report=term-missing`

## Code Style
### Python
* Indentation: 4 spaces
* Line length: 88 characters
* Imports: stdlib → third-party → local, alphabetized within groups
* Naming: `snake_case` for functions/variables, `CamelCase` for classes
* Types: Use type annotations consistently

### TypeScript/React
* Component files: Use PascalCase for component names and files (e.g., `LoginPage.tsx`)
* File organization: Components organized by feature in subdirectories
* State management: React Query for data fetching and state
* Styling: Fluent UI components and styling system
* Types: Define strong TypeScript interfaces/types

## Documentation
* Markdown filenames: Use ALL_CAPS with UNDERSCORES (e.g., `PLATFORM_OVERVIEW.md`, `CODEBASE_STRUCTURE.md`)
* Documentation goes in relevant docs/ directories

## Tools
* Python: Uses uv for environment/dependency management
* Linting/Formatting: black, isort, flake8 (Python), ESLint (TypeScript)
* Type checking: mypy (Python), TypeScript compiler
* Testing: pytest (Python)
* Frontend: React 19, Fluent UI components
* Package management: uv (Python), pnpm (Frontend)