# Cortex Core Testing Guide

This document outlines the testing approach, tools, and practices for the Cortex Core project.

## Testing Philosophy

Cortex Core follows these testing principles:

1. **Test-Driven Development**: Write tests before implementation when possible
2. **Comprehensive Coverage**: Test all critical paths and edge cases
3. **Fast Feedback**: Tests should run quickly to support rapid iteration
4. **Integration Focus**: Emphasize integration tests over unit tests for critical flows
5. **Realistic Scenarios**: Test with realistic data and scenarios
6. **Clean Resource Management**: Verify that resources are properly cleaned up
7. **Dependency Injection**: Use FastAPI's dependency injection for clean testing

## Testing Stack

The project uses the following testing tools:

- **pytest**: Primary testing framework
- **pytest-asyncio**: Support for testing async code
- **httpx**: HTTP client for testing API endpoints
- **FastAPI TestClient**: Simplified API testing

## Types of Tests

### Unit Tests

Unit tests focus on testing individual components in isolation:

- **Event Bus**: Test subscription, publishing, and unsubscription
- **Storage**: Test data storage and retrieval
- **Authentication**: Test token generation and validation
- **Models**: Test model validation and serialization

Example unit test for the Event Bus:

```python
import asyncio
import pytest

from app.core.event_bus import EventBus

@pytest.mark.asyncio
async def test_event_bus_publish_subscribe():
    # Setup
    event_bus = EventBus()
    queue = asyncio.Queue()
    event_bus.subscribe(queue)
    
    # Test data
    test_event = {"type": "test", "data": {"message": "Hello"}, "user_id": "user1"}
    
    # Action
    await event_bus.publish(test_event)
    
    # Assert
    received_event = await asyncio.wait_for(queue.get(), timeout=1)
    assert received_event == test_event
    
    # Cleanup
    event_bus.unsubscribe(queue)
```

### API Tests

API tests focus on testing the HTTP interfaces using FastAPI's TestClient:

- **Endpoint Behavior**: Test request handling and response formatting
- **Authentication**: Test protected endpoints with valid and invalid tokens
- **Validation**: Test request validation with valid and invalid inputs
- **Error Handling**: Test appropriate error responses

Example API test:

```python
from fastapi.testclient import TestClient
from app.main import app
from app.utils.auth import create_access_token

client = TestClient(app)

def test_input_endpoint_with_valid_token():
    # Create a test token
    token = create_access_token({"sub": "test@example.com", "oid": "user1"})
    
    # Test data
    input_data = {
        "content": "Test message",
        "conversation_id": "conv1"
    }
    
    # Make the request
    response = client.post(
        "/input",
        json=input_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Assert
    assert response.status_code == 200
    assert response.json() == {"status": "received"}
```

### Integration Tests

Integration tests verify that components work together correctly:

- **End-to-End Flow**: Test the complete input-to-output flow
- **Event Processing**: Test event propagation through the system
- **Resource Management**: Test proper cleanup of resources
- **Error Propagation**: Test error handling across components

Example integration test:

```python
import asyncio
import pytest
import json
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app
from app.utils.auth import create_access_token

@pytest.mark.asyncio
async def test_input_to_output_flow():
    # Create a test token
    token = create_access_token({"sub": "test@example.com", "oid": "user1"})
    auth_headers = {"Authorization": f"Bearer {token}"}
    
    # Start SSE connection in the background
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Connect to SSE endpoint
        async def sse_client():
            responses = []
            async with client.stream("GET", "/output/stream", headers=auth_headers) as stream:
                async for line in stream.aiter_lines():
                    if line.startswith("data: "):
                        event_data = json.loads(line[6:])
                        responses.append(event_data)
                        if event_data["type"] == "input" and "Test message" in str(event_data):
                            return responses
            return responses
        
        # Start SSE client task
        sse_task = asyncio.create_task(sse_client())
        
        # Wait a moment for connection to establish
        await asyncio.sleep(0.1)
        
        # Send input
        input_response = await client.post(
            "/input",
            json={"content": "Test message", "conversation_id": "conv1"},
            headers=auth_headers
        )
        
        # Wait for the event to be received
        responses = await asyncio.wait_for(sse_task, timeout=2)
        
        # Assertions
        assert input_response.status_code == 200
        assert len(responses) > 0
        assert any(
            e["type"] == "input" and "Test message" in str(e["data"])
            for e in responses
        )
```

### Resource Management Tests

These tests verify that resources are properly cleaned up:

- **Connection Cleanup**: Test SSE connection cleanup on disconnect
- **Task Cleanup**: Test background task cleanup
- **Memory Management**: Test for memory leaks in long-running operations

Example resource management test:

```python
import asyncio
import pytest
import gc
import weakref

from app.core.event_bus import EventBus

@pytest.mark.asyncio
async def test_event_bus_subscription_cleanup():
    # Setup
    event_bus = EventBus()
    queue_refs = []
    
    # Create and subscribe 10 queues
    for _ in range(10):
        queue = asyncio.Queue()
        queue_refs.append(weakref.ref(queue))
        event_bus.subscribe(queue)
    
    # Unsubscribe all queues
    for i in range(10):
        event_bus.unsubscribe(queue_refs[i]())
    
    # Force garbage collection
    gc.collect()
    
    # Verify all queues are garbage collected
    assert all(ref() is None for ref in queue_refs)
```

## Test Organization

Tests are organized by type and component:

