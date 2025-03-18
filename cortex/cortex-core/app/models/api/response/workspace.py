"""API response models for workspace endpoints."""
from typing import List

from pydantic import BaseModel

from app.models.domain.workspace import WorkspaceInfo, WorkspaceWithUsers


class WorkspaceResponse(WorkspaceInfo):
    """API response model for workspace information."""
    pass


class WorkspaceWithUsersResponse(WorkspaceWithUsers):
    """API response model for workspace with users."""
    pass


class WorkspacesResponse(BaseModel):
    """API response model for a list of workspaces."""
    
    workspaces: List[WorkspaceResponse]
    count: int
    total: int