"""
Conversation API endpoints for Cortex Core
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid
from datetime import datetime, timezone
import json
import asyncio

from app.utils.json_helpers import DateTimeEncoder
from app.exceptions import (
    ResourceNotFoundError
)

from app.database.connection import get_db
from app.database.models import User, Workspace, Conversation
from app.database.repositories import ConversationRepository, get_conversation_repository
from app.api.auth import get_current_user
from app.utils.logger import logger
from app.api.sse import send_event_to_conversation, send_event_to_workspace

router = APIRouter()

# Dependencies

def get_repository(db: Session = Depends(get_db)) -> ConversationRepository:
    """Get the conversation repository"""
    return get_conversation_repository(db)

# Request and response models


class ConversationCreate(BaseModel):
    """Conversation creation model"""
    title: str
    modality: str
    metadata: Optional[Dict[str, Any]] = None


class ConversationUpdate(BaseModel):
    """Conversation update model"""
    title: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class MessageCreate(BaseModel):
    """Message creation model"""
    content: str
    role: str = "user"
    metadata: Optional[Dict[str, Any]] = None


class MessageResponse(BaseModel):
    """Message response model"""
    id: str
    content: str
    role: str
    created_at_utc: datetime  # UTC timestamp for message creation
    metadata: Optional[Dict[str, Any]] = None

    model_config = {
        "json_encoders": {
            # Ensure datetime is serialized to ISO format
            datetime: lambda dt: dt.isoformat()
        }
    }


class ConversationResponse(BaseModel):
    """Conversation response model"""
    id: str
    title: str
    modality: str
    workspace_id: str
    created_at: datetime
    last_active_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = {
        "from_attributes": True,
        "json_encoders": {
            # Ensure datetime is serialized to ISO format
            datetime: lambda dt: dt.isoformat()
        }
    }


@router.get("/workspaces/{workspace_id}/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    workspace_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    repository: ConversationRepository = Depends(get_repository)
):
    """
    List conversations in a workspace

    Args:
        workspace_id: Workspace ID
        limit: Maximum number of conversations to return
        offset: Number of conversations to skip
        user: Authenticated user
        db: Database session
        repository: Conversation repository

    Returns:
        List of conversations
    """
    # Verify workspace exists and belongs to user
    workspace = db.query(Workspace).filter(
        Workspace.id == workspace_id,
        Workspace.user_id == user.id
    ).first()

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Get conversations for the workspace
    conversations = repository.get_conversations_by_workspace(workspace_id, limit, offset)

    # Process each conversation to handle the JSON fields
    processed_conversations = []
    for conversation in conversations:
        # Parse JSON strings to dictionaries
        meta_data_value = getattr(conversation, 'meta_data')
        meta_data_str = str(meta_data_value) if meta_data_value is not None else "{}"
        try:
            metadata = json.loads(meta_data_str)
        except json.JSONDecodeError:
            metadata = {}

        conversation_dict = {
            "id": str(conversation.id),
            "title": str(conversation.title),
            "modality": str(conversation.modality),
            "workspace_id": str(conversation.workspace_id),
            "created_at": conversation.created_at_utc,
            "last_active_at": conversation.last_active_at_utc,
            "metadata": metadata
        }
        processed_conversations.append(ConversationResponse.model_validate(conversation_dict))

    return processed_conversations


@router.post("/workspaces/{workspace_id}/conversations", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    workspace_id: str,
    conversation: ConversationCreate,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    repository: ConversationRepository = Depends(get_repository)
):
    """
    Create a new conversation in a workspace

    Args:
        workspace_id: Workspace ID
        conversation: Conversation data
        background_tasks: FastAPI background tasks
        user: Authenticated user
        db: Database session
        repository: Conversation repository

    Returns:
        Newly created conversation
    """
    # Verify workspace exists and belongs to user
    workspace = db.query(Workspace).filter(
        Workspace.id == workspace_id,
        Workspace.user_id == user.id
    ).first()

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Create conversation using repository
    new_conversation = repository.create_conversation(
        workspace_id=workspace_id,
        title=conversation.title,
        modality=conversation.modality,
        metadata=conversation.metadata or {}
    )

    # Send SSE event for the new conversation in the background
    background_tasks.add_task(
        send_event_to_workspace,
        str(workspace_id),
        "conversation_created",
        {
            "id": str(new_conversation.id),
            "title": str(new_conversation.title),
            "modality": str(new_conversation.modality),
            "created_at_utc": new_conversation.created_at_utc.isoformat()
        }
    )

    # Parse JSON strings and return validated model
    metadata = {}
    if new_conversation.meta_data is not None:
        try:
            meta_data_str = str(new_conversation.meta_data)
            if meta_data_str and meta_data_str != "{}":
                metadata = json.loads(meta_data_str)
        except (json.JSONDecodeError, TypeError):
            pass

    return ConversationResponse.model_validate({
        "id": new_conversation.id,
        "title": new_conversation.title,
        "modality": new_conversation.modality,
        "workspace_id": new_conversation.workspace_id,
        "created_at": new_conversation.created_at_utc,
        "last_active_at": new_conversation.last_active_at_utc,
        "metadata": metadata
    })


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    repository: ConversationRepository = Depends(get_repository)
):
    """
    Get conversation details

    Args:
        conversation_id: Conversation ID
        user: Authenticated user
        db: Database session
        repository: Conversation repository

    Returns:
        Conversation details
    """
    # Get conversation with access check (still need to do join across tables for access check)
    conversation = db.query(Conversation).join(Workspace).filter(
        Conversation.id == conversation_id,
        Workspace.user_id == user.id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Get conversation details using repository
    conversation = repository.get_conversation_by_id(conversation_id)

    # Parse JSON strings and return validated model
    metadata = {}
    if conversation is not None and getattr(conversation, 'meta_data', None) is not None:
        try:
            meta_data_str = str(conversation.meta_data)
            if meta_data_str and meta_data_str != "{}":
                metadata = json.loads(meta_data_str)
        except (json.JSONDecodeError, TypeError):
            pass

    if conversation is None:
        raise ResourceNotFoundError(
            detail="Conversation not found",
            resource_type="conversation",
            resource_id=conversation_id
        )

    return ConversationResponse.model_validate({
        "id": conversation.id,
        "title": conversation.title,
        "modality": conversation.modality,
        "workspace_id": conversation.workspace_id,
        "created_at": conversation.created_at_utc,
        "last_active_at": conversation.last_active_at_utc,
        "metadata": metadata
    })


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    update_data: ConversationUpdate,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    repository: ConversationRepository = Depends(get_repository)
):
    """
    Update conversation details

    Args:
        conversation_id: Conversation ID
        update_data: Updated conversation data
        background_tasks: FastAPI background tasks
        user: Authenticated user
        db: Database session
        repository: Conversation repository

    Returns:
        Updated conversation
    """
    # Get conversation with access check
    conversation = db.query(Conversation).join(Workspace).filter(
        Conversation.id == conversation_id,
        Workspace.user_id == user.id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Update conversation using repository
    updated_conversation = repository.update_conversation(
        conversation_id=conversation_id,
        title=update_data.title,
        metadata=update_data.metadata
    )

    # Parse metadata for the event
    meta_data_value = getattr(updated_conversation, 'meta_data')
    meta_data_str = str(meta_data_value) if meta_data_value is not None else "{}"
    try:
        metadata = json.loads(meta_data_str)
    except json.JSONDecodeError:
        metadata = {}

    # Send SSE event for conversation update in the background
    background_tasks.add_task(
        send_event_to_conversation,
        str(conversation_id),
        "conversation_update",
        {
            "id": str(getattr(updated_conversation, 'id')),
            "title": str(getattr(updated_conversation, 'title')),
            "last_active_at_utc": getattr(updated_conversation, 'last_active_at_utc').isoformat(),
            "metadata": metadata
        }
    )

    # Check if conversation was updated successfully
    if updated_conversation is None:
        raise ResourceNotFoundError(
            detail="Conversation not found or could not be updated",
            resource_type="conversation",
            resource_id=conversation_id
        )

    # Parse JSON strings and return validated model
    return ConversationResponse.model_validate({
        "id": updated_conversation.id,
        "title": updated_conversation.title,
        "modality": updated_conversation.modality,
        "workspace_id": updated_conversation.workspace_id,
        "created_at": updated_conversation.created_at_utc,
        "last_active_at": updated_conversation.last_active_at_utc,
        "metadata": metadata
    })


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    repository: ConversationRepository = Depends(get_repository)
):
    """
    Delete a conversation

    Args:
        conversation_id: Conversation ID
        background_tasks: FastAPI background tasks
        user: Authenticated user
        db: Database session
        repository: Conversation repository

    Returns:
        Success message
    """
    # Get conversation with access check and workspace information
    conversation = db.query(Conversation).join(Workspace).filter(
        Conversation.id == conversation_id,
        Workspace.user_id == user.id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    workspace_id = conversation.workspace_id

    # Delete the conversation using repository
    success = repository.delete_conversation(conversation_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete conversation")

    # Send SSE event for conversation deletion in the background
    background_tasks.add_task(
        send_event_to_workspace,
        str(workspace_id),
        "conversation_deleted",
        {
            "id": str(conversation_id)
        }
    )

    return {"message": "Conversation deleted successfully"}


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    repository: ConversationRepository = Depends(get_repository)
):
    """
    Get messages in a conversation

    Args:
        conversation_id: Conversation ID
        limit: Maximum number of messages to return
        offset: Number of messages to skip
        user: Authenticated user
        db: Database session
        repository: Conversation repository

    Returns:
        List of messages
    """
    # Verify conversation exists and belongs to user
    conversation = db.query(Conversation).join(Workspace).filter(
        Conversation.id == conversation_id,
        Workspace.user_id == user.id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Get messages using repository
    entries = repository.get_messages(conversation_id, limit, offset)

    # Convert entries to response format
    messages = []
    for entry in entries:
        # Get timestamp from created_at_utc field or use current UTC time
        timestamp = entry.get("created_at_utc", datetime.now(timezone.utc))

        # Convert string timestamps to datetime objects if needed
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp)
            except ValueError:
                # If parsing fails, use current timezone-aware UTC datetime
                timestamp = datetime.now(timezone.utc)

        messages.append(MessageResponse(
            id=entry.get("id", ""),
            content=entry.get("content", ""),
            role=entry.get("role", ""),
            created_at_utc=timestamp,
            metadata=entry.get("metadata", {})
        ))

    return messages


@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse, status_code=201)
async def add_message(
    conversation_id: str,
    message: MessageCreate,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    repository: ConversationRepository = Depends(get_repository)
):
    """
    Add a message to a conversation

    Args:
        conversation_id: Conversation ID
        message: Message data
        background_tasks: FastAPI background tasks
        user: Authenticated user
        db: Database session
        repository: Conversation repository

    Returns:
        Newly created message
    """
    # Verify conversation exists and belongs to user
    conversation = db.query(Conversation).join(Workspace).filter(
        Conversation.id == conversation_id,
        Workspace.user_id == user.id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Create message using repository
    entry = repository.add_message(
        conversation_id=conversation_id,
        content=message.content,
        role=message.role,
        metadata=message.metadata
    )

    if not entry:
        raise HTTPException(status_code=500, detail="Failed to add message")

    # For serialization in the event
    message_id = entry["id"]
    now = datetime.fromisoformat(entry["created_at_utc"]) if isinstance(entry["created_at_utc"], str) else entry["created_at_utc"]

    # Send SSE event for the new message in the background
    background_tasks.add_task(
        send_event_to_conversation,
        str(conversation_id),
        "message_received",
        {
            "id": str(message_id),
            "content": str(message.content),
            "role": str(message.role),
            "created_at_utc": now.isoformat() if isinstance(now, datetime) else now,
            "metadata": message.metadata or {}
        }
    )

    # Create response
    response = MessageResponse(
        id=message_id,
        content=message.content,
        role=message.role,
        created_at_utc=now,
        metadata=message.metadata
    )

    # If this is a user message, simulate assistant response
    if message.role == "user":
        # This would typically be handled by your LLM integration
        # For demo purposes, we'll simulate response generation in a background task
        background_tasks.add_task(
            simulate_assistant_response,
            str(conversation_id),
            str(message.content),
            db
        )

    return response


@router.post("/conversations/{conversation_id}/messages/stream")
async def stream_message(
    conversation_id: str,
    message: MessageCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send a message and stream the response

    Args:
        conversation_id: Conversation ID
        message: Message data
        user: Authenticated user
        db: Database session

    Returns:
        Streaming response
    """
    # Verify conversation exists and belongs to user
    conversation = db.query(Conversation).join(Workspace).filter(
        Conversation.id == conversation_id,
        Workspace.user_id == user.id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Add user message to conversation with timezone-aware UTC datetime
    message_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # Create message entry
    new_entry = {
        "id": message_id,
        "content": message.content,
        "role": message.role,
        "created_at_utc": now,  # Store as datetime object
        "metadata": message.metadata or {}
    }

    # Parse and update entries
    try:
        entries = json.loads(str(getattr(conversation, 'entries')))
    except json.JSONDecodeError:
        entries = []

    entries.append(new_entry)

    # Update conversation - use custom encoder for datetime objects
    setattr(conversation, 'entries', json.dumps(entries, cls=DateTimeEncoder))
    setattr(conversation, 'last_active_at_utc', now)

    db.commit()

    # Send message_received event to all clients
    asyncio.create_task(send_event_to_conversation(
        conversation_id,
        "message_received",
        {
            "id": message_id,
            "content": message.content,
            "role": message.role,
            "created_at_utc": now.isoformat(),
            "metadata": message.metadata or {}
        }
    ))

    # We'll handle the typing indicator in the response generator

    # Get the conversation to get workspace_id
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Set up the input receiver and output publisher for this conversation
    from app.components.conversation_channels import ConversationInputReceiver, get_conversation_publisher

    # Ensure there's an output publisher for this conversation
    await get_conversation_publisher(conversation_id)

    # Create input receiver to send message to the router
    input_receiver = ConversationInputReceiver(conversation_id)

    # Send the message to the router (fire and forget)
    await input_receiver.receive_input(
        content=message.content,
        workspace_id=str(getattr(conversation, 'workspace_id')),
        metadata=message.metadata,
        db=db
    )

    # This is the generator function that will handle streaming
    # Note: The actual content will come from the router via the event system later
    async def stream_response():
        """Generator function for client streaming interface"""
        message_id = str(uuid.uuid4())

        # Simulate initial role message for the client
        yield f"data: {json.dumps({'choices': [{'delta': {'role': 'assistant'}}]})}\n\n"

        # For now, we'll simulate the streaming content here
        # In a real implementation, we'd get this from the router
        await asyncio.sleep(0.5)

        # Send "thinking" message
        yield f"data: {json.dumps({'choices': [{'delta': {'content': '...'}, 'index': 0}]})}\n\n"

        # Keep the connection open for a bit to demonstrate
        # that the router will respond asynchronously
        await asyncio.sleep(1)

        # Indicate that the client should wait for server-sent events
        yield f"data: {json.dumps({'choices': [{'delta': {'content': ' [Waiting for response...]'}, 'index': 0}]})}\n\n"

        # Send end of stream
        final_data = {
            "id": message_id,
            "created": int(datetime.now(timezone.utc).timestamp()),
            "model": "simulation",
            "choices": [{"delta": {}, "finish_reason": "listen_for_sse", "index": 0}]
        }
        yield f"data: {json.dumps(final_data)}\n\n"

    # Return streaming response
    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# Helper functions

async def simulate_assistant_response(conversation_id: str, user_message: str, db: Session):
    """
    Send a message to the Cortex Router for processing

    Args:
        conversation_id: Conversation ID
        user_message: Message from user
        db: Database session
    """
    # Get repository
    repository = get_conversation_repository(db)

    # Get conversation to get workspace_id
    conversation = repository.get_conversation_by_id(conversation_id)

    if not conversation:
        logger.warning(f"Conversation {conversation_id} not found")
        return

    # Ensure there's an output publisher and input receiver for this conversation
    from app.components.conversation_channels import ConversationInputReceiver, get_conversation_publisher

    # Set up the output publisher
    await get_conversation_publisher(conversation_id)

    # Create or get an input receiver
    input_receiver = ConversationInputReceiver(conversation_id)

    # Send the message to the router via the input receiver
    success = await input_receiver.receive_input(
        content=user_message,
        workspace_id=str(getattr(conversation, 'workspace_id')),
        db=db
    )

    if success:
        logger.info(f"Message received for conversation {conversation_id}")
    else:
        logger.error(f"Failed to process message for conversation {conversation_id}")


