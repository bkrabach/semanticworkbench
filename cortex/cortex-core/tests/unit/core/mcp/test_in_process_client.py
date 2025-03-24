"""
Tests for the InProcessMCPClient implementation.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from app.core.mcp.exceptions import (
    MCPError, ServiceNotFoundError, ToolNotFoundError, 
    ResourceNotFoundError, ToolExecutionError, ResourceAccessError
)
from app.core.mcp.in_process_client import InProcessMCPClient


class MockServiceDefinition:
    """Mock for a service definition in the registry."""
    def __init__(self, service_instance):
        self.service_instance = service_instance


class MockToolDefinition:
    """Mock for a tool definition in the registry."""
    def __init__(self, func, schema=None):
        self.func = func
        self.schema = schema or {}


class MockResourceDefinition:
    """Mock for a resource definition in the registry."""
    def __init__(self, func, schema=None):
        self.func = func
        self.schema = schema or {}


@pytest.fixture
def mock_registry():
    """Create a mock registry for testing."""
    with patch('app.core.mcp.in_process_client.registry') as mock_reg:
        yield mock_reg


@pytest.fixture
def in_process_client():
    """Create an InProcessMCPClient instance for testing."""
    return InProcessMCPClient()


@pytest.mark.asyncio
async def test_call_tool_success(in_process_client, mock_registry):
    """Test calling a tool successfully."""
    # Create mock service and tool
    mock_service = Mock()
    mock_tool_func = AsyncMock(return_value={"result": "success"})
    
    # Set up the registry mocks
    mock_service_def = MockServiceDefinition(mock_service)
    mock_tool_def = MockToolDefinition(mock_tool_func)
    
    mock_registry.get_service.return_value = mock_service_def
    mock_registry.get_tool.return_value = mock_tool_def
    
    # Call the tool
    result = await in_process_client.call_tool(
        "test_service", "test_tool", {"param": "value"}
    )
    
    # Verify the result
    assert result == {"result": "success"}
    
    # Verify the correct calls were made
    mock_registry.get_service.assert_called_once_with("test_service")
    mock_registry.get_tool.assert_called_once_with("test_service", "test_tool")
    mock_tool_func.assert_called_once_with(mock_service, param="value")


@pytest.mark.asyncio
async def test_call_tool_service_not_found(in_process_client, mock_registry):
    """Test calling a tool on a service that doesn't exist."""
    # Make get_service raise ServiceNotFoundError
    mock_registry.get_service.side_effect = ServiceNotFoundError("nonexistent_service")
    
    # Call the tool on a nonexistent service
    with pytest.raises(ServiceNotFoundError) as exc_info:
        await in_process_client.call_tool(
            "nonexistent_service", "test_tool", {"param": "value"}
        )
    
    # Verify the error message
    assert "nonexistent_service" in str(exc_info.value)
    
    # Verify the correct calls were made
    mock_registry.get_service.assert_called_once_with("nonexistent_service")
    mock_registry.get_tool.assert_not_called()


@pytest.mark.asyncio
async def test_call_tool_not_found(in_process_client, mock_registry):
    """Test calling a tool that doesn't exist."""
    # Create mock service
    mock_service = Mock()
    mock_service_def = MockServiceDefinition(mock_service)
    
    # Set up the registry mocks
    mock_registry.get_service.return_value = mock_service_def
    mock_registry.get_tool.side_effect = ToolNotFoundError("test_service", "nonexistent_tool")
    
    # Call a nonexistent tool
    with pytest.raises(ToolNotFoundError) as exc_info:
        await in_process_client.call_tool(
            "test_service", "nonexistent_tool", {"param": "value"}
        )
    
    # Verify the error message
    assert "nonexistent_tool" in str(exc_info.value)
    assert "test_service" in str(exc_info.value)
    
    # Verify the correct calls were made
    mock_registry.get_service.assert_called_once_with("test_service")
    mock_registry.get_tool.assert_called_once_with("test_service", "nonexistent_tool")


@pytest.mark.asyncio
async def test_call_tool_execution_error(in_process_client, mock_registry):
    """Test calling a tool that raises an exception during execution."""
    # Create mock service and tool
    mock_service = Mock()
    mock_tool_func = AsyncMock(side_effect=ValueError("Tool execution error"))
    
    # Set up the registry mocks
    mock_service_def = MockServiceDefinition(mock_service)
    mock_tool_def = MockToolDefinition(mock_tool_func)
    
    mock_registry.get_service.return_value = mock_service_def
    mock_registry.get_tool.return_value = mock_tool_def
    
    # Call the tool that raises an exception
    with pytest.raises(ToolExecutionError) as exc_info:
        await in_process_client.call_tool(
            "test_service", "error_tool", {"param": "value"}
        )
    
    # Verify the error message
    assert "test_service" in str(exc_info.value)
    assert "error_tool" in str(exc_info.value)
    assert "Tool execution error" in str(exc_info.value)
    
    # Verify the correct calls were made
    mock_registry.get_service.assert_called_once_with("test_service")
    mock_registry.get_tool.assert_called_once_with("test_service", "error_tool")
    mock_tool_func.assert_called_once_with(mock_service, param="value")


