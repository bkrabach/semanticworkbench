# Testing MCP Services

## Overview

This document provides a comprehensive guide for testing MCP-based services in Phase 3 of the Cortex Core project. It covers testing strategies, frameworks, techniques, and examples for thoroughly testing the in-process MCP services implemented in this phase.

Testing MCP services requires a specialized approach that verifies both the correct implementation of the MCP interface (tools and resources) and the underlying service functionality. This document focuses on the unique aspects of testing these services, with an emphasis on maintaining service boundaries even during testing.

In Phase 3, all services are implemented in-process, but they are designed with clear boundaries to facilitate the transition to distributed services in Phase 4. The testing approach outlined here respects these boundaries while providing comprehensive test coverage.

## Testing Philosophy

The testing philosophy for MCP services follows these core principles:

1. **Respect Service Boundaries**: Test services through their defined interfaces
2. **Isolated Unit Testing**: Test individual components in isolation with proper mocking
3. **Integration Testing**: Test the interaction between components
4. **End-to-End Testing**: Test complete flows through the system
5. **Error Scenario Coverage**: Extensively test error handling and recovery
6. **Performance Awareness**: Include basic performance testing
7. **Maintainable Tests**: Organize tests for clarity and maintainability

## Testing Framework

### pytest and pytest-asyncio

The preferred testing framework for MCP services is pytest with the pytest-asyncio extension for testing async code:

```bash
# Install testing dependencies
pip install pytest pytest-asyncio pytest-cov pytest-mock
```

Basic pytest configuration in `pytest.ini`:

```ini
[pytest]
asyncio_mode = auto
python_files = test_*.py
python_classes = Test*
python_functions = test_*
testpaths = tests
```

### Testing Utilities

Create a `conftest.py` file with common test fixtures:

```python
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from app.core.mcp_client import McpClient
from app.services.memory_service import MemoryService
from app.services.cognition_service import CognitionService

@pytest.fixture
def mock_repository():
    """Create a mock repository."""
    repository = MagicMock()
    repository.get_items_by_user = AsyncMock(return_value=[])
    repository.store_item = AsyncMock(return_value=None)
    repository.get_item = AsyncMock(return_value={})
    repository.update_item = AsyncMock(return_value={})
    repository.delete_item = AsyncMock(return_value=True)
    return repository

@pytest.fixture
def memory_service(mock_repository):
    """Create a Memory Service with a mock repository."""
    return MemoryService(mock_repository)

@pytest.fixture
def cognition_service():
    """Create a Cognition Service for testing."""
    return CognitionService()

@pytest.fixture
def memory_client(memory_service):
    """Create an MCP client for the Memory Service."""
    return McpClient(memory_service, "memory")

@pytest.fixture
def cognition_client(cognition_service):
    """Create an MCP client for the Cognition Service."""
    return McpClient(cognition_service, "cognition")

@pytest.fixture
def mcp_client_manager(memory_client, cognition_client):
    """Create an MCP client manager with test clients."""
    from app.core.mcp_client import McpClientManager
    manager = McpClientManager()
    manager.register_client("memory", memory_client)
    manager.register_client("cognition", cognition_client)
    return manager

@pytest.fixture
def test_user_id():
    """Return a test user ID."""
    return "test-user-123"

@pytest.fixture
def test_input_data():
    """Return test input data."""
    return {
        "content": "Test content",
        "conversation_id": "conv-123",
        "timestamp": "2023-01-01T12:00:00Z",
        "metadata": {"client_id": "test-client"}
    }
```

## Types of Tests

### Unit Tests

Unit tests verify the functionality of individual components in isolation:

1. **Tool Tests**: Test individual tool implementations
2. **Resource Tests**: Test individual resource implementations
3. **MCP Client Tests**: Test MCP client functionality
4. **Service Method Tests**: Test internal service methods

### Integration Tests

Integration tests verify the interaction between components:

