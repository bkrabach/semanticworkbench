"""
Unit tests for the Unit of Work pattern.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.unit_of_work import UnitOfWork
from app.database.repositories.factory import RepositoryFactory


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create a mock SQLAlchemy session for testing."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.mark.asyncio
async def test_unit_of_work_context_manager() -> None:
    """Test that the UnitOfWork works as a context manager."""
    # Mock the session and repository factory
    mock_session = AsyncMock()
    mock_repo_factory = MagicMock(spec=RepositoryFactory)
    
    # Set up session creation
    with patch("app.database.unit_of_work.get_session", 
               return_value=AsyncMock(
                   __aenter__=AsyncMock(return_value=mock_session),
                   __aexit__=AsyncMock()
               )):
        # Set up repository factory
        with patch("app.database.unit_of_work.RepositoryFactory", 
                   return_value=mock_repo_factory):
            
            # Use the unit of work
            async with UnitOfWork.for_transaction() as uow:
                # Check that the repositories attribute is set
                assert uow.repositories == mock_repo_factory
                assert uow.session == mock_session


@pytest.mark.asyncio
async def test_unit_of_work_commit(mock_session: AsyncMock) -> None:
    """Test that the UnitOfWork commits the transaction."""
    # Create UnitOfWork with mock session
    uow = UnitOfWork(mock_session)
    
    # Call commit
    await uow.commit()
    
    # Verify commit was called
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_unit_of_work_rollback(mock_session: AsyncMock) -> None:
    """Test that the UnitOfWork rolls back the transaction."""
    # Create UnitOfWork with mock session
    uow = UnitOfWork(mock_session)
    
    # Call rollback
    await uow.rollback()
    
    # Verify rollback was called
    mock_session.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_unit_of_work_rollback_with_exception() -> None:
    """Test that the commit and rollback methods are called correctly."""
    mock_session = AsyncMock()
    
    # Create UnitOfWork with mock session
    uow = UnitOfWork(mock_session)
    
    # Call methods
    await uow.commit()
    await uow.rollback()
    
    # Verify calls
    mock_session.commit.assert_called_once()
    mock_session.rollback.assert_called_once()