"""
Common test fixtures for Cortex Core tests.

This file provides pytest fixtures that can be used across all tests in the cortex_core module.
These fixtures include mock objects, sample data, and utilities for testing asynchronous code.

Example usage:
    ```python
    # In a test file:
    import pytest
    
    @pytest.mark.asyncio
    async def test_something(mock_event_bus, mock_memory_client):
        # Test using the fixtures
        assert mock_event_bus is not None
        await mock_memory_client.store_message()
    ```
"""
import asyncio
import pytest
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, TypeVar, cast
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from app.core.event_bus import EventBus
from app.core.response_handler import ResponseHandler
from app.backend.cognition_client import CognitionClient
from app.backend.memory_client import MemoryClient


class MessageRole(str, Enum):
    """Enum for message roles in tests."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class Message(BaseModel):
    """Test message model."""
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None


# Define a protocol for creating type-safe async mock functions
T = TypeVar("T")


class AsyncMockFunction(Protocol):
    """
    Protocol for async mock functions with Mock attributes.
    
    This enables creating async mock functions that maintain type checking
    while having all the Mock assertion methods.
    
    Example usage:
        ```python
        # Create an async mock
        my_mock = async_mock()
        
        # Call it as an async function
        await my_mock(arg1, arg2)
        
        # Use mock assertions
        my_mock.assert_called_once_with(arg1, arg2)
        ```
    """
    mock: Mock

    async def __call__(self, *args: Any, **kwargs: Any) -> Any: ...
    def assert_called(self) -> None: ...
    def assert_called_once(self) -> None: ...
    def assert_called_with(self, *args: Any, **kwargs: Any) -> None: ...
    def assert_called_once_with(self, *args: Any, **kwargs: Any) -> None: ...
    def reset_mock(self) -> None: ...


def async_mock() -> AsyncMockFunction:
    """
    Create an async mock function that works with type checking.
    
    Returns:
        An async function with all the Mock assertion methods.
        
    Example usage:
        ```python
        close_mock = async_mock()
        
        # Later in test
        await close_mock()
        close_mock.assert_called_once()
        ```
    """
    mock = Mock()

    async def async_mock_function(*args: Any, **kwargs: Any) -> Any:
        return mock(*args, **kwargs)

    # Copy attributes from the mock to the function
    async_mock_function.mock = mock  # type: ignore
    async_mock_function.assert_called = mock.assert_called  # type: ignore
    async_mock_function.assert_called_once = mock.assert_called_once  # type: ignore
    async_mock_function.assert_called_with = mock.assert_called_with  # type: ignore
    async_mock_function.assert_called_once_with = mock.assert_called_once_with  # type: ignore
    async_mock_function.call_count = mock.call_count  # type: ignore
    async_mock_function.reset_mock = mock.reset_mock  # type: ignore

    return cast(AsyncMockFunction, async_mock_function)


class MockPydanticAIResult:
    """
    Mock class to simulate Pydantic AI result structure.
    
    This class mimics the structure of results returned by Pydantic AI's agent.run()
    method for testing purposes.
    
    Args:
        data: The data that would be returned in the result's data attribute
        
    Example usage:
        ```python
        mock_agent.run.return_value = MockPydanticAIResult("Test response")
        ```
    """
    def __init__(self, data: Any):
        self.data = data
    
    def __await__(self):
        async def _coro():
            return self
        return _coro().__await__()


@pytest.fixture
def sample_messages() -> List[Message]:
    """
    Fixture to provide sample conversation messages.
    
    Returns:
        A list of Message objects that represent a typical conversation.
        
    Example usage:
        ```python
        def test_message_processing(sample_messages):
            # Use the sample messages
            assert len(sample_messages) == 4
            assert sample_messages[0].role == MessageRole.SYSTEM
        ```
    """
    return [
        Message(role=MessageRole.SYSTEM, content="You are a helpful assistant."),
        Message(role=MessageRole.USER, content="Hello, how are you?"),
        Message(role=MessageRole.ASSISTANT, content="I'm doing well, thank you for asking!"),
        Message(role=MessageRole.USER, content="What can you do?")
    ]


@pytest.fixture
def sample_conversation() -> Dict[str, Any]:
    """
    Fixture to provide a sample conversation dictionary.
    
    Returns:
        A dictionary with conversation data for testing.
        
    Example usage:
        ```python
        def test_conversation_access(sample_conversation):
            conversation_id = sample_conversation["id"]
            # Use the conversation ID in tests
        ```
    """
    return {
        "id": "test-conversation-id",
        "title": "Test Conversation",
        "workspace_id": "test-workspace-id",
        "metadata": {"user_id": "test-user-id"}
    }


@pytest.fixture
def mock_event_bus() -> EventBus:
    """
    Fixture to provide a mocked event bus.
    
    Returns:
        A mocked EventBus instance with AsyncMock for publish.
        
    Example usage:
        ```python
        @pytest.mark.asyncio
        async def test_event_publishing(mock_event_bus):
            await mock_event_bus.publish("event_type", {"data": "value"})
            mock_event_bus.publish.assert_called_once()
        ```
    """
    event_bus = MagicMock(spec=EventBus)
    event_bus.publish = AsyncMock()
    event_bus.subscribe = MagicMock(return_value=asyncio.Queue())
    event_bus.unsubscribe = MagicMock()
    return event_bus


@pytest.fixture
def mock_cognition_client() -> CognitionClient:
    """
    Fixture to provide a mocked cognition client.
    
    Returns:
        A mocked CognitionClient with AsyncMock methods.
        
    Example usage:
        ```python
        @pytest.mark.asyncio
        async def test_response_generation(mock_cognition_client):
            response = await mock_cognition_client.evaluate_context(
                "user-id", "conversation-id", "Hello"
            )
            assert response == "Mock context evaluation"
        ```
    """
    client = MagicMock(spec=CognitionClient)
    client.connect = AsyncMock(return_value=(True, None))
    client.ensure_connected = AsyncMock()
    client.generate_reply = AsyncMock(return_value="Mock AI response")
    client.evaluate_context = AsyncMock(return_value="Mock context evaluation")
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_memory_client() -> MemoryClient:
    """
    Fixture to provide a mocked memory client.
    
    Returns:
        A mocked MemoryClient with AsyncMock methods.
        
    Example usage:
        ```python
        @pytest.mark.asyncio
        async def test_memory_storage(mock_memory_client):
            await mock_memory_client.store_message(
                "user-id", "conversation-id", "Hello", "user"
            )
            mock_memory_client.store_message.assert_called_once()
        ```
    """
    client = MagicMock(spec=MemoryClient)
    client.connect = AsyncMock(return_value=(True, None))
    client.ensure_connected = AsyncMock()
    client.store_message = AsyncMock(return_value=True)
    client.get_recent_messages = AsyncMock(return_value=[{
        "role": "system",
        "content": "Memory summary: Mock memory content"
    }])
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_response_handler(
    mock_event_bus: EventBus, 
    mock_cognition_client: CognitionClient, 
    mock_memory_client: MemoryClient
) -> ResponseHandler:
    """
    Fixture to provide a mocked response handler with its dependencies.
    
    Args:
        mock_event_bus: The mocked event bus to use
        mock_cognition_client: The mocked cognition client to use
        mock_memory_client: The mocked memory client to use
        
    Returns:
        A mocked ResponseHandler with AsyncMock methods and mocked dependencies.
        
    Example usage:
        ```python
        @pytest.mark.asyncio
        async def test_response_handling(mock_response_handler):
            await mock_response_handler.handle_input_event({
                "user_id": "test-user",
                "conversation_id": "test-conversation",
                "content": "Hello"
            })
            mock_response_handler.handle_input_event.assert_called_once()
        ```
    """
    handler = MagicMock(spec=ResponseHandler)
    handler.event_bus = mock_event_bus
    handler.cognition_client = mock_cognition_client
    handler.memory_client = mock_memory_client
    handler.start = async_mock()
    handler.handle_input_event = async_mock()
    handler.process_events = async_mock()
    handler.stop = async_mock()
    handler.running = True
    handler.input_queue = asyncio.Queue()
    return handler


@pytest.fixture
def patched_app_with_mocks():
    """
    Create a context manager that patches the app with mocks.
    
    This is a factory fixture that returns another fixture which
    yields the patched app and mock objects.
    
    Returns:
        A fixture that yields a tuple of (app, mock_event_bus, mock_handler)
    
    Example usage:
        ```python
        @pytest.mark.asyncio
        async def test_app_with_mocks(patched_app_with_mocks):
            app, mock_event_bus, mock_handler = patched_app_with_mocks
            # Test app with mocked dependencies
        ```
    """
    
    @pytest.fixture
    async def _patched_app():
        with patch("app.core.event_bus.event_bus") as mock_event_bus, \
             patch("app.core.response_handler.create_response_handler") as mock_create_handler:
            
            from app.main import app

            # Setup mocks
            mock_event_bus.publish = AsyncMock()
            mock_event_bus.subscribe = MagicMock(return_value=asyncio.Queue())
            
            mock_handler = MagicMock()
            mock_handler.handle_input_event = AsyncMock()
            mock_handler.start = AsyncMock()
            mock_handler.stop = AsyncMock()
            
            mock_create_handler.return_value = mock_handler
            
            # Start the app in test mode
            async with app.router.lifespan_context(app):
                yield app, mock_event_bus, mock_handler
    
    return _patched_app


@pytest.fixture
def test_client():
    """
    Create a test client for the FastAPI app.
    
    This fixture sets up a TestClient for making requests to the FastAPI app
    in tests.
    
    Returns:
        A TestClient instance.
        
    Example usage:
        ```python
        def test_root_endpoint(test_client):
            response = test_client.get("/")
            assert response.status_code == 200
        ```
    """
    from app.main import app
    with TestClient(app) as client:
        yield client