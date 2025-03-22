"""
Integration tests for the database layer.
"""

import uuid

import pytest
from app.database.connection import get_session
from app.database.repositories.factory import get_repository
from app.database.unit_of_work import UnitOfWork
from app.models.domain.pydantic_ai import Conversation, Message, User, Workspace


@pytest.fixture
async def db_session():
    """Create a database session for testing."""
    async with get_session() as session:
        yield session


@pytest.fixture
async def unit_of_work():
    """Create a UnitOfWork instance for testing."""
    async with UnitOfWork() as uow:
        yield uow


@pytest.fixture
def random_id():
    """Generate a random ID for test entities."""
    return str(uuid.uuid4())


@pytest.fixture
async def test_user(db_session, random_id):
    """Create a test user."""
    user = User(
        id=f"test-user-{random_id}", name="Test User", email=f"test-{random_id}@example.com", metadata={"test": True}
    )

    user_repo = get_repository("user", db_session)
    created_user = await user_repo.create(user)

    yield created_user

    # Cleanup
    try:
        await user_repo.delete(user)
    except Exception:
        pass


@pytest.mark.asyncio
async def test_repository_factory(db_session):
    """Test that the repository factory returns the correct repositories."""
    # Test user repository
    user_repo = get_repository("user", db_session)
    assert user_repo is not None
    assert user_repo.__class__.__name__ == "UserRepository"

    # Test workspace repository
    workspace_repo = get_repository("workspace", db_session)
    assert workspace_repo is not None
    assert workspace_repo.__class__.__name__ == "WorkspaceRepository"

    # Test conversation repository
    conversation_repo = get_repository("conversation", db_session)
    assert conversation_repo is not None
    assert conversation_repo.__class__.__name__ == "ConversationRepository"

    # Test message repository
    message_repo = get_repository("message", db_session)
    assert message_repo is not None
    assert message_repo.__class__.__name__ == "MessageRepository"


@pytest.mark.asyncio
async def test_user_crud(db_session, random_id):
    """Test CRUD operations for User entity."""
    # Create a user repository
    user_repo = get_repository("user", db_session)

    # Create a test user
    user = User(
        id=f"crud-user-{random_id}",
        name="CRUD Test User",
        email=f"crud-{random_id}@example.com",
        metadata={"source": "integration-test"},
    )

    # Create
    created_user = await user_repo.create(user)
    assert created_user.id == user.id
    assert created_user.name == user.name
    assert created_user.email == user.email

    # Read
    retrieved_user = await user_repo.get_by_id(user.id)
    assert retrieved_user is not None
    assert retrieved_user.id == user.id
    assert retrieved_user.name == user.name
    assert retrieved_user.metadata["source"] == "integration-test"

    # Update
    retrieved_user.name = "Updated CRUD User"
    retrieved_user.metadata["updated"] = True
    updated_user = await user_repo.update(retrieved_user)
    assert updated_user.name == "Updated CRUD User"
    assert updated_user.metadata["updated"] is True

    # Verify update
    verified_user = await user_repo.get_by_id(user.id)
    assert verified_user.name == "Updated CRUD User"

    # Delete
    result = await user_repo.delete(updated_user)
    assert result is True

    # Verify deletion
    deleted_user = await user_repo.get_by_id(user.id)
    assert deleted_user is None


@pytest.mark.asyncio
async def test_workspace_user_relationship(db_session, test_user, random_id):
    """Test relationship between Workspace and User."""
    # Create repositories
    workspace_repo = get_repository("workspace", db_session)

    # Create a workspace for the test user
    workspace = Workspace(
        id=f"test-workspace-{random_id}",
        name="Test Workspace",
        description="Test workspace for integration testing",
        user_id=test_user.id,
        metadata={"test": True},
    )

    # Create the workspace
    created_workspace = await workspace_repo.create(workspace)
    assert created_workspace.id == workspace.id
    assert created_workspace.user_id == test_user.id

    # List workspaces for the user
    user_workspaces = await workspace_repo.list_by_user(test_user.id)
    assert len(user_workspaces) >= 1
    assert any(ws.id == workspace.id for ws in user_workspaces)

    # Cleanup
    await workspace_repo.delete(workspace)


