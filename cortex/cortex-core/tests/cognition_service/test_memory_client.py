"""
Tests for the Memory Client in the Cognition Service.
"""
import pytest
import unittest.mock as mock
from unittest.mock import AsyncMock, MagicMock, patch, Mock

from cognition_service.memory_client import MemoryClient, MemoryServiceError
from cognition_service.models import Message, MessageRole


class MockContextManager:
    """Mock for a context manager that returns streams."""
    
    def __init__(self, read_stream=None, write_stream=None):
        self.read_stream = read_stream or AsyncMock()
        self.write_stream = write_stream or AsyncMock()
    
    async def __aenter__(self):
        return self.read_stream, self.write_stream
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class MockClientSession:
    """Mock for the MCP client session."""
    
    def __init__(self, read_stream=None, write_stream=None):
        self.read_stream = read_stream
        self.write_stream = write_stream
        self.initialize = AsyncMock()
        self.call_tool = AsyncMock()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture
def mock_sse_client():
    """Fixture for mocking the SSE client."""
    with patch("cognition_service.memory_client.sse_client") as mock_sse:
        # Set up the mock to return a context manager
        mock_sse.return_value = MockContextManager()
        yield mock_sse


@pytest.fixture
def mock_client_session():
    """Fixture for mocking the ClientSession."""
    with patch("cognition_service.memory_client.ClientSession") as mock_session_class:
        # Create a mock session instance
        mock_session = MockClientSession()
        # Make the class constructor return this instance
        mock_session_class.return_value = mock_session
        # Also make __aenter__ return this instance
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        yield mock_session


@pytest.mark.asyncio
async def test_memory_client_init():
    """Test the initialization of the MemoryClient."""
    service_url = "http://localhost:5001/sse"
    client = MemoryClient(service_url)
    
    assert client.service_url == service_url
    assert client.session is None
    assert client.streams_context is None


@pytest.mark.asyncio
async def test_memory_client_connect_success(mock_sse_client, mock_client_session):
    """Test successful connection to the memory service."""
    # Create a memory client
    client = MemoryClient("http://localhost:5001/sse")
    
    # Call connect
    result = await client.connect()
    
    # Verify
    assert result is True
    assert client.session is not None
    assert client.streams_context is not None
    
    # Verify initialize was called
    mock_client_session.initialize.assert_called_once()


@pytest.mark.asyncio
async def test_memory_client_connect_already_connected(mock_sse_client, mock_client_session):
    """Test connecting when already connected."""
    # Create a memory client
    client = MemoryClient("http://localhost:5001/sse")
    
    # First connection
    await client.connect()
    
    # Clear the mocks to verify they aren't called again
    mock_sse_client.reset_mock()
    mock_client_session.initialize.reset_mock()
    
    # Call connect again
    result = await client.connect()
    
    # Verify
    assert result is True
    
    # Verify initialize was NOT called again
    mock_client_session.initialize.assert_not_called()
    mock_sse_client.assert_not_called()


@pytest.mark.asyncio
async def test_memory_client_connect_error(mock_sse_client):
    """Test handling connection errors."""
    # Make the SSE client raise an exception
    mock_sse_client.side_effect = Exception("Connection error")
    
    # Create a memory client
    client = MemoryClient("http://localhost:5001/sse")
    
    # Call connect
    result = await client.connect()
    
    # Verify
    assert result is False
    assert client.session is None
    assert client.streams_context is None


@pytest.mark.asyncio
async def test_memory_client_ensure_connected_already_connected(mock_sse_client, mock_client_session):
    """Test ensure_connected when already connected."""
    # Create a memory client and connect
    client = MemoryClient("http://localhost:5001/sse")
    await client.connect()
    
    # Clear mocks
    mock_sse_client.reset_mock()
    
    # Call ensure_connected
    await client.ensure_connected()
    
    # Verify no additional connection attempt was made
    mock_sse_client.assert_not_called()


@pytest.mark.asyncio
async def test_memory_client_ensure_connected_needs_connection(mock_sse_client, mock_client_session):
    """Test ensure_connected when not yet connected."""
    # Create a memory client without connecting
    client = MemoryClient("http://localhost:5001/sse")
    
    # Call ensure_connected
    await client.ensure_connected()
    
    # Verify connection was established
    mock_sse_client.assert_called_once()
    mock_client_session.initialize.assert_called_once()


