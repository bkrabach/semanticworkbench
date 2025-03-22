"""
Integration tests for database repositories.
"""

import asyncio
import os
from datetime import datetime

import pytest
from app.database.connection import get_session
from app.database.unit_of_work import UnitOfWork
from app.models import Conversation, Message, User, Workspace


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def db_session():
    """Create a database session for testing."""
    # Use in-memory SQLite for testing
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

    # Get session
    async with get_session() as session:
        yield session


@pytest.fixture
async def test_user():
    """Create a test user for database tests."""
    return User(user_id="test-user-id", name="Test User", email="test@example.com")


@pytest.fixture
async def test_workspace(test_user):
    """Create a test workspace for database tests."""
    return Workspace(
        id="test-workspace-id", name="Test Workspace", description="A test workspace", owner_id=test_user.user_id
    )


@pytest.fixture
async def test_conversation(test_workspace):
    """Create a test conversation for database tests."""
    return Conversation(
        id="test-conversation-id",
        workspace_id=test_workspace.id,
        topic="Test Topic",
        participant_ids=[test_workspace.owner_id],
    )


@pytest.fixture
async def test_message(test_conversation):
    """Create a test message for database tests."""
    return Message(
        id="test-message-id",
        conversation_id=test_conversation.id,
        sender_id=test_conversation.participant_ids[0],
        content="Test message content",
        timestamp=datetime.now().isoformat(),
    )


@pytest.mark.asyncio
async def test_user_repository_operations(test_user):
    """Test user repository operations."""
    async with UnitOfWork.for_transaction() as uow:
        user_repository = uow.repositories.get_user_repository()

        # Create user
        created_user = await user_repository.create(test_user)
        assert created_user.user_id == test_user.user_id

        # Get user by ID
        retrieved_user = await user_repository.get_by_id(test_user.user_id)
        assert retrieved_user is not None
        assert retrieved_user.user_id == test_user.user_id
        assert retrieved_user.name == test_user.name

        # List users (should include our test user)
        users = await user_repository.list_all()
        assert any(user.user_id == test_user.user_id for user in users)

        # Update user
        updated_name = "Updated Test User"
        test_user.name = updated_name
        updated_user = await user_repository.update(test_user)
        assert updated_user.name == updated_name

        # Get by email
        user_by_email = await user_repository.get_by_email(test_user.email)
        assert user_by_email is not None
        assert user_by_email.user_id == test_user.user_id


@pytest.mark.asyncio
async def test_workspace_repository_operations(test_workspace, test_user):
    """Test workspace repository operations."""
    async with UnitOfWork.for_transaction() as uow:
        workspace_repository = uow.repositories.get_workspace_repository()

        # Create workspace
        created_workspace = await workspace_repository.create(test_workspace)
        assert created_workspace.id == test_workspace.id

        # Get workspace by ID
        retrieved_workspace = await workspace_repository.get_by_id(test_workspace.id)
        assert retrieved_workspace is not None
        assert retrieved_workspace.id == test_workspace.id
        assert retrieved_workspace.name == test_workspace.name

        # List workspaces by owner
        workspaces = await workspace_repository.list_by_owner(test_user.user_id)
        assert len(workspaces) > 0
        assert any(ws.id == test_workspace.id for ws in workspaces)

        # Update workspace
        updated_name = "Updated Workspace"
        test_workspace.name = updated_name
        updated_workspace = await workspace_repository.update(test_workspace)
        assert updated_workspace.name == updated_name


@pytest.mark.asyncio
async def test_conversation_repository_operations(test_conversation):
    """Test conversation repository operations."""
    async with UnitOfWork.for_transaction() as uow:
        conversation_repository = uow.repositories.get_conversation_repository()

        # Create conversation
        created_conversation = await conversation_repository.create(test_conversation)
        assert created_conversation.id == test_conversation.id

        # Get conversation by ID
        retrieved_conversation = await conversation_repository.get_by_id(test_conversation.id)
        assert retrieved_conversation is not None
        assert retrieved_conversation.id == test_conversation.id
        assert retrieved_conversation.topic == test_conversation.topic

        # List conversations by workspace
        conversations = await conversation_repository.list_by_workspace(test_conversation.workspace_id)
        assert len(conversations) > 0
        assert any(conv.id == test_conversation.id for conv in conversations)

        # Update conversation
        updated_topic = "Updated Topic"
        test_conversation.topic = updated_topic
        updated_conversation = await conversation_repository.update(test_conversation)
        assert updated_conversation.topic == updated_topic


@pytest.mark.asyncio
async def test_message_repository_operations(test_message):
    """Test message repository operations."""
    async with UnitOfWork.for_transaction() as uow:
        message_repository = uow.repositories.get_message_repository()

        # Create message
        created_message = await message_repository.create(test_message)
        assert created_message.id == test_message.id

        # Get message by ID
        retrieved_message = await message_repository.get_by_id(test_message.id)
        assert retrieved_message is not None
        assert retrieved_message.id == test_message.id
        assert retrieved_message.content == test_message.content

        # List messages by conversation
        messages = await message_repository.list_by_conversation(test_message.conversation_id)
        assert len(messages) > 0
        assert any(msg.id == test_message.id for msg in messages)

        # Update message
        updated_content = "Updated message content"
        test_message.content = updated_content
        updated_message = await message_repository.update(test_message)
        assert updated_message.content == updated_content
