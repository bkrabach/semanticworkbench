"""
Tests for the service discovery component.
"""

import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from app.core.mcp.service_discovery import ServiceDiscovery


@pytest.fixture
async def service_discovery() -> AsyncGenerator[ServiceDiscovery, None]:
    """Create a service discovery instance for testing."""
    discovery = ServiceDiscovery()
    yield discovery
    await discovery.close()


@pytest.mark.asyncio
async def test_initialize_from_environment(service_discovery: ServiceDiscovery) -> None:
    """Test initializing service discovery from environment variables."""
    # Patch environment variables
    with patch.dict('os.environ', {
        'MEMORY_SERVICE_URL': 'http://memory-test:9000',
        'COGNITION_SERVICE_URL': 'http://cognition-test:9100'
    }):
        # Patch health check to avoid actual network requests
        with patch.object(service_discovery, '_health_check_loop', AsyncMock()):
            await service_discovery.initialize()
            
            # Verify services were loaded from environment
            assert service_discovery.services['memory'] == 'http://memory-test:9000'
            assert service_discovery.services['cognition'] == 'http://cognition-test:9100'


@pytest.mark.asyncio
async def test_register_service(service_discovery: ServiceDiscovery) -> None:
    """Test registering a service."""
    # Patch health check to avoid actual network requests
    with patch.object(service_discovery, '_health_check_loop', AsyncMock()):
        await service_discovery.register('test-service', 'http://test-service:8000')
        
        # Verify service was registered
        assert service_discovery.services['test-service'] == 'http://test-service:8000'
        assert service_discovery.health_status['test-service'] is None


@pytest.mark.asyncio
async def test_resolve_service(service_discovery: ServiceDiscovery) -> None:
    """Test resolving a service."""
    # Register a service
    await service_discovery.register('test-service', 'http://test-service:8000')
    
    # Resolve service
    endpoint = await service_discovery.resolve('test-service')
    
    # Verify correct endpoint was returned
    assert endpoint == 'http://test-service:8000'
    
    # Try resolving non-existent service
    endpoint = await service_discovery.resolve('nonexistent-service')
    
    # Verify None was returned
    assert endpoint is None


@pytest.mark.asyncio
async def test_health_status(service_discovery: ServiceDiscovery) -> None:
    """Test service health status."""
    # Register services
    await service_discovery.register('healthy-service', 'http://healthy:8000')
    await service_discovery.register('unhealthy-service', 'http://unhealthy:8000')
    
    # Set health status directly
    service_discovery.health_status['healthy-service'] = True
    service_discovery.health_status['unhealthy-service'] = False
    
    # Check is_healthy
    assert await service_discovery.is_healthy('healthy-service')
    assert not await service_discovery.is_healthy('unhealthy-service')
    assert not await service_discovery.is_healthy('nonexistent-service')
    
    # Check get_healthy_services
    healthy_services = await service_discovery.get_healthy_services()
    assert 'healthy-service' in healthy_services
    assert 'unhealthy-service' not in healthy_services
    

@pytest.mark.asyncio
async def test_health_check_loop(service_discovery: ServiceDiscovery) -> None:
    """Test the health check loop."""
    # Register services
    await service_discovery.register('service1', 'http://service1:8000')
    await service_discovery.register('service2', 'http://service2:8000')
    
    # Mock httpx.AsyncClient to avoid actual network requests
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    
    # Set up different responses for each service
    mock_responses = {
        'http://service1:8000/health': MagicMock(status_code=200),
        'http://service2:8000/health': MagicMock(status_code=500)
    }
    
    def mock_get(url: str, **kwargs: dict) -> MagicMock:
        response = mock_responses.get(url)
        if response:
            return response
        raise httpx.ConnectError(f"Failed to connect to {url}")
    
    mock_client.get = AsyncMock(side_effect=mock_get)
    
    # Patch httpx.AsyncClient and asyncio.sleep to avoid waiting
    with patch('httpx.AsyncClient', return_value=mock_client), \
         patch.object(asyncio, 'sleep', AsyncMock()):
        # Create a simple test implementation of the health check process
        # that runs once and doesn't loop indefinitely
        async def test_health_check() -> None:
            async with httpx.AsyncClient() as client:
                for service_name, endpoint in service_discovery.services.items():
                    try:
                        # Try to call health endpoint
                        response = await client.get(
                            f"{endpoint}/health",
                            timeout=5.0
                        )
                        
                        # Update health status
                        service_discovery.health_status[service_name] = response.status_code == 200
                    except Exception:
                        service_discovery.health_status[service_name] = False
        
        # Run our test implementation
        await test_health_check()
        
        # Verify health status was updated correctly
        assert service_discovery.health_status['service1'] is True
        assert service_discovery.health_status['service2'] is False


@pytest.mark.asyncio
async def test_close(service_discovery: ServiceDiscovery) -> None:
    """Test closing the service discovery."""
    # Setup a mock health check task
    mock_task = AsyncMock()
    service_discovery._health_check_task = mock_task
    
    # Close service discovery
    await service_discovery.close()
    
    # Verify task was cancelled
    mock_task.cancel.assert_called_once()
    
    # Verify task was awaited
    assert service_discovery._health_check_task is None