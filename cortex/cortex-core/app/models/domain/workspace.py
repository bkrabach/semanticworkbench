"""Workspace domain models for the Cortex application."""
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.models.domain.base import BaseModelWithMetadata


class WorkspaceCreate(BaseModel):
    """Model for creating a new workspace."""
    
    name: str
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkspaceInfo(BaseModelWithMetadata):
    """Model for workspace information."""
    
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: Optional[str] = None


class WorkspaceUpdate(BaseModel):
    """Model for updating a workspace."""
    
    name: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class WorkspaceUserAccess(BaseModel):
    """Model for granting a user access to a workspace."""
    
    user_id: UUID
    role: str  # 'owner', 'editor', 'viewer'


class WorkspaceWithUsers(WorkspaceInfo):
    """Workspace model with user access information."""
    
    users: List["UserAccess"] = Field(default_factory=list)


class UserAccess(BaseModel):
    """Model for user's access in a workspace."""
    
    user_id: UUID
    role: str  # 'owner', 'editor', 'viewer'


# Update forward references
WorkspaceWithUsers.model_rebuild()