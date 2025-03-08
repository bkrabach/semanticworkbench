"""
Data models and types for the SSE module.
"""

from typing import Dict, Any, Optional, List, Literal
from pydantic import BaseModel, Field
from datetime import datetime

# Channel types
ChannelType = Literal["global", "user", "workspace", "conversation"]

class UserInfo(BaseModel):
    """User information extracted from authentication"""
    id: str
    roles: List[str] = Field(default_factory=list)
    
class SSEEvent(BaseModel):
    """SSE event model"""
    event: str
    data: Dict[str, Any] = Field(default_factory=dict)
    
class ConnectionInfo(BaseModel):
    """Information about an SSE connection"""
    id: str
    user_id: str
    connected_at: datetime
    
class ConnectionStats(BaseModel):
    """Statistics about active connections"""
    global_count: int
    channel_counts: Dict[str, Dict[str, int]]
    total: int