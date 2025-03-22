"""
API schemas for Cortex Core.

These Pydantic models define the request and response schemas for the API endpoints.
They are separate from domain models to maintain a clear boundary between API
and internal representations.
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.models.domain import User, Workspace, Conversation


# Auth schemas
class LoginRequest(BaseModel):
    """Login request parameters."""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Response returned upon successful login."""
    access_token: str
    token_type: str = "bearer"


# Workspace schemas
class WorkspaceCreateRequest(BaseModel):
    """Request to create a new workspace."""
    name: str
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# Conversation schemas
class ConversationCreateRequest(BaseModel):
    """Request to create a new conversation."""
    workspace_id: str
    topic: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# Message schemas
class InputMessage(BaseModel):
    """Schema for the chat input endpoint."""
    content: str
    conversation_id: str
    metadata: Optional[Dict[str, Any]] = None


class MessageAck(BaseModel):
    """Acknowledgment response for message input."""
    status: str = "received"
    data: Dict[str, Any]


# Responses for list endpoints
class WorkspaceListResponse(BaseModel):
    """Response for listing workspaces."""
    workspaces: List[Workspace]


class ConversationListResponse(BaseModel):
    """Response for listing conversations."""
    conversations: List[Conversation]


# User profile response
class UserProfileResponse(BaseModel):
    """Response for user profile information."""
    profile: User