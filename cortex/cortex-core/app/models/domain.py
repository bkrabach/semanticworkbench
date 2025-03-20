import uuid
from datetime import datetime
from typing import List
from pydantic import Field

from .base import BaseModelWithMetadata

class User(BaseModelWithMetadata):
    """System user model."""
    user_id: str
    name: str
    email: str

class Workspace(BaseModelWithMetadata):
    """Workspace model."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    owner_id: str

class Conversation(BaseModelWithMetadata):
    """Conversation model."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workspace_id: str
    topic: str
    participant_ids: List[str]

class Message(BaseModelWithMetadata):
    """Message model."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str
    sender_id: str
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

def generate_id() -> str:
    """Generate a unique ID."""
    return str(uuid.uuid4())