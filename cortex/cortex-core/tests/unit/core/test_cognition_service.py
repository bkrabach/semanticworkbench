"""
Unit tests for the Cognition Service.
"""

from unittest.mock import MagicMock, AsyncMock
import pytest
from datetime import datetime, timedelta

from app.services.cognition import CognitionService


@pytest.fixture
def mock_memory_service():
    """Create a mock Memory Service."""
    memory_service = MagicMock()
    
    # Mock the expected methods
    memory_service.get_history = AsyncMock(return_value=[])
    memory_service.get_limited_history = AsyncMock(return_value=[])
    memory_service.get_conversation = AsyncMock(return_value=[])
    
    return memory_service


@pytest.fixture
def cognition_service(mock_memory_service):
    """Create a Cognition Service with mocked dependencies."""
    service = CognitionService(memory_service=mock_memory_service)
    return service


def create_mock_message(
    message_id="msg1",
    user_id="user1",
    conversation_id="conv1",
    content="Test message",
    timestamp=None
):
    """Create a mock message for testing."""
    if timestamp is None:
        timestamp = datetime.now().isoformat()
    
    return {
        "id": message_id,
        "user_id": user_id,
        "conversation_id": conversation_id,
        "content": content,
        "timestamp": timestamp,
        "metadata": {}
    }


@pytest.mark.asyncio
async def test_initialization(cognition_service):
    """Test service initialization."""
    # Not initialized at first
    assert cognition_service.initialized is False
    
    # Initialize the service
    await cognition_service.initialize()
    
    # Should be initialized now
    assert cognition_service.initialized is True
    
    # Initializing again should not cause errors
    await cognition_service.initialize()
    assert cognition_service.initialized is True


@pytest.mark.asyncio
async def test_initialization_no_memory_service():
    """Test initialization fails without memory service."""
    service = CognitionService(memory_service=None)
    
    # Initialization should raise an error
    with pytest.raises(ValueError) as exc_info:
        await service.initialize()
    
    assert "Memory Service reference is required" in str(exc_info.value)
    assert service.initialized is False


@pytest.mark.asyncio
async def test_shutdown(cognition_service):
    """Test service shutdown."""
    # Initialize first
    await cognition_service.initialize()
    assert cognition_service.initialized is True
    
    # Shutdown
    await cognition_service.shutdown()
    
    # Should no longer be initialized
    assert cognition_service.initialized is False
    
    # Shutting down again should not cause errors
    await cognition_service.shutdown()
    assert cognition_service.initialized is False


@pytest.mark.asyncio
async def test_get_context_empty_user_id(cognition_service):
    """Test get_context with empty user ID."""
    # Initialize the service
    await cognition_service.initialize()
    
    # Call with empty user ID
    result = await cognition_service.get_context(user_id="")
    
    # Should return error
    assert result["context"] == []
    assert result["count"] == 0
    assert "error" in result
    assert "User ID is required" in result["error"]
    
    # Memory service should not be called
    cognition_service.memory_service.get_history.assert_not_called()
    cognition_service.memory_service.get_limited_history.assert_not_called()


@pytest.mark.asyncio
async def test_get_context_no_history(cognition_service):
    """Test get_context with no history."""
    # Initialize the service
    await cognition_service.initialize()
    
    # Mock empty history
    cognition_service.memory_service.get_limited_history.return_value = []
    
    # Call with valid user ID
    result = await cognition_service.get_context(user_id="user1")
    
    # Should return empty context
    assert result["context"] == []
    assert result["count"] == 0
    assert result["user_id"] == "user1"
    assert "error" not in result
    
    # Memory service should be called
    cognition_service.memory_service.get_limited_history.assert_called_once()


@pytest.mark.asyncio
async def test_get_context_with_history(cognition_service):
    """Test get_context with history items."""
    # Initialize the service
    await cognition_service.initialize()
    
    # Mock history with 3 messages
    now = datetime.now()
    history = [
        create_mock_message(message_id="msg1", content="Hello world", timestamp=(now - timedelta(minutes=10)).isoformat()),
        create_mock_message(message_id="msg2", content="How are you today?", timestamp=(now - timedelta(minutes=5)).isoformat()),
        create_mock_message(message_id="msg3", content="I'm doing well", timestamp=now.isoformat())
    ]
    cognition_service.memory_service.get_limited_history.return_value = history
    
    # Call with valid user ID
    result = await cognition_service.get_context(user_id="user1", limit=2)
    
    # Should return context with limited items
    assert len(result["context"]) == 2
    assert result["count"] == 2
    assert result["user_id"] == "user1"
    
    # By default, most recent messages should be first
    assert result["context"][0]["id"] == "msg3"
    assert result["context"][1]["id"] == "msg2"