1. **Service-Repository Tests**: Test service interaction with repositories
2. **Client-Service Tests**: Test MCP client interaction with services
3. **Service-Service Tests**: Test communication between services

### End-to-End Tests

End-to-end tests verify complete flows through the system:

1. **API-Service Tests**: Test API endpoints that use services
2. **Complete Flow Tests**: Test flows from input to output through multiple services

## Testing MCP Clients

### Testing Direct Method Calls

Test calling methods on the MCP client:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_mcp_client_call_tool():
    """Test calling a tool via the MCP client."""
    # Create mock service
    mock_service = MagicMock()
    mock_service.test_tool = AsyncMock(return_value={"status": "success", "data": "result"})

    # Create MCP client
    from app.core.mcp_client import McpClient
    client = McpClient(mock_service, "test_service")

    # Call tool
    result = await client.call_tool(
        "test_tool",
        {"param1": "value1", "param2": "value2"}
    )

    # Verify result
    assert result == {"status": "success", "data": "result"}

    # Verify service method was called with correct arguments
    mock_service.test_tool.assert_called_once_with(
        param1="value1",
        param2="value2"
    )

@pytest.mark.asyncio
async def test_mcp_client_get_resource():
    """Test getting a resource via the MCP client."""
    # Create mock service
    mock_service = MagicMock()
    mock_service.get_resource_test = AsyncMock(return_value={"key": "value"})

    # Create MCP client
    from app.core.mcp_client import McpClient
    client = McpClient(mock_service, "test_service")

    # Get resource
    result, _ = await client.get_resource("test/param1/param2")

    # Verify result
    assert result == {"key": "value"}

    # Verify service method was called with correct arguments
    mock_service.get_resource_test.assert_called_once_with("param1", "param2")
```

### Testing Error Handling

Test error handling in the MCP client:

```python
@pytest.mark.asyncio
async def test_mcp_client_tool_not_found():
    """Test error handling when a tool doesn't exist."""
    # Create mock service without the requested tool
    mock_service = MagicMock()

    # Create MCP client
    from app.core.mcp_client import McpClient, ToolNotFoundError
    client = McpClient(mock_service, "test_service")

    # Call non-existent tool
    with pytest.raises(ToolNotFoundError):
        await client.call_tool("non_existent_tool", {})

@pytest.mark.asyncio
async def test_mcp_client_tool_execution_error():
    """Test error handling when a tool raises an exception."""
    # Create mock service with a tool that raises an exception
    mock_service = MagicMock()
    mock_service.test_tool = AsyncMock(side_effect=Exception("Test error"))

    # Create MCP client
    from app.core.mcp_client import McpClient, ToolExecutionError
    client = McpClient(mock_service, "test_service")

    # Call tool that raises an exception
    with pytest.raises(ToolExecutionError):
        await client.call_tool("test_tool", {})
```

### Testing Client Manager

Test the MCP client manager:

```python
def test_mcp_client_manager():
    """Test the MCP client manager."""
    # Create mock clients
    mock_client1 = MagicMock()
    mock_client2 = MagicMock()

    # Create client manager
    from app.core.mcp_client import McpClientManager, ServiceNotFoundError
    manager = McpClientManager()

    # Register clients
    manager.register_client("service1", mock_client1)
    manager.register_client("service2", mock_client2)

    # Get client
    client1 = manager.get_client("service1")
    client2 = manager.get_client("service2")

    # Verify clients
    assert client1 == mock_client1
    assert client2 == mock_client2

    # Test error when service not found
    with pytest.raises(ServiceNotFoundError):
        manager.get_client("non_existent_service")
```

## Testing MCP Services

### Testing Tool Implementations

Test individual tool implementations within a service:

```python
@pytest.mark.asyncio
async def test_store_input_tool(memory_service, test_user_id, test_input_data):
    """Test the store_input tool in the Memory Service."""
    # Call the tool directly
    result = await memory_service.store_input(test_user_id, test_input_data)

    # Verify the result format
    assert "status" in result
    assert result["status"] == "stored"
    assert "item_id" in result

    # Verify repository interaction
    memory_service.repository.store_item.assert_called_once()

    # Verify item format in repository call
    call_args = memory_service.repository.store_item.call_args[0][0]
    assert call_args["user_id"] == test_user_id
    assert call_args["data"] == test_input_data
    assert "id" in call_args
    assert "timestamp" in call_args

