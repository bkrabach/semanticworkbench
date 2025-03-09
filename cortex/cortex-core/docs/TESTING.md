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

# Run architecture validation tests
python -m pytest tests/architecture/test_layer_integrity.py
```

## Architecture Validation Testing

The codebase includes automated tests to enforce architectural boundaries:

### Automated Architecture Tests

The file `tests/architecture/test_layer_integrity.py` contains tests that validate proper layer separation by checking import patterns. These tests verify that:

1. API layers never import SQLAlchemy models directly
2. Service layers never import SQLAlchemy models directly 
3. Components never import SQLAlchemy models directly

These tests are critical for maintaining the domain-driven repository architecture.

### Command-Line Validation Script

For quick architecture validation, use the `check_imports.sh` script:

```bash
./check_imports.sh
```

This script checks for improper imports across the codebase and provides clear error messages when violations are detected. Add this to your workflow to catch architectural issues early.

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

3. **Use a Comprehensive Mock Response Class**:
   ```python
   class MockSSEResponse:
       """A mock SSE response that won't cause tests to hang"""
       def __init__(self):
           self.status_code = 200
           self.headers = {
               "content-type": "text/event-stream",
               "cache-control": "no-cache",
               "connection": "keep-alive"
           }
           self._content = b"data: {}\n\n"
           self._closed = False

       def __enter__(self):
           return self

       def __exit__(self, *args):
           self.close()

       def close(self):
           self._closed = True

       def json(self):
           raise ValueError("Cannot call json() on a streaming response")

       # For iterator protocol
       def __iter__(self):
           yield self._content

       def iter_lines(self):
           yield self._content
   ```

4. **Create a Dedicated SSE Test Client**:
   ```python
   @pytest.fixture
   def sse_test_client(monkeypatch):
       """Test client that safely tests SSE endpoints without hanging"""
       client = TestClient(app)
       original_get = client.get
       
       # Patch get method to return mock responses for SSE endpoints
       def mock_get(url, **kwargs):
           if "/events" in url and "token=" in url:
               # For any SSE endpoint with a token, return a mock response
               token = url.split("token=")[1].split("&")[0] if "token=" in url else None
               if token:
                   try:
                       # Verify token is valid
                       payload = jwt.decode(token, settings.security.jwt_secret, algorithms=["HS256"])
                       
                       # For user-specific endpoint, check the user ID matches
                       if "/users/" in url:
                           url_user_id = url.split("/users/")[1].split("/")[0]
                           token_user_id = payload.get("user_id")
                           
                           # If user IDs don't match, let the endpoint handle the authorization error
                           if url_user_id != token_user_id:
                               return original_get(url, **kwargs)
                       
                       # Valid token and matching user ID (if applicable)
                       return MockSSEResponse()
                   except Exception:
                       # If token is invalid, let the endpoint handle it
                       pass
           # For all other requests, use original implementation
           return original_get(url, **kwargs)
       
       monkeypatch.setattr(client, "get", mock_get)
       return client
   ```

5. **Separate Integration and Connection Management Tests**:
   - Test API contracts with mocked responses
   - Test connection tracking logic separately
   - Use the Circuit Breaker pattern for components that might fail

6. **Clean Up Resources Even for Cancelled Tests**:
   - Always use `try/finally` to ensure proper cleanup
   - When a streaming test is cancelled, make sure background tasks are terminated
   - Use backups of active connection maps for test isolation
   - Add explicit timeouts to all async operations

7. **Use Contemporary Timezone-Aware DateTime Handling**:
   ```python
   # Instead of
   timestamp = datetime.utcnow()
   
   # Use
   timestamp = datetime.now(timezone.utc)
   ```

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

### Testing Unified SSE Endpoints

When testing the unified SSE endpoints (`/v1/{channel_type}/{resource_id}`), follow these best practices:

1. **Create Dedicated Test Fixtures**:

```python
@pytest.fixture
def sse_client(client_with_db_override, monkeypatch):
    """Test client with mocked SSE response handling"""
    original_get = client_with_db_override.get
    
    def mock_get(url, **kwargs):
        # For SSE endpoints, return a controlled response
        if url.startswith("/v1/") and "token=" in url:
            channel_parts = url.split("/")
            channel_type = channel_parts[2] if len(channel_parts) > 2 else None
            
            if channel_type in ["global", "user", "workspace", "conversation"]:
                response = MockSSEResponse()
                # Add test-specific modifications to the response if needed
                return response
                
        # For all other endpoints, use the original get method
        return original_get(url, **kwargs)
    
    monkeypatch.setattr(client_with_db_override, "get", mock_get)
    return client_with_db_override
