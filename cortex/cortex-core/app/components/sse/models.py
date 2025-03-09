"""
DEPRECATED: Data models and types for the SSE module.

This module has been deprecated and replaced with domain models in app.models.domain.sse
and app.models.domain.user. These models are maintained here only for backwards
compatibility during the migration to the domain-driven repository architecture.
"""

import warnings
from typing import Dict, Any, List, Literal
from pydantic import BaseModel, Field
from datetime import datetime

# Emit deprecation warning
warnings.warn(
    "The models in app.components.sse.models are deprecated. "
    "Use the domain models from app.models.domain.sse and app.models.domain.user instead.",
    DeprecationWarning,
    stacklevel=2
)

# Channel types
ChannelType = Literal["global", "user", "workspace", "conversation"]

class UserInfo(BaseModel):
    """
    DEPRECATED: User information extracted from authentication.
    Use app.models.domain.user.UserInfo instead.
    """
    id: str
    roles: List[str] = Field(default_factory=list)
    
    def __init__(self, **data):
        super().__init__(**data)
        warnings.warn(
            "UserInfo is deprecated. Use app.models.domain.user.UserInfo instead.",
            DeprecationWarning,
            stacklevel=2
        )
    
class SSEEvent(BaseModel):
    """
    DEPRECATED: SSE event model.
    Use app.models.domain.sse.SSEEvent instead.
    """
    event: str
    data: Dict[str, Any] = Field(default_factory=dict)
    
    def __init__(self, **data):
        super().__init__(**data)
        warnings.warn(
            "SSEEvent is deprecated. Use app.models.domain.sse.SSEEvent instead.",
            DeprecationWarning,
            stacklevel=2
        )
    
class ConnectionInfo(BaseModel):
    """
    DEPRECATED: Information about an SSE connection.
    Use app.models.domain.sse.SSEConnection instead.
    """
    id: str
    user_id: str
    connected_at: datetime
    
    def __init__(self, **data):
        super().__init__(**data)
        warnings.warn(
            "ConnectionInfo is deprecated. Use app.models.domain.sse.SSEConnection instead.",
            DeprecationWarning,
            stacklevel=2
        )
    
class ConnectionStats(BaseModel):
    """
    DEPRECATED: Statistics about active connections.
    Use app.models.domain.sse.SSEConnectionStats instead.
    """
    global_count: int
    channel_counts: Dict[str, Dict[str, int]]
    total: int
    
    def __init__(self, **data):
        super().__init__(**data)
        warnings.warn(
            "ConnectionStats is deprecated. Use app.models.domain.sse.SSEConnectionStats instead.",
            DeprecationWarning,
            stacklevel=2
        )