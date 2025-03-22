import json
import asyncio
import logging
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from datetime import datetime
from typing import Dict, Any

from ..utils.auth import get_current_user
from ..core.event_bus import event_bus
from ..core.exceptions import ServiceUnavailableException
from ..core.response_handler import get_output_queue
from ..models.api.response import ErrorResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["output"])

@router.get("/output/stream", responses={
    401: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
    503: {"model": ErrorResponse}
})
async def output_stream(
    request: Request,
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Server-Sent Events (SSE) endpoint for streaming output to clients.

    Args:
        request: The HTTP request
        conversation_id: The ID of the conversation to stream
        current_user: The authenticated user

    Returns:
        SSE streaming response
    """
    user_id = current_user["user_id"]
    logger.info(f"New SSE connection established for user {user_id}, conversation {conversation_id}")

    # Get or create a queue for this conversation
    queue = get_output_queue(conversation_id)

    # Subscribe to event bus as well for system events
    event_bus_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
    
    try:
        event_bus.subscribe(event_bus_queue)
    except Exception as e:
        logger.error(f"Failed to subscribe to event bus: {e}")
        raise ServiceUnavailableException(
            message="Unable to establish event stream",
            service_name="event_bus"
        )

    async def event_generator():
        """Generate SSE events from both conversation queue and event bus."""
        try:
            # Send initial connection established event
            connection_event = {
                "type": "connection_established",
                "user_id": user_id,
                "conversation_id": conversation_id,
                "timestamp": datetime.now().isoformat()
            }
            yield f"data: {json.dumps(connection_event)}\n\n"

            # Track when the last heartbeat was sent
            last_heartbeat = datetime.now()
            heartbeat_interval = 30  # seconds

            while True:
                # Check if we need to send a heartbeat
                now = datetime.now()
                if (now - last_heartbeat).total_seconds() >= heartbeat_interval:
                    heartbeat_event = {
                        "type": "heartbeat",
                        "timestamp": now.isoformat()
                    }
                    yield f"data: {json.dumps(heartbeat_event)}\n\n"
                    last_heartbeat = now
                    continue

                # Check both queues with a timeout
                try:
                    # Wait for either a response handler event or an event bus event
                    done, pending = await asyncio.wait(
                        [
                            asyncio.create_task(queue.get()),
                            asyncio.create_task(event_bus_queue.get())
                        ],
                        timeout=heartbeat_interval/2,
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    # Cancel any pending tasks
                    for task in pending:
                        task.cancel()
                        
                    # Process completed tasks
                    for task in done:
                        event = task.result()
                        
                        # If it's a string (from response handler), pass it through
                        if isinstance(event, str):
                            yield f"data: {event}\n\n"
                        # Otherwise, it's a dict from the event bus
                        elif isinstance(event, dict):
                            # Filter events for this user/conversation
                            if (event.get("user_id") == user_id or 
                                event.get("conversation_id") == conversation_id or 
                                event.get("type") == "heartbeat"):
                                # Format as SSE event
                                yield f"data: {json.dumps(event)}\n\n"
                                
                except asyncio.TimeoutError:
                    # No event received, continue and check heartbeat
                    continue

        except asyncio.CancelledError:
            # Client disconnected
            logger.info(f"SSE connection closed for user {user_id}, conversation {conversation_id}")
            raise
        except Exception as e:
            logger.error(f"Error in SSE stream for user {user_id}: {e}")
            error_event = {
                "type": "error",
                "message": "Stream error occurred",
                "timestamp": datetime.now().isoformat()
            }
            yield f"data: {json.dumps(error_event)}\n\n"
            raise ServiceUnavailableException(
                message=f"Error in event stream: {str(e)}",
                service_name="event_stream"
            )
        finally:
            # Always unsubscribe to prevent memory leaks
            try:
                event_bus.unsubscribe(event_bus_queue)
                logger.info(f"Cleaned up SSE connection for user {user_id}")
            except Exception as cleanup_error:
                logger.error(f"Error during connection cleanup: {cleanup_error}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )