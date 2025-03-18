"""
Server-Sent Events (SSE) domain models for the Cortex Core application.

This module defines the domain models related to server-sent events,
which enable real-time client updates.
"""

from datetime import datetime, timezone
from typing import Dict, Any, ClassVar
from pydantic import Field, field_validator

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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Define allowed channel types as class variable
    _ALLOWED_CHANNEL_TYPES: ClassVar[list[str]] = ['user', 'workspace', 'conversation', 'global']
    
    @field_validator('channel_type')
    @classmethod
    def validate_channel_type(cls, v: str) -> str:
        """Validate that channel_type is one of the allowed values"""
        if v not in cls._ALLOWED_CHANNEL_TYPES:
            raise ValueError(f'channel_type must be one of: {", ".join(cls._ALLOWED_CHANNEL_TYPES)}')
        return v


class SSEConnection(DomainModel):
    """
    Domain model for an SSE connection.
    
    Represents a client connection to the SSE stream.
    """
    channel_type: str
    resource_id: str
    user_id: str
    connected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_active_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Define allowed channel types as class variable
    _ALLOWED_CHANNEL_TYPES: ClassVar[list[str]] = ['user', 'workspace', 'conversation', 'global']
    
    @field_validator('channel_type')
    @classmethod
    def validate_channel_type(cls, v: str) -> str:
        """Validate that channel_type is one of the allowed values"""
        if v not in cls._ALLOWED_CHANNEL_TYPES:
            raise ValueError(f'channel_type must be one of: {", ".join(cls._ALLOWED_CHANNEL_TYPES)}')
        return v


class SSEConnectionStats(DomainModel):
    """
    Domain model for SSE connection statistics.
    
    Provides statistics about active SSE connections.
    """
    id: str = Field(default="stats")
    total_connections: int = Field(default=0)
    connections_by_channel: Dict[str, int] = Field(default_factory=dict)
    connections_by_user: Dict[str, int] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # This model explicitly declares which fields can be passed as keyword arguments
    # to ensure consistent construction across the codebase
    model_config = {
        "populate_by_name": True,
        "extra": "forbid"
    }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SSEConnectionStats":
        """
        Create an SSEConnectionStats instance from a dictionary.
        
        This factory method provides a consistent way to create instances
        from raw data dictionaries, handling any necessary transformations.
        
        Args:
            data: Dictionary containing the connection statistics
            
        Returns:
            SSEConnectionStats instance
        """
        return cls(
            id="stats",
            total_connections=data.get("total_connections", 0),
            connections_by_channel=data.get("connections_by_channel", {}),
            connections_by_user=data.get("connections_by_user", {}),
            generated_at=data.get("generated_at", datetime.now(timezone.utc))
        )