@pytest.mark.asyncio
async def test_get_context_with_query(cognition_service):
    """Test get_context with query parameter."""
    # Initialize the service
    await cognition_service.initialize()
    
    # Mock history with messages including the query term
    now = datetime.now()
    history = [
        create_mock_message(message_id="msg1", content="Hello world", timestamp=(now - timedelta(minutes=10)).isoformat()),
        create_mock_message(message_id="msg2", content="How are you today?", timestamp=(now - timedelta(minutes=5)).isoformat()),
        create_mock_message(message_id="msg3", content="Python is great", timestamp=now.isoformat())
    ]
    cognition_service.memory_service.get_limited_history.return_value = history
    
    # Call with query
    result = await cognition_service.get_context(user_id="user1", query="python", limit=3)
    
    # Should prioritize messages containing the query term
    assert len(result["context"]) == 3
    assert result["query"] == "python"
    
    # The message containing "python" should be first
    assert result["context"][0]["id"] == "msg3"


@pytest.mark.asyncio
async def test_get_context_recency_weight(cognition_service):
    """Test get_context with different recency weight values."""
    # Initialize the service
    await cognition_service.initialize()
    
    # Mock history with messages
    now = datetime.now()
    history = [
        create_mock_message(message_id="msg1", content="Python tutorial", timestamp=(now - timedelta(minutes=10)).isoformat()),
        create_mock_message(message_id="msg2", content="How are you today?", timestamp=(now - timedelta(minutes=5)).isoformat()),
        create_mock_message(message_id="msg3", content="Hello world", timestamp=now.isoformat())
    ]
    cognition_service.memory_service.get_limited_history.return_value = history
    
    # Call with query and recency_weight=1.0 (full recency priority)
    result_recency = await cognition_service.get_context(user_id="user1", query="python", recency_weight=1.0, limit=3)
    
    # Call with query and recency_weight=0.0 (full relevance priority)
    result_relevance = await cognition_service.get_context(user_id="user1", query="python", recency_weight=0.0, limit=3)
    
    # With recency priority, most recent message should be first
    assert result_recency["context"][0]["id"] == "msg3"
    
    # With relevance priority, message containing "python" should be first
    assert result_relevance["context"][0]["id"] == "msg1"


@pytest.mark.asyncio
async def test_analyze_conversation_invalid_params(cognition_service):
    """Test analyze_conversation with invalid parameters."""
    # Initialize the service
    await cognition_service.initialize()
    
    # Call with empty user ID
    result1 = await cognition_service.analyze_conversation(user_id="", conversation_id="conv1")
    assert "error" in result1
    assert "User ID and conversation ID are required" in result1["error"]
    
    # Call with empty conversation ID
    result2 = await cognition_service.analyze_conversation(user_id="user1", conversation_id="")
    assert "error" in result2
    assert "User ID and conversation ID are required" in result2["error"]


@pytest.mark.asyncio
async def test_analyze_conversation_not_found(cognition_service):
    """Test analyze_conversation with non-existent conversation."""
    # Initialize the service
    await cognition_service.initialize()
    
    # Mock empty conversation
    cognition_service.memory_service.get_conversation.return_value = []
    
    # Call with valid IDs but non-existent conversation
    result = await cognition_service.analyze_conversation(user_id="user1", conversation_id="nonexistent")
    
    # Should return error
    assert "error" in result
    assert "Conversation not found" in result["error"]
    
    # Memory service should be called
    cognition_service.memory_service.get_conversation.assert_called_once_with("nonexistent")


