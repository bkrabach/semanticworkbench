# Cortex Core Testing Strategy

This document outlines the testing strategy for the Cortex Core system. It provides guidance on testing approaches, tools, and techniques to ensure the system functions correctly and reliably.

## Testing Philosophy

Our testing approach is guided by the following principles:

1. **Focus on Complete Flows**: Test end-to-end functionality first (vertical slices) before optimizing individual components
2. **Fast Feedback**: Prioritize tests that provide immediate feedback during development
3. **Realistic Scenarios**: Create tests that mimic real-world usage patterns
4. **Minimal Mocking**: Use actual dependencies where practical, mocks only when necessary
5. **Pragmatic Coverage**: Focus on testing critical paths thoroughly rather than aiming for arbitrary coverage metrics

## Testing Levels

### 1. Unit Tests

Unit tests verify the functionality of individual components in isolation.

**Focus Areas**:

- Event bus
- Authentication utilities
- Data models
- Simple business logic

**Example Unit Test**:

```python
import pytest
from app.models.domain import User, generate_id

def test_user_model():
    """Test User model creation and validation."""
    # Create user
    user = User(
        user_id="test123",
        name="Test User",
        email="test@example.com",
        metadata={"role": "admin"}
    )

    # Verify fields
    assert user.user_id == "test123"
    assert user.name == "Test User"
    assert user.email == "test@example.com"
    assert user.metadata == {"role": "admin"}

    # Test ID generation
    id1 = generate_id()
    id2 = generate_id()
    assert id1 != id2  # IDs should be unique
    assert isinstance(id1, str)  # ID should be a string
```

### 2. Integration Tests

Integration tests verify that components work together correctly.

**Focus Areas**:

- API endpoints with authentication
- Event bus with subscribers
- MCP client integration with backends
- Database operations (when added)

**Example Integration Test**:

```python
import pytest
import asyncio
from httpx import AsyncClient
from app.main import app
from app.utils.auth import create_access_token

@pytest.mark.asyncio
async def test_input_endpoint():
    """Test the input endpoint with authentication."""
    # Create test token
    token = create_access_token({
        "sub": "test@example.com",
        "oid": "test-user-123",
        "name": "Test User",
        "email": "test@example.com"
    })

    # Set up test client
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Set auth header
        headers = {"Authorization": f"Bearer {token}"}

        # Send test input
        response = await client.post(
            "/input",
            json={"content": "Test message", "metadata": {}},
            headers=headers
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"
        assert data["data"]["content"] == "Test message"
```

### 3. End-to-End Tests

End-to-end tests verify complete workflows from input to output.

**Focus Areas**:

- Input handling and routing
- Authentication flow
- Event routing to output
- MCP backend interaction

**Example End-to-End Test**:

```python
import pytest
import asyncio
import json
from httpx import AsyncClient
from app.main import app
from app.core.event_bus import event_bus
from app.utils.auth import create_access_token
from app.services.memory import MemoryServiceClient
from tests.mocks import MockMcpServer

@pytest.mark.asyncio
async def test_input_to_output_flow():
    """Test the complete flow from input to output."""
    # Start mock MCP server
    mock_server = MockMcpServer()
    await mock_server.start()

    # Create test token
    token = create_access_token({
        "sub": "test@example.com",
        "oid": "test-user-123",
        "name": "Test User",
        "email": "test@example.com"
    })

    # Set up test client
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Set auth header
        headers = {"Authorization": f"Bearer {token}"}

        # Connect to output stream
        async with client.stream("GET", "/output/stream", headers=headers) as stream:
            # Send test input in another task
            input_task = asyncio.create_task(
                client.post(
                    "/input",
                    json={"content": "Test message", "metadata": {}},
                    headers=headers
                )
            )

            # Wait for input response
            input_response = await input_task
            assert input_response.status_code == 200

            # Read from SSE stream
            async for line in stream.aiter_lines():
                if line.startswith("data:"):
                    event_data = json.loads(line[5:].strip())
                    # Verify event data
                    assert event_data["type"] == "input"
                    assert event_data["user_id"] == "test-user-123"
                    assert event_data["data"]["content"] == "Test message"
                    break

            # Verify Memory Service received the input
            stored_data = mock_server.get_stored_data("test-user-123")
            assert len(stored_data) == 1
            assert stored_data[0]["content"] == "Test message"

    # Stop mock server
    await mock_server.stop()
```

## Testing Infrastructure

### 1. Testing Framework

**pytest**: Used for all test types with the following plugins:

- `pytest-asyncio`: For testing async functions
- `pytest-cov`: For measuring test coverage
- `pytest-mock`: For mocking dependencies
- `pytest-env`: For setting environment variables

### 2. Mock Implementations

