"""
Server-Sent Events (SSE) domain models for the Cortex Core application.

This module defines the domain models related to server-sent events,
which enable real-time client updates.
"""

from datetime import datetime
from typing import Dict, Any
from pydantic import Field, validator

from app.models.domain.base import DomainModel, MetadataModel


class SSEEvent(MetadataModel):
    """
    Domain model for an SSE event.
    
    Represents an event that can be sent to clients via SSE.
    """
    event_type: str
    data: Dict[str, Any] = Field(default_factory=dict)
    channel_type: str
    resource_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    
    @validator('channel_type')
    def validate_channel_type(cls, v):
        """Validate that channel_type is one of the allowed values"""
        allowed_values = ['user', 'workspace', 'conversation', 'global']
        if v not in allowed_values:
            raise ValueError(f'channel_type must be one of: {", ".join(allowed_values)}')
        return v


class SSEConnection(DomainModel):
    """
    Domain model for an SSE connection.
    
    Represents a client connection to the SSE stream.
    """
    channel_type: str
    resource_id: str
    user_id: str
    connected_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    last_active_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    
    @validator('channel_type')
    def validate_channel_type(cls, v):
        """Validate that channel_type is one of the allowed values"""
        allowed_values = ['user', 'workspace', 'conversation', 'global']
        if v not in allowed_values:
            raise ValueError(f'channel_type must be one of: {", ".join(allowed_values)}')
        return v


class SSEConnectionStats(DomainModel):
    """
    Domain model for SSE connection statistics.
    
    Provides statistics about active SSE connections.
    """
    id: str = Field(default="stats")
    total_connections: int = 0
    connections_by_channel: Dict[str, int] = Field(default_factory=dict)
    connections_by_user: Dict[str, int] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=lambda: datetime.utcnow())