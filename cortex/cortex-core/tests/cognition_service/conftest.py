"""
Common test fixtures for the Cognition Service tests.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from cognition_service.models import Message, MessageRole
from cognition_service.config import Settings


class MockPydanticAIResult:
    """Mock class to simulate Pydantic AI result structure."""
    def __init__(self, data):
        self.data = data
    
    def __await__(self):
        async def _coro():
            return self
        return _coro().__await__()


@pytest.fixture
def mock_settings():
    """Fixture to provide mock settings for testing."""
    return Settings(
        port=5000,
        host="localhost",
        llm_provider="test",
        model_name="test-model",
        temperature=0.0,
        max_tokens=100,
        system_prompt="Test system prompt",
        memory_service_url="http://localhost:5001/sse",
        enable_memory_integration=True,
        enable_tool_use=True
    )


@pytest.fixture
def sample_messages():
    """Fixture to provide sample conversation messages."""
    return [
        Message(role=MessageRole.SYSTEM, content="You are a helpful assistant."),
        Message(role=MessageRole.USER, content="Hello, how are you?"),
        Message(role=MessageRole.ASSISTANT, content="I'm doing well, thank you for asking!"),
        Message(role=MessageRole.USER, content="What can you do?")
    ]


@pytest.fixture
def mock_agent():
    """Fixture to provide a mock LLM agent."""
    with patch("cognition_service.logic.agent") as mock_agent:
        # Set up default response
        mock_result = MockPydanticAIResult("This is a mock response")
        mock_agent.run = AsyncMock(return_value=mock_result)
        yield mock_agent


@pytest.fixture
def mock_memory_client():
    """Fixture to provide a mock memory client."""
    with patch("cognition_service.logic.memory_client") as mock_client:
        # Set default behavior
        mock_client.get_conversation_history = AsyncMock(return_value=[])
        yield mock_client