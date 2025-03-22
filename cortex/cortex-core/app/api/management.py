from typing import Any, Dict, List

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel

from app.core.event_bus import event_bus
from app.models.api import UserProfileResponse
from app.models.domain import User
from app.utils.auth import get_current_user

router = APIRouter(prefix="/management", tags=["management"])


class SystemStatus(BaseModel):
    """System status information model."""

    active_users: int
    active_conversations: int
    uptime_seconds: int
    service_status: Dict[str, str]
    memory_usage: Dict[str, float]


@router.get("/system/status", response_model=SystemStatus)
async def system_status(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get overall system status information.
    This is an admin-only endpoint (in production, we would check if the user has admin role).
    """
    # For MVP, we return simulated status data
    # In a real implementation, we would gather metrics from various components

    return SystemStatus(
        active_users=1,
        active_conversations=1,
        uptime_seconds=3600,
        service_status={"cognition": "healthy", "memory": "healthy"},
        memory_usage={"total_mb": 100, "used_mb": 50, "available_mb": 50},
    )


@router.post("/events/publish")
async def publish_system_event(
    event_type: str = Body(..., embed=True),
    payload: Dict[str, Any] = Body(..., embed=True),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Publish a custom event to the system event bus.
    This is primarily for administrative and debugging purposes.
    """
    # In production, we would verify the user has admin privileges

    # Only allow certain event types for safety
    allowed_event_types = ["system.notification", "system.config.update"]

    if event_type not in allowed_event_types:
        raise HTTPException(
            status_code=400, detail=f"Event type {event_type} is not allowed. Allowed types: {allowed_event_types}"
        )

    # Add user_id to the event payload
    event_payload = {"type": event_type, "user_id": current_user["id"], "data": payload}

    # Publish the event
    await event_bus.publish(event_payload)

    return {"status": "published", "event_type": event_type}


@router.get("/admin/users", response_model=List[UserProfileResponse])
async def list_users(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    List all users in the system.
    In production, this would be an admin-only endpoint.
    """
    # For MVP, return a mock list with just the current user
    # In production, this would query a database
    user = User(id=current_user["id"], name=current_user["name"], email=current_user["email"])

    return [UserProfileResponse(profile=user)]