@pytest.mark.asyncio
async def test_get_context_tool(cognition_service, test_user_id):
    """Test the get_context tool in the Cognition Service."""
    # Mock the memory service access
    mock_history = [
        {"id": "item1", "user_id": test_user_id, "data": {"content": "Test content"}},
        {"id": "item2", "user_id": test_user_id, "data": {"content": "More content"}}
    ]
    cognition_service._get_history_from_memory = AsyncMock(return_value=mock_history)

    # Call the tool directly
    result = await cognition_service.get_context(
        test_user_id,
        query="test",
        limit=5
    )

    # Verify the result format
    assert "context" in result
    assert "user_id" in result
    assert "query" in result
    assert "count" in result

    # Verify memory service access
    cognition_service._get_history_from_memory.assert_called_once_with(
        test_user_id,
        limit=10  # Should request twice as many items for ranking
    )
```

### Testing Resource Implementations

Test individual resource implementations within a service:

```python
@pytest.mark.asyncio
async def test_get_history_resource(memory_service, test_user_id):
    """Test the get_history resource in the Memory Service."""
    # Mock repository to return test data
    test_items = [
        {"id": "item1", "user_id": test_user_id, "data": {"content": "Test content"}},
        {"id": "item2", "user_id": test_user_id, "data": {"content": "More content"}}
    ]
    memory_service.repository.get_items_by_user = AsyncMock(return_value=test_items)

    # Call the resource directly
    result = await memory_service.get_history(test_user_id)

    # Verify the result
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["id"] == "item1"
    assert result[1]["id"] == "item2"

    # Verify repository call
    memory_service.repository.get_items_by_user.assert_called_once_with(test_user_id)

@pytest.mark.asyncio
async def test_get_limited_history_resource(memory_service, test_user_id):
    """Test the get_limited_history resource in the Memory Service."""
    # Mock repository to return test data
    test_items = [
        {"id": "item1", "user_id": test_user_id, "data": {"content": "Test content"}},
        {"id": "item2", "user_id": test_user_id, "data": {"content": "More content"}}
    ]
    memory_service.repository.get_items_by_user = AsyncMock(return_value=test_items)

    # Call the resource directly
    result = await memory_service.get_limited_history(test_user_id, "5")

    # Verify the result
    assert isinstance(result, list)
    assert len(result) == 2

    # Verify repository call with limit
    # Note: The implementation should convert the string to int
    memory_service.repository.get_items_by_user.assert_called_once()
    call_args = memory_service.repository.get_items_by_user.call_args
    assert call_args[0][0] == test_user_id
    assert "limit" in call_args[1]
    assert call_args[1]["limit"] == 5
```

### Testing Error Handling

Test error handling in service implementations:

```python
@pytest.mark.asyncio
async def test_store_input_validation(memory_service):
    """Test input validation in the store_input tool."""
    # Call with missing user_id
    result1 = await memory_service.store_input("", {"content": "Test"})
    assert result1["status"] == "error"
    assert "user_id is required" in result1["error"]

    # Call with missing input_data
    result2 = await memory_service.store_input("test_user", None)
    assert result2["status"] == "error"
    assert "input_data is required" in result2["error"]

@pytest.mark.asyncio
async def test_store_input_repository_error(memory_service, test_user_id, test_input_data):
    """Test repository error handling in the store_input tool."""
    # Mock repository to raise an exception
    memory_service.repository.store_item = AsyncMock(side_effect=Exception("Test error"))

    # Call the tool
    result = await memory_service.store_input(test_user_id, test_input_data)

    # Verify error response
    assert result["status"] == "error"
    assert "error" in result
    assert "Test error" in result["error"]