Create mock implementations for external dependencies:

**MockMcpServer**:

```python
import asyncio
from typing import Dict, List, Any

class MockMcpServer:
    """Mock MCP server for testing."""

    def __init__(self):
        self.stored_data = {}
        self.running = False

    async def start(self):
        """Start the mock server."""
        self.running = True

    async def stop(self):
        """Stop the mock server."""
        self.running = False

    def store_input(self, user_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock store_input tool."""
        if user_id not in self.stored_data:
            self.stored_data[user_id] = []

        self.stored_data[user_id].append(input_data)
        return {"status": "stored", "user_id": user_id}

    def get_stored_data(self, user_id: str) -> List[Dict[str, Any]]:
        """Get stored data for a user."""
        return self.stored_data.get(user_id, [])
```

**MockEventBus**:

```python
import asyncio
from typing import Dict, Any, List

class MockEventBus:
    """Mock event bus for testing."""

    def __init__(self):
        self.published_events = []

    async def publish(self, event: Dict[str, Any]) -> None:
        """Record published events."""
        self.published_events.append(event)

    def get_published_events(self) -> List[Dict[str, Any]]:
        """Get all published events."""
        return self.published_events

    def clear(self) -> None:
        """Clear recorded events."""
        self.published_events.clear()
```

### 3. Test Fixtures

Create reusable test fixtures:

```python
import pytest
import asyncio
from app.utils.auth import create_access_token

@pytest.fixture
def test_token():
    """Create a test authentication token."""
    return create_access_token({
        "sub": "test@example.com",
        "oid": "test-user-123",
        "name": "Test User",
        "email": "test@example.com"
    })

@pytest.fixture
def auth_headers(test_token):
    """Create authentication headers."""
    return {"Authorization": f"Bearer {test_token}"}

@pytest.fixture
async def mock_mcp_server():
    """Create and manage a mock MCP server."""
    server = MockMcpServer()
    await server.start()
    yield server
    await server.stop()

@pytest.fixture
def mock_event_bus():
    """Create a mock event bus."""
    return MockEventBus()
```

## API Testing

### 1. FastAPI TestClient

Use FastAPI's TestClient for API testing:

```python
from fastapi.testclient import TestClient
from app.main import app

def test_api_status():
    """Test API status endpoint."""
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "online", "service": "Cortex Core"}
```

### 2. Async Testing with httpx