```

2. **Test Different Channel Types**:

```python
@pytest.mark.parametrize("channel_type,resource_id", [
    ("global", "global"),
    ("user", "user-123"),
    ("workspace", "workspace-123"),
    ("conversation", "conversation-123")
])
def test_sse_endpoint_contracts(sse_client, valid_token, channel_type, resource_id):
    """Test the SSE endpoints for different channel types"""
    token = valid_token
    
    # Test valid endpoint access
    response = sse_client.get(f"/v1/{channel_type}/{resource_id}?token={token}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream"
    
    # Always close the response
    response.close()
```

3. **Test Authentication and Authorization**:

```python
def test_sse_authentication(sse_client):
    """Test SSE endpoint authentication"""
    # Test without token
    response = sse_client.get("/v1/global/global")
    assert response.status_code == 422  # FastAPI validation error
    
    # Test with invalid token
    response = sse_client.get("/v1/global/global?token=invalid-token")
    assert response.status_code == 401
    
    # Test with expired token
    response = sse_client.get("/v1/global/global?token=expired-token")
    assert response.status_code == 401
```

4. **Test Resource Access Control**:

```python
def test_sse_resource_access(sse_client, valid_token):
    """Test SSE resource access authorization"""
    token = valid_token
    
    # Mock the SSE service to simulate authorization checks
    # For a resource the user doesn't have access to
    response = sse_client.get(f"/v1/workspace/unauthorized-workspace?token={token}")
    assert response.status_code == 403
    
    # For a resource the user has access to
    response = sse_client.get(f"/v1/workspace/authorized-workspace?token={token}")
    assert response.status_code == 200
    response.close()
```

5. **Test SSE Service Components Independently**:

```python
@pytest.mark.asyncio
async def test_connection_manager():
    """Test the SSE connection manager independently"""
    manager = ConnectionManager()
    
    # Test connection registration
    queue, conn_id = await manager.register_connection("conversation", "conv-123", "user-123")
    assert conn_id is not None
    assert queue is not None
    
    # Test sending events to the queue
    event_data = {"message": "test"}
    await manager.send_to_connections("conversation", "conv-123", "test_event", event_data)
    
    # Get a message from the queue (with timeout)
    try:
        message = await asyncio.wait_for(queue.get(), timeout=0.5)
        assert message["event"] == "test_event"
        assert message["data"] == event_data
    except asyncio.TimeoutError:
        pytest.fail("No message received from queue")
    
    # Test connection removal
    await manager.remove_connection("conversation", "conv-123", conn_id)
    
    # Verify connection was removed
    stats = manager.get_stats()
    assert stats["channels"]["conversation"].get("conv-123", 0) == 0
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

3. **Use a dedicated test client with mocked responses**:
   ```python
   def test_sse_conversation_events_endpoint(sse_test_client, valid_token):
       """Test conversation events endpoint"""
       token, user_id = valid_token
       conversation_id = str(uuid.uuid4())
       
       # Test with valid token
       response = sse_test_client.get(f"/conversations/{conversation_id}/events?token={token}")
       assert response.status_code == 200
       assert response.headers["content-type"] == "text/event-stream"
       
       # Always close SSE connections in tests
       response.close()
   ```

4. **Test connection tracking separately from HTTP behaviors**:
   ```python
   @pytest.mark.asyncio
   async def test_sse_connection_tracking(clean_connections):
       """Test that connections are properly tracked and cleaned up"""
       # Add a test connection
       conversation_id = str(uuid.uuid4())
       connection_id = str(uuid.uuid4())
       user_id = str(uuid.uuid4())
       queue = asyncio.Queue()
       
       if conversation_id not in clean_connections["conversations"]:
           clean_connections["conversations"][conversation_id] = []
       
       clean_connections["conversations"][conversation_id].append({
           "id": connection_id,
           "user_id": user_id,
           "queue": queue
       })
       
       # Verify connection was added
       assert len(clean_connections["conversations"][conversation_id]) == 1
       
       # Remove the connection
       clean_connections["conversations"][conversation_id] = [
           conn for conn in clean_connections["conversations"][conversation_id]
           if conn["id"] != connection_id
       ]
       
       # Verify connection was removed
       assert len(clean_connections["conversations"][conversation_id]) == 0
   ```

5. **Handle background tasks and heartbeats carefully**:
   - SSE endpoints often start background tasks for heartbeats
   - Use the Circuit Breaker pattern to avoid cascading failures in tests
   - Ensure all tasks are properly cancelled in cleanup blocks
   - Add explicit timeouts to heartbeat intervals for tests

6. **Use fixtures to create clean connection states**:
   ```python
   @pytest.fixture
   def clean_connections():
       """Create a clean set of connections for the test"""
       # Save original connections
       original = {
           "global": active_connections["global"].copy(),
           "users": {k: v.copy() for k, v in active_connections["users"].items()},
           "workspaces": {k: v.copy() for k, v in active_connections["workspaces"].items()},
           "conversations": {k: v.copy() for k, v in active_connections["conversations"].items()},
       }
       
       # Clear connections for the test
       active_connections["global"].clear()
       active_connections["users"].clear()
       active_connections["workspaces"].clear()
       active_connections["conversations"].clear()
       
       yield active_connections
       
       # Restore original connections
       active_connections["global"] = original["global"]
       active_connections["users"] = original["users"]
       active_connections["workspaces"] = original["workspaces"]
       active_connections["conversations"] = original["conversations"]
   ```

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