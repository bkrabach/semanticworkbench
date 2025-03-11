"""
Test suite for the Integration Hub component
"""

from pydantic import AnyUrl
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from app.components.integration_hub import (
    IntegrationHub,
    CortexMcpClient,
    get_integration_hub
)


class TestCortexMcpClient:
    """Test suite for the CortexMcpClient class"""

    @pytest.fixture
    def mock_mcp_client(self):
        """Create a mock for the MCP client"""
        mock_client = AsyncMock()
        mock_client.initialize = AsyncMock()
        mock_client.tools_list = AsyncMock(return_value={"tools": []})
        mock_client.tools_call = AsyncMock(return_value={"result": "success"})
        mock_client.resources_read = AsyncMock(return_value={"content": "test"})
        mock_client.shutdown = AsyncMock()
        return mock_client

    @pytest.mark.asyncio
    async def test_connect(self, mock_mcp_client):
        """Test connection initialization"""
        # Use individual import patches instead of attribute paths
        with patch("app.components.integration_hub.sse_client"), \
             patch("app.components.integration_hub.ClientSession", return_value=mock_mcp_client), \
             patch("asyncio.create_task"):
            client = CortexMcpClient(endpoint="http://test.endpoint", service_name="test-service")

            # Initially client should be None
            assert client.client is None

            # Connect should initialize the client
            await client.connect()

            # Verify McpClient was initialized
            assert client.client is mock_mcp_client
            mock_mcp_client.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_tools(self, mock_mcp_client):
        """Test listing tools"""
        # Create a return value with model_dump
        tools_result = MagicMock()
        tools_result.model_dump = lambda: {"tools": []}

        # Set up the mock to return our expected value
        mock_mcp_client.list_tools = AsyncMock(return_value=tools_result)

        # Set up the test
        client = CortexMcpClient(endpoint="http://test.endpoint", service_name="test-service")
        client.client = mock_mcp_client  # Directly set the client

        # Call list_tools
        result = await client.list_tools()

        # Verify the method was called
        mock_mcp_client.list_tools.assert_called_once()

        # Verify the result
        assert result == {"tools": []}

    @pytest.mark.asyncio
    async def test_call_tool(self, mock_mcp_client):
        """Test calling a tool"""
        # Create a return value with model_dump
        call_result = MagicMock()
        call_result.model_dump = lambda: {"result": "success"}

        # Set up the mock to return our expected value
        mock_mcp_client.call_tool = AsyncMock(return_value=call_result)

        # Set up the test
        client = CortexMcpClient(endpoint="http://test.endpoint", service_name="test-service")
        client.client = mock_mcp_client  # Directly set the client

        # Call the tool
        result = await client.call_tool(name="test-tool", arguments={"arg1": "value1"})

        # Verify the method was called with correct arguments
        mock_mcp_client.call_tool.assert_called_once_with(name="test-tool", arguments={"arg1": "value1"})

        # Verify the result
        assert result == {"result": "success"}

    @pytest.mark.asyncio
    async def test_read_resource(self, mock_mcp_client):
        """Test reading a resource"""
        # Create a return value with model_dump
        resource_result = MagicMock()
        resource_result.model_dump = lambda: {"content": "test"}

        # Set up the mock to return our expected value
        mock_mcp_client.read_resource = AsyncMock(return_value=resource_result)

        # Set up the test
        client = CortexMcpClient(endpoint="http://test.endpoint", service_name="test-service")
        client.client = mock_mcp_client  # Directly set the client

        # Read a resource
        result = await client.read_resource(uri=AnyUrl("test-uri"))

        # Verify the method was called with correct arguments
        mock_mcp_client.read_resource.assert_called_once_with(uri="test-uri")

        # Verify the result
        assert result == {"content": "test"}

    @pytest.mark.asyncio
    async def test_close(self, mock_mcp_client):
        """Test closing the connection"""
        with patch("app.components.integration_hub.sse_client"), \
             patch("app.components.integration_hub.ClientSession", return_value=mock_mcp_client), \
             patch("asyncio.create_task"):
            client = CortexMcpClient(endpoint="http://test.endpoint", service_name="test-service")

            # Set the client directly
            client.client = mock_mcp_client

            # Then close
            await client.close()

            # Verify client is set back to None
            assert client.client is None

    @pytest.mark.asyncio
    async def test_connect_error_handling(self):
        """Test error handling during connection"""
        with patch("app.components.integration_hub.ClientSession") as mock_client_class, \
             patch("asyncio.create_task"):
            # Make the initialize method raise an exception
            mock_client = AsyncMock()
            mock_client.initialize.side_effect = Exception("Connection failed")
            mock_client_class.return_value = mock_client

            client = CortexMcpClient(endpoint="http://test.endpoint", service_name="test-service")

            # Connect should raise the exception
            with pytest.raises(Exception, match="Connection failed"):
                await client.connect()


