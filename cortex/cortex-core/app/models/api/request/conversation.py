"""
Conversation API request models for the Cortex Core application.

This module defines the API request models related to conversations.
These models handle HTTP request validation and documentation.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class CreateConversationRequest(BaseModel):
    """
    Request model for creating a new conversation.
    """
    title: str = Field(..., description="Conversation title")
    modality: str = Field(..., description="Conversation modality (e.g., 'text', 'voice')")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata")


class AddMessageRequest(BaseModel):
    """
    Request model for adding a message to a conversation.
    """
    content: str = Field(..., description="Message content")
    role: str = Field(..., description="Message role (user or assistant)")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata")


class UpdateTitleRequest(BaseModel):
    """
    Request model for updating a conversation's title.
    """
    title: str = Field(..., description="New conversation title")


class UpdateMetadataRequest(BaseModel):
    """
    Request model for updating a conversation's metadata.
    """
    metadata: Dict[str, Any] = Field(..., description="New metadata dictionary")