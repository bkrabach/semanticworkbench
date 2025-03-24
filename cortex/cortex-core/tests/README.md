# Cortex Core Testing Documentation

This document describes the testing strategy and structure for the Cortex Core project.

## Test Structure

The tests are organized by component, mirroring the structure of the application:

```
tests/
├── cortex_core/        # Tests for core application components
├── cognition_service/  # Tests for the cognition service
├── memory_service/     # Tests for the memory service
└── README.md           # This document
```

## Types of Tests

1. **Unit Tests**: Tests individual functions and classes in isolation
2. **Integration Tests**: Tests components working together, categorized as:
   - **Component Integration**: Tests how components within a service work together (e.g., `test_integration.py`)
   - **Client Integration**: Tests how clients connect to a running service (e.g., `test_client_integration.py`)
   - **System Integration**: Tests cross-service integration points (e.g., the core app with service backends)
3. **API Tests**: Tests HTTP endpoints and payload validation
4. **E2E Tests**: Minimal end-to-end tests of critical flows

## Test Fixtures

Test fixtures are defined in `conftest.py` files within each test directory. These fixtures provide:

- Mock objects for testing in isolation
- Sample data for tests
- Utilities for testing async code
- Helper functions for common test patterns

### Key Fixtures

- `mock_event_bus`: A mocked EventBus for testing event publishing and subscribing
- `mock_memory_client`: A mocked MemoryClient with AsyncMock methods
- `mock_cognition_client`: A mocked CognitionClient with AsyncMock methods
- `mock_response_handler`: A mocked ResponseHandler with its dependencies
- `sample_messages`: Sample conversation messages for testing
- `sample_conversation`: A sample conversation data structure

### Utilities

- `async_mock()`: A utility for creating async mock functions that support type checking
- `MockPydanticAIResult`: A mock for simulating Pydantic AI results

## Running Tests

To run all tests:
```bash
cd cortex-core && python -m pytest
```

To run tests for a specific module:
```bash
python -m pytest tests/cortex_core/
python -m pytest tests/memory_service/
python -m pytest tests/cognition_service/
```

To run a specific test:
```bash
python -m pytest tests/cortex_core/test_response_handler.py::test_handle_input_event
```

## Test Coverage

To run tests with coverage:
```bash
python -m pytest --cov=app tests/
```

To generate a coverage report:
```bash
python -m pytest --cov=app --cov-report=html tests/
```

## Testing Best Practices

1. **Use fixtures from conftest.py** for common test setup
2. **Test in isolation** using proper mocks for dependencies
3. **Test error handling** with appropriate mocked exceptions
4. **Use type hints** for better IDE support and documentation
5. **Document test expectations** with clear assertions
6. **Use descriptive test names** that explain what's being tested

## Async Testing

Most components in the system are asynchronous. To test async code:

1. Mark test functions with `@pytest.mark.asyncio`
2. Use `async_mock()` for mocking async functions
3. For complex async testing, use the AsyncMock class
4. Test both success and error paths for async functions

Example:
```python
@pytest.mark.asyncio
async def test_async_function(mock_dependency):
    # Test async function
    result = await function_under_test()
    assert result == expected_value
    
    # Verify mock was called
    mock_dependency.assert_called_once()
```