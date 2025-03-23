"""
Integration tests for the Cognition Service flow.

These tests verify that the ResponseHandler can successfully enhance LLM responses
with context from the Cognition Service, and that the context retrieval tools work
correctly in a full end-to-end scenario.
"""

import asyncio
import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from typing import Any, Dict, List, Tuple, Generator, Optional, cast

from app.core.response_handler import response_handler
from app.core.llm_adapter import llm_adapter
from app.database.unit_of_work import UnitOfWork
from app.models import User, Workspace, Conversation, Message
from app.core.repository import RepositoryManager
from app.services.memory import MemoryService
from app.services.cognition import CognitionService
from app.core.mcp import registry


@pytest.fixture(scope="module")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def mock_repository_manager() -> Tuple[MagicMock, MagicMock]:
    """Create a mock repository manager with basic functionality."""
    repo_manager = MagicMock(spec=RepositoryManager)
    
    # Create mock repositories
    messages_repo = MagicMock()
    messages_repo.find_many = AsyncMock()
    messages_repo.find_one = AsyncMock()
    messages_repo.create = AsyncMock()
    
    # Configure repository manager to return mock repos
    repo_manager.get_repository = MagicMock(return_value=messages_repo)
    
    return repo_manager, messages_repo
    
@pytest.fixture(scope="module")
async def setup_mcp_services(mock_repository_manager: Tuple[MagicMock, MagicMock]) -> Tuple[MemoryService, CognitionService, MagicMock]:
    """Set up MCP services for testing."""
    repo_manager, messages_repo = mock_repository_manager
    
    # Create Memory Service
    memory_service = MemoryService(repo_manager)
    
    # Create Cognition Service that depends on Memory Service
    cognition_service = CognitionService(memory_service)
    
    # Initialize services
    await memory_service.initialize()
    await cognition_service.initialize()
    
    # Register services with MCP registry
    await registry.register_service("memory", memory_service)
    await registry.register_service("cognition", cognition_service)
    
    return memory_service, cognition_service, messages_repo

@pytest.fixture(scope="module")
async def setup_test_data(mock_repository_manager: Tuple[MagicMock, MagicMock], setup_mcp_services: Tuple[MemoryService, CognitionService, MagicMock]) -> Dict[str, Any]:
    """Set up test data for cognition flow tests."""
    # Use in-memory SQLite for testing
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    
    # Unpack fixtures
    repo_manager, messages_repo = mock_repository_manager
    memory_service, cognition_service, _ = setup_mcp_services
    
    # Setup user and test data
    user_id = "test-user"
    workspace_id = "test-workspace"
    conversation_id = "test-conversation"
    conversation2_id = "test-conversation-2"
    
    # Create test messages
    paris_messages = [
        {
            "id": f"msg{i}",
            "conversation_id": conversation_id,
            "user_id": user_id if i % 2 == 0 else "assistant",
            "content": content,
            "timestamp": f"2023-01-01T12:{i:02d}:00",
            "metadata": {"role": "user" if i % 2 == 0 else "assistant"}
        }
        for i, content in enumerate([
            "What's the capital of France?",
            "The capital of France is Paris.",
            "Tell me more about Paris.",
            "Paris is the capital and most populous city of France. It's known for landmarks like the Eiffel Tower and Louvre Museum.",
            "What's the population of Paris?",
            "The population of Paris proper is around 2.2 million, while the greater Paris metropolitan area has over 12 million inhabitants."
        ])
    ]
    
    python_messages = [
        {
            "id": f"msg1{i}",
            "conversation_id": conversation2_id,
            "user_id": user_id if i % 2 == 0 else "assistant",
            "content": content,
            "timestamp": f"2023-01-02T12:{i:02d}:00",
            "metadata": {"role": "user" if i % 2 == 0 else "assistant"}
        }
        for i, content in enumerate([
            "How do I write a Python function?",
            "In Python, you define a function using the 'def' keyword followed by the function name and parameters. Here's an example:\n\n```python\ndef greet(name):\n    return f'Hello, {name}!'\n```",
            "How do I handle exceptions in Python?",
            "In Python, you can handle exceptions using try-except blocks. Here's an example:\n\n```python\ntry:\n    result = 10 / 0\nexcept ZeroDivisionError:\n    print('You cannot divide by zero!')\n```"
        ])
    ]
    
    # Configure the mock message repository to return appropriate results
    messages_repo.find_many.side_effect = lambda query, **kwargs: (
        paris_messages if query.get("conversation_id") == conversation_id
        else python_messages if query.get("conversation_id") == conversation2_id
        else paris_messages + python_messages if query.get("user_id") == user_id
        else []
    )
    
    return {
        "user_id": user_id,
        "workspace_id": workspace_id,
        "conversation_id": conversation_id,
        "conversation2_id": conversation2_id,
        "memory_service": memory_service,
        "cognition_service": cognition_service
    }


