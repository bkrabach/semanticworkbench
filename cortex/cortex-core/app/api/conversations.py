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

from app.database.connection import get_db
from app.database.models import User, Workspace, Conversation
from app.api.auth import get_current_user
from app.utils.logger import logger
from app.api.sse import send_event_to_conversation, send_event_to_workspace

router = APIRouter()

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
    db: Session = Depends(get_db)
):
    """
    List conversations in a workspace

    Args:
        workspace_id: Workspace ID
        limit: Maximum number of conversations to return
        offset: Number of conversations to skip
        user: Authenticated user
        db: Database session

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
    conversations = db.query(Conversation).filter(
        Conversation.workspace_id == workspace_id
    ).order_by(
        Conversation.last_active_at_utc.desc()
    ).offset(offset).limit(limit).all()
    
    # Process each conversation to handle the JSON fields
    processed_conversations = []
    for conversation in conversations:
        # Parse JSON strings to dictionaries
        meta_data_str = str(conversation.meta_data) if conversation.meta_data else "{}"
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


@router.post("/workspaces/{workspace_id}/conversations", response_model=ConversationResponse)
async def create_conversation(
    workspace_id: str,
    conversation: ConversationCreate,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new conversation in a workspace

    Args:
        workspace_id: Workspace ID
        conversation: Conversation data
        background_tasks: FastAPI background tasks
        user: Authenticated user
        db: Database session

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

    # Create new conversation with timezone-aware UTC datetime
    now = datetime.now(timezone.utc)
    metadata = conversation.metadata or {}

    # Convert metadata to JSON string
    metadata_json = json.dumps(metadata)

    new_conversation = Conversation(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        title=conversation.title,
        modality=conversation.modality,
        created_at_utc=now,
        last_active_at_utc=now,
        entries="[]",
        meta_data=metadata_json
    )

    db.add(new_conversation)
    db.commit()
    db.refresh(new_conversation)

    # Update workspace last_active_at_utc
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if workspace:
        workspace.last_active_at_utc = now
        db.commit()

    # Send SSE event for the new conversation in the background
    background_tasks.add_task(
        send_event_to_workspace,
        workspace_id,
        "conversation_created",
        {
            "id": new_conversation.id,
            "title": new_conversation.title,
            "modality": new_conversation.modality,
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
    db: Session = Depends(get_db)
):
    """
    Get conversation details

    Args:
        conversation_id: Conversation ID
        user: Authenticated user
        db: Database session

    Returns:
        Conversation details
    """
    # Get conversation with access check
    conversation = db.query(Conversation).join(Workspace).filter(
        Conversation.id == conversation_id,
        Workspace.user_id == user.id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Parse JSON strings and return validated model
    metadata = {}
    if conversation.meta_data is not None:
        try:
            meta_data_str = str(conversation.meta_data)
            if meta_data_str and meta_data_str != "{}":
                metadata = json.loads(meta_data_str)
        except (json.JSONDecodeError, TypeError):
            pass
            
    return ConversationResponse.model_validate({
        "id": conversation.id,
        "title": conversation.title,
        "modality": conversation.modality,
        "workspace_id": conversation.workspace_id,
        "created_at": conversation.created_at_utc,
        "last_active_at": conversation.last_active_at_utc,
        "metadata": metadata
    })


@router.put("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    update_data: ConversationUpdate,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update conversation details

    Args:
        conversation_id: Conversation ID
        update_data: Updated conversation data
        background_tasks: FastAPI background tasks
        user: Authenticated user
        db: Database session

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

    # Update conversation fields
    if update_data.title is not None:
        conversation.title = update_data.title

    if update_data.metadata is not None:
        # Parse existing metadata
        try:
            existing_metadata = json.loads(conversation.meta_data)
        except json.JSONDecodeError:
            existing_metadata = {}

        # Update with new metadata
        existing_metadata.update(update_data.metadata)
        conversation.meta_data = json.dumps(existing_metadata)

    # Update last_active_at_utc with timezone-aware UTC datetime
    conversation.last_active_at_utc = datetime.now(timezone.utc)

    db.commit()
    db.refresh(conversation)

    # Parse metadata for the event
    metadata = json.loads(conversation.meta_data) if conversation.meta_data else {}
    
    # Send SSE event for conversation update in the background
    background_tasks.add_task(
        send_event_to_conversation,
        conversation_id,
        "conversation_update",
        {
            "id": conversation.id,
            "title": conversation.title,
            "last_active_at_utc": conversation.last_active_at_utc.isoformat(),
            "metadata": metadata
        }
    )

    # Parse JSON strings and return validated model
    return ConversationResponse.model_validate({
        "id": conversation.id,
        "title": conversation.title,
        "modality": conversation.modality,
        "workspace_id": conversation.workspace_id,
        "created_at": conversation.created_at_utc,
        "last_active_at": conversation.last_active_at_utc,
        "metadata": metadata
    })


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a conversation

    Args:
        conversation_id: Conversation ID
        background_tasks: FastAPI background tasks
        user: Authenticated user
        db: Database session

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

    # Delete the conversation
    db.delete(conversation)
    db.commit()

    # Send SSE event for conversation deletion in the background
    background_tasks.add_task(
        send_event_to_workspace,
        workspace_id,
        "conversation_deleted",
        {
            "id": conversation_id
        }
    )

    return {"message": "Conversation deleted successfully"}


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get messages in a conversation

    Args:
        conversation_id: Conversation ID
        limit: Maximum number of messages to return
        offset: Number of messages to skip
        user: Authenticated user
        db: Database session

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

    # Parse entries from conversation
    try:
        entries = json.loads(conversation.entries)
    except json.JSONDecodeError:
        entries = []

    # Apply pagination (reversing to get newest first, then reversing back)
    entries.reverse()
    paginated_entries = entries[offset:offset+limit]
    paginated_entries.reverse()  # Back to chronological order

    # Convert entries to response format
    messages = []
    for entry in paginated_entries:
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


@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse)
async def add_message(
    conversation_id: str,
    message: MessageCreate,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add a message to a conversation

    Args:
        conversation_id: Conversation ID
        message: Message data
        background_tasks: FastAPI background tasks
        user: Authenticated user
        db: Database session

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

    # Create new message with timezone-aware UTC datetime
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
        entries = json.loads(conversation.entries)
    except json.JSONDecodeError:
        entries = []

    entries.append(new_entry)

    # Update conversation - use custom encoder for datetime objects
    conversation.entries = json.dumps(entries, cls=DateTimeEncoder)
    conversation.last_active_at_utc = now

    db.commit()

    # Send SSE event for the new message in the background
    background_tasks.add_task(
        send_event_to_conversation,
        conversation_id,
        "message_received",
        {
            "id": message_id,
            "content": message.content,
            "role": message.role,
            "created_at_utc": now.isoformat(),  # Convert to ISO string for transport
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
            conversation_id,
            message.content,
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
        entries = json.loads(conversation.entries)
    except json.JSONDecodeError:
        entries = []

    entries.append(new_entry)

    # Update conversation - use custom encoder for datetime objects
    conversation.entries = json.dumps(entries, cls=DateTimeEncoder)
    conversation.last_active_at_utc = now

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
        workspace_id=conversation.workspace_id,
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
    # Get conversation to get workspace_id
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()
    
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
        workspace_id=conversation.workspace_id,
        db=db
    )
    
    if success:
        logger.info(f"Message received for conversation {conversation_id}")
    else:
        logger.error(f"Failed to process message for conversation {conversation_id}")


def generate_demo_response(user_message: str) -> str:
    """
    Generate a simple demo response based on user input

    Args:
        user_message: Message from user

    Returns:
        Generated response
    """
    user_message = user_message.lower()

    if "hello" in user_message or "hi" in user_message:
        return "Hello! How can I help you today?"

    if "how are you" in user_message:
        return "I'm functioning well, thank you for asking! What can I assist you with today?"

    if "help" in user_message:
        return "I'd be happy to help. Could you provide more details about what you need assistance with?"

    if "thank" in user_message:
        return "You're welcome! Is there anything else I can help you with?"

    if "bye" in user_message or "goodbye" in user_message:
        return "Goodbye! Feel free to reach out if you need anything else."

    # Default response
    return "I've received your message. Is there anything specific you'd like to know or discuss?"