@pytest.mark.asyncio
async def test_get_history_error_handling(memory_service, test_user_id):
    """Test error handling in the get_history resource."""
    # Mock repository to raise an exception
    memory_service.repository.get_items_by_user = AsyncMock(side_effect=Exception("Test error"))

    # Call the resource
    result = await memory_service.get_history(test_user_id)

    # Verify empty result on error (resources should never throw)
    assert isinstance(result, list)
    assert len(result) == 0
```

## Testing Service Integration

### Testing Service-to-Service Communication

Test the communication between services:

```python
@pytest.mark.asyncio
async def test_cognition_memory_integration(
    cognition_service,
    memory_service,
    memory_client,
    mcp_client_manager,
    test_user_id
):
    """Test integration between Cognition and Memory services."""
    # Set up cognition service to use MCP client
    cognition_service.mcp_client_manager = mcp_client_manager

    # Mock data in memory service
    test_items = [
        {"id": "item1", "user_id": test_user_id, "data": {"content": "Test content"}},
        {"id": "item2", "user_id": test_user_id, "data": {"content": "More content"}}
    ]
    memory_service.repository.get_items_by_user = AsyncMock(return_value=test_items)

    # Call cognition service method that uses memory service
    result = await cognition_service.get_context(test_user_id, query="test")

    # Verify result
    assert "context" in result
    assert len(result["context"]) > 0
    assert result["user_id"] == test_user_id
```

### Testing Complete Flows

Test complete flows through multiple services:

```python
@pytest.mark.asyncio
async def test_input_processing_flow(
    memory_service,
    cognition_service,
    memory_client,
    cognition_client,
    mcp_client_manager,
    test_user_id,
    test_input_data
):
    """Test the complete input processing flow."""
    # Set up services and clients
    cognition_service.mcp_client_manager = mcp_client_manager

    # Mock data for memory service
    test_items = [
        {"id": "item1", "user_id": test_user_id, "data": {"content": "Previous content"}},
        {"id": "item2", "user_id": test_user_id, "data": {"content": "More content"}}
    ]
    memory_service.repository.get_items_by_user = AsyncMock(return_value=test_items)

    # Step 1: Store input in memory service
    store_result = await memory_client.call_tool(
        "store_input",
        {
            "user_id": test_user_id,
            "input_data": test_input_data
        }
    )

    # Verify store result
    assert store_result["status"] == "stored"
    assert "item_id" in store_result

    # Step 2: Get context from cognition service
    context_result = await cognition_client.call_tool(
        "get_context",
        {
            "user_id": test_user_id,
            "query": test_input_data["content"],
            "limit": 5
        }
    )

    # Verify context result
    assert "context" in context_result
    assert "user_id" in context_result
    assert context_result["user_id"] == test_user_id
```

## Testing with Mocks

### Creating Mock Services

Create mock services for testing components that use services:

```python
def create_mock_memory_service():
    """Create a mock Memory Service."""
    mock_service = MagicMock()

    # Mock tools
    mock_service.store_input = AsyncMock(
        return_value={"status": "stored", "item_id": "test-item-id"}
    )
    mock_service.update_item = AsyncMock(
        return_value={"status": "updated", "item_id": "test-item-id"}
    )
    mock_service.delete_item = AsyncMock(
        return_value={"status": "deleted", "item_id": "test-item-id"}
    )

    # Mock resources
    mock_service.get_resource_history = AsyncMock(
        return_value=[
            {"id": "item1", "user_id": "test-user", "data": {"content": "Test content"}},
            {"id": "item2", "user_id": "test-user", "data": {"content": "More content"}}
        ]
    )
    mock_service.get_resource_item = AsyncMock(
        return_value={"id": "item1", "user_id": "test-user", "data": {"content": "Test content"}}
    )

    return mock_service

