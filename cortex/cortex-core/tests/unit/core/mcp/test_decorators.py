"""
Unit tests for MCP decorators.
"""

from pydantic import BaseModel
import pytest
from typing import Optional
import inspect

from app.core.mcp.decorators import tool, resource
from app.core.mcp.exceptions import ValidationError
from app.core.mcp.registry import ToolDefinition, ResourceDefinition


# Test models
class _TestToolInput(BaseModel):
    """Test input model for tools."""
    name: str
    value: int
    optional: Optional[str] = None


class _TestResourceParams(BaseModel):
    """Test params model for resources."""
    id: str
    limit: Optional[int] = 10


class _TestService:
    """Test service class for decorator tests."""
    
    @tool(description="Test tool")
    async def test_tool(self, name: str, value: int) -> dict:
        """Test tool docstring."""
        return {"name": name, "value": value}
    
    @tool(name="custom_tool", input_model=_TestToolInput)
    async def tool_with_model(self, name: str, value: int, optional: Optional[str] = None) -> dict:
        """Tool with input model."""
        return {"name": name, "value": value, "optional": optional}
    
    @resource(description="Test resource")
    async def test_resource(self, id: str, limit: Optional[int] = 10) -> dict:
        """Test resource docstring."""
        return {"id": id, "limit": limit}
    
    @resource(name="custom_resource", params_model=_TestResourceParams)
    async def resource_with_model(self, id: str, limit: Optional[int] = 10) -> dict:
        """Resource with params model."""
        return {"id": id, "limit": limit}


@pytest.fixture
def test_service() -> _TestService:
    """Create test service instance."""
    return _TestService()


def test_tool_decorator_metadata() -> None:
    """Test that tool decorator adds correct metadata."""
    # Access the wrapped method with metadata
    method = _TestService.test_tool
    
    # Check that the method has the tool definition attribute
    assert hasattr(method, '_mcp_tool')
    
    # Check tool definition
    tool_def = getattr(method, '_mcp_tool')
    assert isinstance(tool_def, ToolDefinition)
    assert tool_def.name == "test_tool"
    assert tool_def.description == "Test tool"
    assert tool_def.func is not None  # Just check it exists, not the exact function
    assert isinstance(tool_def.schema, dict)
    
    # Check schema properties
    assert "properties" in tool_def.schema
    assert "name" in tool_def.schema["properties"]
    assert "value" in tool_def.schema["properties"]
    
    # Check required fields
    assert "required" in tool_def.schema
    assert len(tool_def.schema["required"]) == 2  # name and value


def test_tool_with_custom_name() -> None:
    """Test tool decorator with custom name."""
    # Access the wrapped method with metadata
    method = _TestService.tool_with_model
    
    # Check that the method has the tool definition attribute
    assert hasattr(method, '_mcp_tool')
    
    # Check tool definition
    tool_def = getattr(method, '_mcp_tool')
    assert tool_def.name == "custom_tool"


def test_tool_with_input_model() -> None:
    """Test tool decorator with input model."""
    # Access the wrapped method with metadata
    method = _TestService.tool_with_model
    
    # Check that the method has the tool definition attribute
    assert hasattr(method, '_mcp_tool')
    
    # Check tool definition
    tool_def = getattr(method, '_mcp_tool')
    
    # Check schema - should come from Pydantic model
    assert "properties" in tool_def.schema
    assert "name" in tool_def.schema["properties"]
    assert "value" in tool_def.schema["properties"]
    assert "optional" in tool_def.schema["properties"]


def test_resource_decorator_metadata() -> None:
    """Test that resource decorator adds correct metadata."""
    # Access the wrapped method with metadata
    method = _TestService.test_resource
    
    # Check that the method has the resource definition attribute
    assert hasattr(method, '_mcp_resource')
    
    # Check resource definition
    resource_def = getattr(method, '_mcp_resource')
    assert isinstance(resource_def, ResourceDefinition)
    assert resource_def.name == "test_resource"
    assert resource_def.description == "Test resource"
    assert resource_def.func is not None  # Just check it exists, not the exact function
    assert isinstance(resource_def.schema, dict)
    
    # Check schema properties
    assert "properties" in resource_def.schema
    assert "id" in resource_def.schema["properties"]
    assert "limit" in resource_def.schema["properties"]
    
    # Check required fields
    assert "required" in resource_def.schema
    assert len(resource_def.schema["required"]) >= 1  # At least id is required