```
tests/
├── __init__.py
├── test_api.py         # API endpoint tests
├── test_event_bus.py   # Event bus unit tests
├── test_integration.py # End-to-end integration tests
└── test_storage.py     # Storage tests
```

## Test Fixtures

Reusable test fixtures are defined in `conftest.py`:

```python
import pytest
import asyncio
from fastapi.testclient import TestClient
from app.main import app
from app.utils.auth import create_access_token
from app.core.event_bus import EventBus
from app.core.storage import InMemoryStorage

@pytest.fixture
def test_client():
    return TestClient(app)

@pytest.fixture
def test_token():
    return create_access_token({
        "sub": "test@example.com",
        "oid": "user1",
        "name": "Test User",
        "email": "test@example.com"
    })

@pytest.fixture
def event_bus():
    return EventBus()

@pytest.fixture
def storage():
    return InMemoryStorage()

@pytest.fixture
def auth_headers(test_token):
    return {"Authorization": f"Bearer {test_token}"}
```

## Testing Async Code

When testing async code with pytest-asyncio:

1. Mark tests as asyncio tests:
   ```python
   @pytest.mark.asyncio
   async def test_async_function():
       # Test async code here
   ```

2. Use asyncio utilities for testing:
   ```python
   # Wait for a result with timeout
   result = await asyncio.wait_for(some_async_function(), timeout=1)
   
   # Run multiple async tasks concurrently
   task1 = asyncio.create_task(function1())
   task2 = asyncio.create_task(function2())
   await asyncio.gather(task1, task2)
   ```

3. Clean up resources properly:
   ```python
   try:
       # Test code here
   finally:
       # Clean up resources
       await some_resource.close()
   ```

## Testing SSE Endpoints

Testing SSE endpoints requires special handling:

1. Use AsyncClient for streaming:
   ```python
   async with AsyncClient(app=app, base_url="http://test") as client:
       async with client.stream("GET", "/output/stream", headers=auth_headers) as stream:
           # Process stream
   ```

2. Parse SSE format:
   ```python
   async for line in stream.aiter_lines():
       if line.startswith("data: "):
           event_data = json.loads(line[6:])
           # Process event data
   ```

3. Set up timeouts for tests:
   ```python
   # Set a reasonable timeout to prevent tests from hanging
   with pytest.raises(asyncio.TimeoutError):
       await asyncio.wait_for(sse_client(), timeout=1)
   ```

## Mocking Dependencies

Use FastAPI's dependency overriding for clean testing:

```python
from app.main import app
from app.dependencies import get_event_bus, get_storage

# Create test dependencies
test_event_bus = EventBus()
test_storage = InMemoryStorage()

# Override dependencies for testing
app.dependency_overrides[get_event_bus] = lambda: test_event_bus
app.dependency_overrides[get_storage] = lambda: test_storage

# Run tests with the overridden dependencies

# Clean up after tests
app.dependency_overrides = {}
```

## Best Practices

### General Testing Practices

1. **Isolate Tests**: Each test should be independent and not rely on the state from other tests
2. **Clear Setup and Teardown**: Initialize test state clearly and clean up afterward
3. **Descriptive Names**: Use clear, descriptive test names that indicate what's being tested
4. **Test Failure Cases**: Test both success and failure conditions
5. **Avoid Test Interdependence**: Tests should not depend on the order of execution

### Async Testing Practices

1. **Handle CancelledError**: Always account for asyncio.CancelledError in tests
2. **Use Proper Timeouts**: Set reasonable timeouts to prevent tests from hanging
3. **Clean Up Resources**: Always clean up asyncio resources in finally blocks
4. **Test Concurrency Issues**: Test concurrent operations explicitly
5. **Mock Slow Operations**: Use mocks for slow external services

### API Testing Practices

1. **Test Authentication**: Test both with and without valid authentication
2. **Test Validation**: Test with both valid and invalid inputs
3. **Test Error Responses**: Verify appropriate error responses and status codes
4. **Test Headers and Content Types**: Verify correct headers and content types
5. **Test Rate Limiting**: Test rate limiting behavior (when implemented)

## Continuous Integration

Tests are run automatically on CI for:

1. Pull requests
2. Pushes to main branch
3. Nightly builds

The CI pipeline includes:

1. Running all tests
2. Checking code coverage
3. Linting with ruff
4. Type checking with mypy

## Test Coverage

Aim for high test coverage, especially for critical components:

- Event Bus: 100% coverage
- Authentication: 100% coverage
- API Endpoints: 95%+ coverage
- Storage: 90%+ coverage

Use coverage reports to identify untested code:

```bash
pytest --cov=app --cov-report=html
```

## Debugging Failed Tests

When tests fail:

1. Run the specific failed test with verbose output:
   ```bash
   pytest tests/test_file.py::test_function -v
   ```

2. Add debug logging to see what's happening:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

3. Use pytest's built-in debugger:
   ```bash
   pytest tests/test_file.py::test_function --pdb
   ```

4. Use print statements in tests (remove before committing):
   ```python
   print(f"Debug value: {some_value}")
   ```

## Performance Testing

Future phases will include explicit performance testing:

1. Load testing with locust
2. Benchmarking critical operations
3. Memory usage analysis
4. Connection handling limits

## Conclusion

Comprehensive testing is critical for ensuring the reliability and correctness of Cortex Core. By following these testing guidelines, we can maintain high quality and prevent regressions as the codebase evolves.