def create_mock_cognition_service():
    """Create a mock Cognition Service."""
    mock_service = MagicMock()

    # Mock tools
    mock_service.get_context = AsyncMock(
        return_value={
            "context": [
                {"id": "item1", "data": {"content": "Context item 1"}},
                {"id": "item2", "data": {"content": "Context item 2"}}
            ],
            "user_id": "test-user",
            "query": "test",
            "count": 2
        }
    )
    mock_service.analyze_conversation = AsyncMock(
        return_value={
            "analysis": {
                "type": "summary",
                "summary": "Test conversation summary"
            },
            "conversation_id": "test-conv",
            "status": "success"
        }
    )

    return mock_service
```

### Using Mock Services in Tests

Use mock services to test components that depend on services:

```python
@pytest.mark.asyncio
async def test_component_with_mock_services():
    """Test a component that uses services."""
    # Create mock services
    mock_memory_service = create_mock_memory_service()
    mock_cognition_service = create_mock_cognition_service()

    # Create mock clients
    memory_client = McpClient(mock_memory_service, "memory")
    cognition_client = McpClient(mock_cognition_service, "cognition")

    # Create client manager
    client_manager = McpClientManager()
    client_manager.register_client("memory", memory_client)
    client_manager.register_client("cognition", cognition_client)

    # Create component to test
    component = InputProcessor(client_manager)

    # Test the component
    result = await component.process_input(
        "test-user",
        {"content": "Test input", "conversation_id": "test-conv"}
    )

    # Verify result
    assert "response" in result
    assert "context" in result

    # Verify service interactions
    mock_memory_service.store_input.assert_called_once()
    mock_cognition_service.get_context.assert_called_once()
```

## Testing API Integration

Test API endpoints that use MCP services:

```python
from fastapi.testclient import TestClient
from app.main import app

def test_input_endpoint(mcp_client_manager):
    """Test the input endpoint."""
    # Replace app's MCP client manager with test manager
    app.state.mcp_client_manager = mcp_client_manager

    # Create test client
    client = TestClient(app)

    # Create test token
    # (Assuming a create_test_token helper function)
    token = create_test_token(user_id="test-user")

    # Make request
    response = client.post(
        "/input",
        json={"content": "Test input", "conversation_id": "test-conv"},
        headers={"Authorization": f"Bearer {token}"}
    )

    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "received"
```

For async endpoints, use an async test client:

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_async_endpoint(mcp_client_manager):
    """Test an async endpoint."""
    # Replace app's MCP client manager with test manager
    app.state.mcp_client_manager = mcp_client_manager

    # Create token
    token = create_test_token(user_id="test-user")

    # Make request
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/input",
            json={"content": "Test input", "conversation_id": "test-conv"},
            headers={"Authorization": f"Bearer {token}"}
        )

    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "received"
```

## Testing Error Scenarios

Test error scenarios for MCP services:

```python
@pytest.mark.asyncio
async def test_tool_not_found_error(memory_client):
    """Test error handling when a tool doesn't exist."""
    from app.core.mcp_client import ToolNotFoundError

    # Attempt to call non-existent tool
    with pytest.raises(ToolNotFoundError):
        await memory_client.call_tool("non_existent_tool", {"user_id": "test-user"})

@pytest.mark.asyncio
async def test_resource_not_found_error(memory_client):
    """Test error handling when a resource doesn't exist."""
    from app.core.mcp_client import ResourceNotFoundError

    # Attempt to access non-existent resource
    with pytest.raises(ResourceNotFoundError):
        await memory_client.get_resource("non_existent_resource/test-user")

@pytest.mark.asyncio
async def test_tool_validation_error(memory_service, memory_client):
    """Test error handling when tool validation fails."""
    # Call tool with invalid parameters
    result = await memory_client.call_tool(
        "store_input",
        {"user_id": "", "input_data": None}
    )

    # Verify error response
    assert result["status"] == "error"
    assert "error" in result

@pytest.mark.asyncio
async def test_resource_error_handling(memory_service, memory_client):
    """Test that resources don't throw exceptions to clients."""
    # Mock repository to throw an exception
    memory_service.repository.get_items_by_user = AsyncMock(
        side_effect=Exception("Test error")
    )

    # Call resource
    # Should return empty list instead of throwing
    result, _ = await memory_client.get_resource(f"history/test-user")

    # Verify empty result
    assert isinstance(result, list)
    assert len(result) == 0
```