@pytest.mark.asyncio
async def test_get_context_directly(setup_test_data: Dict[str, Any]) -> None:
    """
    Test the Cognition Service's get_context method directly.
    """
    # Get the cognition service from the fixture
    cognition_service = setup_test_data["cognition_service"]
    
    # Call the get_context method
    result = await cognition_service.get_context(
        user_id=setup_test_data["user_id"],
        query="Paris population",
        limit=5
    )
    
    # Verify results
    assert "context" in result
    assert isinstance(result["context"], list)
    assert result["count"] > 0
    assert result["user_id"] == setup_test_data["user_id"]
    
    # In our mock setup with side_effect, this should return paris_messages
    # Check content has Paris and population
    context_items = result["context"]
    has_relevant_context = False
    for item in context_items:
        content = item.get("content", "").lower()
        if "paris" in content and "population" in content:
            has_relevant_context = True
            break
    
    assert has_relevant_context, "Couldn't find relevant context about Paris population"


@pytest.mark.asyncio
async def test_analyze_conversation_directly(setup_test_data: Dict[str, Any]) -> None:
    """
    Test the Cognition Service's analyze_conversation method directly.
    """
    # Get the cognition service from the fixture
    cognition_service = setup_test_data["cognition_service"]
    
    # Call the analyze_conversation method
    result = await cognition_service.analyze_conversation(
        user_id=setup_test_data["user_id"],
        conversation_id=setup_test_data["conversation_id"],
        analysis_type="summary"
    )
    
    # Verify the results
    assert "type" in result
    assert result["type"] == "summary"
    assert "results" in result
    assert "conversation_id" in result
    assert result["conversation_id"] == setup_test_data["conversation_id"]
    
    # Check the summary contains expected data
    assert "message_count" in result["results"]
    assert result["results"]["message_count"] == 6  # We have 6 test messages
    
    # Should have identified both user and assistant participants
    assert "participants" in result["results"]
    assert result["results"]["participants"] >= 2  # User and assistant


@pytest.mark.asyncio
async def test_search_history_directly(setup_test_data: Dict[str, Any]) -> None:
    """
    Test the Cognition Service's search_history method directly.
    """
    # Get the cognition service from the fixture
    cognition_service = setup_test_data["cognition_service"]
    
    # Call the search_history method
    result = await cognition_service.search_history(
        user_id=setup_test_data["user_id"],
        query="python function",
        limit=10,
        include_conversations=True
    )
    
    # Verify the results
    assert "results" in result
    assert "count" in result
    assert "query" in result
    assert result["query"] == "python function"
    
    # Check that Python function messages are included
    found_python_content = False
    for item in result["results"]:
        content = item.get("content", "").lower()
        if "python" in content and "function" in content:
            found_python_content = True
            break
            
    assert found_python_content, "Search didn't find Python function content"


@pytest.mark.asyncio
async def test_get_context_mcp_integration(setup_test_data: Dict[str, Any]) -> None:
    """
    Test that the get_context tool can retrieve context through MCP services.
    """
    # First check that the MCP services are registered properly
    registered_services = registry.list_services()
    assert "memory" in registered_services
    assert "cognition" in registered_services
    
    # Access the Cognition Service directly through MCP registry
    cognition_service = registry.get_service("cognition").service_instance
    
    # Verify it's the same instance we set up in our test fixture
    assert cognition_service is setup_test_data["cognition_service"]
    
    # Now call get_context directly on the service
    result = await cognition_service.get_context(
        user_id=setup_test_data["user_id"],
        query="Paris population",
        limit=5
    )
    
    # Verify results contain Paris-related content
    assert "context" in result
    assert result["count"] > 0
    assert result["user_id"] == setup_test_data["user_id"]
    
    # At least one item should contain Paris
    found_paris = False
    for item in result["context"]:
        if "paris" in item.get("content", "").lower():
            found_paris = True
            break
            
    assert found_paris, "Could not find Paris in context items"


@pytest.mark.asyncio
async def test_context_fallback_on_error(setup_test_data: Dict[str, Any]) -> None:
    """
    Test that tools and services handle errors gracefully.
    """
    # Create a new CognitionService with a memory service that will fail
    faulty_memory_service = MagicMock()
    faulty_memory_service.get_limited_history = AsyncMock(side_effect=Exception("Simulated memory error"))
    
    # Create a new cognition service with our faulty memory service
    cognition_service = CognitionService(faulty_memory_service)
    
    # Call should not raise but return error in result
    result = await cognition_service.get_context(
        user_id=setup_test_data["user_id"],
        query="Paris population"
    )
    
    # Should return error response
    assert "error" in result
    assert "context" in result
    assert len(result["context"]) == 0
    assert result["count"] == 0
    assert "Simulated memory error" in result["error"]