Use `httpx.AsyncClient` for testing async API endpoints:

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_async_endpoint():
    """Test an async API endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/some/async/endpoint")
        assert response.status_code == 200
```

## MCP Testing

### 1. Testing MCP Clients

Test MCP client functionality:

```python
import pytest
from unittest.mock import AsyncMock, patch
from app.core.mcp_client import McpClient

@pytest.mark.asyncio
async def test_mcp_client_call_tool():
    """Test MCP client tool call."""
    with patch("mcp.client.sse.sse_client") as mock_sse_client, \
         patch("mcp.ClientSession") as mock_session:
        # Set up mocks
        mock_read_stream = AsyncMock()
        mock_write_stream = AsyncMock()
        mock_sse_client.return_value = (mock_read_stream, mock_write_stream)

        mock_session_instance = AsyncMock()
        mock_session.return_value = mock_session_instance
        mock_session_instance.call_tool.return_value = {"result": "success"}

        # Create client and call tool
        client = McpClient("http://test-server")
        result = await client.call_tool("test-tool", {"arg": "value"})

        # Verify calls
        mock_sse_client.assert_called_once_with("http://test-server")
        mock_session_instance.initialize.assert_called_once()
        mock_session_instance.call_tool.assert_called_once_with(
            "test-tool", {"arg": "value"}
        )

        # Verify result
        assert result == {"result": "success"}
```

### 2. Testing MCP Servers

Test MCP server functionality:

```python
import pytest
from unittest.mock import AsyncMock, patch
from mcp.server.fastmcp import FastMCP

@pytest.mark.asyncio
async def test_mcp_server_tool():
    """Test MCP server tool handling."""
    # Create test server
    mcp = FastMCP("TestServer")

    # Define test tool
    @mcp.tool()
    def test_tool(arg1: str, arg2: int) -> dict:
        return {"arg1": arg1, "arg2": arg2}

    # Patch server run to intercept tool call
    with patch.object(mcp, "run"):
        # Start server
        mcp.run()

        # Call tool directly
        result = test_tool("test", 123)

        # Verify result
        assert result == {"arg1": "test", "arg2": 123}
```

## Event Bus Testing

Test event bus functionality:

```python
import pytest
import asyncio
from app.core.event_bus import EventBus

@pytest.mark.asyncio
async def test_event_bus():
    """Test event bus publish/subscribe."""
    bus = EventBus()

    # Create test queues
    queue1 = asyncio.Queue()
    queue2 = asyncio.Queue()

    # Subscribe both queues
    bus.subscribe(queue1)
    bus.subscribe(queue2)

    # Publish test event
    test_event = {"type": "test", "data": "hello"}
    await bus.publish(test_event)

    # Check both queues received the event
    event1 = await queue1.get()
    event2 = await queue2.get()

    assert event1 == test_event
    assert event2 == test_event

    # Unsubscribe queue1
    bus.unsubscribe(queue1)

    # Publish another event
    test_event2 = {"type": "test2", "data": "world"}
    await bus.publish(test_event2)

    # Only queue2 should receive it
    assert queue1.empty()
    event2_2 = await queue2.get()
    assert event2_2 == test_event2
```

## Authentication Testing

Test JWT authentication:

```python
import pytest
import jwt
from datetime import datetime, timedelta
from app.utils.auth import create_access_token, get_current_user
from fastapi import HTTPException
from unittest.mock import AsyncMock

def test_create_access_token():
    """Test JWT token creation."""
    # Test data
    test_data = {
        "sub": "test@example.com",
        "oid": "test-user-123",
        "name": "Test User"
    }

    # Create token
    token = create_access_token(test_data)

    # Decode token
    decoded = jwt.decode(
        token,
        "devsecretkey",  # Use test secret key
        algorithms=["HS256"]
    )

    # Verify data
    assert decoded["sub"] == test_data["sub"]
    assert decoded["oid"] == test_data["oid"]
    assert decoded["name"] == test_data["name"]
    assert "exp" in decoded  # Should have expiration

@pytest.mark.asyncio
async def test_get_current_user_valid():
    """Test getting current user with valid token."""
    # Create valid token
    test_data = {
        "sub": "test@example.com",
        "oid": "test-user-123",
        "name": "Test User",
        "email": "test@example.com"
    }
    token = create_access_token(test_data)

    # Get current user
    user = await get_current_user(token)

    # Verify user data
    assert user["user_id"] == test_data["oid"]
    assert user["name"] == test_data["name"]
    assert user["email"] == test_data["email"]

@pytest.mark.asyncio
async def test_get_current_user_invalid():
    """Test getting current user with invalid token."""
    # Invalid token
    token = "invalid.token.here"

    # Should raise HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token)

    # Verify exception
    assert exc_info.value.status_code == 401
    assert "Invalid authentication credentials" in exc_info.value.detail
```

## Test Organization

Organize tests by component and test type:

```
tests/
├── unit/                  # Unit tests
│   ├── test_models.py     # Test data models
│   ├── test_auth.py       # Test auth utilities
│   └── test_event_bus.py  # Test event bus
├── integration/           # Integration tests
│   ├── test_api.py        # Test API endpoints
│   ├── test_mcp.py        # Test MCP integration
│   └── test_services.py   # Test service clients
├── e2e/                   # End-to-end tests
│   └── test_workflows.py  # Test complete workflows
└── conftest.py            # Shared test fixtures
```

## Running Tests

Run tests with the following commands:

```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/unit/test_models.py

# Run tests with coverage
python -m pytest --cov=app

# Run tests with verbose output
python -m pytest -v

# Run async tests
python -m pytest --asyncio-mode=auto
```

## Test Coverage

Track test coverage using pytest-cov:

```bash
# Generate coverage report
python -m pytest --cov=app --cov-report=term-missing

# Generate HTML coverage report
python -m pytest --cov=app --cov-report=html
```

Focus on covering:

1. Critical business logic
2. Error handling paths
3. Authentication and authorization
4. User data partitioning
5. Cross-component integration

## Test Environment

Set up test environment variables in `pytest.ini`:

```ini
[pytest]
env =
    JWT_SECRET_KEY=test_secret_key
    MEMORY_SERVICE_URL=http://localhost:9000
    COGNITION_SERVICE_URL=http://localhost:9100
```

## Continuous Integration

Integrate testing into CI pipeline:

```yaml
# Example GitHub Actions workflow
name: Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.10"
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov
      - name: Run tests
        run: |
          python -m pytest --cov=app --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

## Summary

This testing strategy provides a comprehensive approach to testing the Cortex Core system. By following these guidelines, you can ensure:

1. **Complete Functionality**: End-to-end testing of critical user flows
2. **Component Reliability**: Unit and integration testing of individual components
3. **Early Feedback**: Fast, focused tests that catch issues early
4. **Realistic Scenarios**: Tests that mimic actual usage patterns
5. **Maintainable Tests**: Clear organization and minimal brittleness

Implement these testing practices from the beginning of development to ensure a stable, reliable system.
