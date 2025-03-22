import json
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models import User
from ..models import User as DbUser
from .base import BaseRepository


class UserRepository(BaseRepository[User, DbUser]):
    """Repository for user operations."""

    def __init__(self, session: AsyncSession):
        """
        Initialize user repository.

        Args:
            session: SQLAlchemy async session
        """
        super().__init__(session, User, DbUser)

    async def list_all(self, limit: int = 100, offset: int = 0):
        """
        List all users.

        Args:
            limit: Maximum number of users to return
            offset: Pagination offset

        Returns:
            List of users
        """
        return await self.list(filters=None, limit=limit, offset=offset)

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email.

        Args:
            email: User email

        Returns:
            User if found, None otherwise
        """
        try:
            result = await self.session.execute(select(DbUser).where(DbUser.email == email))
            db_user = result.scalars().first()
            return self._to_domain(db_user) if db_user else None
        except Exception as e:
            self._handle_db_error(e, f"Error getting user with email {email}")
            return None  # Added explicit return to satisfy type checker

    async def get_by_id(self, entity_id: str) -> Optional[User]:
        """
        Get user by ID.

        Args:
            entity_id: User ID

        Returns:
            User if found, None otherwise
        """
        try:
            result = await self.session.execute(select(DbUser).where(DbUser.user_id == entity_id))
            db_user = result.scalars().first()
            return self._to_domain(db_user) if db_user else None
        except Exception as e:
            self._handle_db_error(e, f"Error getting user with ID {entity_id}")
            return None  # Added explicit return to satisfy type checker

    def _to_domain(self, db_entity: Optional[DbUser]) -> Optional[User]:
        """
        Convert database user to domain user.

        Args:
            db_entity: Database user

        Returns:
            Domain user
        """
        if not db_entity:
            return None

        # Parse metadata JSON
        metadata = {}
        # Use getattr to avoid SQLAlchemy Column type issues
        metadata_json = getattr(db_entity, "metadata_json", None)
        if metadata_json is not None:
            try:
                metadata_str = str(metadata_json)
                metadata = json.loads(metadata_str)
            except (json.JSONDecodeError, TypeError):
                pass

        return User(
            user_id=str(getattr(db_entity, "user_id")),
            name=str(getattr(db_entity, "name")),
            email=str(getattr(db_entity, "email")),
            metadata=metadata,
        )

    def _to_db(self, entity: User) -> DbUser:
        """
        Convert domain user to database user.

        Args:
            entity: Domain user

        Returns:
            Database user
        """
        metadata_json = "{}"
        if entity.metadata:
            metadata_json = json.dumps(entity.metadata)

        return DbUser(user_id=entity.user_id, name=entity.name, email=entity.email, metadata_json=metadata_json)

    def _update_db_entity(self, db_entity: DbUser, entity: User) -> DbUser:
        """
        Update database user from domain user.

        Args:
            db_entity: Database user to update
            entity: Domain user with new values

        Returns:
            Updated database user
        """
        # Use setattr to safely update Column attributes
        setattr(db_entity, "name", entity.name)
        setattr(db_entity, "email", entity.email)

        # Update metadata
        metadata_json = "{}"
        if entity.metadata:
            metadata_json = json.dumps(entity.metadata)

        setattr(db_entity, "metadata_json", metadata_json)

        return db_entity
