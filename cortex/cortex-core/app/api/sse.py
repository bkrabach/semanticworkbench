"""
Server-Sent Events (SSE) API endpoints for Cortex Core

Provides real-time event streams to clients via Server-Sent Events.
This implementation uses a unified, clean architecture without backward compatibility
requirements.
"""

from fastapi import APIRouter, Depends, Request, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import Optional
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.components.sse import get_sse_service, SSEAuthService
from app.utils.logger import logger
from app.database.repositories import get_resource_access_repository

router = APIRouter(
    prefix="/v1",
    tags=["Events"]
)

# Helper function to handle SSE connections
async def handle_sse_connection(
    channel_type: str,
    resource_id: str,
    token: str,  # This function expects a non-None token
    sse_service,
    db: Session
):
    """
    Common function to handle SSE connections for all channel types
    
    Args:
        channel_type: Type of events to subscribe to
        resource_id: ID of the resource to subscribe to
        token: Authentication token (must be non-null)
        sse_service: SSE service instance
        db: Database session
        
    Returns:
        Tuple containing the event queue, connection ID, and background tasks
    """
    # Authenticate user
    user_info = await sse_service.authenticate_token(token)
    
    # For non-global channels, verify resource access with repository
    if channel_type != "global":
        # Get resource access repository for explicit DB access pattern
        resource_access_repo = get_resource_access_repository(db)
        
        # Create temporary auth service with repository or use the service's auth
        if not hasattr(sse_service.auth_service, 'resource_access_repo') or not sse_service.auth_service.resource_access_repo:
            temp_auth_service = SSEAuthService(resource_access_repo)
            has_access = await temp_auth_service.verify_resource_access(
                user_info, channel_type, resource_id, db)
        else:
            has_access = await sse_service.verify_resource_access(
                user_info, channel_type, resource_id, db
        )
        
        if not has_access:
            raise HTTPException(
                status_code=403,
                detail=f"Not authorized to access {channel_type} events for {resource_id}"
            )
    
    # Register connection
    connection_manager = sse_service.connection_manager
    queue, connection_id = await connection_manager.register_connection(
        channel_type, resource_id, user_info["id"]
    )
    
    # Create background tasks object
    background_tasks = BackgroundTasks()
    
    # Handle special case for conversation channel - start publisher
    if channel_type == "conversation":
        try:
            from app.components.conversation_channels import get_conversation_publisher
            # Add publisher task to background tasks
            background_tasks.add_task(
                get_conversation_publisher, 
                resource_id
            )
        except Exception as e:
            logger.error(f"Error initializing conversation publisher: {e}")
    
    # Add cleanup task to background tasks
    background_tasks.add_task(
        connection_manager.remove_connection,
        channel_type, resource_id, connection_id
    )
    
    return queue, connection_id, background_tasks

# Global events endpoint
@router.get("/global")
async def global_events(
    request: Request,
    token: Optional[str] = None,  # Make token parameter optional at function level
    sse_service = Depends(get_sse_service),
    db: Session = Depends(get_db)
):
    """
    Global events endpoint for system-wide events
    
    Args:
        request: FastAPI request object
        token: Authentication token (technically optional at function level but required for actual use)
        sse_service: SSE service
        db: Database session
        
    Returns:
        SSE stream for global events
    """
    # Validate token is provided - this will trigger 422 error when missing
    if not token:
        raise HTTPException(
            status_code=422,
            detail="Missing required parameter: token"
        )
    
    queue, connection_id, background_tasks = await handle_sse_connection(
        "global", "global", token, sse_service, db
    )
    
    # Create event generator
    generator = sse_service.connection_manager.generate_sse_events(queue)
    
    # Return streaming response with background tasks
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
        background=background_tasks
    )


# Dynamic channel type endpoints
@router.get("/{channel_type}/{resource_id}")
async def events(
    channel_type: str,
    resource_id: str,
    request: Request,
    token: Optional[str] = None,  # Make token parameter optional at function level
    sse_service = Depends(get_sse_service),
    db: Session = Depends(get_db)
):
    """
    Unified SSE endpoint for all event types
    
    Args:
        channel_type: Type of events to subscribe to (user, workspace, conversation)
        resource_id: ID of the resource to subscribe to
        request: FastAPI request object
        token: Authentication token (technically optional at function level but required for actual use)
        sse_service: SSE service
        db: Database session
        
    Returns:
        SSE stream for the requested events
    """
    # Validate token is provided - this will trigger 422 error when missing
    if not token:
        raise HTTPException(
            status_code=422,
            detail="Missing required parameter: token"
        )
        
    # Validate channel type
    valid_channels = ["user", "workspace", "conversation"]
    if channel_type not in valid_channels:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid channel type: {channel_type}. Must be one of: {', '.join(valid_channels)}"
        )
    
    queue, connection_id, background_tasks = await handle_sse_connection(
        channel_type, resource_id, token, sse_service, db
    )
    
    # Create event generator
    generator = sse_service.connection_manager.generate_sse_events(queue)
    
    # Return streaming response with background tasks
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
        background=background_tasks
    )

@router.get("/stats")
async def connection_stats(
    sse_service = Depends(get_sse_service)
):
    """
    Get statistics about active SSE connections
    
    Args:
        sse_service: SSE service
        
    Returns:
        Dictionary with connection statistics
    """
    return sse_service.connection_manager.get_stats()