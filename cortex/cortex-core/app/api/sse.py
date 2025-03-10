"""
Server-Sent Events (SSE) API endpoints for Cortex Core
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from typing import Optional
from app.services.sse_service import get_sse_service, SSEService
from app.models.api.response.sse import SSEConnectionStatsResponse

router = APIRouter(prefix="/v1", tags=["Events"])


@router.get("/{channel_type}/{resource_id}", response_model=None)
async def events(
    channel_type: str,
    resource_id: str,
    request: Request,
    token: str,
    sse_service: SSEService = Depends(get_sse_service),
):
    """
    Unified SSE endpoint for all event types

    Args:
        channel_type: Type of events to subscribe to (global, user, workspace, conversation)
        resource_id: ID of the resource to subscribe to
        request: FastAPI request object
        token: Authentication token
        sse_service: SSE service

    Returns:
        SSE stream for the requested events
    """
    # Validate channel type
    valid_channels = ["global", "user", "workspace", "conversation"]
    if channel_type not in valid_channels:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid channel type: {channel_type}"
        )
    
    # Pass to service to create stream
    return await sse_service.create_sse_stream(
        channel_type=channel_type,
        resource_id=resource_id,
        token=token,
        request=request
    )


@router.get("/stats", response_model=SSEConnectionStatsResponse)
async def connection_stats(sse_service: SSEService = Depends(get_sse_service)):
    """
    Get statistics about active SSE connections

    Args:
        sse_service: SSE service

    Returns:
        Connection statistics
    """
    stats = sse_service.get_connection_stats()
    
    return SSEConnectionStatsResponse(
        total_connections=stats.total_connections,
        connections_by_channel=stats.connections_by_channel,
        connections_by_user=stats.connections_by_user,
        generated_at=stats.generated_at,
    )
