"""
Server-Sent Events (SSE) API endpoints for the Cortex application.

This module handles SSE connections for real-time updates.
"""
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Path, Query, Request
from sse_starlette.sse import EventSourceResponse

from app.api.auth import get_current_user
from app.components.sse.manager import SseManager, get_sse_manager
from app.models.api.response.user import UserInfo

router = APIRouter(tags=["sse"])


@router.get("/sse/{resource_type}/{resource_id}")
async def sse_endpoint(
    request: Request,
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    sse_manager: Annotated[SseManager, Depends(get_sse_manager)],
    resource_type: str = Path(..., description="The type of resource to subscribe to"),
    resource_id: str = Path(..., description="The ID of the resource to subscribe to"),
) -> EventSourceResponse:
    """
    Subscribe to SSE events for a specific resource.
    
    Args:
        request: The FastAPI request object
        resource_type: The type of resource (workspace, conversation)
        resource_id: The ID of the resource
        current_user: The current authenticated user
        sse_manager: The SSE manager instance
        
    Returns:
        An EventSourceResponse for the SSE connection
    """
    # Register connection with SSE manager
    queue, connection_id = await sse_manager.register_connection(
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=current_user.id,
    )
    
    # Create event generator
    async def event_generator():
        try:
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break
                
                # Wait for next event
                event = await queue.get()
                
                # Send event to client
                if event.get("type") == "heartbeat":
                    yield {
                        "event": "heartbeat",
                        "data": "",
                    }
                else:
                    yield {
                        "event": event.get("type", "message"),
                        "data": event.get("data", {}),
                    }
                
                # Mark event as processed
                queue.task_done()
        finally:
            # Clean up connection on disconnect
            await sse_manager.remove_connection(
                resource_type=resource_type,
                resource_id=resource_id,
                connection_id=connection_id,
            )
    
    # Return SSE response
    return EventSourceResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )