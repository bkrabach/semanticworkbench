"""
Common test fixtures for Cortex Core tests.
"""
import pytest
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

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


class MockPydanticAIResult:
    """Mock class to simulate Pydantic AI result structure."""
    def __init__(self, data: Any):
        self.data = data
    
    def __await__(self):
        async def _coro():
            return self
        return _coro().__await__()


@pytest.fixture
def sample_messages() -> List[Message]:
    """Fixture to provide sample conversation messages."""
    return [
        Message(role=MessageRole.SYSTEM, content="You are a helpful assistant."),
        Message(role=MessageRole.USER, content="Hello, how are you?"),
        Message(role=MessageRole.ASSISTANT, content="I'm doing well, thank you for asking!"),
        Message(role=MessageRole.USER, content="What can you do?")
    ]


@pytest.fixture
def sample_conversation() -> Dict[str, Any]:
    """Fixture to provide a sample conversation dictionary."""
    return {
        "id": "test-conversation-id",
        "title": "Test Conversation",
        "workspace_id": "test-workspace-id",
        "metadata": {"user_id": "test-user-id"}
    }


@pytest.fixture
def mock_event_bus() -> EventBus:
    """Fixture to provide a mocked event bus."""
    event_bus = MagicMock(spec=EventBus)
    event_bus.publish = AsyncMock()
    event_bus.subscribe = MagicMock()
    event_bus.unsubscribe = MagicMock()
    return event_bus


@pytest.fixture
def mock_cognition_client() -> CognitionClient:
    """Fixture to provide a mocked cognition client."""
    client = MagicMock(spec=CognitionClient)
    client.connect = AsyncMock(return_value=True)
    client.generate_reply = AsyncMock(return_value="Mock AI response")
    client.evaluate_context = AsyncMock(return_value="Mock context evaluation")
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_memory_client() -> MemoryClient:
    """Fixture to provide a mocked memory client."""
    client = MagicMock(spec=MemoryClient)
    client.connect = AsyncMock(return_value=True)
    client.get_memory = AsyncMock(return_value={"content": "Mock memory content"})
    client.update_memory = AsyncMock(return_value=True)
    client.delete_memory = AsyncMock(return_value=True)
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_response_handler(
    mock_event_bus: EventBus, 
    mock_cognition_client: CognitionClient, 
    mock_memory_client: MemoryClient
) -> ResponseHandler:
    """Fixture to provide a mocked response handler."""
    handler = MagicMock(spec=ResponseHandler)
    handler.event_bus = mock_event_bus
    handler.cognition_client = mock_cognition_client
    handler.memory_client = mock_memory_client
    handler.process_user_message = AsyncMock()
    handler.process_system_command = AsyncMock()
    handler.stop = AsyncMock()
    return handler


@pytest.fixture
def patched_app_with_mocks():
    """Create a context manager that patches the app with mocks."""
    
    @pytest.fixture
    async def _patched_app():
        with patch("app.core.event_bus.event_bus") as mock_event_bus, \
             patch("app.core.response_handler.create_response_handler") as mock_create_handler:
            
            from app.main import app

            # Setup mocks
            mock_event_bus.publish = AsyncMock()
            mock_event_bus.subscribe = MagicMock()
            
            mock_handler = MagicMock()
            mock_handler.process_user_message = AsyncMock()
            mock_handler.stop = AsyncMock()
            
            mock_create_handler.return_value = mock_handler
            
            # Start the app in test mode
            async with app.router.lifespan_context(app):
                yield app, mock_event_bus, mock_handler
    
    return _patched_app


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    from app.main import app
    with TestClient(app) as client:
        yield client