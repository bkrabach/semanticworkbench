from fastapi import APIRouter, Request, Query, Depends
from fastapi.responses import StreamingResponse
from typing import Optional, AsyncGenerator, Dict, Any
import asyncio
import json

from app.utils.auth import get_current_user
from app.api.input import event_bus  # Import the global event bus
# No model imports needed for now

router = APIRouter(prefix="/output", tags=["output"])

async def event_generator(request: Request, user_id: str, conversation_id: Optional[str] = None) -> AsyncGenerator[str, None]:
    """Generate SSE events for a specific user and optionally a specific conversation."""
    # Create a queue for this client
    client_queue: asyncio.Queue = asyncio.Queue()
    
    # Subscribe to the event bus
    event_bus.subscribe(client_queue)
    
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
                
            # Filter events for this user
            if event.get("user_id") != user_id:
                continue
                
            # Filter by conversation_id if specified
            if conversation_id and event.get("conversation_id") != conversation_id:
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
    current_user: Dict[str, Any] = Depends(get_current_user)
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
            "X-Accel-Buffering": "no"  # Disable buffering in nginx
        }
    )
