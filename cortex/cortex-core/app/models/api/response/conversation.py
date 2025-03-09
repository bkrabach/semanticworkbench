"""
Conversation API response models for the Cortex Core application.

This module defines the API response models related to conversations.
These models handle HTTP response validation and documentation.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class MessageResponse(BaseModel):
    """
    API response model for a message within a conversation.
    """
    id: str
    content: str
    role: str
    created_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        """Pydantic configuration"""
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }


class ConversationSummaryResponse(BaseModel):
    """
    API response model for a conversation summary.
    
    This model is used when returning a list of conversations without
    including all messages.
    """
    id: str
    title: str
    workspace_id: str
    modality: str
    created_at: datetime
    last_active_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)
    message_count: int = 0
    
    class Config:
        """Pydantic configuration"""
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }


class ConversationDetailResponse(BaseModel):
    """
    API response model for a detailed conversation.
    
    This model includes all messages in the conversation and is used
    when retrieving a single conversation.
    """
    id: str
    title: str
    workspace_id: str
    modality: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_active_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)
    messages: List[MessageResponse] = Field(default_factory=list)
    
    class Config:
        """Pydantic configuration"""
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }


class ConversationListResponse(BaseModel):
    """
    API response model for a list of conversations.
    """
    conversations: List[ConversationSummaryResponse] = Field(default_factory=list)
    count: int
    
    class Config:
        """Pydantic configuration"""
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }