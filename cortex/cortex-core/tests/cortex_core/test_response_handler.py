"""Tests for the Response Handler component."""

from typing import Any, Protocol, TypeVar, cast
from unittest.mock import MagicMock, Mock, patch

import pytest
from app.backend.cognition_client import CognitionClient
from app.backend.memory_client import MemoryClient
from app.core.event_bus import EventBus
from app.core.llm_orchestrator import LLMOrchestrator
from app.core.response_handler import ResponseHandler


@pytest.mark.asyncio
async def test_response_handler_init():
    """Test initializing the response handler with dependencies."""
    # Create mocks
    mock_event_bus = MagicMock(spec=EventBus)
    mock_memory_client = MagicMock(spec=MemoryClient)
    mock_cognition_client = MagicMock(spec=CognitionClient)

    # Create handler
    handler = ResponseHandler(
        event_bus=mock_event_bus, memory_client=mock_memory_client, cognition_client=mock_cognition_client
    )

    # Verify handler has correct attributes
    assert handler.event_bus is mock_event_bus
    assert handler.memory_client is mock_memory_client
    assert handler.cognition_client is mock_cognition_client
    assert handler.running is False
    assert handler.llm_orchestrator is None


# Define a protocol for our async mock functions
T = TypeVar("T")


class AsyncMockFunction(Protocol):
    """Protocol for async mock functions with Mock attributes."""

    mock: Mock

    async def __call__(self, *args: Any, **kwargs: Any) -> Any: ...
    def assert_called(self) -> None: ...
    def assert_called_once(self) -> None: ...
    def assert_called_with(self, *args: Any, **kwargs: Any) -> None: ...
    def assert_called_once_with(self, *args: Any, **kwargs: Any) -> None: ...
    def reset_mock(self) -> None: ...


def async_mock() -> AsyncMockFunction:
    """Create an async mock function that works with type checking."""
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


@pytest.mark.asyncio
async def test_response_handler_start_stop():
    """Test starting and stopping the response handler."""
    # Create mocks
    mock_event_bus = MagicMock(spec=EventBus)

    # Create methods with our special async_mock to better support type checking
    stop_mock = async_mock()
    memory_close_mock = async_mock()
    cognition_close_mock = async_mock()

    # Create the clients with mocked methods
    mock_memory_client = MagicMock(spec=MemoryClient)
    mock_memory_client.close = memory_close_mock

    mock_cognition_client = MagicMock(spec=CognitionClient)
    mock_cognition_client.close = cognition_close_mock

    # Create orchestrator with mocked method
    mock_llm_orchestrator = MagicMock(spec=LLMOrchestrator)
    mock_llm_orchestrator.stop = stop_mock

    # Create handler
    handler = ResponseHandler(
        event_bus=mock_event_bus, memory_client=mock_memory_client, cognition_client=mock_cognition_client
    )

    # Mock create_llm_orchestrator function
    with patch("app.core.response_handler.create_llm_orchestrator", return_value=mock_llm_orchestrator):
        # Start the handler
        await handler.start()

        # Verify handler is running and llm_orchestrator was initialized
        assert handler.running is True
        assert handler.llm_orchestrator is mock_llm_orchestrator

        # Stop the handler
        await handler.stop()

        # Verify handler is stopped
        assert handler.running is False

        # Use the regular mock object inside our async_mock to check calls
        stop_mock.mock.assert_called_once()
        memory_close_mock.mock.assert_called_once()
        cognition_close_mock.mock.assert_called_once()


@pytest.mark.asyncio
async def test_create_response_handler():
    """Test the create_response_handler factory function."""
    # Mock dependencies
    mock_event_bus = MagicMock(spec=EventBus)
    mock_memory_client = MagicMock(spec=MemoryClient)
    mock_cognition_client = MagicMock(spec=CognitionClient)
    mock_response_handler = MagicMock(spec=ResponseHandler)

    # Create mock start method
    start_mock = async_mock()
    mock_response_handler.start = start_mock

    # Set up patches for factory function dependencies
    with (
        patch("app.core.response_handler.MemoryClient", return_value=mock_memory_client),
        patch("app.core.response_handler.CognitionClient", return_value=mock_cognition_client),
        patch("app.core.response_handler.ResponseHandler", return_value=mock_response_handler),
    ):
        # Call the factory function
        from app.core.response_handler import create_response_handler

        handler = await create_response_handler(
            event_bus=mock_event_bus, memory_url="http://test-memory", cognition_url="http://test-cognition"
        )

        # Verify mock response handler was returned
        assert handler is mock_response_handler

        # Check start method was called
        start_mock.mock.assert_called_once()
