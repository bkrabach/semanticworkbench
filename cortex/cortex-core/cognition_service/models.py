"""
Cognition Service - Models

Defines the Pydantic models for events, requests, and responses used in the
Cognition Service for LLM interaction and event handling.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Union

from app.models.llm import FinalAnswer, ToolRequest
from pydantic import BaseModel, Field


# Event models
class EventType(str, Enum):
    """Types of events handled by the Cognition Service."""

    CONTEXT_UPDATE = "context_update"
    USER_INPUT = "user_input"
    SYSTEM_MESSAGE = "system_message"


class Event(BaseModel):
    """Base model for all events."""

    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    conversation_id: str
    data: Dict[str, Any]


class UserInputEvent(Event):
    """Event for user input requiring AI response."""

    event_type: EventType = EventType.USER_INPUT
    data: Dict[str, Any] = Field(...)

    @property
    def message_text(self) -> str:
        """Extract the user message text from the event data."""
        content = self.data.get("content")
        return str(content) if content is not None else ""

    @property
    def user_id(self) -> str:
        """Extract the user ID from the event data."""
        user_id = self.data.get("user_id")
        return str(user_id) if user_id is not None else ""


# LLM I/O models
class MessageRole(str, Enum):
    """Role types for conversation messages."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class Message(BaseModel):
    """Model for a single conversation message."""

    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Conversation(BaseModel):
    """Model representing a conversation history."""

    id: str
    messages: List[Message] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Type alias for LLM output
LLMOutput = Union[FinalAnswer, ToolRequest]
