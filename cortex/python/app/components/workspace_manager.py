"""
Workspace Manager Component

This module implements a workspace manager that handles workspaces for user sessions.
Workspaces serve as containers for related activities, data, and context.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Union, Any

from fastapi import HTTPException, status
from pydantic import BaseModel, Field

from app.cache.redis import redis_cache
from app.config import settings
from app.database.connection import get_session
from app.database.models import Workspace as WorkspaceModel
from app.utils.logger import get_contextual_logger

# Configure logger
logger = get_contextual_logger("components.workspace_manager")


class WorkspaceMetadata(BaseModel):
    """Model for workspace metadata"""

    name: Optional[str] = None
    description: Optional[str] = None
    type: str = "default"
    tags: List[str] = Field(default_factory=list)
    custom_data: Dict[str, Any] = Field(default_factory=dict)


class Workspace(BaseModel):
    """Model representing a workspace"""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    owner_id: Optional[uuid.UUID] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_active_at: datetime = Field(default_factory=datetime.utcnow)
    is_archived: bool = False
    is_private: bool = True
    metadata: WorkspaceMetadata = Field(default_factory=WorkspaceMetadata)

    class Config:
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "owner_id": "550e8400-e29b-41d4-a716-446655440001",
                "created_at": "2025-03-06T15:30:45.123456",
                "updated_at": "2025-03-06T15:30:45.123456",
                "last_active_at": "2025-03-06T15:30:45.123456",
                "is_archived": False,
                "is_private": True,
                "metadata": {
                    "name": "My Workspace",
                    "description": "A workspace for my project",
                    "type": "project",
                    "tags": ["project", "important"],
                    "custom_data": {"priority": "high"},
                },
            }
        }


class WorkspaceManager:
    """
    Workspace Manager for handling user workspaces

    This class provides functionality for creating, retrieving, and managing
    workspaces, which serve as containers for related activities and context.
    """

    WORKSPACE_CACHE_PREFIX = "workspace:"
    WORKSPACE_CACHE_TTL = 3600  # 1 hour in seconds

    def __init__(self):
        """Initialize the workspace manager"""
        # In-memory cache for active workspaces
        self.active_workspaces: Dict[uuid.UUID, Workspace] = {}

        # User workspace mapping (user_id -> set of workspace_ids)
        self.user_workspaces: Dict[uuid.UUID, Set[uuid.UUID]] = {}

        logger.info("Workspace manager initialized")

    async def create_workspace(
        self,
        owner_id: Optional[uuid.UUID] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        workspace_type: str = "default",
        is_private: bool = True,
        tags: Optional[List[str]] = None,
        custom_data: Optional[Dict[str, Any]] = None,
    ) -> Workspace:
        """
        Create a new workspace

        Args:
            owner_id: Optional owner user ID
            name: Optional workspace name
            description: Optional workspace description
            workspace_type: Workspace type
            is_private: Whether the workspace is private
            tags: Optional tags for the workspace
            custom_data: Optional custom data for the workspace

        Returns:
            New workspace
        """
        try:
            # Create metadata
            metadata = WorkspaceMetadata(
                name=name,
                description=description,
                type=workspace_type,
                tags=tags or [],
                custom_data=custom_data or {},
            )

            # Create workspace
            workspace_id = uuid.uuid4()
            workspace = Workspace(
                id=workspace_id,
                owner_id=owner_id,
                is_private=is_private,
                metadata=metadata,
            )

            # Save to database
            async with get_session() as db:
                db_workspace = WorkspaceModel(
                    id=str(workspace.id),
                    owner_id=str(workspace.owner_id) if workspace.owner_id else None,
                    created_at=workspace.created_at,
                    updated_at=workspace.updated_at,
                    last_active_at=workspace.last_active_at,
                    is_archived=workspace.is_archived,
                    is_private=workspace.is_private,
                    metadata=workspace.metadata.dict(),
                )

                db.add(db_workspace)
                await db.commit()
                await db.refresh(db_workspace)

            # Add to cache
            self.active_workspaces[workspace_id] = workspace
            await self._cache_workspace(workspace)

            # Update user workspace mapping
            if owner_id:
                if owner_id not in self.user_workspaces:
                    self.user_workspaces[owner_id] = set()
                self.user_workspaces[owner_id].add(workspace_id)

            logger.info(f"Created workspace: {workspace_id}")
            return workspace

        except Exception as e:
            logger.error(f"Failed to create workspace: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create workspace: {str(e)}",
            )

    async def get_workspace(self, workspace_id: uuid.UUID) -> Optional[Workspace]:
        """
        Get a workspace by ID

        Args:
            workspace_id: Workspace ID

        Returns:
            Workspace or None if not found
        """
        try:
            # Check in-memory cache first
            workspace = self.active_workspaces.get(workspace_id)

            if workspace is None:
                # Try to get from Redis cache
                cached_workspace = await redis_cache.get(
                    key=self._get_cache_key(workspace_id)
                )

                if cached_workspace:
                    workspace = Workspace(**cached_workspace)

                    # Add to in-memory cache
                    self.active_workspaces[workspace_id] = workspace

                    # Update user workspace mapping
                    if workspace.owner_id:
                        if workspace.owner_id not in self.user_workspaces:
                            self.user_workspaces[workspace.owner_id] = set()
                        self.user_workspaces[workspace.owner_id].add(workspace_id)

            if workspace is None:
                # Try to get from database
                async with get_session() as db:
                    db_workspace = await db.get(WorkspaceModel, str(workspace_id))

                    if db_workspace:
                        # Convert to Workspace model
                        workspace = Workspace(
                            id=uuid.UUID(db_workspace.id),
                            owner_id=uuid.UUID(db_workspace.owner_id)
                            if db_workspace.owner_id
                            else None,
                            created_at=db_workspace.created_at,
                            updated_at=db_workspace.updated_at,
                            last_active_at=db_workspace.last_active_at,
                            is_archived=db_workspace.is_archived,
                            is_private=db_workspace.is_private,
                            metadata=WorkspaceMetadata(**db_workspace.metadata),
                        )

                        # Add to caches
                        self.active_workspaces[workspace_id] = workspace
                        await self._cache_workspace(workspace)

                        # Update user workspace mapping
                        if workspace.owner_id:
                            if workspace.owner_id not in self.user_workspaces:
                                self.user_workspaces[workspace.owner_id] = set()
                            self.user_workspaces[workspace.owner_id].add(workspace_id)

            if workspace is None:
                logger.warning(f"Workspace not found: {workspace_id}")
                return None

            # Update last active time
            workspace.last_active_at = datetime.utcnow()
            workspace.updated_at = datetime.utcnow()

            # Update cache
            await self._cache_workspace(workspace)

            return workspace

        except Exception as e:
            logger.error(f"Failed to get workspace: {str(e)}", exc_info=True)
            return None

    async def update_workspace(
        self,
        workspace_id: uuid.UUID,
        owner_id: Optional[uuid.UUID] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        workspace_type: Optional[str] = None,
        is_private: Optional[bool] = None,
        is_archived: Optional[bool] = None,
        tags: Optional[List[str]] = None,
        custom_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[Workspace]:
        """
        Update a workspace

        Args:
            workspace_id: Workspace ID to update
            owner_id: Optional new owner user ID
            name: Optional new workspace name
            description: Optional new workspace description
            workspace_type: Optional new workspace type
            is_private: Optional new privacy setting
            is_archived: Optional new archive status
            tags: Optional new tags
            custom_data: Optional new custom data

        Returns:
            Updated workspace or None if not found
        """
        try:
            # Get current workspace
            workspace = await self.get_workspace(workspace_id)
            if workspace is None:
                logger.warning(f"Workspace not found for update: {workspace_id}")
                return None

            # Update workspace properties
            if owner_id is not None:
                # If owner changed, update user workspace mapping
                if workspace.owner_id and workspace.owner_id != owner_id:
                    if workspace.owner_id in self.user_workspaces:
                        self.user_workspaces[workspace.owner_id].discard(workspace_id)

                workspace.owner_id = owner_id

                # Add to new owner's workspace list
                if owner_id:
                    if owner_id not in self.user_workspaces:
                        self.user_workspaces[owner_id] = set()
                    self.user_workspaces[owner_id].add(workspace_id)

            if is_private is not None:
                workspace.is_private = is_private

            if is_archived is not None:
                workspace.is_archived = is_archived

            # Update metadata
            metadata_updated = False

            if name is not None:
                workspace.metadata.name = name
                metadata_updated = True

            if description is not None:
                workspace.metadata.description = description
                metadata_updated = True

            if workspace_type is not None:
                workspace.metadata.type = workspace_type
                metadata_updated = True

            if tags is not None:
                workspace.metadata.tags = tags
                metadata_updated = True

            if custom_data is not None:
                workspace.metadata.custom_data = custom_data
                metadata_updated = True

            # Update timestamps
            workspace.updated_at = datetime.utcnow()
            workspace.last_active_at = datetime.utcnow()

            # Save to database
            async with get_session() as db:
                db_workspace = await db.get(WorkspaceModel, str(workspace_id))

                if db_workspace:
                    db_workspace.owner_id = (
                        str(workspace.owner_id) if workspace.owner_id else None
                    )
                    db_workspace.updated_at = workspace.updated_at
                    db_workspace.last_active_at = workspace.last_active_at
                    db_workspace.is_archived = workspace.is_archived
                    db_workspace.is_private = workspace.is_private
                    db_workspace.metadata = workspace.metadata.dict()

                    await db.commit()
                    await db.refresh(db_workspace)
                else:
                    logger.warning(f"Workspace not found in database: {workspace_id}")

            # Update caches
            self.active_workspaces[workspace_id] = workspace
            await self._cache_workspace(workspace)

            logger.info(f"Updated workspace: {workspace_id}")
            return workspace

        except Exception as e:
            logger.error(f"Failed to update workspace: {str(e)}", exc_info=True)
            return None

    async def delete_workspace(self, workspace_id: uuid.UUID) -> bool:
        """
        Delete a workspace

        Args:
            workspace_id: Workspace ID to delete

        Returns:
            True if deleted, False if not found or error
        """
        try:
            # Get current workspace
            workspace = await self.get_workspace(workspace_id)
            if workspace is None:
                logger.warning(f"Workspace not found for deletion: {workspace_id}")
                return False

            # Remove from user workspace mapping
            if workspace.owner_id and workspace.owner_id in self.user_workspaces:
                self.user_workspaces[workspace.owner_id].discard(workspace_id)

            # Remove from in-memory cache
            if workspace_id in self.active_workspaces:
                del self.active_workspaces[workspace_id]

            # Remove from Redis cache
            await redis_cache.delete(key=self._get_cache_key(workspace_id))

            # Delete from database
            async with get_session() as db:
                db_workspace = await db.get(WorkspaceModel, str(workspace_id))

                if db_workspace:
                    await db.delete(db_workspace)
                    await db.commit()
                else:
                    logger.warning(f"Workspace not found in database: {workspace_id}")

            logger.info(f"Deleted workspace: {workspace_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete workspace: {str(e)}", exc_info=True)
            return False

    async def archive_workspace(self, workspace_id: uuid.UUID) -> bool:
        """
        Archive a workspace

        Args:
            workspace_id: Workspace ID to archive

        Returns:
            True if archived, False if not found or error
        """
        try:
            # Update workspace with archived status
            workspace = await self.update_workspace(
                workspace_id=workspace_id,
                is_archived=True,
            )

            return workspace is not None

        except Exception as e:
            logger.error(f"Failed to archive workspace: {str(e)}", exc_info=True)
            return False

    async def get_user_workspaces(
        self,
        user_id: uuid.UUID,
        include_archived: bool = False,
    ) -> List[Workspace]:
        """
        Get all workspaces for a user

        Args:
            user_id: User ID
            include_archived: Whether to include archived workspaces

        Returns:
            List of workspaces
        """
        try:
            result = []

            # Check in-memory mapping
            workspace_ids = self.user_workspaces.get(user_id, set())

            if workspace_ids:
                # Get workspaces from cache or database
                for workspace_id in workspace_ids:
                    workspace = await self.get_workspace(workspace_id)

                    if workspace:
                        # Filter archived workspaces if needed
                        if include_archived or not workspace.is_archived:
                            result.append(workspace)

            # If no workspaces found in memory, query database
            if not result:
                async with get_session() as db:
                    query = db.query(WorkspaceModel).filter(
                        WorkspaceModel.owner_id == str(user_id)
                    )

                    if not include_archived:
                        query = query.filter(WorkspaceModel.is_archived == False)

                    db_workspaces = await query.all()

                    for db_workspace in db_workspaces:
                        # Convert to Workspace model
                        workspace = Workspace(
                            id=uuid.UUID(db_workspace.id),
                            owner_id=uuid.UUID(db_workspace.owner_id)
                            if db_workspace.owner_id
                            else None,
                            created_at=db_workspace.created_at,
                            updated_at=db_workspace.updated_at,
                            last_active_at=db_workspace.last_active_at,
                            is_archived=db_workspace.is_archived,
                            is_private=db_workspace.is_private,
                            metadata=WorkspaceMetadata(**db_workspace.metadata),
                        )

                        # Add to caches
                        workspace_id = workspace.id
                        self.active_workspaces[workspace_id] = workspace
                        await self._cache_workspace(workspace)

                        # Update user workspace mapping
                        if user_id not in self.user_workspaces:
                            self.user_workspaces[user_id] = set()
                        self.user_workspaces[user_id].add(workspace_id)

                        result.append(workspace)

            return result

        except Exception as e:
            logger.error(f"Failed to get user workspaces: {str(e)}", exc_info=True)
            return []

    def _get_cache_key(self, workspace_id: uuid.UUID) -> str:
        """Get Redis cache key for a workspace"""
        return f"{self.WORKSPACE_CACHE_PREFIX}{workspace_id}"

    async def _cache_workspace(self, workspace: Workspace) -> None:
        """Cache a workspace in Redis"""
        key = self._get_cache_key(workspace.id)

        await redis_cache.set(
            key=key,
            value=workspace.dict(),
            ttl=self.WORKSPACE_CACHE_TTL,
        )


# Global instance
workspace_manager = None


def initialize_workspace_manager() -> WorkspaceManager:
    """
    Initialize the global workspace manager instance

    Returns:
        The initialized workspace manager
    """
    global workspace_manager
    if workspace_manager is None:
        workspace_manager = WorkspaceManager()
    return workspace_manager


# Export public symbols
__all__ = [
    "WorkspaceMetadata",
    "Workspace",
    "WorkspaceManager",
    "workspace_manager",
    "initialize_workspace_manager",
]