@pytest.mark.asyncio
async def test_analyze_conversation_summary(cognition_service):
    """Test analyze_conversation with summary type."""
    # Initialize the service
    await cognition_service.initialize()
    
    # Mock conversation with messages from different users
    now = datetime.now()
    conversation = [
        create_mock_message(user_id="user1", content="Hello", timestamp=(now - timedelta(minutes=10)).isoformat()),
        create_mock_message(user_id="user2", content="Hi there", timestamp=(now - timedelta(minutes=9)).isoformat()),
        create_mock_message(user_id="user1", content="How are you?", timestamp=(now - timedelta(minutes=8)).isoformat()),
        create_mock_message(user_id="user2", content="I'm good", timestamp=(now - timedelta(minutes=7)).isoformat())
    ]
    cognition_service.memory_service.get_conversation.return_value = conversation
    
    # Call with summary type
    result = await cognition_service.analyze_conversation(user_id="user1", conversation_id="conv1", analysis_type="summary")
    
    # Should return summary data
    assert result["type"] == "summary"
    assert "results" in result
    assert result["results"]["message_count"] == 4
    assert result["results"]["participants"] == 2
    assert result["results"]["duration_seconds"] > 0
    assert "participant_counts" in result["results"]
    assert result["results"]["participant_counts"]["user1"] == 2
    assert result["results"]["participant_counts"]["user2"] == 2


@pytest.mark.asyncio
async def test_analyze_conversation_topics(cognition_service):
    """Test analyze_conversation with topics type."""
    # Initialize the service
    await cognition_service.initialize()
    
    # Mock conversation with topical content
    conversation = [
        create_mock_message(content="Python programming is fun"),
        create_mock_message(content="I love coding in Python"),
        create_mock_message(content="Python is a great language for AI")
    ]
    cognition_service.memory_service.get_conversation.return_value = conversation
    
    # Call with topics type
    result = await cognition_service.analyze_conversation(user_id="user1", conversation_id="conv1", analysis_type="topics")
    
    # Should return topic data
    assert result["type"] == "topics"
    assert "results" in result
    assert "keywords" in result["results"]
    assert "word_count" in result["results"]
    
    # "python" should be one of the top keywords
    python_keywords = [kw for kw in result["results"]["keywords"] if kw["word"] == "python"]
    assert len(python_keywords) > 0
    assert python_keywords[0]["count"] >= 3


@pytest.mark.asyncio
async def test_analyze_conversation_sentiment(cognition_service):
    """Test analyze_conversation with sentiment type."""
    # Initialize the service
    await cognition_service.initialize()
    
    # Mock conversation with positive sentiment
    positive_conversation = [
        create_mock_message(content="I'm having a great day"),
        create_mock_message(content="This is wonderful"),
        create_mock_message(content="I love the new features")
    ]
    
    # Mock conversation with negative sentiment
    negative_conversation = [
        create_mock_message(content="This is terrible"),
        create_mock_message(content="I hate when this happens"),
        create_mock_message(content="The system is awful")
    ]
    
    # Test positive sentiment
    cognition_service.memory_service.get_conversation.return_value = positive_conversation
    positive_result = await cognition_service.analyze_conversation(user_id="user1", conversation_id="conv1", analysis_type="sentiment")
    
    # Reset mock for negative test
    cognition_service.memory_service.get_conversation.reset_mock()
    cognition_service.memory_service.get_conversation.return_value = negative_conversation
    negative_result = await cognition_service.analyze_conversation(user_id="user1", conversation_id="conv1", analysis_type="sentiment")
    
    # Check positive result
    assert positive_result["type"] == "sentiment"
    assert positive_result["results"]["sentiment_score"] > 0
    assert positive_result["results"]["positive_count"] > 0
    
    # Check negative result
    assert negative_result["type"] == "sentiment"
    assert negative_result["results"]["sentiment_score"] < 0
    assert negative_result["results"]["negative_count"] > 0


@pytest.mark.asyncio
async def test_analyze_conversation_unknown_type(cognition_service):
    """Test analyze_conversation with unknown analysis type."""
    # Initialize the service
    await cognition_service.initialize()
    
    # Mock valid conversation
    cognition_service.memory_service.get_conversation.return_value = [create_mock_message()]
    
    # Call with unknown type
    result = await cognition_service.analyze_conversation(user_id="user1", conversation_id="conv1", analysis_type="unknown_type")
    
    # Should return error
    assert "error" in result
    assert "Unknown analysis type" in result["error"]


@pytest.mark.asyncio
async def test_search_history_invalid_params(cognition_service):
    """Test search_history with invalid parameters."""
    # Initialize the service
    await cognition_service.initialize()
    
    # Call with empty user ID
    result1 = await cognition_service.search_history(user_id="", query="query")
    assert "error" in result1
    assert "User ID and query are required" in result1["error"]
    
    # Call with empty query
    result2 = await cognition_service.search_history(user_id="user1", query="")
    assert "error" in result2
    assert "User ID and query are required" in result2["error"]


