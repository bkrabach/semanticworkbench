import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, Request
from app.core.storage_service import storage_service
from app.models import api as api_models
from app.utils.auth import get_current_user
from app.utils.exceptions import ResourceNotFoundException

# Set up logger
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/input", tags=["input"])


@router.post("/", response_model=api_models.MessageAck)
async def receive_input(
    message: api_models.InputMessage, 
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> api_models.MessageAck:
    """
    Receive a user message and publish it to the event bus.

    Args:
        message: The input message containing content and metadata
        current_user: The authenticated user information

    Returns:
        A message acknowledgment with status information

    Raises:
        ResourceNotFoundException: If the conversation doesn't exist
    """
    # Check if conversation exists
    conversation_id = message.conversation_id
    user_id = current_user["id"]

    logger.info(f"Received message for conversation: {conversation_id} from user: {user_id}")
    logger.debug(f"Message length: {len(message.content)} chars, has metadata: {message.metadata is not None}")

    if not storage_service.get_conversation(conversation_id):
        logger.warning(f"Message received for non-existent conversation: {conversation_id}")
        raise ResourceNotFoundException(resource_id=conversation_id, resource_type="conversation")

    # Get the event bus from app state
    event_bus = request.app.state.event_bus
    
    # Create an event for the message
    input_event = {
        "user_id": user_id,
        "conversation_id": conversation_id,
        "content": message.content,
        "metadata": message.metadata if message.metadata else {},
        "role": "user"
    }

    # Publish the event to the event bus
    logger.debug(f"Publishing input event for conversation: {conversation_id}")
    await event_bus.publish("input", input_event)

    logger.info(f"Message from user: {user_id} for conversation: {conversation_id} acknowledged")
    # Return immediate acknowledgment
    return api_models.MessageAck(
        status="received",
        data={
            "content": message.content,
            "conversation_id": conversation_id,
            "metadata": message.metadata if message.metadata else {},
        },
    )
