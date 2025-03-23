import asyncio
import json
from typing import Any, AsyncGenerator, Dict, Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from app.core.event_bus import event_bus
from app.utils.auth import get_current_user

# No model imports needed for now

router = APIRouter(prefix="/output", tags=["output"])


async def event_generator(
    request: Request, user_id: str, conversation_id: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """Generate SSE events for a specific user and optionally a specific conversation."""
    # Subscribe to the event bus with filters for this user and conversation
    # This is more efficient than manually filtering events after receiving them
    client_queue: asyncio.Queue = event_bus.subscribe(
        event_type=None,  # Subscribe to all event types
        conversation_id=conversation_id  # Filter by conversation if specified
    )

    try:
        # Keep the connection open
        while True:
            # Check if the client has disconnected
            if await request.is_disconnected():
                break

            # Get the next event (with timeout to check for disconnection regularly)
            try:
                event = await asyncio.wait_for(client_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                # Send a keep-alive comment (optional)
                yield ": ping\n\n"
                continue

            # Filter events for this user (the EventBus doesn't do this filtering yet)
            if event.get("user_id") != user_id:
                continue

            # Format as SSE event
            event_type = event.get("type", "message")
            event_data = json.dumps(event)
            yield f"event: {event_type}\ndata: {event_data}\n\n"

            # Mark task as done
            client_queue.task_done()

    finally:
        # Ensure we unsubscribe when the client disconnects
        event_bus.unsubscribe(client_queue)


@router.get("/stream")
async def stream_output(
    request: Request,
    conversation_id: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Open a Server-Sent Events stream for outputs."""
    # User has already been authenticated via the dependency
    user_id = current_user["id"]

    # Return SSE stream response
    return StreamingResponse(
        event_generator(request, user_id, conversation_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable buffering in nginx
        },
    )
