# Testing Guide for Cortex Core

This document provides guidelines and best practices for testing the Cortex Core platform.

## Running Tests

```bash
# Run all tests
python -m pytest

# Run specific tests
python -m pytest tests/api/test_auth.py

# Run with coverage report
python -m pytest --cov=app tests/

# Run only the event system tests
python -m pytest tests/components/test_event_system.py
```

## Test Structure

Each test module should follow this structure:

- Import statements
- Fixture definitions
- Test functions grouped by functionality
- Helper functions (if needed)

Example:

```python
"""
Test suite for authentication API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from app.main import app
from app.database.connection import get_db
from app.database.models import User

# Fixtures
@pytest.fixture
def mock_db():
    """Create a mock DB session"""
    mock = MagicMock()
    return mock

@pytest.fixture
def client_with_db_override(mock_db):
    """Create a test client with DB dependency override"""
    app.dependency_overrides[get_db] = lambda: mock_db
    client = TestClient(app)
    yield client
    app.dependency_overrides = {}

# Tests
def test_login_success(client_with_db_override, mock_db):
    # Test implementation
    pass
```

## FastAPI Dependency Testing Best Practices

### Use Dependency Overrides, Not Patching

FastAPI uses a dependency injection system. When testing, it's best to override the dependencies directly rather than patching functions:

```python
# DON'T DO THIS:
with patch("app.api.auth.get_db", return_value=mock_db):
    response = test_client.post("/auth/login", json={"username": "test"})

# DO THIS INSTEAD:
app.dependency_overrides[get_db] = lambda: mock_db
client = TestClient(app)
response = client.post("/auth/login", json={"username": "test"})
```

### Clean Up After Tests

Always clean up dependency overrides after your test, using either a try/finally block or a fixture with yield:

```python
# Using try/finally
def test_with_cleanup():
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        response = client.get("/endpoint")
        assert response.status_code == 200
    finally:
        app.dependency_overrides = {}

# Using fixture with yield (PREFERRED)
@pytest.fixture
def client_with_override():
    app.dependency_overrides[get_db] = lambda: mock_db
    client = TestClient(app)
    yield client
    app.dependency_overrides = {}

def test_with_fixture(client_with_override):
    response = client_with_override.get("/endpoint")
    assert response.status_code == 200
```

### Create Reusable Fixtures

Create fixtures for common dependencies and test setups:

```python
@pytest.fixture
def mock_user():
    """Create a mock user for testing"""
    return User(
        id="test-user-id",
        email="test@example.com",
        name="Test User"
    )

@pytest.fixture
def client_with_auth_override(mock_db, mock_user):
    """Create a test client with DB and auth overrides"""
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user
    client = TestClient(app)
    yield client
    app.dependency_overrides = {}
```

## Testing Async Code

### Always Use @pytest.mark.asyncio

For tests involving async functions:

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

### Handle Coroutines Properly

Ensure you properly await async functions:

```python
# DON'T DO THIS (won't run the function):
user = get_current_user(token, db)  # Returns a coroutine, not a User

# DO THIS INSTEAD:
user = await get_current_user(token, db)
```

### Testing Streaming Endpoints (SSE, WebSockets)

When testing streaming endpoints like Server-Sent Events (SSE) or WebSockets:

1. **Focus on API Contracts, Not Streaming Behavior**:
   - Test only the HTTP status codes, headers, and initial connection
   - Don't attempt to test the full streaming functionality in unit tests

2. **Never Read From Streams in Tests Without Proper Controls**:
   - Reading from infinite streams will cause tests to hang
   - If you must test stream content, use strict timeouts and proper cancellation

3. **Mock the HTTP Response, Not Internal Components**:
   ```python
   # Create a mock response for streaming endpoints
   class MockSSEResponse:
       def __init__(self):
           self.status_code = 200
           self.headers = {"content-type": "text/event-stream"}
           self._content = b"data: {}\n\n"
           
       def close(self):
           pass
           
   # Patch the client's get method for the specific endpoint
   def mock_get(url, **kwargs):
       if url == "/events":
           return MockSSEResponse()
       return original_get(url, **kwargs)
       
   monkeypatch.setattr(client, "get", mock_get)
   ```

4. **Avoid Modifying FastAPI's Internal Route Structure**:
   - Don't attempt to replace route handlers or endpoints directly
   - Use dependency injection or response mocking instead

