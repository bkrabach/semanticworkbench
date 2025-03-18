"""Conversation domain models for the Cortex application."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.models.domain.base import BaseModelWithMetadata


class MessageCreate(BaseModel):
    """Model for creating a new message."""
    
    content: str
    role: str = "user"  # 'user', 'assistant', 'system'
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MessageInfo(BaseModelWithMetadata):
    """Model for message information."""
    
    id: UUID = Field(default_factory=uuid4)
    conversation_id: UUID
    user_id: Optional[UUID] = None
    role: str  # 'user', 'assistant', 'system'
    content: str


class ConversationCreate(BaseModel):
    """Model for creating a new conversation."""
    
    title: str
    modality: str = "text"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationInfo(BaseModelWithMetadata):
    """Model for conversation information."""
    
    id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID
    title: str
    modality: str = "text"
    last_active_at: datetime = Field(default_factory=datetime.now)


class ConversationUpdate(BaseModel):
    """Model for updating a conversation."""
    
    title: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ConversationWithMessages(ConversationInfo):
    """Conversation model with messages."""
    
    messages: List[MessageInfo] = Field(default_factory=list)