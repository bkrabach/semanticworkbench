from typing import Any, Dict

from fastapi import APIRouter, Depends

from app.core.event_bus import event_bus
from app.core.storage_service import storage_service
from app.models import api as api_models
from app.utils.auth import get_current_user
from app.utils.exceptions import ResourceNotFoundException

router = APIRouter(prefix="/input", tags=["input"])


@router.post("/", response_model=api_models.MessageAck)
async def receive_input(message: api_models.InputMessage, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Receive a user message (conversation input)."""
    # Check if conversation exists
    conversation_id = message.conversation_id
    if not storage_service.get_conversation(conversation_id):
        raise ResourceNotFoundException(resource_id=conversation_id, resource_type="conversation")

    # Use the user ID from the validated token
    user_id = current_user["id"]

    # Create an event for the message
    input_event = {
        "user_id": user_id,
        "conversation_id": conversation_id,
        "data": {"content": message.content, "metadata": message.metadata if message.metadata else {}, "role": "user"},
    }

    # Publish the event to the event bus
    event_bus.publish("user_message", input_event)

    # Return immediate acknowledgment
    return api_models.MessageAck(
        status="received",
        data={
            "content": message.content,
            "conversation_id": conversation_id,
            "metadata": message.metadata if message.metadata else {},
        },
    )