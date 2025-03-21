import logging
from fastapi import APIRouter, Depends
from datetime import datetime

from ..utils.auth import get_current_user
from ..models.api.request import InputRequest
from ..models.api.response import InputResponse
from ..core.event_bus import event_bus
from ..models.domain import Message
from ..core.storage import storage
from ..core.exceptions import ResourceNotFoundException, EventBusException

logger = logging.getLogger(__name__)
router = APIRouter(tags=["input"])

@router.post("/input", response_model=InputResponse)
async def receive_input(request: InputRequest, current_user: dict = Depends(get_current_user)):
    """
    Receive input from a client.

    Args:
        request: The input request
        current_user: The authenticated user

    Returns:
        Status response
    """
    user_id = current_user["user_id"]
    logger.info(f"Received input from user {user_id}")
    
    # Verify conversation exists
    conversation = storage.get_conversation(request.conversation_id)
    if not conversation:
        raise ResourceNotFoundException(
            message="Conversation not found",
            resource_type="conversation",
            resource_id=request.conversation_id
        )
    
    # Create a timestamp
    timestamp = datetime.now().isoformat()

    # Create event with user ID
    event = {
        "type": "input",
        "data": {
            "content": request.content,
            "conversation_id": request.conversation_id,
            "timestamp": timestamp,
        },
        "user_id": user_id,
        "timestamp": timestamp,
        "metadata": request.metadata
    }

    # Create and store message
    message = Message(
        sender_id=user_id,
        content=request.content,
        conversation_id=request.conversation_id,
        timestamp=timestamp,
        metadata=request.metadata
    )
    storage.create_message(message)

    # Publish event to event bus
    try:
        await event_bus.publish(event)
    except Exception as e:
        logger.error(f"Failed to publish event: {e}")
        raise EventBusException(
            message="Failed to publish input event",
            details={"conversation_id": request.conversation_id}
        )

    # Return response
    return InputResponse(
        status="received",
        data={
            "content": request.content,
            "conversation_id": request.conversation_id,
            "timestamp": timestamp,
            "metadata": request.metadata
        }
    )