"""API request models for workspace endpoints."""

from app.models.domain.workspace import (
    WorkspaceCreate, WorkspaceUpdate, WorkspaceUserAccess
)


class CreateWorkspaceRequest(WorkspaceCreate):
    """API request model for creating a workspace."""
    pass


class UpdateWorkspaceRequest(WorkspaceUpdate):
    """API request model for updating a workspace."""
    pass


class AddUserRequest(WorkspaceUserAccess):
    """API request model for adding a user to a workspace."""
    pass


class RemoveUserRequest(WorkspaceUserAccess):
    """API request model for removing a user from a workspace."""
    pass