@pytest.mark.asyncio
async def test_memory_client_ensure_connected_failure(mock_sse_client):
    """Test ensure_connected when connection fails."""
    # Make the SSE client raise an exception
    mock_sse_client.side_effect = Exception("Connection error")
    
    # Create a memory client
    client = MemoryClient("http://localhost:5001/sse")
    
    # Call ensure_connected
    with pytest.raises(MemoryServiceError) as exc_info:
        await client.ensure_connected()
    
    # Verify error message
    assert "Failed to connect" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_conversation_history_success(mock_sse_client, mock_client_session):
    """Test successfully retrieving conversation history."""
    # Prepare mock return data for call_tool
    mock_response = Mock()
    mock_response.model_extra = {
        "messages": [
            {"role": "user", "content": "Hello", "timestamp": "2023-01-01T12:00:00"},
            {"role": "assistant", "content": "Hi there!", "timestamp": "2023-01-01T12:01:00"}
        ]
    }
    mock_client_session.call_tool.return_value = mock_response
    
    # Create and connect client
    client = MemoryClient("http://localhost:5001/sse")
    client.session = mock_client_session
    
    # Call get_conversation_history
    result = await client.get_conversation_history("test-convo-123")
    
    # Verify the call
    mock_client_session.call_tool.assert_called_once_with(
        "get_conversation_history", 
        {"conversation_id": "test-convo-123"}
    )
    
    # Verify the result
    assert isinstance(result, list)
    assert len(result) == 2
    assert all(isinstance(msg, Message) for msg in result)
    assert result[0].role == MessageRole.USER
    assert result[0].content == "Hello"
    assert result[1].role == MessageRole.ASSISTANT
    assert result[1].content == "Hi there!"


@pytest.mark.asyncio
async def test_get_conversation_history_empty_response(mock_client_session):
    """Test handling empty response from memory service."""
    # Set up mock to return None/empty
    mock_client_session.call_tool.return_value = None
    
    # Create and connect client
    client = MemoryClient("http://localhost:5001/sse")
    client.session = mock_client_session
    
    # Call get_conversation_history
    result = await client.get_conversation_history("test-convo-123")
    
    # Verify the result is an empty list
    assert isinstance(result, list)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_get_conversation_history_parse_error(mock_client_session):
    """Test handling message parsing errors."""
    # Prepare mock return data with invalid message
    mock_response = Mock()
    mock_response.model_extra = {
        "messages": [
            {"role": "invalid_role", "content": "This will cause an error"},  # Invalid role
            {"role": "user", "content": "This is valid"}  # Valid message
        ]
    }
    mock_client_session.call_tool.return_value = mock_response
    
    # Create and connect client
    client = MemoryClient("http://localhost:5001/sse")
    client.session = mock_client_session
    
    # Call get_conversation_history
    result = await client.get_conversation_history("test-convo-123")
    
    # Verify only the valid message was included
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].role == MessageRole.USER
    assert result[0].content == "This is valid"


@pytest.mark.asyncio
async def test_get_conversation_history_error(mock_client_session):
    """Test handling complete failure in get_conversation_history."""
    # Make call_tool raise an exception
    mock_client_session.call_tool.side_effect = Exception("Tool call failed")
    
    # Create and connect client
    client = MemoryClient("http://localhost:5001/sse")
    client.session = mock_client_session
    
    # Call get_conversation_history
    with pytest.raises(MemoryServiceError) as exc_info:
        await client.get_conversation_history("test-convo-123")
    
    # Verify error message
    assert "Error retrieving conversation history" in str(exc_info.value)


@pytest.mark.asyncio
async def test_close_success(mock_client_session):
    """Test successfully closing the client connection."""
    # Create a context for the streams
    streams_context = MockContextManager()
    
    # Create client and set up as connected
    client = MemoryClient("http://localhost:5001/sse")
    client.session = mock_client_session
    client.streams_context = streams_context
    
    # Spy on the context manager's __aexit__
    spy_session_exit = AsyncMock()
    mock_client_session.__aexit__ = spy_session_exit
    
    spy_streams_exit = AsyncMock()
    streams_context.__aexit__ = spy_streams_exit
    
    # Call close
    await client.close()
    
    # Verify both context managers were exited
    spy_session_exit.assert_called_once()
    spy_streams_exit.assert_called_once()
    
    # Verify session and streams_context are reset
    assert client.session is None
    assert client.streams_context is None


@pytest.mark.asyncio
async def test_close_logs_errors():
    """Test that close logs errors when they occur during context exit."""
    # Create mocks with manual control
    mock_session = AsyncMock()
    mock_session.__aexit__.side_effect = Exception("Exit error")
    
    mock_streams = AsyncMock()
    mock_streams.__aexit__.side_effect = Exception("Streams exit error")
    
    # Create client and set up as connected
    client = MemoryClient("http://localhost:5001/sse")
    client.session = mock_session
    client.streams_context = mock_streams
    
    # Call close
    with mock.patch("cognition_service.memory_client.logger") as mock_logger:
        await client.close()
        
        # Verify errors were logged
        mock_logger.error.assert_any_call("Error closing memory service session: Exit error")
        mock_logger.error.assert_any_call("Error closing memory service streams: Streams exit error")
    
    # Verify both __aexit__ methods were called despite errors
    mock_session.__aexit__.assert_called_once()
    mock_streams.__aexit__.assert_called_once()