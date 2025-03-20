"""Workspace repository for database operations."""
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Workspace, UserWorkspaceAccess
from app.database.repositories.base import BaseRepository
from app.models.domain.workspace import WorkspaceCreate, WorkspaceUpdate


class WorkspaceRepository(BaseRepository[Workspace, WorkspaceCreate, WorkspaceUpdate]):
    """Repository for workspace operations."""
    
    def __init__(self, db: AsyncSession):
        """Initialize the repository.
        
        Args:
            db: The database session
        """
        super().__init__(Workspace, db)
    
    async def get_workspace_users(self, workspace_id: UUID) -> List[UserWorkspaceAccess]:
        """Get all users that have access to a workspace.
        
        Args:
            workspace_id: The workspace ID
            
        Returns:
            List of user workspace access records
        """
        query = select(UserWorkspaceAccess).where(UserWorkspaceAccess.workspace_id == workspace_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_user_role_in_workspace(self, user_id: UUID, workspace_id: UUID) -> Optional[str]:
        """Get a user's role in a workspace.
        
        Args:
            user_id: The user ID
            workspace_id: The workspace ID
            
        Returns:
            The user's role or None if the user doesn't have access
        """
        query = select(UserWorkspaceAccess.role).where(
            UserWorkspaceAccess.user_id == user_id,
            UserWorkspaceAccess.workspace_id == workspace_id
        )
        result = await self.db.execute(query)
        role = result.scalar_one_or_none()
        return role
    
    async def has_access(self, user_id: UUID, workspace_id: UUID, required_role: Optional[str] = None) -> bool:
        """Check if a user has access to a workspace.
        
        Args:
            user_id: The user ID
            workspace_id: The workspace ID
            required_role: Optional role requirement
            
        Returns:
            True if the user has access, False otherwise
        """
        role = await self.get_user_role_in_workspace(user_id, workspace_id)
        
        if role is None:
            return False
            
        if required_role is None:
            return True
            
        # Simple role hierarchy: owner > editor > viewer
        if required_role == "viewer":
            return role in ["viewer", "editor", "owner"]
        elif required_role == "editor":
            return role in ["editor", "owner"]
        elif required_role == "owner":
            return role == "owner"
            
        return False