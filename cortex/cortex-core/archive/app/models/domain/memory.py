"""Memory domain models for the Cortex application."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.models.domain.base import BaseModelWithMetadata


class MemoryItemCreate(BaseModel):
    """Model for creating a new memory item."""
    
    item_type: str
    content: Optional[str] = None
    binary_content: Optional[bytes] = None
    content_type: Optional[str] = None
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MemoryItemInfo(BaseModelWithMetadata):
    """Model for memory item information."""
    
    id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID
    item_type: str
    content: Optional[str] = None
    content_type: Optional[str] = None
    expires_at: Optional[datetime] = None


class MemoryQuery(BaseModel):
    """Model for querying memory items."""
    
    item_type: Optional[str] = None
    content_type: Optional[str] = None
    metadata_filter: Dict[str, Any] = Field(default_factory=dict)
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    limit: int = 20
    offset: int = 0


class MemoryContext(BaseModel):
    """Model for representing memory context."""
    
    items: List[MemoryItemInfo] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)