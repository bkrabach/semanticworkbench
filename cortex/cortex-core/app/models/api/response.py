from pydantic import BaseModel, Field
from typing import Dict, Any, List

from ...models.domain import Workspace, Conversation

class LoginResponse(BaseModel):
    """Login response model."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(..., description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    claims: Dict[str, Any] = Field(..., description="User claims")

class InputResponse(BaseModel):
    """Input response model."""
    status: str = Field(..., description="Status of the operation")
    data: Dict[str, Any] = Field(..., description="Echoed input data")

class WorkspaceResponse(BaseModel):
    """Workspace response model."""
    status: str = Field(..., description="Status of the operation")
    workspace: Workspace = Field(..., description="Created workspace")

class WorkspacesListResponse(BaseModel):
    """Workspaces list response model."""
    workspaces: List[Workspace] = Field(..., description="List of workspaces")
    total: int = Field(..., description="Total number of workspaces")

class ConversationResponse(BaseModel):
    """Conversation response model."""
    status: str = Field(..., description="Status of the operation")
    conversation: Conversation = Field(..., description="Created conversation")

class ConversationsListResponse(BaseModel):
    """Conversations list response model."""
    conversations: List[Conversation] = Field(..., description="List of conversations")
    total: int = Field(..., description="Total number of conversations")

class ErrorResponse(BaseModel):
    """Error response model."""
    error: Dict[str, Any] = Field(..., description="Error details")