5. **Clean Up Resources Even for Cancelled Tests**:
   - Always use `try/finally` to ensure proper cleanup
   - When a streaming test is cancelled, make sure background tasks are terminated
   - Consider adding explicit timeouts to all async operations

## Mock Database Sessions Correctly

### Mock at the Right Level

Generally, mock the session rather than individual database calls:

```python
# Configure the mock DB to return a test user
query_mock = MagicMock()
filter_mock = MagicMock()
mock_db.query.return_value = query_mock
query_mock.filter.return_value = filter_mock
filter_mock.first.return_value = test_user
```

### Handle SQLAlchemy Operations

When mocking, beware of SQLAlchemy's behavior:

```python
# For filtering methods
query_mock.filter.return_value = query_mock  # For chained query methods
query_mock.first.return_value = test_user    # For the terminal method

# For count operations
query_mock.count.return_value = 5
```

## Common Testing Patterns

### API Endpoint Testing

```python
def test_login_endpoint(client_with_db_override, mock_db):
    # Configure mock DB to return expected user
    mock_db.query.return_value.filter.return_value.first.return_value = mock_user
    
    # Make the request
    response = client_with_db_override.post(
        "/auth/login", 
        json={"email": "test@example.com", "password": "password"}
    )
    
    # Assert response
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["token"] is not None
```

### Testing Server-Sent Events (SSE) Endpoints

Testing SSE endpoints requires special care to avoid test hangs and race conditions:

```python
def test_sse_endpoint_contract(client_with_auth_override):
    """Test the SSE endpoint's contract, not its implementation"""
    response = client_with_auth_override.get("/events")
    
    # Only verify the contract (status code and content type)
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream"
    
    # Close immediately to prevent hanging
    response.close()
```

#### SSE Testing Principles

1. **Test the API contract, not implementation details**:
   - Focus on validating HTTP status codes, headers, and response formats
   - Avoid testing streaming behavior or content that could cause tests to hang

2. **Avoid reading from SSE streams in tests**:
   - Reading from an SSE stream may cause the test to hang indefinitely
   - If you must test stream content, use timeouts and proper cleanup

3. **Mock or replace the endpoint rather than patching internals**:
   - For more complex tests, consider replacing the endpoint entirely:

```python
def test_sse_endpoint_with_override():
    # Save original endpoint
    original_endpoint = None
    for route in app.routes:
        if route.path == "/events":
            original_endpoint = route.endpoint
            break
    
    # Create simplified version that doesn't use async generators
    async def mock_events_endpoint(request: Request):
        return StreamingResponse(
            content=iter([b"data: {}\n\n"]),  # Minimal SSE response
            media_type="text/event-stream"
        )
    
    # Replace the endpoint
    for route in app.routes:
        if route.path == "/events":
            route.endpoint = mock_events_endpoint
    
    try:
        # Test with the simplified endpoint
        client = TestClient(app)
        response = client.get("/events")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream"
    finally:
        # Restore the original endpoint
        for route in app.routes:
            if route.path == "/events":
                route.endpoint = original_endpoint
```

4. **Handle background tasks carefully**:
   - SSE endpoints often start background tasks that need cleanup
   - Mock `asyncio.create_task()` to intercept task creation
   - Ensure all tasks are properly cancelled in cleanup

5. **Validate connection tracking if necessary**:
   - If your SSE system tracks active connections, validate this separately
   - Set up connections directly rather than relying on the endpoint to do it
   - Clean up connections after the test

### Event System Testing

```python
@pytest.mark.asyncio
async def test_event_system(event_system):
    # Define subscriber
    received_events = []
    async def subscriber(event_type, payload):
        received_events.append(payload)
    
    # Subscribe and publish
    await event_system.subscribe("test.*", subscriber)
    await event_system.publish("test.event", {"data": "value"}, "source")
    
    # Assert
    assert len(received_events) == 1
    assert received_events[0].data == {"data": "value"}
```

### Component Testing with Mocks

```python
@pytest.mark.asyncio
async def test_component_with_dependency(mock_dependency):
    # Setup component with mock dependency
    component = Component(dependency=mock_dependency)
    
    # Configure mock behavior
    mock_dependency.method.return_value = "expected result"
    
    # Test the component
    result = await component.process_data("input")
    assert result == "expected result"
    
    # Verify mock was called correctly
    mock_dependency.method.assert_called_once_with("input")
```

## Further Resources

For more detailed information on testing in Python:

- [pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing Documentation](https://fastapi.tiangolo.com/tutorial/testing/)
- [Mocking with unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)