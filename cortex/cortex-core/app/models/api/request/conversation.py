"""API request models for conversation endpoints."""
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.models.domain.conversation import (
    ConversationCreate, ConversationUpdate, MessageCreate
)


class CreateConversationRequest(ConversationCreate):
    """API request model for creating a conversation."""
    
    workspace_id: UUID


class UpdateConversationRequest(ConversationUpdate):
    """API request model for updating a conversation."""
    pass


class AddMessageRequest(MessageCreate):
    """API request model for adding a message to a conversation."""
    pass


class GetMessagesRequest(BaseModel):
    """API request model for getting messages in a conversation."""
    
    limit: int = 50
    before_id: Optional[UUID] = None