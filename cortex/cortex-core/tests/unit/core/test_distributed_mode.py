"""
Tests for distributed MCP architecture.

This module tests the distributed MCP architecture components, ensuring
that remote services can be discovered and used properly.
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.mcp.network_client import NetworkMcpClient, ConnectionPool, CircuitBreaker, CircuitState
from app.core.mcp.service_discovery import ServiceDiscovery
from app.core.mcp.factory import create_mcp_client, get_mcp_client


@pytest.mark.asyncio
async def test_service_discovery_initialization() -> None:
    """Test that service discovery initializes properly."""
    discovery = ServiceDiscovery()
    with patch.dict(os.environ, {
        "MEMORY_SERVICE_URL": "http://test-memory:9000",
        "COGNITION_SERVICE_URL": "http://test-cognition:9100"
    }):
        await discovery.initialize()
        
        # Check that services were loaded from environment
        assert discovery.services["memory"] == "http://test-memory:9000"
        assert discovery.services["cognition"] == "http://test-cognition:9100"
        
        # Check service resolution
        assert await discovery.resolve("memory") == "http://test-memory:9000"
        assert await discovery.resolve("cognition") == "http://test-cognition:9100"
        assert await discovery.resolve("nonexistent") is None


@pytest.mark.asyncio
async def test_service_discovery_registration() -> None:
    """Test registering a service with service discovery."""
    discovery = ServiceDiscovery()
    await discovery.register("test-service", "http://test-service:8888")
    
    # Check that service was registered
    assert "test-service" in discovery.services
    assert discovery.services["test-service"] == "http://test-service:8888"
    
    # Check service resolution
    assert await discovery.resolve("test-service") == "http://test-service:8888"


@pytest.mark.asyncio
async def test_connection_pool() -> None:
    """Test connection pool management."""
    pool = ConnectionPool("http://test-service:8080")
    
    # Initialize the pool
    await pool.initialize()
    
    # Check initial pool size
    assert len(pool.connections) == pool.min_size
    
    # Get a connection
    connection = await pool.get_connection()
    assert connection is not None
    
    # Check that the connection was removed from the pool
    assert len(pool.connections) == pool.min_size - 1
    
    # Release the connection
    pool.release_connection(connection)
    
    # Check that the connection was returned to the pool
    assert len(pool.connections) == pool.min_size
    
    # Close all connections
    await pool.close_all()
    
    # Check that all connections were closed
    assert len(pool.connections) == 0


def test_circuit_breaker() -> None:
    """Test circuit breaker logic."""
    breaker = CircuitBreaker(failure_threshold=3, recovery_time=1)
    
    # Initially circuit should be closed
    assert not breaker.is_open()
    
    # Record failures
    breaker.record_failure()
    breaker.record_failure()
    assert not breaker.is_open()  # Not enough failures yet
    
    # Record another failure to reach threshold
    breaker.record_failure()
    assert breaker.is_open()  # Circuit should now be open
    
    # Record success in open state doesn't change state
    breaker.record_success()
    assert breaker.is_open()
    
    # Simulate time passing - adjust based on actual implementation
    import time
    # Store the current time as last_failure_time, minus recovery_time + 1 second
    breaker.last_failure_time = time.time() - (breaker.recovery_time + 1)
    
    # Now the circuit should move to half-open when checked
    assert not breaker.is_open()  # Should change to half-open
    assert breaker.state == CircuitState.HALF_OPEN
    
    # Record success in half-open state
    breaker.record_success()
    assert not breaker.is_open()
    assert breaker.state == CircuitState.CLOSED
    assert breaker.failure_count == 0


@pytest.mark.asyncio
async def test_network_client_initialization() -> None:
    """Test NetworkMcpClient initialization."""
    discovery = MagicMock()
    discovery.resolve = AsyncMock(return_value="http://test-service:8080")
    
    client = NetworkMcpClient(discovery)
    
    # Check that client was initialized
    assert client.service_discovery == discovery
    
    # Connect to a service
    await client.connect("test-service")
    
    # Check that connection pool was created
    assert "test-service" in client.connection_pools
    assert "test-service" in client.circuit_breakers
    
    # Close client
    await client.close()
    
    # Check that everything was cleaned up
    assert len(client.connection_pools) == 0
    assert len(client.circuit_breakers) == 0


@pytest.mark.asyncio
async def test_factory_create_client() -> None:
    """Test MCP client factory."""
    # Test in-process client creation
    with patch('app.core.mcp.factory.InProcessMCPClient') as mock_in_process:
        mock_in_process.return_value = MagicMock()
        client = await create_mcp_client(distributed=False)
        assert mock_in_process.called
    
    # Test network client creation
    with patch('app.core.mcp.factory.NetworkMcpClient') as mock_network, \
         patch('app.core.mcp.factory.service_discovery') as mock_discovery:
        
        mock_network.return_value = MagicMock()
        mock_discovery.initialize = AsyncMock()
        
        client = await create_mcp_client(distributed=True)
        assert mock_network.called
        assert mock_discovery.initialize.called


@pytest.mark.asyncio
async def test_get_mcp_client() -> None:
    """Test global MCP client accessor."""
    # Reset global client
    from app.core.mcp.factory import mcp_client
    import app.core.mcp.factory
    app.core.mcp.factory.mcp_client = None
    
    # Test client creation
    with patch('app.core.mcp.factory.create_mcp_client') as mock_create:
        mock_create.return_value = "test-client"
        
        # First call should create a new client
        client = await get_mcp_client()
        assert mock_create.called
        assert client == "test-client"
        
        # Reset mock
        mock_create.reset_mock()
        
        # Second call should use cached client
        client = await get_mcp_client()
        assert not mock_create.called
        assert client == "test-client"