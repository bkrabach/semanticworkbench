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
def client() -> TestClient:
    """Return a FastAPI TestClient."""
    return TestClient(app)


@pytest.fixture
def mock_env_vars() -> Generator[None, None, None]:
    """Set test environment variables."""
    original = os.environ.copy()
    # Set any environment variables needed for testing here
    yield
    os.environ.clear()
    os.environ.update(original)


@pytest.fixture
def test_token() -> str:
    """Create a test JWT token."""
    return create_access_token({
        "sub": "test@example.com",
        "oid": "test-user-id",
        "name": "Test User",
        "email": "test@example.com",
    })


@pytest.fixture
def auth_headers(test_token: str) -> dict[str, str]:
    """Create authorization headers with test token."""
    return {"Authorization": f"Bearer {test_token}"}


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async client for testing async endpoints."""

    # For HTTPX AsyncClient, we set the base_url and don't pass the app directly
    async with AsyncClient(base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_event_bus() -> EventBus:
    """Create a mock event bus."""
    from app.core.event_bus import EventBus

    bus = EventBus()
    # You could add test-specific behavior here
    return bus


@pytest.fixture
async def mock_db_session() -> AsyncMock:
    """Create a mock database session."""
    session = AsyncMock()
    # Configure common mock behavior
    return session


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a real database session for integration tests."""
    async with get_session() as session:
        yield session


@pytest.fixture
def user_data() -> dict[str, object]:
    """Sample user data for tests."""
    return {"id": "test-user-id", "name": "Test User", "email": "test@example.com", "metadata": {"test": True}}


@pytest.fixture
def workspace_data(user_data: dict[str, object]) -> dict[str, object]:
    """Sample workspace data for tests."""
    return {
        "id": "test-workspace-id",
        "name": "Test Workspace",
        "description": "Workspace for testing",
        "user_id": user_data["id"],
        "metadata": {"test": True},
    }


@pytest.fixture
def conversation_data(workspace_data: dict[str, object]) -> dict[str, object]:
    """Sample conversation data for tests."""
    return {
        "id": "test-conversation-id",
        "workspace_id": workspace_data["id"],
        "user_id": workspace_data["user_id"],
        "topic": "Test Conversation",
        "metadata": {"test": True},
    }


@pytest.fixture
def message_data(conversation_data: dict[str, object]) -> dict[str, object]:
    """Sample message data for tests."""
    return {
        "id": "test-message-id",
        "conversation_id": conversation_data["id"],
        "user_id": conversation_data["user_id"],
        "content": "Test message content",
        "role": "user",
        "metadata": {"test": True},
    }
