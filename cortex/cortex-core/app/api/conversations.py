"""
Conversation API endpoints for Cortex Core
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid
from datetime import datetime
import json
import asyncio

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


class ConversationResponse(BaseModel):
    """Conversation response model"""
    id: str
    title: str
    modality: str
    workspace_id: str
    created_at: datetime
    last_active_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        from_attributes = True  # Allow model creation from ORM objects


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
        Conversation.last_active_at.desc()
    ).offset(offset).limit(limit).all()
    
    # Process each conversation to handle the JSON fields
    processed_conversations = []
    for conversation in conversations:
        # Parse JSON strings to dictionaries
        metadata = json.loads(conversation.meta_data) if conversation.meta_data else {}
        
        conversation_dict = {
            "id": conversation.id,
            "title": conversation.title,
            "modality": conversation.modality,
            "workspace_id": conversation.workspace_id,
            "created_at": conversation.created_at,
            "last_active_at": conversation.last_active_at,
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

    # Create new conversation
    now = datetime.utcnow()
    metadata = conversation.metadata or {}

    # Convert metadata to JSON string
    metadata_json = json.dumps(metadata)

    new_conversation = Conversation(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        title=conversation.title,
        modality=conversation.modality,
        created_at=now,
        last_active_at=now,
        entries="[]",
        meta_data=metadata_json
    )

    db.add(new_conversation)
    db.commit()
    db.refresh(new_conversation)

    # Update workspace last_active_at
    workspace.last_active_at = now
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
            "created_at": new_conversation.created_at.isoformat()
        }
    )

    # Parse JSON strings and return validated model
    return ConversationResponse.model_validate({
        "id": new_conversation.id,
        "title": new_conversation.title,
        "modality": new_conversation.modality,
        "workspace_id": new_conversation.workspace_id,
        "created_at": new_conversation.created_at,
        "last_active_at": new_conversation.last_active_at,
        "metadata": json.loads(new_conversation.meta_data) if new_conversation.meta_data else {}
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
    return ConversationResponse.model_validate({
        "id": conversation.id,
        "title": conversation.title,
        "modality": conversation.modality,
        "workspace_id": conversation.workspace_id,
        "created_at": conversation.created_at,
        "last_active_at": conversation.last_active_at,
        "metadata": json.loads(conversation.meta_data) if conversation.meta_data else {}
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

    # Update last_active_at
    conversation.last_active_at = datetime.utcnow()

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
            "last_active_at": conversation.last_active_at.isoformat(),
            "metadata": metadata
        }
    )

    # Parse JSON strings and return validated model
    return ConversationResponse.model_validate({
        "id": conversation.id,
        "title": conversation.title,
        "modality": conversation.modality,
        "workspace_id": conversation.workspace_id,
        "created_at": conversation.created_at,
        "last_active_at": conversation.last_active_at,
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
        messages.append(MessageResponse(
            id=entry.get("id", ""),
            content=entry.get("content", ""),
            role=entry.get("role", ""),
            created_at=datetime.fromisoformat(
                entry.get("timestamp", datetime.utcnow().isoformat())),
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

    # Create new message
    message_id = str(uuid.uuid4())
    now = datetime.utcnow()

    # Create message entry
    new_entry = {
        "id": message_id,
        "content": message.content,
        "role": message.role,
        "created_at_utc": now.isoformat(),
        "metadata": message.metadata or {}
    }

    # Parse and update entries
    try:
        entries = json.loads(conversation.entries)
    except json.JSONDecodeError:
        entries = []

    entries.append(new_entry)

    # Update conversation
    conversation.entries = json.dumps(entries)
    conversation.last_active_at = now

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
            "created_at_utc": now.isoformat(),
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

    # If this is a user message, simulate assistant typing indicator
    if message.role == "user":
        background_tasks.add_task(
            send_event_to_conversation,
            conversation_id,
            "typing_indicator",
            {
                "isTyping": True,
                "role": "assistant"
            }
        )

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

    # Add user message to conversation
    message_id = str(uuid.uuid4())
    now = datetime.utcnow()

    # Create message entry
    new_entry = {
        "id": message_id,
        "content": message.content,
        "role": message.role,
        "created_at_utc": now.isoformat(),
        "metadata": message.metadata or {}
    }

    # Parse and update entries
    try:
        entries = json.loads(conversation.entries)
    except json.JSONDecodeError:
        entries = []

    entries.append(new_entry)

    # Update conversation
    conversation.entries = json.dumps(entries)
    conversation.last_active_at = now

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

    # Send typing indicator
    asyncio.create_task(send_event_to_conversation(
        conversation_id,
        "typing_indicator",
        {
            "isTyping": True,
            "role": "assistant"
        }
    ))

    # Stream the response
    async def response_generator():
        # This would typically be handled by your LLM integration
        # For demo purposes, we'll simulate a streaming response
        assistant_message_id = str(uuid.uuid4())
        assistant_content = ""

        # Simulate typing indicator
        yield f"data: {json.dumps({'choices': [{'delta': {'role': 'assistant'}}]})}\n\n"

        # Generate a simple echo response
        response_text = f"ECHO: {message.content}"
        logger.info(f"Streaming echo response for conversation {conversation_id}")
        
        # Wait 5 seconds to simulate processing time
        await asyncio.sleep(5)

        for chunk in response_text.split():
            # Wait a bit to simulate thinking/typing
            await asyncio.sleep(0.1)

            # Send the chunk
            assistant_content += chunk + " "
            chunk_data = {
                "id": assistant_message_id,
                "created": int(datetime.utcnow().timestamp()),
                "model": "simulation",
                "choices": [
                    {
                        "delta": {
                            "content": chunk + " "
                        },
                        "index": 0
                    }
                ]
            }
            yield f"data: {json.dumps(chunk_data)}\n\n"

        # Final chunk with stop reason
        final_data = {
            "id": assistant_message_id,
            "created": int(datetime.utcnow().timestamp()),
            "model": "simulation",
            "choices": [
                {
                    "delta": {},
                    "finish_reason": "stop",
                    "index": 0
                }
            ]
        }
        yield f"data: {json.dumps(final_data)}\n\n"

        # Save the assistant's message to the conversation
        # This would typically be done after full completion in a production system
        try:
            latest_conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()

            if latest_conversation:
                try:
                    latest_entries = json.loads(latest_conversation.entries)
                except json.JSONDecodeError:
                    latest_entries = []

                # Add assistant response
                assistant_entry = {
                    "id": assistant_message_id,
                    "content": assistant_content.strip(),
                    "role": "assistant",
                    "created_at_utc": datetime.utcnow().isoformat(),
                    "metadata": {}
                }

                latest_entries.append(assistant_entry)
                latest_conversation.entries = json.dumps(latest_entries)
                db.commit()

                # Send message_received event
                await send_event_to_conversation(
                    conversation_id,
                    "message_received",
                    {
                        "id": assistant_message_id,
                        "content": assistant_content.strip(),
                        "role": "assistant",
                        "created_at_utc": datetime.utcnow().isoformat()
                    }
                )

                # Turn off typing indicator
                await send_event_to_conversation(
                    conversation_id,
                    "typing_indicator",
                    {
                        "isTyping": False,
                        "role": "assistant"
                    }
                )

        except Exception as e:
            logger.error(f"Error saving assistant response: {e}")

    return StreamingResponse(
        response_generator(),
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
    Simulate an assistant response (for demo purposes only)
    In a real implementation, this would call your LLM service

    Args:
        conversation_id: Conversation ID
        user_message: Message from user
        db: Database session
    """
    # Make sure typing indicator is shown
    await send_event_to_conversation(
        conversation_id,
        "typing_indicator",
        {
            "isTyping": True,
            "role": "assistant"
        }
    )
    
    # Wait 5 seconds to simulate processing time
    logger.info(f"Waiting 5 seconds before sending echo response for conversation {conversation_id}")
    await asyncio.sleep(5)

    # Generate an echo response
    response_text = f"ECHO: {user_message}"
    logger.info(f"Generated echo response for conversation {conversation_id}: {response_text}")
    
    # Use the client's current local time for display consistency
    now = datetime.now().replace(tzinfo=None)

    # Get the conversation
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()

    if not conversation:
        # Conversation might have been deleted
        logger.warning(
            f"Conversation {conversation_id} not found for assistant response")
        return

    # Create message entry
    message_id = str(uuid.uuid4())
    now = datetime.utcnow()

    # Parse entries
    try:
        entries = json.loads(conversation.entries)
    except json.JSONDecodeError:
        entries = []

    # Add new entry
    new_entry = {
        "id": message_id,
        "content": response_text,
        "role": "assistant",
        "created_at_utc": now.isoformat(),
        "metadata": {}
    }

    entries.append(new_entry)

    # Update conversation
    conversation.entries = json.dumps(entries)
    conversation.last_active_at = now

    db.commit()
    logger.info(f"Saved assistant response to conversation {conversation_id}")

    # Send message received event
    await send_event_to_conversation(
        conversation_id,
        "message_received",
        {
            "id": message_id,
            "content": response_text,
            "role": "assistant",
            "created_at_utc": now.isoformat()
        }
    )
    logger.info(f"Sent message_received event for conversation {conversation_id}")

    # Turn off typing indicator
    await send_event_to_conversation(
        conversation_id,
        "typing_indicator",
        {
            "isTyping": False,
            "role": "assistant"
        }
    )
    logger.info(f"Turned off typing indicator for conversation {conversation_id}")


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
