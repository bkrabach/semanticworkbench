"""API response models for SSE (Server-Sent Events)."""
from datetime import datetime
from typing import Any, Dict, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field


class SseEvent(BaseModel):
    """Base model for SSE events."""
    
    event: str
    id: str
    data: Dict[str, Any] = Field(default_factory=dict)
    retry: Optional[int] = None


class MessageEvent(SseEvent):
    """SSE event for a new message."""
    
    event: str = "message"
    data: Dict[str, Any]


class ConversationUpdateEvent(SseEvent):
    """SSE event for a conversation update."""
    
    event: str = "conversation_update"
    data: Dict[str, Any]


class TypingIndicatorEvent(SseEvent):
    """SSE event for typing indicator."""
    
    event: str = "typing"
    data: Dict[str, Any]
    
    
class HeartbeatEvent(SseEvent):
    """SSE event for heartbeat."""
    
    event: str = "heartbeat"
    data: Dict[str, Any] = Field(default_factory=lambda: {"timestamp": datetime.now().isoformat()})
    retry: int = 15000  # 15 seconds