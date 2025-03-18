"""User repository for database operations."""
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User, UserWorkspaceAccess, Workspace
from app.database.repositories.base import BaseRepository
from app.models.domain.user import UserCreate, UserInfo, UserUpdate


class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
    """Repository for user operations."""
    
    def __init__(self, db: AsyncSession):
        """Initialize the repository.
        
        Args:
            db: The database session
        """
        super().__init__(User, db)
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email.
        
        Args:
            email: The user's email
            
        Returns:
            The user or None if not found
        """
        query = select(User).where(User.email == email)
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def get_user_workspaces(self, user_id: UUID) -> List[UserWorkspaceAccess]:
        """Get all workspaces that a user has access to.
        
        Args:
            user_id: The user ID
            
        Returns:
            List of user workspace access records
        """
        query = select(UserWorkspaceAccess).where(UserWorkspaceAccess.user_id == user_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def add_user_to_workspace(
        self, user_id: UUID, workspace_id: UUID, role: str
    ) -> UserWorkspaceAccess:
        """Add a user to a workspace.
        
        Args:
            user_id: The user ID
            workspace_id: The workspace ID
            role: The user's role in the workspace
            
        Returns:
            The created user workspace access record
        """
        access = UserWorkspaceAccess(
            user_id=user_id,
            workspace_id=workspace_id,
            role=role
        )
        self.db.add(access)
        await self.db.flush()
        return access
    
    async def remove_user_from_workspace(self, user_id: UUID, workspace_id: UUID) -> bool:
        """Remove a user from a workspace.
        
        Args:
            user_id: The user ID
            workspace_id: The workspace ID
            
        Returns:
            True if the access was removed, False otherwise
        """
        query = select(UserWorkspaceAccess).where(
            UserWorkspaceAccess.user_id == user_id,
            UserWorkspaceAccess.workspace_id == workspace_id
        )
        result = await self.db.execute(query)
        access = result.scalars().first()
        
        if access:
            await self.db.delete(access)
            return True
        return False