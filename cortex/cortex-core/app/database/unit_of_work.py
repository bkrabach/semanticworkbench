from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from .connection import get_session
from .repositories.factory import RepositoryFactory

class UnitOfWork:
    """
    Unit of Work pattern implementation for managing database transactions.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize Unit of Work.
        
        Args:
            session: SQLAlchemy async session
        """
        self.session = session
        self.repositories = RepositoryFactory(session)
    
    async def commit(self) -> None:
        """Commit current transaction."""
        await self.session.commit()
    
    async def rollback(self) -> None:
        """Rollback current transaction."""
        await self.session.rollback()
    
    @classmethod
    @asynccontextmanager
    async def for_transaction(cls) -> AsyncGenerator["UnitOfWork", None]:
        """
        Create a Unit of Work for a transaction.
        
        Usage:
            ```
            async with UnitOfWork.for_transaction() as uow:
                # Do work with repositories
                workspace = await uow.repositories.get_workspace_repository().create(new_workspace)
                # Commit transaction
                await uow.commit()
            ```
        
        Yields:
            Unit of Work instance
        """
        async with get_session() as session:
            uow = cls(session)
            try:
                yield uow
            except Exception:
                # Rollback on exception
                await uow.rollback()
                raise