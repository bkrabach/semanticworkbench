"""Base service for business logic."""
from typing import Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.base import BaseRepository
from app.models.domain.base import BaseModelWithMetadata

# Generic type for the repository
RepoType = TypeVar("RepoType", bound=BaseRepository)

# Generic type for the domain model
ModelType = TypeVar("ModelType", bound=BaseModelWithMetadata)


class BaseService(Generic[RepoType, ModelType]):
    """Base service for business logic operations.
    
    This service provides a foundation for implementing business logic
    that uses repositories for data access.
    """
    
    def __init__(self, repository: RepoType, db: AsyncSession):
        """Initialize the service.
        
        Args:
            repository: The repository for data access
            db: The database session
        """
        self.repository = repository
        self.db = db
        
    async def commit(self) -> None:
        """Commit the current transaction."""
        await self.db.commit()
        
    async def rollback(self) -> None:
        """Rollback the current transaction."""
        await self.db.rollback()