@pytest.mark.asyncio
async def test_search_history_no_results(cognition_service):
    """Test search_history with no matching results."""
    # Initialize the service
    await cognition_service.initialize()
    
    # Mock history with no matching messages
    cognition_service.memory_service.get_history.return_value = [
        create_mock_message(content="Hello world"),
        create_mock_message(content="How are you today?")
    ]
    
    # Call with non-matching query
    result = await cognition_service.search_history(user_id="user1", query="python")
    
    # Should return empty results
    assert result["results"] == []
    assert result["count"] == 0
    assert result["query"] == "python"
    assert "error" not in result
    
    # Memory service should be called
    cognition_service.memory_service.get_history.assert_called_once_with("user1")


@pytest.mark.asyncio
async def test_search_history_with_results(cognition_service):
    """Test search_history with matching results."""
    # Initialize the service
    await cognition_service.initialize()
    
    # Mock history with some matching messages
    history = [
        create_mock_message(message_id="msg1", content="Hello world"),
        create_mock_message(message_id="msg2", content="Python is great"),
        create_mock_message(message_id="msg3", content="I'm learning Python")
    ]
    cognition_service.memory_service.get_history.return_value = history
    
    # Call with matching query
    result = await cognition_service.search_history(user_id="user1", query="python")
    
    # Should return matching results
    assert len(result["results"]) == 2
    assert result["count"] == 2
    assert result["query"] == "python"
    
    # Results should be sorted by relevance
    # "Python is great" has better relevance than "I'm learning Python"
    result_ids = [item["id"] for item in result["results"]]
    assert "msg2" in result_ids
    assert "msg3" in result_ids


@pytest.mark.asyncio
async def test_search_history_with_conversation_data(cognition_service):
    """Test search_history with conversation data included."""
    # Initialize the service
    await cognition_service.initialize()
    
    # Mock history with matching messages
    history = [
        create_mock_message(message_id="msg1", conversation_id="conv1", content="Python is great"),
        create_mock_message(message_id="msg2", conversation_id="conv2", content="Learning Python basics")
    ]
    cognition_service.memory_service.get_history.return_value = history
    
    # Mock conversation data
    conv1_data = [
        create_mock_message(conversation_id="conv1", user_id="user1", content="Python is great"),
        create_mock_message(conversation_id="conv1", user_id="user2", content="Yes, I agree")
    ]
    conv2_data = [
        create_mock_message(conversation_id="conv2", user_id="user1", content="Learning Python basics"),
        create_mock_message(conversation_id="conv2", user_id="user3", content="Need any help?")
    ]
    
    # Setup the mock to return different data based on conversation_id
    async def mock_get_conversation(conv_id):
        if conv_id == "conv1":
            return conv1_data
        elif conv_id == "conv2":
            return conv2_data
        return []
    
    cognition_service.memory_service.get_conversation = AsyncMock(side_effect=mock_get_conversation)
    
    # Call with matching query and include_conversations=True
    result = await cognition_service.search_history(user_id="user1", query="python", include_conversations=True)
    
    # Should return matching results with conversation data
    assert len(result["results"]) == 2
    assert result["count"] == 2
    
    # Results should have conversation data
    for item in result["results"]:
        assert "_conversation_data" in item
        assert "message_count" in item["_conversation_data"]
        assert "participants" in item["_conversation_data"]
        assert "first_message" in item["_conversation_data"]
    
    # Memory service get_conversation should be called for each unique conversation
    assert cognition_service.memory_service.get_conversation.call_count == 2


@pytest.mark.asyncio
async def test_search_history_without_conversation_data(cognition_service):
    """Test search_history with conversation data excluded."""
    # Initialize the service
    await cognition_service.initialize()
    
    # Mock history with matching messages
    history = [
        create_mock_message(message_id="msg1", conversation_id="conv1", content="Python is great"),
        create_mock_message(message_id="msg2", conversation_id="conv2", content="Learning Python basics")
    ]
    cognition_service.memory_service.get_history.return_value = history
    
    # Call with matching query and include_conversations=False
    result = await cognition_service.search_history(user_id="user1", query="python", include_conversations=False)
    
    # Should return matching results without conversation data
    assert len(result["results"]) == 2
    assert result["count"] == 2
    
    # Results should not have conversation data
    for item in result["results"]:
        assert "_conversation_data" not in item
    
    # Memory service get_conversation should not be called
    cognition_service.memory_service.get_conversation.assert_not_called()