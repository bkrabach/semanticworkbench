"""
Tests for the network MCP client.
"""

import asyncio
import json
from typing import AsyncGenerator, AsyncIterable
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from app.core.mcp.exceptions import (
    CircuitOpenError,
    ResourceAccessError,
    ResourceNotFoundError,
    ServiceNotFoundError,
    ToolExecutionError,
    ToolNotFoundError,
)
from app.core.mcp.network_client import CircuitBreaker, ConnectionPool, NetworkMcpClient


@pytest.fixture
async def mock_service_discovery() -> AsyncMock:
    """Create a mock service discovery for testing."""
    discovery = AsyncMock()
    discovery.resolve.return_value = "http://test-service:8000"
    return discovery


@pytest.fixture
async def network_client(mock_service_discovery: AsyncMock) -> AsyncGenerator[NetworkMcpClient, None]:
    """Create a network MCP client for testing."""
    client = NetworkMcpClient(mock_service_discovery)
    yield client
    await client.close()


@pytest.mark.asyncio
async def test_connect_to_service(network_client: NetworkMcpClient, mock_service_discovery: AsyncMock) -> None:
    """Test connecting to a service."""
    # Mock initialize method to avoid actual initialization
    with patch.object(ConnectionPool, "initialize", AsyncMock()):
        await network_client.connect("test-service")

    # Verify service discovery was called
    mock_service_discovery.resolve.assert_called_once_with("test-service")
    
    # Verify connection pool was created
    assert "test-service" in network_client.connection_pools
    
    # Verify circuit breaker was created
    assert "test-service" in network_client.circuit_breakers


@pytest.mark.asyncio
async def test_call_tool_success(network_client: NetworkMcpClient) -> None:
    """Test successfully calling a tool."""
    # Mock connection pool to avoid actual HTTP requests
    mock_pool = AsyncMock()
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"result": {"message": "success"}}
    mock_client.post.return_value = mock_response
    mock_pool.get_connection.return_value = mock_client
    
    # Insert mock pool
    network_client.connection_pools["test-service"] = mock_pool
    
    # Mock connect to avoid actual connection
    with patch.object(network_client, "connect", AsyncMock()):
        result = await network_client.call_tool("test-service", "test-tool", {"param": "value"})
    
    # Verify client was called correctly
    mock_client.post.assert_called_once_with(
        "/tool/test-tool",
        json={"arguments": {"param": "value"}},
        timeout=30.0  # Default timeout
    )
    
    # Verify result
    assert result == {"message": "success"}


@pytest.mark.asyncio
async def test_call_tool_not_found(network_client: NetworkMcpClient) -> None:
    """Test calling a tool that doesn't exist."""
    # Mock connection pool to avoid actual HTTP requests
    mock_pool = AsyncMock()
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.json.return_value = {"error": {"message": "Tool not found"}}
    mock_client.post.return_value = mock_response
    mock_pool.get_connection.return_value = mock_client
    
    # Insert mock pool
    network_client.connection_pools["test-service"] = mock_pool
    
    # Mock connect to avoid actual connection
    with patch.object(network_client, "connect", AsyncMock()):
        with pytest.raises(ToolNotFoundError):
            await network_client.call_tool("test-service", "nonexistent-tool", {"param": "value"})


@pytest.mark.asyncio
async def test_call_tool_service_error(network_client: NetworkMcpClient) -> None:
    """Test calling a tool that returns an error."""
    # Mock connection pool to avoid actual HTTP requests
    mock_pool = AsyncMock()
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.json.return_value = {"error": {"message": "Internal server error"}}
    mock_client.post.return_value = mock_response
    mock_pool.get_connection.return_value = mock_client
    
    # Insert mock pool
    network_client.connection_pools["test-service"] = mock_pool
    
    # Insert circuit breaker
    network_client.circuit_breakers["test-service"] = CircuitBreaker(failure_threshold=1)
    
    # Mock connect to avoid actual connection
    with patch.object(network_client, "connect", AsyncMock()):
        with pytest.raises(ToolExecutionError) as excinfo:
            await network_client.call_tool("test-service", "test-tool", {"param": "value"}, max_retries=0)
    
    # Verify error message
    assert "Internal server error" in str(excinfo.value)


@pytest.mark.asyncio
async def test_call_tool_network_error_with_retry(network_client: NetworkMcpClient) -> None:
    """Test calling a tool with a network error that gets retried."""
    # Mock connection pool to avoid actual HTTP requests
    mock_pool = AsyncMock()
    mock_client = AsyncMock()
    
    # First call fails, second call succeeds
    mock_client.post.side_effect = [
        httpx.ConnectError("Connection refused"),
        MagicMock(status_code=200, json=lambda: {"result": {"message": "success"}})
    ]
    mock_pool.get_connection.return_value = mock_client
    
    # Insert mock pool
    network_client.connection_pools["test-service"] = mock_pool
    
    # Mock connect to avoid actual connection
    # Mock asyncio.sleep to avoid waiting
    with patch.object(network_client, "connect", AsyncMock()), \
         patch.object(asyncio, "sleep", AsyncMock()):
        result = await network_client.call_tool("test-service", "test-tool", {"param": "value"}, max_retries=1)
    
    # Verify client was called twice
    assert mock_client.post.call_count == 2
    
    # Verify result
    assert result == {"message": "success"}


