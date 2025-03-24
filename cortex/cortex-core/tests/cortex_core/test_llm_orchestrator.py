"""Tests for the LLM Orchestrator component."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.llm_orchestrator import (
    LLMOrchestrator, call_llm, fetch_tool_result, 
    async_memory_tool, set_conversation_context, get_conversation_context
)
from app.core.event_bus import EventBus


class MockPydanticAIResult:
    """Mock Pydantic-AI result for testing."""
    
    def __init__(self, data):
        self.data = data
        self.messages = []
    
    def all_messages(self):
        return self.messages


@pytest.mark.asyncio
async def test_call_llm_with_pydantic_ai():
    """Test that call_llm correctly handles messages with Pydantic-AI."""
    # Create a mock Agent
    mock_agent = AsyncMock()
    mock_agent.run = AsyncMock(return_value=MockPydanticAIResult("Test AI response"))
    
    with patch('app.core.llm_orchestrator.get_pydantic_ai_agent', return_value=mock_agent):
        # Test messages
        messages = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hello, world!"}
        ]
        
        # Call the function
        response = ""
        async for chunk in call_llm(messages):
            response += chunk
        
        # Verify the response
        assert response == "Test AI response"
        
        # Verify agent was called with the correctly formatted prompt
        mock_agent.run.assert_called_once()
        call_args = mock_agent.run.call_args[0][0]
        assert call_args == "You are a helpful assistant\n\nHello, world!"


@pytest.mark.asyncio
async def test_fetch_tool_result_memory():
    """Test that fetch_tool_result correctly calls memory service."""
    # Mock the MemoryClient
    mock_client = AsyncMock()
    mock_client.ensure_connected = AsyncMock()
    mock_client.get_recent_messages = AsyncMock(return_value=[
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"}
    ])
    mock_client.close = AsyncMock()
    
    with patch('app.core.llm_orchestrator.MemoryClient', return_value=mock_client):
        # Call the function with a memory tool request
        result = await fetch_tool_result(
            tool_name="memory",
            args={"query": "recent_messages", "limit": 2},
            user_id="test-user",
            conversation_id="test-conversation"
        )
        
        # Verify the client was called correctly
        mock_client.ensure_connected.assert_called_once()
        mock_client.get_recent_messages.assert_called_once_with(
            user_id="test-user",
            conversation_id="test-conversation",
            limit=2
        )
        mock_client.close.assert_called_once()
        
        # Verify the result contains the expected content
        assert "user: Hello" in result
        assert "assistant: Hi there" in result


@pytest.mark.asyncio
async def test_conversation_context():
    """Test setting and getting conversation context."""
    # Test initial state
    assert get_conversation_context() is None
    
    # Set the context
    set_conversation_context("test-user", "test-conversation")
    
    # Check that it was set correctly
    context = get_conversation_context()
    assert context is not None
    assert context["user_id"] == "test-user"
    assert context["conversation_id"] == "test-conversation"


@pytest.mark.asyncio
async def test_async_memory_tool():
    """Test that async_memory_tool correctly retrieves memory with context."""
    # Mock the MemoryClient
    mock_client = AsyncMock()
    mock_client.ensure_connected = AsyncMock()
    mock_client.get_recent_messages = AsyncMock(return_value=[
        {"role": "user", "content": "Hello", "timestamp": "2023-01-01"},
        {"role": "assistant", "content": "Hi there", "timestamp": "2023-01-01"}
    ])
    mock_client.close = AsyncMock()
    
    # Set the conversation context
    set_conversation_context("test-user", "test-conversation")
    
    with patch('app.core.llm_orchestrator.MemoryClient', return_value=mock_client):
        # Call the memory tool
        result = await async_memory_tool(query="recent_messages", limit=2)
        
        # Verify the client was called correctly
        mock_client.ensure_connected.assert_called_once()
        mock_client.get_recent_messages.assert_called_once_with(
            user_id="test-user",
            conversation_id="test-conversation",
            limit=2
        )
        mock_client.close.assert_called_once()
        
        # Verify the result contains the expected content
        assert "Recent messages" in result
        assert "user" in result
        assert "Hello" in result
        assert "assistant" in result
        assert "Hi there" in result


@pytest.mark.asyncio
async def test_llm_orchestrator_start_stop():
    """Test the LLM Orchestrator start and stop methods."""
    mock_event_bus = MagicMock(spec=EventBus)
    mock_queue = asyncio.Queue()
    mock_event_bus.subscribe.return_value = mock_queue
    
    # Create orchestrator
    orchestrator = LLMOrchestrator(event_bus=mock_event_bus)
    
    # Start orchestrator
    await orchestrator.start()
    
    # Verify it subscribed correctly
    mock_event_bus.subscribe.assert_called_once_with(event_type="user_message")
    assert orchestrator.running is True
    
    # Stop orchestrator
    await orchestrator.stop()
    
    # Verify correct shutdown
    mock_event_bus.unsubscribe.assert_called_once_with(mock_queue)
    assert orchestrator.running is False


@pytest.mark.asyncio
async def test_orchestrator_handle_basic_query():
    """Test that orchestrator correctly handles a basic query (directly answerable)."""
    # Setup mocks
    mock_event_bus = MagicMock(spec=EventBus)
    mock_event_bus.publish = AsyncMock()
    
    mock_memory_client = AsyncMock()
    mock_memory_client.ensure_connected = AsyncMock()
    mock_memory_client.store_message = AsyncMock()
    mock_memory_client.close = AsyncMock()
    
    # Create test event
    test_event = {
        "user_id": "test-user",
        "conversation_id": "test-conv",
        "data": {"content": "What is the capital of France?", "role": "user"}
    }
    
    # Mock Pydantic-AI agent
    mock_agent = AsyncMock()
    mock_result = MockPydanticAIResult("Paris is the capital of France.")
    mock_agent.run = AsyncMock(return_value=mock_result)
    
    # Create orchestrator with patched dependencies
    with patch('app.core.llm_orchestrator.MemoryClient', return_value=mock_memory_client), \
         patch('app.core.llm_orchestrator.get_pydantic_ai_agent', return_value=mock_agent), \
         patch('app.core.llm_orchestrator.set_conversation_context') as mock_set_context:
            
        # Create orchestrator
        orchestrator = LLMOrchestrator(event_bus=mock_event_bus)
        
        # Handle the event
        await orchestrator.handle_input_event(test_event)
        
        # Verify memory client interactions
        mock_memory_client.ensure_connected.assert_called()
        assert mock_memory_client.store_message.call_count == 2  # Once for user, once for assistant
        
        # Verify conversation context was set
        mock_set_context.assert_called_once_with("test-user", "test-conv")
        
        # Verify agent was called with correct messages
        mock_agent.run.assert_called_once()
        
        # Verify correct response was published
        mock_event_bus.publish.assert_called_once()
        call_args = mock_event_bus.publish.call_args
        assert call_args[0][0] == "output"  # First arg is event type
        assert call_args[0][1]["user_id"] == "test-user"  # Second arg is event data
        assert call_args[0][1]["conversation_id"] == "test-conv"
        assert call_args[0][1]["content"] == "Paris is the capital of France."


@pytest.mark.asyncio
async def test_orchestrator_handle_tool_request():
    """Test that orchestrator correctly handles a query requiring a tool call."""
    # Setup mocks
    mock_event_bus = MagicMock(spec=EventBus)
    mock_event_bus.publish = AsyncMock()
    
    mock_memory_client = AsyncMock()
    mock_memory_client.ensure_connected = AsyncMock()
    mock_memory_client.store_message = AsyncMock()
    mock_memory_client.close = AsyncMock()
    
    # Create test event
    test_event = {
        "user_id": "test-user",
        "conversation_id": "test-conv",
        "data": {"content": "What did we talk about earlier?", "role": "user"}
    }
    
    # Create a mock Pydantic-AI result with tool usage
    mock_result = MockPydanticAIResult("We discussed machine learning earlier.")
    
    # Create a mock tool call part
    class MockToolCallPart:
        def __init__(self, tool_name, args):
            self.tool_name = tool_name
            self.args = args
            self.part_kind = "tool-call"
    
    # Create a mock response message with a tool call
    class MockResponseMessage:
        def __init__(self, parts):
            self.parts = parts
            self.kind = "response"
    
    # Add a message with a tool call to the result
    mock_result.messages = [
        MockResponseMessage([
            MockToolCallPart("memory", {"query": "recent_messages", "limit": 5})
        ])
    ]
    
    # Mock the Pydantic-AI agent
    mock_agent = AsyncMock()
    mock_agent.run = AsyncMock(return_value=mock_result)
    
    # Create orchestrator with patched dependencies
    with patch('app.core.llm_orchestrator.MemoryClient', return_value=mock_memory_client), \
         patch('app.core.llm_orchestrator.get_pydantic_ai_agent', return_value=mock_agent), \
         patch('app.core.llm_orchestrator.set_conversation_context') as mock_set_context:
            
        # Create orchestrator
        orchestrator = LLMOrchestrator(event_bus=mock_event_bus)
        
        # Handle the event
        await orchestrator.handle_input_event(test_event)
        
        # Verify context was set
        mock_set_context.assert_called_once_with("test-user", "test-conv")
        
        # Verify agent was called
        mock_agent.run.assert_called_once()
        
        # Verify memory client interactions
        assert mock_memory_client.store_message.call_count == 2  # Once for user, once for assistant
        
        # Verify correct response was published
        mock_event_bus.publish.assert_called_once()
        call_args = mock_event_bus.publish.call_args
        assert call_args[0][0] == "output"  # First arg is event type
        assert "We discussed machine learning earlier." in call_args[0][1]["content"]
