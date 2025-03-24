"""
Tests for the input API endpoints.
"""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from app.api.input import receive_input
from app.core.exceptions import EventBusException
from app.models.api.request import InputRequest
from app.models.core_domain import Conversation, Workspace
from fastapi import HTTPException


@pytest.fixture
def mock_uow():
    """Create a mock UnitOfWork for testing."""
    mock = Mock()
    mock.repositories = Mock()

    # Mock conversation repository
    mock_conv_repo = Mock()
    mock.repositories.get_conversation_repository.return_value = mock_conv_repo

    # Mock workspace repository
    mock_ws_repo = Mock()
    mock.repositories.get_workspace_repository.return_value = mock_ws_repo

    # Create async mock for context manager
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock

    # Mock the commit method
    mock.commit = AsyncMock()

    return mock_context, mock_conv_repo, mock_ws_repo


@pytest.mark.asyncio
async def test_receive_input_valid_request(mock_uow):
    """Test successfully receiving a valid input request."""
    # Unpack mocks
    mock_context, mock_conv_repo, mock_ws_repo = mock_uow

    # Mock conversation and workspace
    mock_conversation = Conversation(
        id="test-conv-id",
        workspace_id="test-ws-id",
        topic="Test Conversation",
        participant_ids=["user123"],
    )
    mock_conv_repo.get_by_id = AsyncMock(return_value=mock_conversation)

    mock_workspace = Workspace(
        id="test-ws-id", name="Test Workspace", description="Test workspace description", owner_id="owner123"
    )
    mock_ws_repo.get_by_id = AsyncMock(return_value=mock_workspace)

    # Create request
    request = InputRequest(conversation_id="test-conv-id", content="Hello, world!", metadata={"key": "value"}, streaming=True)

    # Mock background tasks
    mock_background = Mock()

    # Mock current user
    current_user = {"user_id": "user123", "name": "Test User"}

    # Mock dependencies
    with (
        patch("app.api.input.UnitOfWork.for_transaction", return_value=mock_context),
        patch("app.api.input.event_bus.publish", new_callable=AsyncMock) as mock_publish,
        patch("app.api.input.response_handler.handle_message") as mock_handle_message,
    ):
        # Call the endpoint
        response = await receive_input(request, mock_background, current_user)

        # Verify the response
        assert response.status == "received"
        assert response.data["content"] == "Hello, world!"
        assert response.data["conversation_id"] == "test-conv-id"
        assert response.data["metadata"] == {"key": "value"}
        assert "timestamp" in response.data

        # Verify the background task was added
        mock_background.add_task.assert_called_once_with(
            mock_handle_message,
            user_id="user123",
            conversation_id="test-conv-id",
            message_content="Hello, world!",
            metadata={"key": "value"},
            streaming=True,  # Default value
        )

        # Verify event bus was called
        mock_publish.assert_called_once()
        event = mock_publish.call_args[0][0]
        assert event["type"] == "message"
        assert event["message_type"] == "user"
        assert event["data"]["content"] == "Hello, world!"
        assert event["data"]["conversation_id"] == "test-conv-id"
        assert event["data"]["sender"]["id"] == "user123"
        assert event["data"]["sender"]["name"] == "Test User"
        assert event["data"]["sender"]["role"] == "user"
        assert event["metadata"] == {"key": "value"}


@pytest.mark.asyncio
async def test_receive_input_conversation_not_found(mock_uow):
    """Test receiving input for a non-existent conversation."""
    # Unpack mocks
    mock_context, mock_conv_repo, _ = mock_uow

    # Mock conversation not found
    mock_conv_repo.get_by_id = AsyncMock(return_value=None)

    # Create request
    request = InputRequest(conversation_id="nonexistent-conv-id", content="Hello, world!", streaming=True)

    # Mock background tasks
    mock_background = Mock()

    # Mock current user
    current_user = {"user_id": "user123", "name": "Test User"}

    # Mock dependencies
    with (
        patch("app.api.input.UnitOfWork.for_transaction", return_value=mock_context),
        pytest.raises(HTTPException) as exc_info,
    ):
        # Call the endpoint
        await receive_input(request, mock_background, current_user)

    # Verify the exception
    assert exc_info.value.status_code == 404
    assert "resource_not_found" in json.dumps(exc_info.value.detail)
    assert "Conversation not found" in json.dumps(exc_info.value.detail)


@pytest.mark.asyncio
async def test_receive_input_workspace_not_found(mock_uow):
    """Test receiving input when workspace is not found."""
    # Unpack mocks
    mock_context, mock_conv_repo, mock_ws_repo = mock_uow

    # Mock conversation found but workspace not found
    mock_conversation = Conversation(
        id="test-conv-id",
        workspace_id="test-ws-id",
        topic="Test Conversation",
        participant_ids=["user123"],
    )
    mock_conv_repo.get_by_id = AsyncMock(return_value=mock_conversation)

    # Workspace not found
    mock_ws_repo.get_by_id = AsyncMock(return_value=None)

    # Create request
    request = InputRequest(conversation_id="test-conv-id", content="Hello, world!", streaming=True)

    # Mock background tasks
    mock_background = Mock()

    # Mock current user
    current_user = {"user_id": "user123", "name": "Test User"}

    # Mock dependencies
    with (
        patch("app.api.input.UnitOfWork.for_transaction", return_value=mock_context),
        pytest.raises(HTTPException) as exc_info,
    ):
        # Call the endpoint
        await receive_input(request, mock_background, current_user)

    # Verify the exception
    assert exc_info.value.status_code == 404
    assert "resource_not_found" in json.dumps(exc_info.value.detail)
    assert "Workspace not found" in json.dumps(exc_info.value.detail)


