"""Workspace service for handling workspace-related business logic."""

from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session

from app.database.repositories.workspace_repository import WorkspaceRepository
from app.models.domain.workspace import Workspace
from app.services.base import Service
from app.components.event_system import EventSystem

class WorkspaceService(Service[Workspace, WorkspaceRepository]):
    """Service for workspace-related operations"""
    
    def __init__(self, db_session: Session, repository: WorkspaceRepository, event_system: Optional[EventSystem] = None):
        self.db = db_session
        self.repository = repository
        self.event_system = event_system
        
    def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        """Get a workspace by ID"""
        return self.repository.get_by_id(workspace_id)
    
    def get_user_workspaces(self, user_id: str, limit: Optional[int] = None) -> List[Workspace]:
        """Get all workspaces for a user"""
        return self.repository.get_user_workspaces(user_id, limit)
        
    def create_workspace(self, user_id: str, name: str, description: Optional[str] = None) -> Workspace:
        """Create a new workspace"""
        # Business logic - pre-creation validations can go here
        
        # Call repository to create workspace
        workspace = self.repository.create_workspace(
            user_id=user_id,
            name=name,
            description=description
        )
        
        # Post-creation logic (e.g., publish events)
        if self.event_system:
            self._publish_workspace_created_event(workspace)
            
        return workspace
        
    def update_workspace(self, workspace_id: str, name: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Optional[Workspace]:
        """Update a workspace"""
        # Business logic - pre-update validations can go here
        
        # Call repository to update workspace
        workspace = self.repository.update_workspace(
            workspace_id=workspace_id,
            name=name,
            metadata=metadata
        )
        
        # Post-update logic (e.g., publish events)
        if workspace and self.event_system:
            self._publish_workspace_updated_event(workspace)
            
        return workspace
        
    def delete_workspace(self, workspace_id: str) -> bool:
        """Delete a workspace"""
        # Business logic - pre-deletion validations can go here
        
        # Store workspace before deletion for events
        workspace = self.repository.get_by_id(workspace_id)
        if not workspace:
            return False
            
        # Call repository to delete workspace
        result = self.repository.delete_workspace(workspace_id)
        
        # Post-deletion logic (e.g., publish events)
        if result and self.event_system:
            self._publish_workspace_deleted_event(workspace)
            
        return result
    
    def _publish_workspace_created_event(self, workspace: Workspace) -> None:
        """Publish workspace created event"""
        if not self.event_system:
            return
            
        self.event_system.publish(
            event_type="workspace.created",
            data={
                "workspace_id": workspace.id,
                "user_id": workspace.user_id,
                "name": workspace.name
            },
            source="workspace_service"
        )
        
    def _publish_workspace_updated_event(self, workspace: Workspace) -> None:
        """Publish workspace updated event"""
        if not self.event_system:
            return
            
        self.event_system.publish(
            event_type="workspace.updated",
            data={
                "workspace_id": workspace.id,
                "user_id": workspace.user_id,
                "name": workspace.name
            },
            source="workspace_service"
        )
        
    def _publish_workspace_deleted_event(self, workspace: Workspace) -> None:
        """Publish workspace deleted event"""
        if not self.event_system:
            return
            
        self.event_system.publish(
            event_type="workspace.deleted",
            data={
                "workspace_id": workspace.id,
                "user_id": workspace.user_id
            },
            source="workspace_service"
        )

# Factory function for dependency injection
def get_workspace_service(
    db: Session,
    repository: WorkspaceRepository,
    event_system: Optional[EventSystem] = None
) -> WorkspaceService:
    """Get a workspace service instance"""
    return WorkspaceService(db, repository, event_system)