"""User domain models for the Cortex application."""
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, EmailStr, Field

from app.models.domain.base import BaseModelWithMetadata


class UserCreate(BaseModel):
    """Model for creating a new user."""
    
    email: EmailStr
    password: str
    name: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UserInfo(BaseModelWithMetadata):
    """Model for user information."""
    
    id: UUID = Field(default_factory=uuid4)
    email: EmailStr
    name: Optional[str] = None
    is_active: bool = True


class UserUpdate(BaseModel):
    """Model for updating a user."""
    
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class UserWithWorkspaces(UserInfo):
    """User model with workspace access."""
    
    workspaces: List["WorkspaceAccess"] = Field(default_factory=list)


class WorkspaceAccess(BaseModel):
    """Model for user's access to a workspace."""
    
    workspace_id: UUID
    role: str  # 'owner', 'editor', 'viewer'


# Update forward references
UserWithWorkspaces.model_rebuild()