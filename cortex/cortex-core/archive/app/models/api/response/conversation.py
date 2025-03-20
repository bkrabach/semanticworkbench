"""API response models for conversation endpoints."""
from typing import List

from pydantic import BaseModel

from app.models.domain.conversation import (
    ConversationInfo, ConversationWithMessages, MessageInfo
)


class ConversationResponse(ConversationInfo):
    """API response model for conversation information."""
    pass


class ConversationWithMessagesResponse(ConversationWithMessages):
    """API response model for conversation with messages."""
    pass


class MessageResponse(MessageInfo):
    """API response model for message information."""
    pass


class ConversationsResponse(BaseModel):
    """API response model for a list of conversations."""
    
    conversations: List[ConversationResponse]
    count: int
    total: int


class MessagesResponse(BaseModel):
    """API response model for a list of messages."""
    
    messages: List[MessageResponse]
    count: int
    total: int