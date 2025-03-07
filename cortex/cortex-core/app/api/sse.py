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
from datetime import datetime
from fastapi import Query
from app.components.security_manager import get_current_user_or_none
from app.components.tokens import verify_jwt_token
from app.api.auth import get_current_user

from app.database.connection import get_db
from app.database.models import User, Workspace, Conversation
from app.utils.logger import logger

router = APIRouter()

# In-memory store for active SSE connections
active_connections: Dict[str, List[Dict[str, Any]]] = {
    "global": [],
    "users": {},
    "workspaces": {},
    "conversations": {},
}


async def event_generator(client_id: str, user_id: str, channel: str) -> AsyncGenerator[str, None]:
    """
    Generate SSE events for a client connection

    Args:
        client_id: Unique identifier for the client connection
        user_id: User ID associated with the connection
        channel: Event channel (global, workspace-specific, etc.)

    Yields:
        SSE formatted event strings
    """
    connection = {
        "client_id": client_id,
        "user_id": user_id,
        "created_at": datetime.utcnow(),
        "queue": None
    }

    # Register this connection
    if channel.startswith("users:"):
        user_id = channel.split(":", 1)[1]
        if user_id not in active_connections["users"]:
            active_connections["users"][user_id] = []
        active_connections["users"][user_id].append(connection)
    elif channel.startswith("workspaces:"):
        workspace_id = channel.split(":", 1)[1]
        if workspace_id not in active_connections["workspaces"]:
            active_connections["workspaces"][workspace_id] = []
        active_connections["workspaces"][workspace_id].append(connection)
    elif channel.startswith("conversations:"):
        conversation_id = channel.split(":", 1)[1]
        if conversation_id not in active_connections["conversations"]:
            active_connections["conversations"][conversation_id] = []
        active_connections["conversations"][conversation_id].append(connection)
    else:
        active_connections["global"].append(connection)

    # Send initial connection event
    yield f"event: connect\ndata: {json.dumps({'connected': True, 'timestamp': datetime.utcnow().isoformat()})}\n\n"

    try:
        # Create an event queue for this connection
        queue = asyncio.Queue()
        connection["queue"] = queue

        # Send a heartbeat every 30 seconds to keep connection alive
        heartbeat_task = asyncio.create_task(send_heartbeats(queue))

        # Process events from the queue
        while True:
            event = await queue.get()
            if event.get("type") == "close":
                break

            event_type = event.get("event", "message")
            data = json.dumps(event.get("data", {}))
            yield f"event: {event_type}\ndata: {data}\n\n"
    except asyncio.CancelledError:
        logger.info(f"SSE connection closed for client {client_id}")
    finally:
        # Clean up
        try:
            heartbeat_task.cancel()

            # Remove connection from appropriate channel
            if channel.startswith("users:"):
                user_id = channel.split(":", 1)[1]
                if user_id in active_connections["users"]:
                    active_connections["users"][user_id].remove(connection)
            elif channel.startswith("workspaces:"):
                workspace_id = channel.split(":", 1)[1]
                if workspace_id in active_connections["workspaces"]:
                    active_connections["workspaces"][workspace_id].remove(
                        connection)
            elif channel.startswith("conversations:"):
                conversation_id = channel.split(":", 1)[1]
                if conversation_id in active_connections["conversations"]:
                    active_connections["conversations"][conversation_id].remove(
                        connection)
            else:
                active_connections["global"].remove(connection)

        except (ValueError, KeyError):
            pass


async def send_heartbeats(queue: asyncio.Queue):
    """
    Send periodic heartbeats to keep the connection alive

    Args:
        queue: Event queue for the connection
    """
    while True:
        await asyncio.sleep(30)
        await queue.put({
            "event": "heartbeat",
            "data": {"timestamp": datetime.utcnow().isoformat()}
        })


async def broadcast_to_channel(connections: List[Dict[str, Any]], event_type: str, data: Dict[str, Any]):
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
                await connection["queue"].put({
                    "event": event_type,
                    "data": data
                })
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
        await broadcast_to_channel(active_connections["conversations"][conversation_id], event_type, data)


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
        "users": {user_id: len(connections) for user_id, connections in active_connections["users"].items()},
        "workspaces": {workspace_id: len(connections) for workspace_id, connections in active_connections["workspaces"].items()},
        "conversations": {conversation_id: len(connections) for conversation_id, connections in active_connections["conversations"].items()},
    }