@pytest.mark.asyncio
async def test_conversation_workspace_relationship(db_session, test_user, random_id):
    """Test relationship between Conversation and Workspace."""
    # Create repositories
    workspace_repo = get_repository("workspace", db_session)
    conversation_repo = get_repository("conversation", db_session)

    # Create a workspace
    workspace = Workspace(
        id=f"conv-workspace-{random_id}",
        name="Conversation Test Workspace",
        description="Workspace for testing conversations",
        user_id=test_user.id,
        metadata={},
    )
    created_workspace = await workspace_repo.create(workspace)

    # Create conversations in the workspace
    conversations = []
    for i in range(3):
        conversation = Conversation(
            id=f"conv-{i}-{random_id}",
            workspace_id=created_workspace.id,
            user_id=test_user.id,
            topic=f"Test Conversation {i}",
            metadata={"index": i},
        )
        created_conv = await conversation_repo.create(conversation)
        conversations.append(created_conv)

    # List conversations in the workspace
    workspace_conversations = await conversation_repo.list_by_workspace(created_workspace.id, test_user.id)
    assert len(workspace_conversations) >= 3
    assert all(any(c.id == conv.id for c in workspace_conversations) for conv in conversations)

    # Cleanup
    for conv in conversations:
        await conversation_repo.delete(conv)
    await workspace_repo.delete(workspace)


@pytest.mark.asyncio
async def test_unit_of_work(unit_of_work, random_id):
    """Test the UnitOfWork pattern with transactions."""
    # Create a user and workspace in a single transaction
    user = User(id=f"uow-user-{random_id}", name="UOW Test User", email=f"uow-{random_id}@example.com", metadata={})

    workspace = Workspace(
        id=f"uow-workspace-{random_id}",
        name="UOW Test Workspace",
        description="Testing the Unit of Work pattern",
        user_id=user.id,
        metadata={},
    )
    
    # Create entities within the transaction
    created_user = await unit_of_work.user_repository.create(user)
    created_workspace = await unit_of_work.workspace_repository.create(workspace)

    # Commit the transaction
    await unit_of_work.commit()

    # Verify the entities were created
    verified_user = await unit_of_work.user_repository.get_by_id(user.id)
    verified_workspace = await unit_of_work.workspace_repository.get_by_id(workspace.id)

    assert verified_user is not None
    assert verified_user.id == user.id
    assert verified_workspace is not None
    assert verified_workspace.id == workspace.id

    # Cleanup
    await unit_of_work.workspace_repository.delete(workspace)
    await unit_of_work.user_repository.delete(user)
    await unit_of_work.commit()


@pytest.mark.asyncio
async def test_unit_of_work_rollback(unit_of_work, random_id):
    """Test UnitOfWork rollback functionality."""
    # Create a user
    user = User(
        id=f"rollback-user-{random_id}",
        name="Rollback Test User",
        email=f"rollback-{random_id}@example.com",
        metadata={},
    )

    created_user = await unit_of_work.user_repository.create(user)
    await unit_of_work.commit()

    # Try to create a workspace with an invalid ID (should fail)
    workspace = Workspace(
        id="invalid id with spaces",  # Invalid format
        name="Invalid Workspace",
        description="Should trigger rollback",
        user_id=created_user.id,
        metadata={},
    )

    try:
        # This should fail and trigger a rollback
        await unit_of_work.workspace_repository.create(workspace)
        await unit_of_work.commit()
        assert False, "Expected an exception but none was raised"
    except Exception:
        # Expected exception
        await unit_of_work.rollback()

    # Verify the workspace was not created
    verified_workspace = await unit_of_work.workspace_repository.get_by_id(workspace.id)
    assert verified_workspace is None

    # Cleanup
    await unit_of_work.user_repository.delete(user)
    await unit_of_work.commit()


@pytest.mark.asyncio
async def test_message_conversation_relationship(db_session, test_user, random_id):
    """Test relationship between Message and Conversation."""
    # Create repositories
    workspace_repo = get_repository("workspace", db_session)
    conversation_repo = get_repository("conversation", db_session)
    message_repo = get_repository("message", db_session)

    # Create a workspace and conversation
    workspace = Workspace(
        id=f"msg-workspace-{random_id}",
        name="Message Test Workspace",
        description="Workspace for testing messages",
        user_id=test_user.id,
        metadata={},
    )
    created_workspace = await workspace_repo.create(workspace)

    conversation = Conversation(
        id=f"msg-conv-{random_id}",
        workspace_id=created_workspace.id,
        user_id=test_user.id,
        topic="Message Test Conversation",
        metadata={},
    )
    created_conv = await conversation_repo.create(conversation)

    # Create messages in the conversation
    messages = []
    for i in range(5):
        message = Message(
            id=f"msg-{i}-{random_id}",
            conversation_id=created_conv.id,
            user_id=test_user.id,
            content=f"Test message {i}",
            role="user" if i % 2 == 0 else "assistant",
            metadata={"index": i},
        )
        created_msg = await message_repo.create(message)
        messages.append(created_msg)

    # List messages in the conversation
    conversation_messages = await message_repo.list_by_conversation(created_conv.id)
    assert len(conversation_messages) >= 5
    assert all(any(m.id == msg.id for m in conversation_messages) for msg in messages)

    # Cleanup
    for msg in messages:
        await message_repo.delete(msg)
    await conversation_repo.delete(conversation)
    await workspace_repo.delete(workspace)