## Testing Performance

Basic performance testing for MCP services:

```python
import time
import statistics

@pytest.mark.asyncio
async def test_tool_performance(memory_client, test_user_id, test_input_data):
    """Test the performance of a tool."""
    # Number of iterations
    iterations = 100

    # Measure execution times
    execution_times = []
    for _ in range(iterations):
        start_time = time.time()

        await memory_client.call_tool(
            "store_input",
            {"user_id": test_user_id, "input_data": test_input_data}
        )

        end_time = time.time()
        execution_times.append(end_time - start_time)

    # Calculate statistics
    avg_time = statistics.mean(execution_times)
    max_time = max(execution_times)
    min_time = min(execution_times)
    percentile_95 = sorted(execution_times)[int(iterations * 0.95)]

    # Print results
    print(f"Performance results for store_input tool:")
    print(f"  Average time: {avg_time:.6f} seconds")
    print(f"  95th percentile: {percentile_95:.6f} seconds")
    print(f"  Min time: {min_time:.6f} seconds")
    print(f"  Max time: {max_time:.6f} seconds")

    # Assert performance meets requirements
    assert avg_time < 0.01  # 10ms average
    assert percentile_95 < 0.02  # 20ms 95th percentile
```

## Common Testing Patterns

### Tool Testing Pattern

```python
@pytest.mark.asyncio
async def test_tool_pattern(service, mock_repository):
    """General pattern for testing a tool."""
    # 1. Setup test data
    test_user_id = "test-user"
    test_data = {"key": "value"}

    # 2. Configure mocks
    mock_repository.some_method = AsyncMock(return_value={"id": "test-id"})

    # 3. Call the tool
    result = await service.some_tool(test_user_id, test_data)

    # 4. Verify result structure
    assert "status" in result
    assert result["status"] == "success"

    # 5. Verify expected side effects
    mock_repository.some_method.assert_called_once_with(test_user_id, test_data)

    # 6. Verify error cases
    error_result = await service.some_tool("", {})
    assert error_result["status"] == "error"
```

### Resource Testing Pattern

```python
@pytest.mark.asyncio
async def test_resource_pattern(service, mock_repository):
    """General pattern for testing a resource."""
    # 1. Setup test data
    test_user_id = "test-user"
    test_items = [{"id": "item1"}, {"id": "item2"}]

    # 2. Configure mocks
    mock_repository.get_items = AsyncMock(return_value=test_items)

    # 3. Call the resource
    result = await service.get_resource_something(test_user_id)

    # 4. Verify result
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["id"] == "item1"

    # 5. Verify repository calls
    mock_repository.get_items.assert_called_once_with(test_user_id)

    # 6. Test error handling
    mock_repository.get_items = AsyncMock(side_effect=Exception("Test error"))
    error_result = await service.get_resource_something(test_user_id)
    assert isinstance(error_result, list)
    assert len(error_result) == 0  # Empty list on error
```

### MCP Client Testing Pattern

```python
@pytest.mark.asyncio
async def test_mcp_client_pattern(service):
    """General pattern for testing an MCP client."""
    # 1. Create mock service
    mock_service = MagicMock()
    mock_service.some_tool = AsyncMock(return_value={"status": "success"})
    mock_service.get_resource_something = AsyncMock(return_value=[{"id": "item1"}])

    # 2. Create MCP client
    client = McpClient(mock_service, "test_service")

    # 3. Test tool call
    tool_result = await client.call_tool(
        "some_tool",
        {"param1": "value1"}
    )

    # 4. Verify tool call
    assert tool_result == {"status": "success"}
    mock_service.some_tool.assert_called_once_with(param1="value1")

    # 5. Test resource access
    resource_result, _ = await client.get_resource("something/param1")

    # 6. Verify resource access
    assert resource_result == [{"id": "item1"}]
    mock_service.get_resource_something.assert_called_once_with("param1")
```