class TestIntegrationHub:
    """Test suite for the IntegrationHub class"""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings with test MCP endpoints"""
        mock_settings = MagicMock()
        mock_settings.mcp.endpoints = [
            {"name": "test-expert", "endpoint": "http://test.endpoint", "type": "expert"},
            {"name": "code-assistant", "endpoint": "http://code.endpoint", "type": "code"}
        ]
        return mock_settings

    @pytest.fixture
    def mock_client(self):
        """Create a mock for the CortexMcpClient"""
        mock = AsyncMock()
        mock.connect = AsyncMock()
        mock.list_tools = AsyncMock(return_value={"tools": [{"name": "test-tool"}]})
        mock.call_tool = AsyncMock(return_value={"result": "success"})
        mock.read_resource = AsyncMock(return_value={"content": "test"})
        mock.close = AsyncMock()
        return mock

    @pytest.mark.asyncio
    async def test_startup(self, mock_settings, mock_client):
        """Test startup initializes connections to all endpoints"""
        with patch("app.components.integration_hub.settings", mock_settings), \
             patch("app.components.integration_hub.CortexMcpClient", return_value=mock_client):

            hub = IntegrationHub()
            await hub.startup()

            # Verify clients were created for both endpoints
            assert len(hub.clients) == 2
            assert "test-expert" in hub.clients
            assert "code-assistant" in hub.clients

            # Verify circuit breakers were created
            assert len(hub.circuit_breakers) == 2
            assert "test-expert" in hub.circuit_breakers
            assert "code-assistant" in hub.circuit_breakers

            # Verify connect was called for both clients
            assert mock_client.connect.call_count == 2

    @pytest.mark.asyncio
    async def test_shutdown(self, mock_settings, mock_client):
        """Test shutdown closes all connections"""
        with patch("app.components.integration_hub.settings", mock_settings), \
             patch("app.components.integration_hub.CortexMcpClient", return_value=mock_client):

            hub = IntegrationHub()

            # Add clients manually
            hub.clients = {
                "test-expert": mock_client,
                "code-assistant": mock_client
            }

            await hub.shutdown()

            # Verify close was called for both clients
            assert mock_client.close.call_count == 2

    @pytest.mark.asyncio
    async def test_list_experts(self, mock_settings):
        """Test listing available experts"""
        with patch("app.components.integration_hub.settings", mock_settings):
            hub = IntegrationHub()

            # Add clients manually
            hub.clients = {
                "test-expert": MagicMock(),
                "code-assistant": MagicMock()
            }

            experts = await hub.list_experts()

            # Verify the expected list of experts
            assert set(experts) == {"test-expert", "code-assistant"}

    @pytest.mark.asyncio
    async def test_list_expert_tools(self, mock_settings, mock_client):
        """Test listing tools for a specific expert"""
        with patch("app.components.integration_hub.settings", mock_settings):
            hub = IntegrationHub()

            # Add clients manually
            hub.clients = {
                "test-expert": mock_client
            }

            # Add circuit breakers manually
            hub.circuit_breakers = {
                "test-expert": MagicMock()
            }

            # Make circuit breaker execute the function directly
            hub.circuit_breakers["test-expert"].execute = AsyncMock(side_effect=lambda func, *args, **kwargs: func())

            tools = await hub.list_expert_tools("test-expert")

            # Verify list_tools was called
            mock_client.list_tools.assert_called_once()

            # Await the coroutine result
            if asyncio.iscoroutine(tools):
                tools = await tools

            # Verify the expected result
            assert tools == {"tools": [{"name": "test-tool"}]}

    @pytest.mark.asyncio
    async def test_list_expert_tools_unknown_expert(self, mock_settings):
        """Test listing tools for an unknown expert"""
        with patch("app.components.integration_hub.settings", mock_settings):
            hub = IntegrationHub()

            # Add clients manually
            hub.clients = {
                "test-expert": MagicMock()
            }

            # This should raise ValueError
            with pytest.raises(ValueError, match="Unknown domain expert: unknown-expert"):
                await hub.list_expert_tools("unknown-expert")

    @pytest.mark.asyncio
    async def test_invoke_expert_tool(self, mock_settings, mock_client):
        """Test invoking a tool on a specific expert"""
        with patch("app.components.integration_hub.settings", mock_settings):
            hub = IntegrationHub()

            # Add clients manually
            hub.clients = {
                "test-expert": mock_client
            }

            # Add circuit breakers manually
            hub.circuit_breakers = {
                "test-expert": MagicMock()
            }

            # Make circuit breaker execute the function directly
            hub.circuit_breakers["test-expert"].execute = AsyncMock(
                side_effect=lambda func, *args, **kwargs: func(*args, **kwargs)
            )

            result = await hub.invoke_expert_tool(
                expert_name="test-expert",
                tool_name="test-tool",
                arguments={"arg1": "value1"}
            )

            # Verify call_tool was called with correct arguments
            mock_client.call_tool.assert_called_once_with(name="test-tool", arguments={"arg1": "value1"})

            # Await the coroutine result
            if asyncio.iscoroutine(result):
                result = await result

            # Verify the expected result
            assert result == {"result": "success"}

    @pytest.mark.asyncio
    async def test_read_expert_resource(self, mock_settings, mock_client):
        """Test reading a resource from a specific expert"""
        with patch("app.components.integration_hub.settings", mock_settings):
            hub = IntegrationHub()

            # Add clients manually
            hub.clients = {
                "test-expert": mock_client
            }

            # Add circuit breakers manually
            hub.circuit_breakers = {
                "test-expert": MagicMock()
            }

            # Make circuit breaker execute the function directly
            hub.circuit_breakers["test-expert"].execute = AsyncMock(
                side_effect=lambda func, *args, **kwargs: func(*args, **kwargs)
            )

            result = await hub.read_expert_resource(
                expert_name="test-expert",
                uri="test-uri"
            )

            # Verify read_resource was called with correct arguments
            mock_client.read_resource.assert_called_once_with(uri="test-uri")

            # Await the coroutine result
            if asyncio.iscoroutine(result):
                result = await result

            # Verify the expected result
            assert result == {"content": "test"}


def test_get_integration_hub():
    """Test the singleton getter function"""
    # First call should create a new instance
    hub1 = get_integration_hub()
    assert isinstance(hub1, IntegrationHub)

    # Second call should return the same instance
    hub2 = get_integration_hub()
    assert hub2 is hub1