@pytest.mark.asyncio
async def test_call_tool_result_types(in_process_client, mock_registry):
    """Test calling a tool with different result types."""
    # Create mock service
    mock_service = Mock()
    mock_service_def = MockServiceDefinition(mock_service)
    mock_registry.get_service.return_value = mock_service_def
    
    # Test cases with different return values
    test_cases = [
        (None, {}),  # None should be converted to empty dict
        ({"key": "value"}, {"key": "value"}),  # Dict should be returned as is
        ("string result", {"result": "string result"}),  # Non-dict should be wrapped
        (123, {"result": 123})  # Numbers should be wrapped
    ]
    
    for input_result, expected_output in test_cases:
        # Create a new mock tool for each case
        mock_tool_func = AsyncMock(return_value=input_result)
        mock_tool_def = MockToolDefinition(mock_tool_func)
        mock_registry.get_tool.return_value = mock_tool_def
        
        # Call the tool
        result = await in_process_client.call_tool(
            "test_service", "test_tool", {}
        )
        
        # Verify the result matches expected output
        assert result == expected_output


@pytest.mark.asyncio
async def test_get_resource_success(in_process_client, mock_registry):
    """Test getting a resource successfully."""
    # Create mock service and resource
    mock_service = Mock()
    mock_resource_func = AsyncMock(return_value={"data": "resource_data"})
    
    # Set up the registry mocks
    mock_service_def = MockServiceDefinition(mock_service)
    mock_resource_def = MockResourceDefinition(mock_resource_func)
    
    mock_registry.get_service.return_value = mock_service_def
    mock_registry.get_resource.return_value = mock_resource_def
    
    # Get the resource
    result = await in_process_client.get_resource(
        "test_service", "test_resource", {"param": "value"}
    )
    
    # Verify the result
    assert result == {"data": "resource_data"}
    
    # Verify the correct calls were made
    mock_registry.get_service.assert_called_once_with("test_service")
    mock_registry.get_resource.assert_called_once_with("test_service", "test_resource")
    mock_resource_func.assert_called_once_with(mock_service, param="value")


@pytest.mark.asyncio
async def test_get_resource_service_not_found(in_process_client, mock_registry):
    """Test getting a resource from a service that doesn't exist."""
    # Make get_service raise ServiceNotFoundError
    mock_registry.get_service.side_effect = ServiceNotFoundError("nonexistent_service")
    
    # Get a resource from a nonexistent service
    with pytest.raises(ServiceNotFoundError) as exc_info:
        await in_process_client.get_resource(
            "nonexistent_service", "test_resource", {"param": "value"}
        )
    
    # Verify the error message
    assert "nonexistent_service" in str(exc_info.value)
    
    # Verify the correct calls were made
    mock_registry.get_service.assert_called_once_with("nonexistent_service")
    mock_registry.get_resource.assert_not_called()


@pytest.mark.asyncio
async def test_get_resource_not_found(in_process_client, mock_registry):
    """Test getting a resource that doesn't exist."""
    # Create mock service
    mock_service = Mock()
    mock_service_def = MockServiceDefinition(mock_service)
    
    # Set up the registry mocks
    mock_registry.get_service.return_value = mock_service_def
    mock_registry.get_resource.side_effect = ResourceNotFoundError("test_service", "nonexistent_resource")
    
    # Get a nonexistent resource
    with pytest.raises(ResourceNotFoundError) as exc_info:
        await in_process_client.get_resource(
            "test_service", "nonexistent_resource", {"param": "value"}
        )
    
    # Verify the error message
    assert "nonexistent_resource" in str(exc_info.value)
    assert "test_service" in str(exc_info.value)
    
    # Verify the correct calls were made
    mock_registry.get_service.assert_called_once_with("test_service")
    mock_registry.get_resource.assert_called_once_with("test_service", "nonexistent_resource")


@pytest.mark.asyncio
async def test_get_resource_access_error(in_process_client, mock_registry):
    """Test getting a resource that raises an exception during access."""
    # Create mock service and resource
    mock_service = Mock()
    mock_resource_func = AsyncMock(side_effect=ValueError("Resource access error"))
    
    # Set up the registry mocks
    mock_service_def = MockServiceDefinition(mock_service)
    mock_resource_def = MockResourceDefinition(mock_resource_func)
    
    mock_registry.get_service.return_value = mock_service_def
    mock_registry.get_resource.return_value = mock_resource_def
    
    # Get the resource that raises an exception
    with pytest.raises(ResourceAccessError) as exc_info:
        await in_process_client.get_resource(
            "test_service", "error_resource", {"param": "value"}
        )
    
    # Verify the error message
    assert "test_service" in str(exc_info.value)
    assert "error_resource" in str(exc_info.value)
    assert "Resource access error" in str(exc_info.value)
    
    # Verify the correct calls were made
    mock_registry.get_service.assert_called_once_with("test_service")
    mock_registry.get_resource.assert_called_once_with("test_service", "error_resource")
    mock_resource_func.assert_called_once_with(mock_service, param="value")


