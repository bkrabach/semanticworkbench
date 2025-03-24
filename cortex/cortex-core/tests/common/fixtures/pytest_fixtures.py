"""
Shared test fixtures and configuration.
"""

import os
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock

import pytest
from app.core.event_bus import EventBus
from app.database.connection import get_session
from app.main import app
from app.utils.auth import create_access_token
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

# Let pytest-asyncio handle the event loop management
# Use the mark.asyncio decorator with scope="session" where needed


@pytest.fixture
def test_client() -> Generator[TestClient, None, None]:
    """Get a TestClient instance for testing API endpoints."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Get an AsyncClient instance for testing async API endpoints."""
    # For HTTPX AsyncClient, we create a client with base_url and manually set app
    client = AsyncClient(base_url="http://test")
    client.app = app  # type: ignore # Set app directly as a property
    try:
        yield client
    finally:
        await client.aclose()


@pytest.fixture
async def mock_event_bus() -> AsyncGenerator[AsyncMock, None]:
    """Get a mock EventBus instance."""
    from app.core.event_bus import event_bus as global_event_bus
    
    # Save the original event bus instance
    original_bus = global_event_bus
    
    # Create a mock event bus
    mock_bus = AsyncMock()
    
    # Replace the global event bus with our mock
    import app.core.event_bus
    app.core.event_bus.event_bus = mock_bus  # type: ignore
    
    try:
        yield mock_bus
    finally:
        # Restore the original event bus
        app.core.event_bus.event_bus = original_bus  # type: ignore


@pytest.fixture
def test_token() -> str:
    """Get a test auth token."""
    return create_access_token({
        "sub": "test@example.com",
        "oid": "test-user-id",
        "name": "Test User",
        "email": "test@example.com"
    })


@pytest.fixture
async def test_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session for testing."""
    # Use a separate test database to prevent modifying production data
    old_db_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test.db"
    
    # Create a session using the context manager
    async with get_session() as session:
        try:
            yield session
            await session.rollback()  # Don't commit test data
        except Exception:
            await session.rollback()
            raise
    
    # Restore original DB URL
    if old_db_url:
        os.environ["DATABASE_URL"] = old_db_url
    else:
        del os.environ["DATABASE_URL"]