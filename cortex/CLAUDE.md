# Development Guidelines for Semantic Workbench Cortex

## Build/Test/Lint Commands

### Frontend (cortex-chat)
- Build: `npm run build` or `cd cortex-chat && npm run build`
- Test: `cd cortex-chat && npm run test`
- Test single file: `cd cortex-chat && npx vitest run src/path/to/file.test.tsx`
- Lint: `cd cortex-chat && npm run lint`

### Backend (cortex-core)
- Run server: `cd cortex-core && python -m app.main`
- Test all: `cd cortex-core && python -m pytest`
- Test single file: `cd cortex-core && python -m pytest tests/path/to/test_file.py`
- Lint: `cd cortex-core && ruff check app tests`
- Type check: `cd cortex-core && mypy app tests`

## Code Style Guidelines
- Python: Follow Google Python Style Guide with type hints
- TypeScript: 4-space indent, 100 char line length, single quotes, semicolons
- Domain-driven architecture with clear layer separation
- Consistent error handling with custom exception hierarchy
- API models separate from domain models
- React components organized by feature in frontend
- Event-driven architecture for SSE implementation