@pytest.mark.asyncio
async def test_get_resource_result_types(in_process_client, mock_registry):
    """Test getting a resource with different result types."""
    # Create mock service
    mock_service = Mock()
    mock_service_def = MockServiceDefinition(mock_service)
    mock_registry.get_service.return_value = mock_service_def
    
    # Test cases with different return values
    test_cases = [
        (None, {}),  # None should be converted to empty dict
        ({"key": "value"}, {"key": "value"}),  # Dict should be returned as is
        ([{"item": 1}, {"item": 2}], [{"item": 1}, {"item": 2}]),  # List should be returned as is
        ("string result", {"result": "string result"}),  # Non-dict should be wrapped
        (123, {"result": 123})  # Numbers should be wrapped
    ]
    
    for input_result, expected_output in test_cases:
        # Create a new mock resource for each case
        mock_resource_func = AsyncMock(return_value=input_result)
        mock_resource_def = MockResourceDefinition(mock_resource_func)
        mock_registry.get_resource.return_value = mock_resource_def
        
        # Get the resource
        result = await in_process_client.get_resource(
            "test_service", "test_resource", {}
        )
        
        # Verify the result matches expected output
        assert result == expected_output


@pytest.mark.asyncio
async def test_get_service_parameter_precedence(in_process_client, mock_registry):
    """Test that service parameter takes precedence over service_name."""
    # Create mock service and resource
    mock_service = Mock()
    mock_resource_func = AsyncMock(return_value={"data": "resource_data"})
    
    # Set up the registry mocks
    mock_service_def = MockServiceDefinition(mock_service)
    mock_resource_def = MockResourceDefinition(mock_resource_func)
    
    mock_registry.get_service.return_value = mock_service_def
    mock_registry.get_resource.return_value = mock_resource_def
    
    # Get a resource with both service_name and service parameters
    await in_process_client.get_resource(
        service_name="ignored_service",
        resource_name="test_resource",
        params={"param": "value"},
        service="effective_service"  # This should take precedence
    )
    
    # Verify the correct service name was used
    mock_registry.get_service.assert_called_once_with("effective_service")
    mock_registry.get_resource.assert_called_once_with("effective_service", "test_resource")


@pytest.mark.asyncio
async def test_get_tool_schema(in_process_client, mock_registry):
    """Test getting a tool schema."""
    # Create a mock tool definition with schema
    tool_schema = {
        "type": "object",
        "properties": {
            "param1": {"type": "string"},
            "param2": {"type": "integer"}
        }
    }
    mock_tool_def = MockToolDefinition(AsyncMock(), tool_schema)
    
    # Set up the registry mocks
    mock_registry.get_tool.return_value = mock_tool_def
    
    # Get the tool schema
    result = in_process_client.get_tool_schema("test_service", "test_tool")
    
    # Verify the result matches the schema
    assert result == tool_schema
    
    # Verify the correct call was made
    mock_registry.get_tool.assert_called_once_with("test_service", "test_tool")


@pytest.mark.asyncio
async def test_get_resource_schema(in_process_client, mock_registry):
    """Test getting a resource schema."""
    # Create a mock resource definition with schema
    resource_schema = {
        "type": "object",
        "properties": {
            "param1": {"type": "string"},
            "param2": {"type": "integer"}
        }
    }
    mock_resource_def = MockResourceDefinition(AsyncMock(), resource_schema)
    
    # Set up the registry mocks
    mock_registry.get_resource.return_value = mock_resource_def
    
    # Get the resource schema
    result = in_process_client.get_resource_schema("test_service", "test_resource")
    
    # Verify the result matches the schema
    assert result == resource_schema
    
    # Verify the correct call was made
    mock_registry.get_resource.assert_called_once_with("test_service", "test_resource")


@pytest.mark.asyncio
async def test_list_services(in_process_client, mock_registry):
    """Test listing available services."""
    # Set up the registry mock
    mock_registry.list_services.return_value = ["service1", "service2", "service3"]
    
    # List the services
    result = in_process_client.list_services()
    
    # Verify the result
    assert result == ["service1", "service2", "service3"]
    
    # Verify the correct call was made
    mock_registry.list_services.assert_called_once()


@pytest.mark.asyncio
async def test_list_tools(in_process_client, mock_registry):
    """Test listing tools for a service."""
    # Set up the registry mock
    mock_registry.list_tools.return_value = ["tool1", "tool2", "tool3"]
    
    # List the tools
    result = in_process_client.list_tools("test_service")
    
    # Verify the result
    assert result == ["tool1", "tool2", "tool3"]
    
    # Verify the correct call was made
    mock_registry.list_tools.assert_called_once_with("test_service")


@pytest.mark.asyncio
async def test_list_resources(in_process_client, mock_registry):
    """Test listing resources for a service."""
    # Set up the registry mock
    mock_registry.list_resources.return_value = ["resource1", "resource2", "resource3"]
    
    # List the resources
    result = in_process_client.list_resources("test_service")
    
    # Verify the result
    assert result == ["resource1", "resource2", "resource3"]
    
    # Verify the correct call was made
    mock_registry.list_resources.assert_called_once_with("test_service")