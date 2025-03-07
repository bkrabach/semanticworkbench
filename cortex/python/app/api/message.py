"""
Message API Routes

This module defines API routes for message processing, including sending messages,
getting message history, and handling message-related operations.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.components.context_manager import context_manager
from app.components.message_handler import MessageResponse, process_message
from app.components.security_manager import security_manager
from app.utils.logger import get_contextual_logger

# Configure logger
logger = get_contextual_logger("api.message")

# Create router
router = APIRouter(
    prefix="/messages",
    tags=["messages"],
    responses={404: {"description": "Not found"}},
)


class MessageRequest(BaseModel):
    """Request model for sending a message"""

    content: str = Field(..., description="Message content")
    role: str = Field("user", description="Message role (user, system, assistant)")
    session_id: Optional[uuid.UUID] = Field(None, description="Session ID")
    workspace_id: Optional[uuid.UUID] = Field(None, description="Workspace ID")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Message metadata"
    )

    class Config:
        schema_extra = {
            "example": {
                "content": "Hello, how can you assist me today?",
                "role": "user",
                "metadata": {"source": "web_client", "client_version": "1.0.0"},
            }
        }


class MessageHistoryResponse(BaseModel):
    """Response model for getting message history"""

    messages: List[Dict[str, Any]] = Field(..., description="List of messages")
    session_id: uuid.UUID = Field(..., description="Session ID")
    workspace_id: uuid.UUID = Field(..., description="Workspace ID")
    count: int = Field(..., description="Number of messages")
    has_more: bool = Field(False, description="Whether there are more messages")

    class Config:
        schema_extra = {
            "example": {
                "messages": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "content": "Hello, how can you assist me today?",
                        "role": "user",
                        "timestamp": "2025-03-06T15:30:45.123456",
                        "metadata": {"source": "web_client"},
                    },
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440001",
                        "content": "I can help with many tasks! What would you like to do?",
                        "role": "assistant",
                        "timestamp": "2025-03-06T15:30:46.123456",
                        "metadata": {},
                    },
                ],
                "session_id": "550e8400-e29b-41d4-a716-446655440002",
                "workspace_id": "550e8400-e29b-41d4-a716-446655440003",
                "count": 2,
                "has_more": False,
            }
        }


@router.post(
    "",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a message",
    description="Send a message to be processed by the system",
)
async def send_message(message: MessageRequest) -> MessageResponse:
    """
    Send a message to be processed

    Args:
        message: Message request

    Returns:
        Message response
    """
    try:
        logger.info(f"Received message from role {message.role}")

        # Process the message
        response = await process_message(
            content=message.content,
            role=message.role,
            session_id=message.session_id,
            workspace_id=message.workspace_id,
            metadata=message.metadata,
        )

        return response

    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing message: {str(e)}",
        )


@router.get(
    "",
    response_model=MessageHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get message history",
    description="Get message history for a session and workspace",
)
async def get_message_history(
    session_id: uuid.UUID,
    workspace_id: uuid.UUID,
    limit: int = Query(50, description="Maximum number of messages to return"),
    offset: int = Query(0, description="Number of messages to skip"),
) -> MessageHistoryResponse:
    """
    Get message history for a session and workspace

    Args:
        session_id: Session ID
        workspace_id: Workspace ID
        limit: Maximum number of messages to return
        offset: Number of messages to skip

    Returns:
        Message history response
    """
    try:
        logger.info(
            f"Getting message history for session {session_id}, workspace {workspace_id}"
        )

        # Get context for this session and workspace
        context = await context_manager.get_context(
            session_id=session_id,
            workspace_id=workspace_id,
        )

        # Get messages from context
        all_messages = context.messages
        total_count = len(all_messages)

        # Apply pagination
        end_index = min(offset + limit, total_count)
        paged_messages = all_messages[offset:end_index] if offset < total_count else []

        # Convert messages to dict format
        message_dicts = [
            {
                "id": msg.id,
                "content": msg.content,
                "role": msg.role,
                "timestamp": msg.timestamp.isoformat(),
                "metadata": msg.metadata,
            }
            for msg in paged_messages
        ]

        # Determine if there are more messages
        has_more = end_index < total_count

        # Create response
        response = MessageHistoryResponse(
            messages=message_dicts,
            session_id=session_id,
            workspace_id=workspace_id,
            count=len(message_dicts),
            has_more=has_more,
        )

        return response

    except Exception as e:
        logger.error(f"Error getting message history: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting message history: {str(e)}",
        )


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear message history",
    description="Clear message history for a session and workspace",
)
async def clear_message_history(
    session_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> None:
    """
    Clear message history for a session and workspace

    Args:
        session_id: Session ID
        workspace_id: Workspace ID
    """
    try:
        logger.info(
            f"Clearing message history for session {session_id}, workspace {workspace_id}"
        )

        # Get context for this session and workspace
        context = await context_manager.get_context(
            session_id=session_id,
            workspace_id=workspace_id,
        )

        # Prune all messages from context
        await context_manager.prune_context(
            session_id=session_id,
            workspace_id=workspace_id,
        )

    except Exception as e:
        logger.error(f"Error clearing message history: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error clearing message history: {str(e)}",
        )


@router.delete(
    "/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a message",
    description="Delete a specific message from history",
)
async def delete_message(
    message_id: str,
    session_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> None:
    """
    Delete a specific message from history

    Args:
        message_id: Message ID to delete
        session_id: Session ID
        workspace_id: Workspace ID
    """
    try:
        logger.info(
            f"Deleting message {message_id} from session {session_id}, workspace {workspace_id}"
        )

        # Update context to remove the message
        from app.components.context_manager import ContextUpdate

        await context_manager.update_context(
            session_id=session_id,
            workspace_id=workspace_id,
            context_update=ContextUpdate(remove_message_ids=[message_id]),
        )

    except Exception as e:
        logger.error(f"Error deleting message: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting message: {str(e)}",
        )