def test_resource_with_custom_name() -> None:
    """Test resource decorator with custom name."""
    # Access the wrapped method with metadata
    method = _TestService.resource_with_model
    
    # Check that the method has the resource definition attribute
    assert hasattr(method, '_mcp_resource')
    
    # Check resource definition
    resource_def = getattr(method, '_mcp_resource')
    assert resource_def.name == "custom_resource"


def test_resource_with_params_model() -> None:
    """Test resource decorator with params model."""
    # Access the wrapped method with metadata
    method = _TestService.resource_with_model
    
    # Check that the method has the resource definition attribute
    assert hasattr(method, '_mcp_resource')
    
    # Check resource definition
    resource_def = getattr(method, '_mcp_resource')
    
    # Check schema - should come from Pydantic model
    assert "properties" in resource_def.schema
    assert "id" in resource_def.schema["properties"]
    assert "limit" in resource_def.schema["properties"]


@pytest.mark.asyncio
async def test_tool_execution(test_service: _TestService) -> None:
    """Test tool execution with the decorator."""
    result = await test_service.test_tool(name="test", value=42)
    
    # Check that the method still works normally
    assert result == {"name": "test", "value": 42}


@pytest.mark.asyncio
async def test_tool_execution_with_model(test_service: _TestService) -> None:
    """Test tool execution with input model validation."""
    # Valid input
    result = await test_service.tool_with_model(name="test", value=42)
    assert result == {"name": "test", "value": 42, "optional": None}
    
    # With optional parameter
    result = await test_service.tool_with_model(name="test", value=42, optional="extra")
    assert result == {"name": "test", "value": 42, "optional": "extra"}
    
    # Invalid input (missing required parameter)
    with pytest.raises(ValidationError) as exc:
        await test_service.tool_with_model(name="test")  # type: ignore[call-arg]
    
    # Check that validation error occurred - don't check specific message
    assert "validation failed" in str(exc.value)
    
    # Invalid input (wrong type)
    with pytest.raises(ValidationError) as exc:
        await test_service.tool_with_model(name="test", value="not_an_int")  # type: ignore[arg-type]
    
    assert "validation failed" in str(exc.value)


@pytest.mark.asyncio
async def test_resource_execution(test_service: _TestService) -> None:
    """Test resource execution with the decorator."""
    result = await test_service.test_resource(id="test123")
    
    # Check that the method still works normally
    assert result == {"id": "test123", "limit": 10}
    
    # With custom limit
    result = await test_service.test_resource(id="test123", limit=20)
    assert result == {"id": "test123", "limit": 20}


@pytest.mark.asyncio
async def test_resource_execution_with_model(test_service: _TestService) -> None:
    """Test resource execution with params model validation."""
    # Valid params
    result = await test_service.resource_with_model(id="test123")
    assert result == {"id": "test123", "limit": 10}
    
    # With custom limit
    result = await test_service.resource_with_model(id="test123", limit=20)
    assert result == {"id": "test123", "limit": 20}
    
    # Invalid params (missing required parameter)
    with pytest.raises(ValidationError) as exc:
        await test_service.resource_with_model()  # type: ignore[call-arg]
    
    # Check that validation error occurred - don't check specific message
    assert "validation failed" in str(exc.value)
    
    # Invalid params (wrong type)
    with pytest.raises(ValidationError) as exc:
        await test_service.resource_with_model(id="test123", limit="not_an_int")  # type: ignore[arg-type]
    
    assert "validation failed" in str(exc.value)


def test_wrapping_preserves_metadata() -> None:
    """Test that decorator preserves function metadata."""
    # Original signatures should be preserved
    tool_sig = inspect.signature(_TestService.test_tool)
    assert "name" in tool_sig.parameters
    assert "value" in tool_sig.parameters
    
    resource_sig = inspect.signature(_TestService.test_resource)
    assert "id" in resource_sig.parameters
    assert "limit" in resource_sig.parameters
    
    # Docstrings should be preserved
    assert _TestService.test_tool.__doc__ == "Test tool docstring."
    assert _TestService.test_resource.__doc__ == "Test resource docstring."
    
    # Function name should be preserved
    assert _TestService.test_tool.__name__ == "test_tool"
    assert _TestService.test_resource.__name__ == "test_resource"