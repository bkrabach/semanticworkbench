"""
Shared test fixtures and configuration.
"""

import asyncio
import os
from unittest.mock import AsyncMock

import pytest
from app.database.connection import get_session
from app.main import app
from app.utils.auth import create_access_token
from fastapi.testclient import TestClient


# Let pytest-asyncio handle the event loop management
# Use the mark.asyncio decorator with scope="session" where needed


@pytest.fixture
def client():
    """Return a FastAPI TestClient."""
    return TestClient(app)


@pytest.fixture
def mock_env_vars():
    """Set test environment variables."""
    original = os.environ.copy()
    os.environ["USE_MOCK_LLM"] = "true"
    yield
    os.environ.clear()
    os.environ.update(original)


@pytest.fixture
def test_token():
    """Create a test JWT token."""
    return create_access_token({
        "sub": "test@example.com",
        "oid": "test-user-id",
        "name": "Test User",
        "email": "test@example.com",
    })


@pytest.fixture
def auth_headers(test_token):
    """Create authorization headers with test token."""
    return {"Authorization": f"Bearer {test_token}"}


@pytest.fixture
async def async_client():
    """Create an async client for testing async endpoints."""
    from httpx import AsyncClient

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_event_bus():
    """Create a mock event bus."""
    from app.core.event_bus import EventBus

    bus = EventBus()
    # You could add test-specific behavior here
    return bus


@pytest.fixture
async def mock_db_session():
    """Create a mock database session."""
    session = AsyncMock()
    # Configure common mock behavior
    return session


@pytest.fixture
async def db_session():
    """Create a real database session for integration tests."""
    async with get_session() as session:
        yield session


@pytest.fixture
def user_data():
    """Sample user data for tests."""
    return {"id": "test-user-id", "name": "Test User", "email": "test@example.com", "metadata": {"test": True}}


@pytest.fixture
def workspace_data(user_data):
    """Sample workspace data for tests."""
    return {
        "id": "test-workspace-id",
        "name": "Test Workspace",
        "description": "Workspace for testing",
        "user_id": user_data["id"],
        "metadata": {"test": True},
    }


@pytest.fixture
def conversation_data(workspace_data):
    """Sample conversation data for tests."""
    return {
        "id": "test-conversation-id",
        "workspace_id": workspace_data["id"],
        "user_id": workspace_data["user_id"],
        "topic": "Test Conversation",
        "metadata": {"test": True},
    }


@pytest.fixture
def message_data(conversation_data):
    """Sample message data for tests."""
    return {
        "id": "test-message-id",
        "conversation_id": conversation_data["id"],
        "user_id": conversation_data["user_id"],
        "content": "Test message content",
        "role": "user",
        "metadata": {"test": True},
    }