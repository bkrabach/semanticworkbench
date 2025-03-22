import json
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository
from ...models.domain import Workspace
from ..models import Workspace as DbWorkspace

class WorkspaceRepository(BaseRepository[Workspace, DbWorkspace]):
    """Repository for workspace operations."""

    def __init__(self, session: AsyncSession):
        """
        Initialize workspace repository.

        Args:
            session: SQLAlchemy async session
        """
        super().__init__(session, Workspace, DbWorkspace)

    async def list_by_owner(self, owner_id: str, limit: int = 100, offset: int = 0) -> List[Workspace]:
        """
        List workspaces for a specific owner.

        Args:
            owner_id: Owner user ID
            limit: Maximum number of workspaces to return
            offset: Pagination offset

        Returns:
            List of workspaces
        """
        try:
            result = await self.session.execute(
                select(DbWorkspace)
                .where(DbWorkspace.owner_id == owner_id)
                .limit(limit)
                .offset(offset)
            )
            db_workspaces = result.scalars().all()
            # Filter out None values to satisfy type checker
            workspaces = [ws for ws in [self._to_domain(db) for db in db_workspaces] if ws is not None]
            return workspaces
        except Exception as e:
            self._handle_db_error(e, f"Error listing workspaces for owner {owner_id}")
            return []  # Return empty list on error

    async def get_by_id(self, entity_id: str, owner_id: Optional[str] = None) -> Optional[Workspace]:
        """
        Get workspace by ID with optional ownership check.

        Args:
            entity_id: Workspace ID
            owner_id: Optional owner ID for access control

        Returns:
            Workspace if found and accessible, None otherwise
        """
        try:
            query = select(DbWorkspace).where(DbWorkspace.id == entity_id)

            # Apply owner filter if provided (for access control)
            if owner_id:
                query = query.where(DbWorkspace.owner_id == owner_id)

            result = await self.session.execute(query)
            db_workspace = result.scalars().first()
            return self._to_domain(db_workspace) if db_workspace else None
        except Exception as e:
            self._handle_db_error(e, f"Error getting workspace with ID {entity_id}")
            return None  # Explicit return None on error

    async def count_by_owner(self, owner_id: str) -> int:
        """
        Count workspaces for a specific owner.

        Args:
            owner_id: Owner user ID

        Returns:
            Count of workspaces
        """
        try:
            result = await self.session.execute(
                select(func.count())
                .select_from(DbWorkspace)
                .where(DbWorkspace.owner_id == owner_id)
            )
            return result.scalar() or 0
        except Exception as e:
            self._handle_db_error(e, f"Error counting workspaces for owner {owner_id}")
            return 0  # Return 0 count on error

    def _to_domain(self, db_entity: Optional[DbWorkspace]) -> Optional[Workspace]:
        """
        Convert database workspace to domain workspace.

        Args:
            db_entity: Database workspace

        Returns:
            Domain workspace
        """
        if not db_entity:
            return None

        # Parse metadata JSON
        metadata = {}
        # Use getattr to avoid SQLAlchemy Column type issues
        metadata_json = getattr(db_entity, 'metadata_json', None)
        if metadata_json is not None:
            try:
                metadata_str = str(metadata_json)
                metadata = json.loads(metadata_str)
            except (json.JSONDecodeError, TypeError):
                pass

        return Workspace(
            id=str(getattr(db_entity, 'id')),
            name=str(getattr(db_entity, 'name')),
            description=str(getattr(db_entity, 'description')),
            owner_id=str(getattr(db_entity, 'owner_id')),
            metadata=metadata
        )

    def _to_db(self, entity: Workspace) -> DbWorkspace:
        """
        Convert domain workspace to database workspace.

        Args:
            entity: Domain workspace

        Returns:
            Database workspace
        """
        metadata_json = "{}"
        if entity.metadata:
            metadata_json = json.dumps(entity.metadata)

        return DbWorkspace(
            id=entity.id,
            name=entity.name,
            description=entity.description,
            owner_id=entity.owner_id,
            metadata_json=metadata_json
        )

    def _update_db_entity(self, db_entity: DbWorkspace, entity: Workspace) -> DbWorkspace:
        """
        Update database workspace from domain workspace.

        Args:
            db_entity: Database workspace to update
            entity: Domain workspace with new values

        Returns:
            Updated database workspace
        """
        # Use setattr to avoid typechecking issues with SQLAlchemy columns
        setattr(db_entity, 'name', entity.name)
        setattr(db_entity, 'description', entity.description)

        # Update metadata
        metadata_json = "{}"
        if entity.metadata:
            metadata_json = json.dumps(entity.metadata)

        setattr(db_entity, 'metadata_json', metadata_json)

        return db_entity