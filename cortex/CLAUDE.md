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

## Legacy Code Cleanup Plan

### LLM Adapter
- Maintain support for all providers (OpenAI, Azure OpenAI, Anthropic)
- Refactor to use Pydantic AI abstraction layer consistently
- Improve configuration system to allow deployment-specific provider selection
- Simplify implementation while maintaining multi-provider support

### Tools Implementation
- Remove fallback implementations in tools.py for when MCP client is not available
- Rely exclusively on MCP architecture for tool execution
- Eliminate conditional code that checks for MCP availability
- Simplify tool implementations to use MCP exclusively

### Mock LLM Implementation
- Move to test-specific directory (tests/mocks/)
- Simplify functionality to focus only on test requirements
- Update test imports to reference the new location
- Ensure test coverage is maintained

### Development-Only Code
- Move the ensure_test_users_exist function from main.py to a separate development module
- Create a clear separation between production and development code
- Implement environment-specific configuration

### Response Handler Simplification
- Optimize the _execute_tool method to remove dynamic inspection
- Streamline streaming implementation to reduce complexity
- Eliminate redundant code paths for different message types