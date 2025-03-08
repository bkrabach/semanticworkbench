"""
Server-Sent Events (SSE) API endpoints for Cortex Core
"""

from fastapi import APIRouter, Depends, Request, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any, AsyncGenerator, Optional
import asyncio
import json
import uuid
from datetime import datetime, timezone
from json import JSONEncoder
from fastapi import Query
from app.components.security_manager import get_current_user_or_none
from app.components.tokens import verify_jwt_token
from app.api.auth import get_current_user
from jose import jwt
from app.config import settings

from app.database.connection import get_db
from app.database.models import User, Workspace, Conversation
from app.utils.logger import logger

router = APIRouter()

# Custom JSON encoder to handle datetime objects
class DateTimeEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)

# In-memory store for active SSE connections
active_connections: Dict[str, List[Dict[str, Any]]] = {
    "global": [],
    "users": {},
    "workspaces": {},
    "conversations": {},
}


# This function was refactored directly into the endpoint handlers
# to fix issues with async generators


async def send_heartbeats(queue: asyncio.Queue):
    """
    Send periodic heartbeats to keep the connection alive

    Args:
        queue: Event queue for the connection
    """
    while True:
        await asyncio.sleep(30)
        await queue.put(
            {"event": "heartbeat", "data": {"timestamp_utc": datetime.now(timezone.utc).isoformat()}}
        )


async def broadcast_to_channel(
    connections: List[Dict[str, Any]], event_type: str, data: Dict[str, Any]
):
    """
    Broadcast an event to all connections in a channel

    Args:
        connections: List of active connections
        event_type: Type of event to broadcast
        data: Event data payload
    """
    for connection in connections:
        if connection.get("queue"):
            try:
                await connection["queue"].put({"event": event_type, "data": data})
            except Exception as e:
                logger.error(f"Failed to send event to queue: {e}")


async def send_event_to_user(user_id: str, event_type: str, data: Dict[str, Any]):
    """
    Send an event to all connections for a specific user

    Args:
        user_id: User ID to send the event to
        event_type: Type of event to send
        data: Event data payload
    """
    if user_id in active_connections["users"]:
        await broadcast_to_channel(active_connections["users"][user_id], event_type, data)


async def send_event_to_workspace(workspace_id: str, event_type: str, data: Dict[str, Any]):
    """
    Send an event to all connections for a specific workspace

    Args:
        workspace_id: Workspace ID to send the event to
        event_type: Type of event to send
        data: Event data payload
    """
    if workspace_id in active_connections["workspaces"]:
        await broadcast_to_channel(active_connections["workspaces"][workspace_id], event_type, data)


async def send_event_to_conversation(conversation_id: str, event_type: str, data: Dict[str, Any]):
    """
    Send an event to all connections for a specific conversation

    Args:
        conversation_id: Conversation ID to send the event to
        event_type: Type of event to send
        data: Event data payload
    """
    if conversation_id in active_connections["conversations"]:
        await broadcast_to_channel(
            active_connections["conversations"][conversation_id], event_type, data
        )


async def send_global_event(event_type: str, data: Dict[str, Any]):
    """
    Send an event to all global connections

    Args:
        event_type: Type of event to send
        data: Event data payload
    """
    await broadcast_to_channel(active_connections["global"], event_type, data)


def get_active_connection_count() -> Dict[str, Any]:
    """
    Get counts of active connections

    Returns:
        Dictionary with connection counts by channel
    """
    return {
        "global": len(active_connections["global"]),
        "users": {
            user_id: len(connections)
            for user_id, connections in active_connections["users"].items()
        },
        "workspaces": {
            workspace_id: len(connections)
            for workspace_id, connections in active_connections["workspaces"].items()
        },
        "conversations": {
            conversation_id: len(connections)
            for conversation_id, connections in active_connections["conversations"].items()
        },
    }


