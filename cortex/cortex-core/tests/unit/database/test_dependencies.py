"""
Tests for the database dependencies.
"""

import pytest
import sys
from unittest.mock import AsyncMock, MagicMock, patch
from typing import AsyncGenerator, TypeVar

from app.database.dependencies import get_repository_factory
from app.database.repositories.factory import RepositoryFactory

T = TypeVar('T')

# Helper function for Python < 3.10
async def async_next(async_iterator: AsyncGenerator[T, None]) -> T:
    """Get the next item from an async iterator."""
    try:
        if sys.version_info >= (3, 10):
            return await anext(async_iterator)  # type: ignore # Python 3.10+
        else:
            # Manual implementation for older Python versions
            return await async_iterator.__anext__()
    except StopAsyncIteration:
        raise StopAsyncIteration("Async iterator is exhausted")


@pytest.mark.asyncio
async def test_get_repository_factory() -> None:
    """Test the repository factory dependency."""
    # Create a mock session for testing
    mock_session = MagicMock()
    
    # Create a mock context manager for get_session
    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__.return_value = mock_session
    
    # Patch the get_session function to return our mock
    with patch('app.database.dependencies.get_session', return_value=mock_session_ctx):
        # Call the dependency function and get the repository factory
        factory_gen = get_repository_factory()
        factory = await async_next(factory_gen)
        
        # Verify we got a proper repository factory
        assert isinstance(factory, RepositoryFactory)
        
        # Verify the factory has the correct session
        assert factory.session == mock_session
        
        # Verify the session context was entered
        mock_session_ctx.__aenter__.assert_called_once()
        
        # Cleanup the generator to exit the context
        try:
            await async_next(factory_gen)
        except StopAsyncIteration:
            pass
        
        # Verify the session context was exited
        mock_session_ctx.__aexit__.assert_called_once()