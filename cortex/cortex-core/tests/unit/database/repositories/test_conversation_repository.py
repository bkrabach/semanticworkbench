"""
Unit tests for the ConversationRepository.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from app.core.exceptions import EntityNotFoundError
from app.database.models import Conversation as ConversationModel
from app.database.repositories.conversation_repository import ConversationRepository
from app.models import Conversation
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def mock_session():
    """Create a mock SQLAlchemy session."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def conversation_repo(mock_session):
    """Create a ConversationRepository with a mock session."""
    return ConversationRepository(mock_session)


def test_model_class(conversation_repo):
    """Test that the repository uses the correct model class."""
    assert conversation_repo.db_model_type == ConversationModel


def test_domain_model_class(conversation_repo):
    """Test that the repository uses the correct domain model class."""
    assert conversation_repo.model_type == Conversation


def create_conversation_model(conversation_id="test-conv-id", workspace_id="test-ws-id"):
    """Create a conversation model for testing."""
    return ConversationModel(
        id=conversation_id, 
        workspace_id=workspace_id, 
        topic="Test Conversation", 
        participant_ids_json='["user1", "user2"]'
    )


def create_conversation_domain(conversation_id="test-conv-id", workspace_id="test-ws-id"):
    """Create a conversation domain model for testing."""
    return Conversation(
        id=conversation_id, 
        workspace_id=workspace_id, 
        topic="Test Conversation", 
        participant_ids=["user1", "user2"]
    )


@pytest.mark.asyncio
async def test_create_conversation(conversation_repo, mock_session):
    """Test creating a conversation."""
    # Setup mock session behavior
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()

    # Create domain model
    conversation = create_conversation_domain()

    # Call create method
    result = await conversation_repo.create(conversation)

    # Verify session was used correctly
    mock_session.add.assert_called_once()
    mock_session.flush.assert_called_once()

    # Verify result
    assert isinstance(result, Conversation)
    assert result.id == conversation.id
    assert result.workspace_id == conversation.workspace_id
    assert result.topic == conversation.topic


@pytest.mark.asyncio
async def test_get_by_id(conversation_repo, mock_session):
    """Test getting a conversation by ID."""
    # Setup mock session behavior
    conversation_model = create_conversation_model()

    # Create a mock result with a scalars method
    mock_scalars = MagicMock()
    mock_scalars.first = MagicMock(return_value=conversation_model)
    
    mock_result = MagicMock()
    mock_result.scalars = MagicMock(return_value=mock_scalars)

    # Set up the execute to return our mock result
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Call get_by_id method
    result = await conversation_repo.get_by_id("test-conv-id")

    # Verify execute was called with a select statement
    mock_session.execute.assert_called_once()

    # Verify result
    assert isinstance(result, Conversation)
    assert result.id == conversation_model.id
    assert result.workspace_id == conversation_model.workspace_id


@pytest.mark.asyncio
async def test_get_by_id_not_found(conversation_repo, mock_session):
    """Test getting a non-existent conversation by ID."""
    # Setup mock session behavior to return None
    mock_scalars = MagicMock()
    mock_scalars.first = MagicMock(return_value=None)
    
    mock_result = MagicMock()
    mock_result.scalars = MagicMock(return_value=mock_scalars)
    
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Call get_by_id method for non-existent ID
    result = await conversation_repo.get_by_id("non-existent-id")

    # Verify result is None
    assert result is None


@pytest.mark.asyncio
async def test_update_conversation(conversation_repo, mock_session):
    """Test updating a conversation."""
    # Setup mock session behavior
    conversation_model = create_conversation_model()

    # Create a mock result with a scalars method
    mock_scalars = MagicMock()
    mock_scalars.first = MagicMock(return_value=conversation_model)
    
    mock_result = MagicMock()
    mock_result.scalars = MagicMock(return_value=mock_scalars)

    # Set up the execute to return our mock result
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.flush = AsyncMock()

    # Create updated domain model
    updated_conversation = create_conversation_domain()
    updated_conversation.topic = "Updated Topic"

    # Call update method
    result = await conversation_repo.update(updated_conversation)

    # Verify session was used correctly
    mock_session.execute.assert_called_once()
    mock_session.flush.assert_called_once()

    # Verify model was updated
    assert conversation_model.topic == "Updated Topic"

    # Verify result
    assert isinstance(result, Conversation)
    assert result.topic == "Updated Topic"


@pytest.mark.asyncio
async def test_update_not_found(conversation_repo, mock_session):
    """Test updating a non-existent conversation."""
    # Setup mock session behavior to return None
    mock_scalars = MagicMock()
    mock_scalars.first = MagicMock(return_value=None)
    
    mock_result = MagicMock()
    mock_result.scalars = MagicMock(return_value=mock_scalars)
    
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Create domain model
    conversation = create_conversation_domain()

    # Call update method with non-existent ID
    with pytest.raises(EntityNotFoundError) as exc_info:
        await conversation_repo.update(conversation)

    # Verify the exception
    assert "Conversation not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_delete_conversation(conversation_repo, mock_session):
    """Test deleting a conversation."""
    # Setup mock session behavior
    conversation_model = create_conversation_model()

    # Create a mock result with a scalars method
    mock_scalars = MagicMock()
    mock_scalars.first = MagicMock(return_value=conversation_model)
    
    mock_result = MagicMock()
    mock_result.scalars = MagicMock(return_value=mock_scalars)

    # Set up the execute to return our mock result
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.delete = AsyncMock()
    mock_session.flush = AsyncMock()

    # Call delete method
    result = await conversation_repo.delete("test-conv-id")

    # Verify session was used correctly
    mock_session.execute.assert_called_once()
    mock_session.delete.assert_called_once_with(conversation_model)
    mock_session.flush.assert_called_once()

    # Verify result
    assert result is True


@pytest.mark.asyncio
async def test_delete_not_found(conversation_repo, mock_session):
    """Test deleting a non-existent conversation."""
    # Setup mock session behavior to return None
    mock_scalars = MagicMock()
    mock_scalars.first = MagicMock(return_value=None)
    
    mock_result = MagicMock()
    mock_result.scalars = MagicMock(return_value=mock_scalars)
    
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Call delete method with non-existent ID
    result = await conversation_repo.delete("non-existent-id")

    # Verify result is False
    assert result is False


@pytest.mark.asyncio
async def test_list_by_workspace(conversation_repo, mock_session):
    """Test listing conversations by workspace ID."""
    # Setup mock session behavior
    conversation_models = [
        create_conversation_model("conv1", "ws1"),
        create_conversation_model("conv2", "ws1"),
    ]

    # Create a mock result with a scalars method that has an all method
    mock_scalars = MagicMock()
    mock_scalars.all = MagicMock(return_value=conversation_models)
    
    mock_result = MagicMock()
    mock_result.scalars = MagicMock(return_value=mock_scalars)

    # Set up the execute to return our mock result
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Call list_by_workspace method
    result = await conversation_repo.list_by_workspace("ws1")

    # Verify session was used correctly
    mock_session.execute.assert_called_once()

    # Verify result
    assert len(result) == 2
    assert all(isinstance(c, Conversation) for c in result)
    assert {c.id for c in result} == {"conv1", "conv2"}