from fastapi import APIRouter, Depends
from typing import Dict, Any
import asyncio

from app.api.config import conversations
from app.utils.auth import get_current_user
from app.core.event_bus import EventBus
from app.utils.exceptions import ResourceNotFoundException
from app.models import api as api_models

# Create a global event bus instance
event_bus = EventBus()

router = APIRouter(prefix="/input", tags=["input"])

@router.post("/", response_model=api_models.MessageAck)
async def receive_input(
    message: api_models.InputMessage,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Receive a user message (conversation input)."""
    # Check if conversation exists
    conversation_id = message.conversation_id
    if conversation_id not in conversations:
        raise ResourceNotFoundException(resource_id=conversation_id, resource_type="conversation")
    
    # Use the user ID from the validated token
    user_id = current_user["id"]
    
    # Create an event for the message
    input_event = {
        "type": "input",
        "user_id": user_id,
        "conversation_id": conversation_id,
        "data": {
            "content": message.content,
            "metadata": message.metadata if message.metadata else {},
            "role": "user"
        }
    }
    
    # Publish the event to the event bus
    asyncio.create_task(event_bus.publish(input_event))
    
    # Return immediate acknowledgment
    return api_models.MessageAck(
        status="received",
        data={
            "content": message.content,
            "conversation_id": conversation_id,
            "metadata": message.metadata if message.metadata else {}
        }
    )
