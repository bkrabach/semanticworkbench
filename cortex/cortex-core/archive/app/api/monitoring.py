"""
Monitoring API endpoints
Provides endpoints for system monitoring and diagnostics
"""

from fastapi import APIRouter, Depends
from app.components.event_system import get_event_system
from app.interfaces.router import EventSystemInterface

router = APIRouter()

@router.get("/events/stats")
async def get_event_stats(event_system: EventSystemInterface = Depends(get_event_system)):
    """
    Get statistics from the event system
    
    Returns a dictionary with metrics such as:
    - Total events published
    - Total events delivered
    - Number of subscribers
    - Event type breakdown
    - Error count
    - Events per second
    """
    return await event_system.get_stats()