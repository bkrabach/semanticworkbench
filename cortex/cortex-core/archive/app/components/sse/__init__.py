"""
Server-Sent Events (SSE) module for Cortex Core.

This module provides components for managing SSE connections and event
broadcasting for real-time client updates.

Note: The service layer implementation has been moved to app/services/sse_service.py
following the domain-driven architecture. This module now exposes only the
component-level functionality.
"""

from app.components.sse.manager import SSEConnectionManager
from app.components.sse.events import SSEEventSubscriber

# This module now only exports the component-level classes
__all__ = ["SSEConnectionManager", "SSEEventSubscriber"]

# Inform users of the moved service class
def get_sse_service():
    """
    This function has been moved to app.services.sse_service.
    
    Please update your import to:
    from app.services.sse_service import get_sse_service
    """
    import warnings
    warnings.warn(
        "get_sse_service has been moved to app.services.sse_service. "
        "Please update your import to: from app.services.sse_service import get_sse_service",
        DeprecationWarning,
        stacklevel=2
    )
    from app.services.sse_service import get_sse_service
    return get_sse_service