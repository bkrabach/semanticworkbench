"""
Domain models for Cortex Core.

These Pydantic models represent the core entities in our system:
- User: A user of the system
- Workspace: A container for conversations
- Conversation: A thread of messages
- Message: An individual message in a conversation
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class User(BaseModel):
    """A user of the system."""
    id: str
    name: str
    email: str


class Workspace(BaseModel):
    """
    A workspace or context container owned by a user.
    A workspace contains conversations.
    """
    id: str
    owner_id: str  # references User.id
    name: str


class Conversation(BaseModel):
    """
    A conversation (chat thread) within a workspace.
    A conversation contains a sequence of messages.
    """
    id: str
    workspace_id: str  # references Workspace.id
    title: Optional[str] = None


class Message(BaseModel):
    """
    A single message in a conversation.
    Can be from the user or the assistant.
    """
    id: str
    conversation_id: str  # references Conversation.id
    sender: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)