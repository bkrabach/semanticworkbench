import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict, Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from app.core.event_bus import event_bus
from app.utils.auth import get_current_user

# Set up logger
logger = logging.getLogger(__name__)

# No model imports needed for now

router = APIRouter(prefix="/output", tags=["output"])


async def event_generator(
    request: Request, user_id: str, conversation_id: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """Generate SSE events for a specific user and optionally a specific conversation."""
    # Subscribe to the event bus with filters for this user and conversation
    # This is more efficient than manually filtering events after receiving them
    logger.info(
        f"Creating SSE stream for user: {user_id}" + (f", conversation: {conversation_id}" if conversation_id else "")
    )

    client_queue: asyncio.Queue = event_bus.subscribe(
        event_type=None,  # Subscribe to all event types
        conversation_id=conversation_id,  # Filter by conversation if specified
    )

    logger.debug("Subscribed to event bus")
    events_sent = 0

    try:
        # Keep the connection open
        while True:
            # Check if the client has disconnected
            if await request.is_disconnected():
                logger.info(f"Client disconnected, closing SSE stream for user: {user_id}")
                break

            # Get the next event (with timeout to check for disconnection regularly)
            try:
                event = await asyncio.wait_for(client_queue.get(), timeout=1.0)
                logger.debug(f"Received event: {event.get('type', 'unknown')} for user: {user_id}")
            except asyncio.TimeoutError:
                # Send a keep-alive comment (optional)
                yield ": ping\n\n"
                continue

            # Filter events for this user (the EventBus doesn't do this filtering yet)
            if event.get("user_id") != user_id:
                logger.debug(f"Filtering event for wrong user: {event.get('user_id')}")
                continue

            # Format as SSE event
            event_type = event.get("type", "message")
            event_data = json.dumps(event)
            yield f"event: {event_type}\ndata: {event_data}\n\n"
            events_sent += 1

            if events_sent % 10 == 0:  # Log every 10 events
                logger.debug(f"Sent {events_sent} events to user: {user_id}")

            # Mark task as done
            client_queue.task_done()

    finally:
        # Ensure we unsubscribe when the client disconnects
        event_bus.unsubscribe(client_queue)
        logger.info(f"Unsubscribed from event bus for user: {user_id}, sent {events_sent} events")


@router.get("/stream")
async def stream_output(
    request: Request,
    conversation_id: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> StreamingResponse:
    """
    Open a Server-Sent Events stream for receiving real-time outputs.

    Args:
        request: The FastAPI request object
        conversation_id: Optional ID of the conversation to filter events
        current_user: The authenticated user information

    Returns:
        A streaming response with server-sent events
    """
    # User has already been authenticated via the dependency
    user_id = current_user["id"]

    logger.info(
        f"SSE stream requested by user: {user_id}"
        + (f" for conversation: {conversation_id}" if conversation_id else "")
    )

    # Return SSE stream response
    response = StreamingResponse(
        event_generator(request, user_id, conversation_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable buffering in nginx
        },
    )

    logger.debug(f"SSE stream response created for user: {user_id}")
    return response
