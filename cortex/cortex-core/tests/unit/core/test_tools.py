"""
Unit tests for the tools module.
"""

import pytest
from app.core.exceptions import ToolExecutionException
from app.core.tools import execute_tool, get_registered_tools, register_tool


@pytest.mark.asyncio
async def test_register_tool():
    """Test registering a tool."""

    # Define a sample tool
    @register_tool("test_tool")
    async def sample_tool(param1: str, param2: int = 0):
        """Sample tool for testing."""
        return {"result": f"{param1}-{param2}"}

    # Check if the tool was registered
    tools = get_registered_tools()
    assert "test_tool" in tools

    # Check schema properties
    schema = tools["test_tool"]["schema"]
    assert schema["name"] == "test_tool"
    assert "description" in schema
    assert "parameters" in schema

    # Check required parameters
    params = schema["parameters"]["properties"]
    assert "param1" in params
    assert "param2" in params
    assert "param1" in schema["parameters"]["required"]
    assert "param2" not in schema["parameters"]["required"]


@pytest.mark.asyncio
async def test_register_tool_with_types():
    """Test registering a tool with various parameter types."""

    @register_tool("typed_tool")
    async def typed_tool(
        str_param: str,
        int_param: int,
        float_param: float,
        bool_param: bool,
        list_param: list,
        dict_param: dict,
    ):
        """Tool with various parameter types."""
        return {"result": "success"}

    # Check if the tool was registered
    tools = get_registered_tools()
    assert "typed_tool" in tools

    # Check schema properties for each type
    params = tools["typed_tool"]["schema"]["parameters"]["properties"]
    assert params["str_param"]["type"] == "string"
    assert params["int_param"]["type"] == "integer"
    assert params["float_param"]["type"] == "number"
    assert params["bool_param"]["type"] == "boolean"
    assert params["list_param"]["type"] == "array"
    assert params["dict_param"]["type"] == "object"


@pytest.mark.asyncio
async def test_execute_tool():
    """Test executing a registered tool."""

    # Register a test tool
    @register_tool("execute_test_tool")
    async def execute_test_tool(a: int, b: int, operation: str = "add"):
        """Test tool for execution."""
        if operation == "add":
            return {"result": a + b}
        elif operation == "multiply":
            return {"result": a * b}
        else:
            raise ValueError(f"Unsupported operation: {operation}")

    # Execute the tool with add operation
    result = await execute_tool("execute_test_tool", {"a": 5, "b": 3, "operation": "add"})
    assert result["result"] == 8

    # Execute the tool with multiply operation
    result = await execute_tool("execute_test_tool", {"a": 5, "b": 3, "operation": "multiply"})
    assert result["result"] == 15


@pytest.mark.asyncio
async def test_execute_nonexistent_tool():
    """Test executing a tool that doesn't exist."""
    with pytest.raises(ToolExecutionException) as exc_info:
        await execute_tool("nonexistent_tool", {"param": "value"})

    assert "Tool not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_execute_tool_missing_params():
    """Test executing a tool with missing required parameters."""

    # Register a test tool with required parameters
    @register_tool("required_params_tool")
    async def required_params_tool(required_param: str, optional_param: int = 0):
        """Tool with required and optional parameters."""
        return {"result": f"{required_param}-{optional_param}"}

    # Execute without the required parameter
    with pytest.raises(ToolExecutionException) as exc_info:
        await execute_tool("required_params_tool", {"optional_param": 42})

    assert "Missing required parameter" in str(exc_info.value)

    # Execute with only the required parameter
    result = await execute_tool("required_params_tool", {"required_param": "test"})
    assert result["result"] == "test-0"


@pytest.mark.asyncio
async def test_execute_tool_with_error():
    """Test executing a tool that raises an error."""

    # Register a test tool that raises an error
    @register_tool("error_tool")
    async def error_tool(trigger_error: bool = True):
        """Tool that raises an error if triggered."""
        if trigger_error:
            raise ValueError("Intentional error for testing")
        return {"result": "success"}

    # Execute with error
    with pytest.raises(ToolExecutionException) as exc_info:
        await execute_tool("error_tool", {"trigger_error": True})

    assert "Intentional error" in str(exc_info.value)

    # Execute without error
    result = await execute_tool("error_tool", {"trigger_error": False})
    assert result["result"] == "success"
