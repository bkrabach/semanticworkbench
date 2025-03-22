from typing import AsyncGenerator

from .connection import get_session
from .repositories.factory import RepositoryFactory

async def get_repository_factory() -> AsyncGenerator[RepositoryFactory, None]:
    """
    Dependency to get a repository factory with proper session management.
    
    Yields:
        Repository factory with an active session
    """
    async with get_session() as session:
        yield RepositoryFactory(session)