@pytest.mark.asyncio
async def test_call_tool_circuit_breaker(network_client: NetworkMcpClient) -> None:
    """Test that the circuit breaker prevents calls after failures."""
    # Mock connection pool to avoid actual HTTP requests
    mock_pool = AsyncMock()
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.json.return_value = {"error": {"message": "Internal server error"}}
    mock_client.post.return_value = mock_response
    mock_pool.get_connection.return_value = mock_client
    
    # Insert mock pool
    network_client.connection_pools["test-service"] = mock_pool
    
    # Create circuit breaker with low threshold
    network_client.circuit_breakers["test-service"] = CircuitBreaker(failure_threshold=2, recovery_time=600)
    
    # Mock connect to avoid actual connection
    with patch.object(network_client, "connect", AsyncMock()):
        # First call - circuit closed
        with pytest.raises(ToolExecutionError):
            await network_client.call_tool("test-service", "test-tool", {"param": "value"}, max_retries=0)
        
        # Second call - circuit closed
        with pytest.raises(ToolExecutionError):
            await network_client.call_tool("test-service", "test-tool", {"param": "value"}, max_retries=0)
        
        # Third call - circuit should be open
        with pytest.raises(CircuitOpenError):
            await network_client.call_tool("test-service", "test-tool", {"param": "value"}, max_retries=0)


@pytest.mark.asyncio
async def test_get_resource_success(network_client: NetworkMcpClient) -> None:
    """Test successfully getting a resource."""
    # Mock connection pool to avoid actual HTTP requests
    mock_pool = AsyncMock()
    mock_client = AsyncMock()
    
    # Mock request response
    mock_response = AsyncMock()
    
    # Set up the raw iterator
    async def mock_aiter_raw() -> AsyncIterable[bytes]:
        raw_data = [
            b"data: " + json.dumps({"id": 1, "value": "test1"}).encode('utf-8'),
            b"data: " + json.dumps({"id": 2, "value": "test2"}).encode('utf-8'),
            b"data: " + json.dumps({"id": 3, "value": "test3"}).encode('utf-8')
        ]
        for item in raw_data:
            yield item
    
    # Make aiter_raw return an async generator
    mock_response.aiter_raw = mock_aiter_raw
    
    # Set up the client.request method
    mock_client.request.return_value = mock_response
    mock_pool.get_connection.return_value = mock_client
    
    # Insert mock pool
    network_client.connection_pools["test-service"] = mock_pool
    
    # Mock connect to avoid actual connection
    with patch.object(network_client, "connect", AsyncMock()):
        # Call with params and resource_id
        result = await network_client.get_resource(
            service_name="test-service",
            resource_name="test-resource",
            params={"limit": 10},
            resource_id="123"
        )
    
    # Verify client was called correctly
    mock_client.request.assert_called_once_with(
        "GET",
        "/resource/test-resource/123?limit=10",
        timeout=60.0,  # Default timeout
        headers={"Accept": "text/event-stream"}
    )
    
    # Verify result - since there are multiple items, result should be a list
    assert isinstance(result, list)
    assert len(result) == 3
    assert result[0]["id"] == 1
    assert result[1]["id"] == 2
    assert result[2]["id"] == 3


@pytest.mark.asyncio
async def test_get_resource_not_found(network_client: NetworkMcpClient) -> None:
    """Test getting a resource that doesn't exist."""
    # Mock connection pool to avoid actual HTTP requests
    mock_pool = AsyncMock()
    mock_client = AsyncMock()
    
    # Create a mock error response
    http_error = httpx.HTTPStatusError(
        "Not Found", 
        request=MagicMock(), 
        response=MagicMock(status_code=404)
    )
    mock_client.request.side_effect = http_error
    mock_pool.get_connection.return_value = mock_client
    
    # Insert mock pool
    network_client.connection_pools["test-service"] = mock_pool
    
    # Mock connect to avoid actual connection
    with patch.object(network_client, "connect", AsyncMock()):
        with pytest.raises(ResourceNotFoundError):
            await network_client.get_resource("test-service", "nonexistent-resource")


@pytest.mark.asyncio
async def test_service_not_found(network_client: NetworkMcpClient, mock_service_discovery: AsyncMock) -> None:
    """Test handling of a service that doesn't exist."""
    # Make service discovery return None to simulate service not found
    mock_service_discovery.resolve.return_value = None
    
    with pytest.raises(ServiceNotFoundError):
        await network_client.call_tool("nonexistent-service", "test-tool", {"param": "value"})


@pytest.mark.asyncio
async def test_circuit_breaker_behavior() -> None:
    """Test the circuit breaker state transitions."""
    # Create circuit breaker with low threshold and recovery time
    breaker = CircuitBreaker(failure_threshold=2, recovery_time=0.1)
    
    # Initially closed
    assert breaker.state.value == "CLOSED"
    assert not breaker.is_open()
    
    # Record failures
    breaker.record_failure()
    assert breaker.state.value == "CLOSED"
    assert not breaker.is_open()
    
    breaker.record_failure()
    assert breaker.state.value == "OPEN"
    assert breaker.is_open()
    
    # Wait for recovery time
    await asyncio.sleep(0.2)
    
    # Should be half-open after recovery time
    assert not breaker.is_open()
    assert breaker.state.value == "HALF_OPEN"
    
    # Success in half-open state should close the circuit
    breaker.record_success()
    assert breaker.state.value == "CLOSED"
    assert not breaker.is_open()