"""Workspace service for business logic."""
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories import WorkspaceRepository, UserRepository
from app.models.domain.workspace import (
    WorkspaceCreate, WorkspaceInfo, WorkspaceUpdate, 
    WorkspaceWithUsers, UserAccess, WorkspaceUserAccess
)
from app.services.base import BaseService
from app.exceptions import ResourceNotFoundError, PermissionDeniedError


class WorkspaceService(BaseService[WorkspaceRepository, WorkspaceInfo]):
    """Service for workspace operations."""
    
    def __init__(self, db: AsyncSession):
        """Initialize the service.
        
        Args:
            db: The database session
        """
        self.user_repository = UserRepository(db)
        repository = WorkspaceRepository(db)
        super().__init__(repository, db)
    
    async def create_workspace(self, workspace_in: WorkspaceCreate, owner_id: UUID) -> WorkspaceInfo:
        """Create a new workspace.
        
        Args:
            workspace_in: The workspace creation model
            owner_id: The user ID of the workspace owner
            
        Returns:
            The created workspace
        """
        # Create the workspace in the database
        workspace_db = await self.repository.create(obj_in=workspace_in)
        
        # Add the owner to the workspace
        await self.repository.db.refresh(workspace_db)
        await self.add_user_to_workspace(workspace_db.id, owner_id, "owner")
        
        # Commit the transaction
        await self.commit()
        
        return WorkspaceInfo(
            id=workspace_db.id,
            name=workspace_db.name,
            description=workspace_db.description,
            created_at=workspace_db.created_at,
            updated_at=workspace_db.updated_at,
            metadata=workspace_db.metadata
        )
    
    async def update_workspace(
        self, workspace_id: UUID, workspace_in: WorkspaceUpdate, user_id: UUID
    ) -> WorkspaceInfo:
        """Update a workspace.
        
        Args:
            workspace_id: The workspace ID
            workspace_in: The workspace update model
            user_id: The user ID performing the update
            
        Returns:
            The updated workspace
            
        Raises:
            PermissionDeniedError: If the user doesn't have permission to update
        """
        # Check if the user has editor or owner access
        has_permission = await self.repository.has_access(
            user_id, workspace_id, required_role="editor"
        )
        
        if not has_permission:
            raise PermissionDeniedError("You don't have permission to update this workspace")
        
        # Get the workspace
        workspace_db = await self.repository.get_or_404(workspace_id)
        
        # Update the workspace
        workspace_db = await self.repository.update(db_obj=workspace_db, obj_in=workspace_in)
        await self.commit()
        
        return WorkspaceInfo(
            id=workspace_db.id,
            name=workspace_db.name,
            description=workspace_db.description,
            created_at=workspace_db.created_at,
            updated_at=workspace_db.updated_at,
            metadata=workspace_db.metadata
        )
    
    async def get_workspace(self, workspace_id: UUID, user_id: UUID) -> WorkspaceInfo:
        """Get a workspace.
        
        Args:
            workspace_id: The workspace ID
            user_id: The user ID accessing the workspace
            
        Returns:
            The workspace
            
        Raises:
            ResourceNotFoundError: If the workspace is not found
            PermissionDeniedError: If the user doesn't have access
        """
        # Check if the user has access
        has_access = await self.repository.has_access(user_id, workspace_id)
        
        if not has_access:
            raise PermissionDeniedError("You don't have access to this workspace")
        
        # Get the workspace
        workspace_db = await self.repository.get_or_404(workspace_id)
        
        return WorkspaceInfo(
            id=workspace_db.id,
            name=workspace_db.name,
            description=workspace_db.description,
            created_at=workspace_db.created_at,
            updated_at=workspace_db.updated_at,
            metadata=workspace_db.metadata
        )
    
    async def get_workspace_with_users(self, workspace_id: UUID, user_id: UUID) -> WorkspaceWithUsers:
        """Get a workspace with its users.
        
        Args:
            workspace_id: The workspace ID
            user_id: The user ID accessing the workspace
            
        Returns:
            The workspace with users
            
        Raises:
            ResourceNotFoundError: If the workspace is not found
            PermissionDeniedError: If the user doesn't have access
        """
        # Check if the user has access
        has_access = await self.repository.has_access(user_id, workspace_id)
        
        if not has_access:
            raise PermissionDeniedError("You don't have access to this workspace")
        
        # Get the workspace
        workspace_db = await self.repository.get_or_404(workspace_id)
        
        # Get the workspace users
        access_records = await self.repository.get_workspace_users(workspace_id)
        
        # Create the user access list
        user_access = [
            UserAccess(user_id=access.user_id, role=access.role)
            for access in access_records
        ]
        
        return WorkspaceWithUsers(
            id=workspace_db.id,
            name=workspace_db.name,
            description=workspace_db.description,
            created_at=workspace_db.created_at,
            updated_at=workspace_db.updated_at,
            metadata=workspace_db.metadata,
            users=user_access
        )
    
    async def add_user_to_workspace(
        self, workspace_id: UUID, user_id: UUID, role: str
    ) -> None:
        """Add a user to a workspace.
        
        Args:
            workspace_id: The workspace ID
            user_id: The user ID to add
            role: The user's role
            
        Raises:
            ResourceNotFoundError: If the workspace or user is not found
        """
        # Check that the workspace exists
        await self.repository.get_or_404(workspace_id)
        
        # Check that the user exists
        await self.user_repository.get_or_404(user_id)
        
        # Add the user to the workspace
        await self.repository.db.flush()  # Make sure workspace ID is valid
        await self.user_repository.add_user_to_workspace(user_id, workspace_id, role)
    
    async def remove_user_from_workspace(
        self, workspace_id: UUID, user_id: UUID, admin_id: UUID
    ) -> bool:
        """Remove a user from a workspace.
        
        Args:
            workspace_id: The workspace ID
            user_id: The user ID to remove
            admin_id: The user ID performing the removal
            
        Returns:
            True if the user was removed, False otherwise
            
        Raises:
            PermissionDeniedError: If the admin doesn't have permission to remove users
        """
        # Check if the admin has owner access
        has_permission = await self.repository.has_access(
            admin_id, workspace_id, required_role="owner"
        )
        
        if not has_permission:
            raise PermissionDeniedError("You don't have permission to remove users from this workspace")
        
        # Can't remove the last owner
        if user_id == admin_id:
            # Check if this is the last owner
            access_records = await self.repository.get_workspace_users(workspace_id)
            owner_count = sum(1 for access in access_records if access.role == "owner")
            
            if owner_count <= 1:
                raise PermissionDeniedError("Cannot remove the last owner from a workspace")
        
        # Remove the user from the workspace
        result = await self.user_repository.remove_user_from_workspace(user_id, workspace_id)
        
        if result:
            await self.commit()
            
        return result
    
    async def update_user_role(
        self, workspace_id: UUID, user_id: UUID, new_role: str, admin_id: UUID
    ) -> bool:
        """Update a user's role in a workspace.
        
        Args:
            workspace_id: The workspace ID
            user_id: The user ID to update
            new_role: The new role
            admin_id: The user ID performing the update
            
        Returns:
            True if the role was updated, False otherwise
            
        Raises:
            PermissionDeniedError: If the admin doesn't have permission to update roles
        """
        # Check if the admin has owner access
        has_permission = await self.repository.has_access(
            admin_id, workspace_id, required_role="owner"
        )
        
        if not has_permission:
            raise PermissionDeniedError("You don't have permission to update roles in this workspace")
        
        # Can't demote yourself if you're the last owner
        if user_id == admin_id and new_role != "owner":
            # Check if this is the last owner
            access_records = await self.repository.get_workspace_users(workspace_id)
            owner_count = sum(1 for access in access_records if access.role == "owner")
            
            if owner_count <= 1:
                raise PermissionDeniedError("Cannot demote the last owner of a workspace")
        
        # Get the current access record
        query = await self.repository.db.execute(
            "SELECT * FROM user_workspace_access WHERE user_id = :user_id AND workspace_id = :workspace_id",
            {"user_id": str(user_id), "workspace_id": str(workspace_id)}
        )
        access = query.first()
        
        if not access:
            return False
            
        # Update the role
        await self.repository.db.execute(
            "UPDATE user_workspace_access SET role = :role WHERE user_id = :user_id AND workspace_id = :workspace_id",
            {"role": new_role, "user_id": str(user_id), "workspace_id": str(workspace_id)}
        )
        
        await self.commit()
        return True