@router.get("/events")
async def global_events(
    request: Request,
    token: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_current_user_or_none)
):
    """
    Global events endpoint

    Args:
        request: FastAPI request object
        token: Authentication token from query param
        current_user: Authenticated user

    Returns:
        SSE stream for global events
    """
    # If token is provided in query params, authenticate with it
    if token and not current_user:
        try:
            token_data = verify_jwt_token(token)
            if token_data:
                # Get user from database
                db = next(get_db())
                current_user = db.query(User).filter(
                    User.id == token_data.user_id).first()
        except Exception as e:
            logger.error(
                f"Failed to authenticate with token from query params: {e}")

    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    client_id = f"client_{uuid.uuid4()}"
    logger.info(
        f"New global SSE connection from user {current_user.id}, client {client_id}")

    async def event_stream():
        async for event in event_generator(client_id, current_user.id, "global"):
            yield event

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable buffering in Nginx
        }
    )


@router.get("/users/{user_id}/events")
async def user_events(
    user_id: str,
    request: Request,
    token: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_current_user_or_none),
    db: Session = Depends(get_db)
):
    """
    User-specific events endpoint

    Args:
        user_id: User ID to subscribe to
        request: FastAPI request object
        token: Authentication token from query param
        current_user: Authenticated user
        db: Database session

    Returns:
        SSE stream for user events
    """
    # If token is provided in query params, authenticate with it
    if token and not current_user:
        try:
            token_data = verify_jwt_token(token)
            if token_data:
                # Get user from database
                current_user = db.query(User).filter(
                    User.id == token_data.user_id).first()
        except Exception as e:
            logger.error(
                f"Failed to authenticate with token from query params: {e}")

    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Only allow users to subscribe to their own events
    if user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this user's events")

    client_id = f"client_{uuid.uuid4()}"
    channel = f"users:{user_id}"
    logger.info(
        f"New user SSE connection from user {current_user.id}, client {client_id}")

    async def event_stream():
        async for event in event_generator(client_id, current_user.id, channel):
            yield event

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/workspaces/{workspace_id}/events")
async def workspace_events(
    workspace_id: str,
    request: Request,
    token: Optional[str] = Query(None),
    user: Optional[User] = Depends(get_current_user_or_none),
    db: Session = Depends(get_db)
):
    """
    Workspace-specific events endpoint

    Args:
        workspace_id: Workspace ID to subscribe to
        request: FastAPI request object
        token: Authentication token from query param
        user: Authenticated user
        db: Database session

    Returns:
        SSE stream for workspace events
    """
    # If token is provided in query params, authenticate with it
    if token and not user:
        try:
            token_data = verify_jwt_token(token)
            if token_data:
                # Get user from database
                user = db.query(User).filter(
                    User.id == token_data.user_id).first()
        except Exception as e:
            logger.error(
                f"Failed to authenticate with token from query params: {e}")

    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Verify workspace access
    workspace = db.query(Workspace).filter(
        Workspace.id == workspace_id,
        Workspace.user_id == user.id
    ).first()

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    client_id = f"client_{uuid.uuid4()}"
    channel = f"workspaces:{workspace_id}"
    logger.info(
        f"New workspace SSE connection from user {user.id}, client {client_id}, workspace {workspace_id}")

    async def event_stream():
        async for event in event_generator(client_id, user.id, channel):
            yield event

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/conversations/{conversation_id}/events")
async def conversation_events(
    conversation_id: str,
    request: Request,
    token: Optional[str] = Query(None),
    user: Optional[User] = Depends(get_current_user_or_none),
    db: Session = Depends(get_db)
):
    """
    Conversation-specific events endpoint

    Args:
        conversation_id: Conversation ID to subscribe to
        request: FastAPI request object
        token: Authentication token from query param
        user: Authenticated user
        db: Database session

    Returns:
        SSE stream for conversation events
    """
    # If token is provided in query params, authenticate with it
    if token and not user:
        try:
            token_data = verify_jwt_token(token)
            if token_data:
                # Get user from database
                user = db.query(User).filter(
                    User.id == token_data.user_id).first()
        except Exception as e:
            logger.error(
                f"Failed to authenticate with token from query params: {e}")

    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Verify conversation access
    conversation = db.query(Conversation).join(Workspace).filter(
        Conversation.id == conversation_id,
        Workspace.user_id == user.id
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=404, detail="Conversation not found or not authorized")

    client_id = f"client_{uuid.uuid4()}"
    channel = f"conversations:{conversation_id}"
    logger.info(
        f"New conversation SSE connection from user {user.id}, client {client_id}, conversation {conversation_id}")

    async def event_stream():
        async for event in event_generator(client_id, user.id, channel):
            yield event

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
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