## Test Organization

Organize MCP service tests for maintainability:

```
tests/
├── unit/                         # Unit tests
│   ├── services/                 # Service tests
│   │   ├── test_memory_service.py    # Memory Service tests
│   │   └── test_cognition_service.py # Cognition Service tests
│   ├── core/                     # Core component tests
│   │   ├── test_mcp_client.py        # MCP client tests
│   │   └── test_event_bus.py         # Event bus tests
│   └── api/                      # API tests
│       ├── test_input_api.py         # Input API tests
│       └── test_output_api.py        # Output API tests
├── integration/                  # Integration tests
│   ├── test_memory_repository.py     # Memory-Repository integration
│   ├── test_cognition_memory.py      # Cognition-Memory integration
│   └── test_api_services.py          # API-Services integration
├── e2e/                          # End-to-end tests
│   └── test_flows.py                 # Complete flow tests
└── conftest.py                   # Shared test fixtures
```

## Testing Anti-Patterns to Avoid

### Anti-Pattern 1: Testing Internal Implementation Details

```python
# BAD: Testing internal implementation details
@pytest.mark.asyncio
async def test_internal_implementation(memory_service):
    """Test an internal method directly."""
    result = await memory_service._internal_helper_method("test-user")
    assert result == expected_value
```

Instead, test through the public interface (tools and resources):

```python
# GOOD: Testing through the public interface
@pytest.mark.asyncio
async def test_public_interface(memory_service):
    """Test the public tool that uses the internal method."""
    result = await memory_service.public_tool("test-user", "data")
    assert result["status"] == "success"
```

### Anti-Pattern 2: Testing Across Service Boundaries

```python
# BAD: Testing across service boundaries
@pytest.mark.asyncio
async def test_across_boundaries(cognition_service, memory_service):
    """Test by setting up direct access to another service."""
    # Directly connecting services
    cognition_service.memory_service = memory_service

    result = await cognition_service.get_context("test-user")
    assert "context" in result
```

Instead, use the MCP client:

```python
# GOOD: Testing using the MCP client
@pytest.mark.asyncio
async def test_using_mcp_client(cognition_service, memory_client, mcp_client_manager):
    """Test using the MCP client."""
    # Set up proper MCP client access
    cognition_service.mcp_client_manager = mcp_client_manager

    result = await cognition_service.get_context("test-user")
    assert "context" in result
```

### Anti-Pattern 3: Overly Complex Test Setup

```python
# BAD: Overly complex test setup
@pytest.mark.asyncio
async def test_with_complex_setup(memory_service, test_user_id):
    """Test with overly complex setup."""
    # Complex setup with many mock objects and configurations
    mock_repo = memory_service.repository
    mock_repo.get_items_by_user = AsyncMock()
    mock_repo.get_items_by_user.side_effect = lambda user_id, **kwargs: [
        {"id": f"item{i}", "user_id": user_id, "data": {"content": f"Content {i}"}}
        for i in range(1, 11)
    ]
    # More complex setup...

    # Finally, the actual test
    result = await memory_service.get_history(test_user_id)
    assert len(result) == 10
```

Instead, use fixtures and helper methods:

```python
# GOOD: Using fixtures and helpers
@pytest.mark.asyncio
async def test_with_fixtures(memory_service, test_user_id, setup_test_data):
    """Test using fixtures and helpers."""
    # Fixture handles the setup
    test_items = setup_test_data(test_user_id, 10)
    memory_service.repository.get_items_by_user = AsyncMock(return_value=test_items)

    # Clean, focused test
    result = await memory_service.get_history(test_user_id)
    assert len(result) == 10
```