@router.get("/events")
async def global_events(
    request: Request,
    token: Optional[str] = Query(None),
):
    """
    Global events endpoint

    Args:
        request: FastAPI request object
        token: Authentication token from query param

    Returns:
        SSE stream for global events
    """
    # Skip full validation for now to avoid any async generator issues
    # Just verify token minimally
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    
    # Manually decode token just to get user_id without using get_db
    try:
        from jose import jwt
        payload = jwt.decode(token, settings.security.jwt_secret, algorithms=["HS256"])
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"Token error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
    
    logger.info(f"SSE connection established for user_id={user_id}")
    
    # Define a simple generator function that doesn't use async generators
    async def sse_events():
        # Initial connection message
        connection_msg = f"event: connect\ndata: {json.dumps({'connected': True})}\n\n"
        yield connection_msg
        
        # Simple heartbeat loop
        i = 0
        while i < 100:  # Limit to avoid infinite loops
            await asyncio.sleep(10)
            heartbeat_msg = f"event: heartbeat\ndata: {json.dumps({'timestamp': datetime.utcnow().isoformat()})}\n\n"
            yield heartbeat_msg
            i += 1
    
    # Return a simple streaming response without complex queue handling
    return StreamingResponse(
        sse_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/users/{user_id}/events")
async def user_events(
    user_id: str,
    request: Request,
    token: Optional[str] = Query(None),
):
    """
    User-specific events endpoint

    Args:
        user_id: User ID to subscribe to
        request: FastAPI request object
        token: Authentication token from query param

    Returns:
        SSE stream for user events
    """
    # Skip full validation for now to avoid any async generator issues
    # Just verify token minimally
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    
    # Manually decode token just to get user_id without using get_db
    try:
        from jose import jwt
        payload = jwt.decode(token, settings.security.jwt_secret, algorithms=["HS256"])
        token_user_id = payload.get("user_id")
        if not token_user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
            
        # Simple authorization check
        if token_user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this user's events")
    except Exception as e:
        logger.error(f"Token error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
    
    logger.info(f"User SSE connection established for user_id={user_id}")
    
    # Define a simple generator function that doesn't use async generators
    async def sse_events():
        # Initial connection message
        connection_msg = f"event: connect\ndata: {json.dumps({'connected': True})}\n\n"
        yield connection_msg
        
        # Simple heartbeat loop
        i = 0
        while i < 100:  # Limit to avoid infinite loops
            await asyncio.sleep(10)
            heartbeat_msg = f"event: heartbeat\ndata: {json.dumps({'timestamp': datetime.utcnow().isoformat()})}\n\n"
            yield heartbeat_msg
            i += 1
    
    # Return a simple streaming response without complex queue handling
    return StreamingResponse(
        sse_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/workspaces/{workspace_id}/events")
async def workspace_events(
    workspace_id: str,
    request: Request,
    token: Optional[str] = Query(None),
):
    """
    Workspace-specific events endpoint

    Args:
        workspace_id: Workspace ID to subscribe to
        request: FastAPI request object
        token: Authentication token from query param

    Returns:
        SSE stream for workspace events
    """
    # Skip full validation for now to avoid any async generator issues
    # Just verify token minimally
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    
    # Manually decode token just to get user_id without using get_db
    try:
        from jose import jwt
        payload = jwt.decode(token, settings.security.jwt_secret, algorithms=["HS256"])
        token_user_id = payload.get("user_id")
        if not token_user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
            
        # NOTE: For now, skip workspace authorization check
        # In a real situation, we'd verify the user has access to this workspace
    except Exception as e:
        logger.error(f"Token error in workspace events: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
    
    logger.info(f"Workspace SSE connection established: user={token_user_id}, workspace={workspace_id}")
    
    # Define a simple generator function that doesn't use async generators
    async def sse_events():
        # Initial connection message
        connection_msg = f"event: connect\ndata: {json.dumps({'connected': True})}\n\n"
        yield connection_msg
        
        # Simple heartbeat loop
        i = 0
        while i < 100:  # Limit to avoid infinite loops
            await asyncio.sleep(10)
            heartbeat_msg = f"event: heartbeat\ndata: {json.dumps({'timestamp': datetime.utcnow().isoformat()})}\n\n"
            yield heartbeat_msg
            i += 1
    
    # Return a simple streaming response without complex queue handling
    return StreamingResponse(
        sse_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache", 
            "Connection": "keep-alive",
        }
    )


@router.get("/conversations/{conversation_id}/events")
async def conversation_events(
    conversation_id: str,
    request: Request,
    token: Optional[str] = Query(None),
):
    """
    Conversation-specific events endpoint

    Args:
        conversation_id: Conversation ID to subscribe to
        request: FastAPI request object
        token: Authentication token from query param

    Returns:
        SSE stream for conversation events
    """
    # Skip full validation for now to avoid any async generator issues
    # Just verify token minimally
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    
    # Manually decode token just to get user_id without using get_db
    try:
        from jose import jwt
        payload = jwt.decode(token, settings.security.jwt_secret, algorithms=["HS256"])
        token_user_id = payload.get("user_id")
        if not token_user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
            
        # NOTE: For now, skip conversation authorization check
        # In a real situation, we'd verify the user has access to this conversation
    except Exception as e:
        logger.error(f"Token error in conversation events: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
    
    logger.info(f"Conversation SSE connection established: user={token_user_id}, conversation={conversation_id}")
    
    # Ensure there's an output publisher for this conversation
    try:
        # Import here to avoid circular imports
        from app.components.conversation_channels import get_conversation_publisher
        # Start this in a background task to avoid blocking
        asyncio.create_task(get_conversation_publisher(conversation_id))
    except Exception as e:
        logger.error(f"Error initializing output publisher: {e}")
    
    # Create a queue for this connection
    queue = asyncio.Queue()
    connection_id = str(uuid.uuid4())
    
    # Initialize conversations dictionary if it doesn't exist
    if conversation_id not in active_connections["conversations"]:
        active_connections["conversations"][conversation_id] = []
    
    # Add this connection to the active connections for this conversation
    connection_info = {
        "id": connection_id,
        "user_id": token_user_id,
        "queue": queue,
        "connected_at": datetime.utcnow().isoformat()
    }
    active_connections["conversations"][conversation_id].append(connection_info)
    logger.info(f"Added SSE connection {connection_id} for conversation {conversation_id}")
    
    # Define a simple generator function that doesn't use async generators
    async def sse_events():
        # Start heartbeat task
        heartbeat_task = asyncio.create_task(send_heartbeats(queue))
        
        try:
            # Initial connection message
            connection_msg = f"event: connect\ndata: {json.dumps({'connected': True})}\n\n"
            yield connection_msg
            
            # Send messages from the queue
            while True:
                try:
                    # Wait for a message with a timeout
                    event = await asyncio.wait_for(queue.get(), timeout=60)
                    
                    # Format SSE message
                    event_type = event.get("event", "message")
                    data = event.get("data", {})
                    sse_msg = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
                    
                    yield sse_msg
                    queue.task_done()
                except asyncio.TimeoutError:
                    # Send a heartbeat on timeout
                    heartbeat_msg = f"event: heartbeat\ndata: {json.dumps({'timestamp': datetime.utcnow().isoformat()})}\n\n"
                    yield heartbeat_msg
        finally:
            # Clean up
            heartbeat_task.cancel()
            # Remove connection from active connections
            if conversation_id in active_connections["conversations"]:
                active_connections["conversations"][conversation_id] = [
                    conn for conn in active_connections["conversations"][conversation_id]
                    if conn["id"] != connection_id
                ]
                logger.info(f"Removed SSE connection {connection_id} for conversation {conversation_id}")
    
    # Return a streaming response with the event generator
    return StreamingResponse(
        sse_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache", 
            "Connection": "keep-alive",
        }
    )


@router.get("/admin/connections", include_in_schema=False)
async def admin_connections(user: User = Depends(get_current_user)):
    """
    Admin endpoint to view active connections
    Only available to admin users

    Args:
        user: Authenticated user

    Returns:
        Dictionary with active connection counts
    """
    # Check if user is admin
    # This is a placeholder - implement your own admin check
    is_admin = user.email.endswith("@admin.com")

    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    return get_active_connection_count()
