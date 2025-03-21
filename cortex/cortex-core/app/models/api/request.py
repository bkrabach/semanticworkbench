from pydantic import BaseModel, Field
from typing import List

from ...models.base import BaseModelWithMetadata

class LoginRequest(BaseModel):
    """Login request model."""
    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")

class InputRequest(BaseModelWithMetadata):
    """Input data from clients."""
    content: str = Field(..., description="Message content")
    conversation_id: str = Field(..., description="Conversation ID")

class WorkspaceCreate(BaseModelWithMetadata):
    """Request to create a workspace."""
    name: str = Field(..., min_length=1, max_length=100, description="Workspace name")
    description: str = Field(..., min_length=1, max_length=500, description="Workspace description")

class ConversationCreate(BaseModelWithMetadata):
    """Request to create a conversation."""
    workspace_id: str = Field(..., description="ID of the parent workspace")
    topic: str = Field(..., min_length=1, max_length=200, description="Conversation topic")
    participant_ids: List[str] = Field(default_factory=list, description="List of user IDs")