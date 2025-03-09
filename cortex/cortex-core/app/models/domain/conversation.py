"""
Conversation domain models for the Cortex Core application.

This module defines the domain models related to conversations and messages,
which are central to the user interaction within the system.
"""

from datetime import datetime
from typing import List
from pydantic import Field

from app.models.domain.base import TimestampedModel, MetadataModel


class Message(MetadataModel):
    """
    Domain model for a message within a conversation.
    
    Represents a single message exchanged between the user and the system.
    """
    content: str
    role: str
    created_at: datetime


class Conversation(TimestampedModel, MetadataModel):
    """
    Domain model for a conversation.
    
    Conversations hold a series of messages exchanged between the
    user and the system within a specific workspace.
    """
    workspace_id: str
    title: str
    modality: str
    last_active_at: datetime
    messages: List[Message] = Field(default_factory=list)