# models.py for memory service
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class MemoryEntry(BaseModel):
    """A single entry in the memory store."""

    conversation_id: str
    memory_content: str
    last_updated: str  # ISO format datetime


class MemoryUpdateRequest(BaseModel):
    """Request to update a conversation's memory."""

    conversation_id: str
    new_messages: List[Dict[str, Any]]  # List of message objects


class MemoryUpdateResponse(BaseModel):
    """Response containing the updated memory."""

    conversation_id: str
    updated_memory: str
    success: bool


class MemoryRetrievalRequest(BaseModel):
    """Request to retrieve a conversation's memory."""

    conversation_id: str


class MemoryRetrievalResponse(BaseModel):
    """Response containing the retrieved memory."""

    conversation_id: str
    memory_content: Optional[str] = None
    exists: bool