@pytest.mark.asyncio
async def test_receive_input_access_denied(mock_uow):
    """Test receiving input when user doesn't have access to the conversation."""
    # Unpack mocks
    mock_context, mock_conv_repo, mock_ws_repo = mock_uow

    # Mock conversation with different participants
    mock_conversation = Conversation(
        id="test-conv-id",
        workspace_id="test-ws-id",
        topic="Test Conversation",
        participant_ids=["other_user"],  # User123 is not a participant
    )
    mock_conv_repo.get_by_id = AsyncMock(return_value=mock_conversation)

    # Mock workspace with different owner
    mock_workspace = Workspace(
        id="test-ws-id",
        name="Test Workspace",
        description="Test workspace description",
        owner_id="other_owner",  # User123 is not the owner
    )
    mock_ws_repo.get_by_id = AsyncMock(return_value=mock_workspace)

    # Create request
    request = InputRequest(conversation_id="test-conv-id", content="Hello, world!", streaming=True)

    # Mock background tasks
    mock_background = Mock()

    # Mock current user (not a participant or owner)
    current_user = {"user_id": "user123", "name": "Test User"}

    # Mock dependencies
    with (
        patch("app.api.input.UnitOfWork.for_transaction", return_value=mock_context),
        pytest.raises(HTTPException) as exc_info,
    ):
        # Call the endpoint
        await receive_input(request, mock_background, current_user)

    # Verify the exception
    assert exc_info.value.status_code == 403
    assert "permission_denied" in json.dumps(exc_info.value.detail)
    assert "You do not have access" in json.dumps(exc_info.value.detail)


@pytest.mark.asyncio
async def test_receive_input_event_bus_exception(mock_uow):
    """Test handling event bus exceptions."""
    # Unpack mocks
    mock_context, mock_conv_repo, mock_ws_repo = mock_uow

    # Mock conversation and workspace
    mock_conversation = Conversation(
        id="test-conv-id",
        workspace_id="test-ws-id",
        topic="Test Conversation",
        participant_ids=["user123"],
    )
    mock_conv_repo.get_by_id = AsyncMock(return_value=mock_conversation)

    mock_workspace = Workspace(
        id="test-ws-id",
        name="Test Workspace",
        description="Test workspace description",
        owner_id="user123",  # User is the owner
    )
    mock_ws_repo.get_by_id = AsyncMock(return_value=mock_workspace)

    # Create request
    request = InputRequest(conversation_id="test-conv-id", content="Hello, world!", streaming=True)

    # Mock background tasks
    mock_background = Mock()

    # Mock current user
    current_user = {"user_id": "user123", "name": "Test User"}

    # Mock dependencies
    with (
        patch("app.api.input.UnitOfWork.for_transaction", return_value=mock_context),
        patch("app.api.input.event_bus.publish", side_effect=Exception("Event bus error")),
        pytest.raises(EventBusException) as exc_info,
    ):
        # Call the endpoint - this will raise EventBusException internally
        # which is NOT converted to HTTPException (it's re-raised directly)
        await receive_input(request, mock_background, current_user)

    # Verify the exception
    assert str(exc_info.value) == "Failed to publish input event"
    assert exc_info.value.details == {"conversation_id": "test-conv-id"}


@pytest.mark.asyncio
async def test_receive_input_with_streaming_param(mock_uow):
    """Test receiving input with a streaming parameter."""
    # Unpack mocks
    mock_context, mock_conv_repo, mock_ws_repo = mock_uow

    # Mock conversation and workspace
    mock_conversation = Conversation(
        id="test-conv-id",
        workspace_id="test-ws-id",
        topic="Test Conversation",
        participant_ids=["user123"],
    )
    mock_conv_repo.get_by_id = AsyncMock(return_value=mock_conversation)

    mock_workspace = Workspace(
        id="test-ws-id", name="Test Workspace", description="Test workspace description", owner_id="owner123"
    )
    mock_ws_repo.get_by_id = AsyncMock(return_value=mock_workspace)

    # Create request with streaming=False
    request = InputRequest(
        conversation_id="test-conv-id",
        content="Hello, world!",
        metadata={},
        streaming=False,  # Explicitly set streaming to False
    )

    # Mock background tasks
    mock_background = Mock()

    # Mock current user
    current_user = {"user_id": "user123", "name": "Test User"}

    # Mock dependencies
    with (
        patch("app.api.input.UnitOfWork.for_transaction", return_value=mock_context),
        patch("app.api.input.event_bus.publish", new_callable=AsyncMock),
        patch("app.api.input.response_handler.handle_message") as mock_handle_message,
    ):
        # Call the endpoint
        response = await receive_input(request, mock_background, current_user)

        # Verify the response
        assert response.status == "received"

        # Verify the background task was added with streaming=False
        mock_background.add_task.assert_called_once_with(
            mock_handle_message,
            user_id="user123",
            conversation_id="test-conv-id",
            message_content="Hello, world!",
            metadata={},
            streaming=False,  # Should pass False
        )
