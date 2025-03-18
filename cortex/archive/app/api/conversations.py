"""
Conversation API endpoints for Cortex Core.

This module provides the API endpoints for managing conversations,
following the domain-driven repository architecture pattern.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, timezone

from app.models.domain.user import User
from app.models.api.request.conversation import (
    CreateConversationRequest,
    AddMessageRequest,
    UpdateTitleRequest,
    UpdateMetadataRequest,
)
from app.models.api.response.conversation import (
    ConversationSummaryResponse,
    ConversationDetailResponse,
    ConversationListResponse,
    MessageResponse,
)
from app.services.conversation_service import ConversationService, get_conversation_service
from app.api.auth import get_current_user
from app.models.domain.user import UserInfo

router = APIRouter()


@router.get("/workspaces/{workspace_id}/conversations", response_model=ConversationListResponse)
async def list_conversations(
    workspace_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    """
    List conversations in a workspace.

    This endpoint demonstrates the domain-driven repository pattern by:
    1. Using the service layer to handle business logic
    2. Converting domain models to API response models
    3. Maintaining a clean separation between layers

    Args:
        workspace_id: Workspace ID
        limit: Maximum number of conversations to return
        offset: Number of conversations to skip
        user: Authenticated user
        service: Conversation service

    Returns:
        List of conversations
    """
    # Verify workspace access (in a real implementation, this would be handled by a workspace service)
    # For now, we'll just proceed with the current user's permissions

    # User is already validated through the dependency

    # Get conversations from the service
    conversations = await service.get_workspace_conversations(workspace_id)

    # Convert domain models to API response models
    conversation_summaries = [
        ConversationSummaryResponse(
            id=conversation.id,
            title=conversation.title,
            workspace_id=conversation.workspace_id,
            modality=conversation.modality,
            created_at=conversation.created_at,
            last_active_at=conversation.last_active_at,
            metadata=conversation.metadata,
            message_count=len(conversation.messages),
        )
        for conversation in conversations
    ]

    # Create and return the list response
    return ConversationListResponse(conversations=conversation_summaries, count=len(conversation_summaries))


@router.post("/workspaces/{workspace_id}/conversations", response_model=ConversationDetailResponse, status_code=201)
async def create_conversation(
    workspace_id: str,
    conversation_request: CreateConversationRequest,
    user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    """
    Create a new conversation in a workspace.

    This endpoint demonstrates the domain-driven repository pattern by:
    1. Converting API request models to service parameters
    2. Using the service layer to handle business logic and events
    3. Converting the resulting domain model to an API response model

    Args:
        workspace_id: Workspace ID
        conversation_request: API request model with conversation data
        user: Authenticated user
        service: Conversation service

    Returns:
        Newly created conversation
    """
    # Verify workspace access (in a real implementation, this would be handled by a workspace service)
    # For now, we'll just proceed with the current user's permissions

    # Convert User domain model to UserInfo domain model for the service
    user_info = UserInfo(
        id=str(user.id),
        email=str(user.email),
        name=str(user.name) if user.name is not None else "",
        created_at=user.created_at if hasattr(user, "created_at") else datetime.now(timezone.utc),
    )

    # Create the conversation using the service
    # The service handles all business logic including event publishing
    conversation = await service.create_conversation(
        workspace_id=workspace_id,
        title=conversation_request.title,
        modality=conversation_request.modality,
        user_info=user_info,
        metadata=conversation_request.metadata or {},
    )

    # Convert domain model to API response model
    # This is where we transform from our internal representation to the external API contract
    return ConversationDetailResponse(
        id=conversation.id,
        title=conversation.title,
        workspace_id=conversation.workspace_id,
        modality=conversation.modality,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        last_active_at=conversation.last_active_at,
        metadata=conversation.metadata,
        messages=[
            MessageResponse(
                id=message.id,
                content=message.content,
                role=message.role,
                created_at=message.created_at,
                metadata=message.metadata,
            )
            for message in conversation.messages
        ],
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    """
    Get conversation details.

    This endpoint demonstrates the domain-driven repository pattern by:
    1. Using the service layer to handle business logic and data access
    2. Converting the resulting domain model to an API response model
    3. Proper error handling with appropriate HTTP status codes

    Args:
        conversation_id: Conversation ID
        user: Authenticated user
        service: Conversation service

    Returns:
        Conversation details including messages
    """
    # Get the conversation using the service
    # Access control would ideally be handled at the service layer
    conversation = await service.get_conversation(conversation_id)

    # Handle not found case
    if conversation is None:
        raise HTTPException(status_code=404, detail=f"Conversation with ID {conversation_id} not found")

    # Convert domain model to API response model
    return ConversationDetailResponse(
        id=conversation.id,
        title=conversation.title,
        workspace_id=conversation.workspace_id,
        modality=conversation.modality,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        last_active_at=conversation.last_active_at,
        metadata=conversation.metadata,
        messages=[
            MessageResponse(
                id=message.id,
                content=message.content,
                role=message.role,
                created_at=message.created_at,
                metadata=message.metadata,
            )
            for message in conversation.messages
        ],
    )


@router.patch("/conversations/{conversation_id}/title", response_model=ConversationDetailResponse)
async def update_conversation_title(
    conversation_id: str,
    update_request: UpdateTitleRequest,
    user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    """
    Update conversation title.

    This endpoint demonstrates the domain-driven repository pattern by:
    1. Using specialized request models for different update operations
    2. Delegating business logic to the service layer
    3. Converting the resulting domain model to an API response model

    Args:
        conversation_id: Conversation ID
        update_request: Request with updated title
        user: Authenticated user
        service: Conversation service

    Returns:
        Updated conversation
    """
    # Update the conversation title using the service
    # The service handles all business logic including event publishing
    conversation = await service.update_title(conversation_id=conversation_id, title=update_request.title)

    # Handle not found case
    if conversation is None:
        raise HTTPException(status_code=404, detail=f"Conversation with ID {conversation_id} not found")

    # Convert domain model to API response model
    return ConversationDetailResponse(
        id=conversation.id,
        title=conversation.title,
        workspace_id=conversation.workspace_id,
        modality=conversation.modality,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        last_active_at=conversation.last_active_at,
        metadata=conversation.metadata,
        messages=[
            MessageResponse(
                id=message.id,
                content=message.content,
                role=message.role,
                created_at=message.created_at,
                metadata=message.metadata,
            )
            for message in conversation.messages
        ],
    )


@router.patch("/conversations/{conversation_id}/metadata", response_model=ConversationDetailResponse)
async def update_conversation_metadata(
    conversation_id: str,
    update_request: UpdateMetadataRequest,
    user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    """
    Update conversation metadata.

    Args:
        conversation_id: Conversation ID
        update_request: Request with updated metadata
        user: Authenticated user
        service: Conversation service

    Returns:
        Updated conversation
    """
    # Update the conversation metadata using the service
    conversation = await service.update_metadata(conversation_id=conversation_id, metadata=update_request.metadata)

    # Handle not found case
    if conversation is None:
        raise HTTPException(status_code=404, detail=f"Conversation with ID {conversation_id} not found")

    # Convert domain model to API response model
    return ConversationDetailResponse(
        id=conversation.id,
        title=conversation.title,
        workspace_id=conversation.workspace_id,
        modality=conversation.modality,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        last_active_at=conversation.last_active_at,
        metadata=conversation.metadata,
        messages=[
            MessageResponse(
                id=message.id,
                content=message.content,
                role=message.role,
                created_at=message.created_at,
                metadata=message.metadata,
            )
            for message in conversation.messages
        ],
    )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    """
    Delete a conversation.

    This endpoint demonstrates the domain-driven repository pattern by:
    1. Delegating business logic to the service layer
    2. Proper error handling with appropriate HTTP status codes
    3. Letting the service handle events and cleanup

    Args:
        conversation_id: Conversation ID
        user: Authenticated user
        service: Conversation service

    Returns:
        Success message
    """
    # Delete the conversation using the service
    # The service handles all business logic including event publishing
    success = await service.delete_conversation(conversation_id)

    # Handle failure case
    if success is False:
        raise HTTPException(
            status_code=404, detail=f"Conversation with ID {conversation_id} not found or could not be deleted"
        )

    # Return success response
    return {"message": "Conversation deleted successfully"}


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    conversation_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    """
    Get messages from a conversation.

    This endpoint demonstrates the domain-driven repository pattern by:
    1. Using pagination parameters for large result sets
    2. Using the service layer to handle business logic
    3. Converting domain models to API response models

    Args:
        conversation_id: Conversation ID
        limit: Maximum number of messages to return
        offset: Number of messages to skip
        user: Authenticated user
        service: Conversation service

    Returns:
        List of messages in the conversation
    """
    # Get the conversation to retrieve messages
    conversation = await service.get_conversation(conversation_id)

    # Handle not found case
    if conversation is None:
        raise HTTPException(status_code=404, detail=f"Conversation with ID {conversation_id} not found")

    # Apply pagination (in a real implementation, this would be more efficient)
    paginated_messages = conversation.messages[offset : offset + limit]

    # Convert domain models to API response models
    return [
        MessageResponse(
            id=message.id,
            content=message.content,
            role=message.role,
            created_at=message.created_at,
            metadata=message.metadata,
        )
        for message in paginated_messages
    ]


@router.post("/conversations/{conversation_id}/messages", status_code=200)
async def add_message(
    conversation_id: str,
    message_request: AddMessageRequest,
    user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    """
    Add a message to a conversation.

    Args:
        conversation_id: Conversation ID
        message_request: Message data
        user: Authenticated user
        service: Conversation service

    Returns:
        Newly created message
    """
    # Add the message using the service
    message = await service.add_message(
        conversation_id=conversation_id,
        content=message_request.content,
        role=message_request.role,
        metadata=message_request.metadata,
    )

    # Handle not found case
    if not message:
        raise HTTPException(status_code=404, detail=f"Conversation with ID {conversation_id} not found")

    # Create input message for router
    from app.components.cortex_router import get_router
    from app.interfaces.router import InputMessage, ChannelType
    import asyncio
    import uuid

    channel_id = f"conversation-{conversation_id}"
    
    # Create message with required conversation_id
    input_message = InputMessage(
        message_id=str(uuid.uuid4()),
        channel_id=channel_id,
        channel_type=ChannelType.CONVERSATION,
        content=message_request.content,
        user_id=str(user.id) if user.id else None,
        workspace_id=message.workspace_id,
        conversation_id=conversation_id,  # Required field
        timestamp=datetime.now(timezone.utc),
        metadata={"source": "api"}
    )

    # Get router and queue the message for processing
    router = get_router()
    asyncio.create_task(router.process_input(input_message))

    # Return acknowledgment
    return {
        "status": "message_received",
        "message_id": message.id,
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at.isoformat(),
        "metadata": message.metadata
    }

# The stream_message endpoint has been removed
# All messages are now routed through the CortexRouter
# Responses are delivered via SSE events
# This follows the desired architecture where:
# 1. Client sends message to add_message endpoint
# 2. Message is passed to CortexRouter
# 3. Router processes message and sends typing indicators
# 4. Router sends response via SSE events
