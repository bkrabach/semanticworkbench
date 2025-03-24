"""
Tests for the database dependencies.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.database.dependencies import get_repository_factory
from app.database.repositories.factory import RepositoryFactory


@pytest.mark.asyncio
async def test_get_repository_factory():
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
        factory = await anext(factory_gen)
        
        # Verify we got a proper repository factory
        assert isinstance(factory, RepositoryFactory)
        
        # Verify the factory has the correct session
        assert factory.session == mock_session
        
        # Verify the session context was entered
        mock_session_ctx.__aenter__.assert_called_once()
        
        # Cleanup the generator to exit the context
        try:
            await anext(factory_gen)
        except StopAsyncIteration:
            pass
        
        # Verify the session context was exited
        mock_session_ctx.__aexit__.assert_called_once()