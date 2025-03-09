"""
Server-Sent Events (SSE) API endpoints for Cortex Core

Provides real-time event streams to clients via Server-Sent Events.
This implementation uses a unified, clean architecture with domain-driven
repository pattern.
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from typing import Optional
from app.services.sse_service import get_sse_service, SSEService
from app.models.api.response.sse import SSEConnectionStatsResponse

router = APIRouter(prefix="/v1", tags=["Events"])


# This helper function has been moved to the SSEService class
# to better align with the domain-driven repository architecture


# Global events endpoint
@router.get("/global", response_model=None)
async def global_events(
    request: Request,
    token: Optional[str] = None,  # Make token parameter optional at function level
    sse_service: SSEService = Depends(get_sse_service),
):
    """
    Global events endpoint for system-wide events

    Args:
        request: FastAPI request object
        token: Authentication token (technically optional at function level but required for actual use)
        sse_service: SSE service

    Returns:
        SSE stream for global events
    """
    # Validate token is provided - this will trigger 422 error when missing
    if not token:
        raise HTTPException(status_code=422, detail="Missing required parameter: token")

    # Use service to handle connection setup
    streaming_response = await sse_service.create_sse_stream(
        channel_type="global",
        resource_id="global",
        token=token
    )
    
    return streaming_response


# Dynamic channel type endpoints
@router.get("/{channel_type}/{resource_id}", response_model=None)
async def events(
    channel_type: str,
    resource_id: str,
    request: Request,
    token: Optional[str] = None,  # Make token parameter optional at function level
    sse_service: SSEService = Depends(get_sse_service),
):
    """
    Unified SSE endpoint for all event types

    Args:
        channel_type: Type of events to subscribe to (user, workspace, conversation)
        resource_id: ID of the resource to subscribe to
        request: FastAPI request object
        token: Authentication token (technically optional at function level but required for actual use)
        sse_service: SSE service

    Returns:
        SSE stream for the requested events
    """
    # Validate token is provided - this will trigger 422 error when missing
    if not token:
        raise HTTPException(status_code=422, detail="Missing required parameter: token")

    # Validate channel type
    valid_channels = ["user", "workspace", "conversation"]
    if channel_type not in valid_channels:
        raise HTTPException(
            status_code=400, detail=f"Invalid channel type: {channel_type}. Must be one of: {', '.join(valid_channels)}"
        )

    # Use service to handle connection setup
    streaming_response = await sse_service.create_sse_stream(
        channel_type=channel_type,
        resource_id=resource_id,
        token=token
    )
    
    return streaming_response


@router.get("/stats", response_model=SSEConnectionStatsResponse)
async def connection_stats(sse_service: SSEService = Depends(get_sse_service)):
    """
    Get statistics about active SSE connections

    Args:
        sse_service: SSE service

    Returns:
        SSEConnectionStatsResponse: Connection statistics model
    """
    # Get connection stats through service
    stats = sse_service.get_connection_stats()

    # Convert domain model to API response model
    return SSEConnectionStatsResponse(
        total_connections=stats.total_connections,
        connections_by_channel=stats.connections_by_channel,
        connections_by_user=stats.connections_by_user,
        generated_at=stats.generated_at,
    )