## Debugging Failed Tests

### Common Failure Patterns

1. **Service Boundary Violations**

   - Error: Accessing internal implementation details across services
   - Fix: Use proper MCP client communication

2. **Async Test Issues**

   - Error: Forgetting to await async calls
   - Fix: Ensure all async calls are properly awaited

3. **Mock Configuration Problems**
   - Error: Mocks not returning expected values
   - Fix: Verify mock setup and return values

### Debugging Techniques

```python
# Add debug logs to tests
import logging
logging.basicConfig(level=logging.DEBUG)

@pytest.mark.asyncio
async def test_with_debugging(memory_service, test_user_id):
    """Test with debugging enabled."""
    # Enable detailed logging
    logging.getLogger("app.services").setLevel(logging.DEBUG)

    # Add debug prints
    print(f"Testing with user_id: {test_user_id}")

    # Run test
    result = await memory_service.get_history(test_user_id)

    # Print results for debugging
    print(f"Result: {result}")

    # Run assertion
    assert len(result) > 0
```

### Test Isolation

Ensure tests are isolated and don't affect each other:

```python
@pytest.fixture(autouse=True)
def reset_mocks(mock_repository):
    """Reset all mocks before each test."""
    mock_repository.reset_mock()
    yield
    # Additional cleanup after test

@pytest.fixture
def isolated_memory_service(mock_repository):
    """Create an isolated memory service for each test."""
    return MemoryService(mock_repository)
```

## Testing Checklist

Use this checklist to ensure comprehensive testing of MCP services:

1. **Tool Tests**

   - [ ] Tool returns expected format
   - [ ] Tool handles valid input correctly
   - [ ] Tool validates input parameters
   - [ ] Tool handles invalid input gracefully
   - [ ] Tool reports errors properly
   - [ ] Tool interacts with repositories correctly

2. **Resource Tests**

   - [ ] Resource returns expected data format
   - [ ] Resource handles parameters correctly
   - [ ] Resource handles errors gracefully (never throws)
   - [ ] Resource returns empty data on error
   - [ ] Resource interacts with repositories correctly

3. **Client Tests**

   - [ ] Client calls tools correctly
   - [ ] Client accesses resources correctly
   - [ ] Client handles tool not found errors
   - [ ] Client handles resource not found errors
   - [ ] Client handles execution errors

4. **Service Integration Tests**

   - [ ] Services communicate properly
   - [ ] Services respect boundaries
   - [ ] Complete flows work end-to-end
   - [ ] Error handling works across services

5. **API Integration Tests**
   - [ ] API endpoints use services correctly
   - [ ] API endpoints handle errors from services
   - [ ] Authentication works properly
   - [ ] Complete API flows work end-to-end

## Continuous Integration

Set up continuous integration for MCP service tests:

```yaml
# .github/workflows/test.yml
name: Run Tests

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
          pip install -e .
          pip install pytest pytest-asyncio pytest-cov
      - name: Run unit tests
        run: pytest tests/unit -v
      - name: Run integration tests
        run: pytest tests/integration -v
      - name: Run end-to-end tests
        run: pytest tests/e2e -v
      - name: Generate coverage report
        run: pytest --cov=app --cov-report=xml
      - name: Upload coverage report
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

## Conclusion

Testing MCP services in Phase 3 requires a careful approach that respects service boundaries while providing comprehensive test coverage. By following the patterns and techniques in this guide, you can create tests that verify both the correct implementation of the MCP interface and the underlying service functionality.

Key takeaways:

1. **Respect Boundaries**: Test services through their defined interfaces
2. **Focus on Tools and Resources**: Test the public MCP interface thoroughly
3. **Mock Dependencies**: Use proper mocking for repositories and services
4. **Test Error Handling**: Verify error scenarios and recovery
5. **End-to-End Testing**: Test complete flows through the system

This testing approach will help ensure that the MCP services are reliable, maintainable, and ready for the transition to distributed services in Phase 4.
