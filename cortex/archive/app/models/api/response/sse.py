"""
API response models for Server-Sent Events (SSE).

This module defines the response models for SSE-related API endpoints.
"""

from datetime import datetime
from typing import Dict
from pydantic import BaseModel


class SSEConnectionStatsResponse(BaseModel):
    """Response model for SSE connection statistics."""
    total_connections: int
    connections_by_channel: Dict[str, int]
    connections_by_user: Dict[str, int]
    generated_at: datetime