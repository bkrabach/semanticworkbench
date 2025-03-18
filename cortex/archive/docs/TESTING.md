# Testing Guide for Cortex Core

This document provides comprehensive guidelines and best practices for testing the Cortex Core platform, with specific guidance for each major component.

## Running Tests

```bash
# Run all tests
python -m pytest

# Run specific tests
python -m pytest tests/api/test_auth.py

# Run with coverage report
python -m pytest --cov=app tests/

# Run only the event system tests
python -m pytest tests/components/test_event_system.py

# Run architecture validation tests
python -m pytest tests/architecture/test_layer_integrity.py
```

## Architecture Validation Testing

The codebase includes automated tests to enforce architectural boundaries:

### Automated Architecture Tests

The file `tests/architecture/test_layer_integrity.py` contains tests that validate proper layer separation by checking import patterns. These tests verify that:

1. API layers never import SQLAlchemy models directly
2. Service layers never import SQLAlchemy models directly 
3. Components never import SQLAlchemy models directly

These tests are critical for maintaining the domain-driven repository architecture.

### Command-Line Validation Script

For quick architecture validation, use the `check_imports.sh` script:

```bash
./check_imports.sh
```

This script checks for improper imports across the codebase and provides clear error messages when violations are detected. Add this to your workflow to catch architectural issues early.

## Test Structure

Each test module should follow this structure:

- Import statements
- Fixture definitions
- Test functions grouped by functionality
- Helper functions (if needed)

Example:

```python
"""
Test suite for authentication API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from app.main import app
from app.database.connection import get_db
from app.database.models import User

# Fixtures
@pytest.fixture
def mock_db():
    """Create a mock DB session"""
    mock = MagicMock()
    return mock

@pytest.fixture
def client_with_db_override(mock_db):
    """Create a test client with DB dependency override"""
    app.dependency_overrides[get_db] = lambda: mock_db
    client = TestClient(app)
    yield client
    app.dependency_overrides = {}

# Tests
def test_login_success(client_with_db_override, mock_db):
    # Test implementation
    pass
```

## Testing Specific Components

### 1. Testing SSE Components

The Server-Sent Events (SSE) system requires special testing approaches:

#### SSE Manager Testing

```python
@pytest.mark.asyncio
async def test_sse_manager():
    """Test the SSE manager component"""
    # Create test manager
    manager = SSEStarletteManager()
    
    # Test connection registration
    queue, connection_id = await manager.register_connection(
        "conversation", "conversation-123", "user-123"
    )
    
    # Verify connection was registered
    connections = manager.get_connections("conversation", "conversation-123")
    assert len(connections) == 1
    assert connections[0].id == connection_id
    
    # Test sending events
    await manager.send_event(
        "conversation", "conversation-123", 
        "test_event", {"message": "Hello"}
    )
    
    # Receive the event with timeout
    event = await asyncio.wait_for(queue.get(), timeout=0.5)
    assert event["event"] == "test_event"
    assert event["data"]["message"] == "Hello"
    
    # Test connection removal
    await manager.remove_connection("conversation", "conversation-123", connection_id)
    connections = manager.get_connections("conversation", "conversation-123")
    assert len(connections) == 0
```

#### SSE Endpoint Testing

```python
def test_sse_endpoint(sse_test_client, valid_token):
    """Test SSE endpoint without hanging"""
    # Configure client to use mock response for SSE endpoints
    response = sse_test_client.get(f"/v1/conversation/conversation-123?token={valid_token}")
    
    # Verify response contract
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream"
    
    # Always close response to prevent resource leaks
    response.close()
```

#### Testing Shared Connection State

```python
@pytest.mark.asyncio
async def test_shared_connection_state():
    """Test that connection state is properly shared"""
    # Create two manager instances
    manager1 = SSEStarletteManager()
    manager2 = SSEStarletteManager()
    
    # Register a connection with the first manager
    queue1, conn_id = await manager1.register_connection(
        "conversation", "conversation-123", "user-123"
    )
    
    # Verify the second manager can see the connection
    connections = manager2.get_connections("conversation", "conversation-123")
    assert len(connections) == 1
    assert connections[0].id == conn_id
    
    # Send an event with the second manager
    await manager2.send_event(
        "conversation", "conversation-123", 
        "test_event", {"message": "Hello"}
    )
    
    # Verify the event was received in the queue from manager1
    event = await asyncio.wait_for(queue1.get(), timeout=0.5)
    assert event["event"] == "test_event"
    assert event["data"]["message"] == "Hello"
```

### 2. Testing LLM Service

The LLM Service requires careful mocking to avoid actual API calls:

#### Mock LLM Service

```python
@pytest.fixture
def mock_llm_service():
    """Create a mock LLM service for testing"""
    # Create mock config
    config = LLMConfig(default_model="openai/gpt-3.5-turbo", use_mock=True)
    
    # Create the service
    service = LiteLLMService(config)
    
    # Optionally override the mock implementation
    async def custom_mock(prompt, system_prompt=None):
        if "weather" in prompt.lower():
            return "It's sunny today."
        elif "name" in prompt.lower():
            return "My name is Cortex."
        else:
            return f"This is a mock response to: {prompt}"
    
    service._mock_completion = custom_mock
    return service
```

#### Testing Completions

```python
@pytest.mark.asyncio
async def test_llm_completion(mock_llm_service):
    """Test LLM completion functionality"""
    # Test basic completion
    response = await mock_llm_service.get_completion(
        "What's the weather like?",
        system_prompt="You are a helpful assistant."
    )
    assert "sunny" in response.lower()
    
    # Test with different prompt
    response = await mock_llm_service.get_completion(
        "What's your name?",
        system_prompt="You are a helpful assistant."
    )
    assert "cortex" in response.lower()
```

#### Testing Streaming Completions

```python
@pytest.mark.asyncio
async def test_llm_streaming(mock_llm_service):
    """Test LLM streaming functionality"""
    # Collect chunks
    chunks = []
    async def callback(chunk):
        chunks.append(chunk)
    
    # Get streaming completion
    full_response = await mock_llm_service.get_streaming_completion(
        "Tell me a story",
        callback=callback,
        system_prompt="You are a storyteller."
    )
    
    # Verify chunks were received
    assert len(chunks) > 0
    # Verify full response is the concatenation of chunks
    assert full_response == "".join(chunks)
```

#### Testing LLM Integration with Router

```python
@pytest.mark.asyncio
async def test_router_llm_integration(mock_llm_service, mock_conversation_service):
    """Test CortexRouter integration with LLM service"""
    # Create router with mock dependencies
    router = CortexRouter(
        conversation_service=mock_conversation_service,
        llm_service=mock_llm_service,
        sse_service=MagicMock()
    )
    
    # Create test message
    message = InputMessage(
        id="msg-123",
        conversation_id="conv-123",
        workspace_id="workspace-123",
        content="Hello, how are you?",
        role="user"
    )
    
    # Set up mock conversation service to return empty conversation
    mock_conversation_service.get_conversation.return_value = Conversation(
        id="conv-123",
        workspace_id="workspace-123",
        name="Test Conversation",
        messages=[]
    )
    
    # Process the message
    await router.process_message(message)
    
    # Verify LLM service was called
    mock_conversation_service.add_message.assert_called()
    # Check the second call (first is for user message, second for assistant response)
    call_args = mock_conversation_service.add_message.call_args_list[1]
    # Extract the content from the args
    response_content = call_args[0][1]
    assert response_content is not None
```

### 3. Testing CortexRouter

The CortexRouter requires testing of decision logic and action handling:

#### Decision Logic Testing

```python
@pytest.mark.asyncio
async def test_router_decision_logic():
    """Test router decision logic"""
    # Create router with mock dependencies
    router = CortexRouter(
        conversation_service=MagicMock(),
        llm_service=MagicMock(),
        sse_service=MagicMock()
    )
    
    # Test message
    message = InputMessage(
        id="msg-123",
        conversation_id="conv-123",
        workspace_id="workspace-123",
        content="Hello, how are you?",
        role="user"
    )
    
    # Override decision method for testing
    original_method = router._make_routing_decision
    decisions = []
    
    async def test_decision(msg):
        decision = await original_method(msg)
        decisions.append(decision)
        return decision
    
    router._make_routing_decision = test_decision
    
    # Process the message
    await router.process_message(message)
    
    # Verify decision was made
    assert len(decisions) == 1
    assert decisions[0].action == RoutingAction.RESPOND
```

#### Action Handling Testing

```python
@pytest.mark.asyncio
async def test_router_respond_action(mock_llm_service):
    """Test router respond action"""
    # Create mocks
    conversation_service = MagicMock()
    sse_service = MagicMock()
    
    # Configure sse_service to use async mock for send_event
    async def mock_send_event(*args, **kwargs):
        pass
    sse_service.send_event = mock_send_event
    
    # Create router
    router = CortexRouter(
        conversation_service=conversation_service,
        llm_service=mock_llm_service,
        sse_service=sse_service
    )
    
    # Configure conversation_service to return conversation
    conversation = Conversation(
        id="conv-123",
        workspace_id="workspace-123",
        name="Test Conversation",
        messages=[]
    )
    async def mock_get_conversation(*args, **kwargs):
        return conversation
    conversation_service.get_conversation = mock_get_conversation
    
    # Configure add_message to work with async
    async def mock_add_message(*args, **kwargs):
        return "msg-456"
    conversation_service.add_message = mock_add_message
    
    # Create test message and decision
    message = InputMessage(
        id="msg-123",
        conversation_id="conv-123",
        workspace_id="workspace-123",
        content="Hello",
        role="user"
    )
    decision = RoutingDecision(
        action=RoutingAction.RESPOND,
        target="llm",
        confidence=1.0
    )
    
    # Handle the action
    await router._handle_respond_action(message, decision)
    
    # Verify the method was called with right arguments
    assert router._send_typing_indicator.call_count == 2  # On and off
```

### 4. Testing Domain Expert Integration

Tests for Domain Expert integration with IntegrationHub:

#### Mock Domain Expert Registration

```python
@pytest.fixture
def mock_integration_hub():
    """Create a mock integration hub with test experts"""
    hub = IntegrationHub()
    
    # Register a test expert
    @hub.register_tool("calculator")
    async def calculator(a: int, b: int, operation: str = "add"):
        """Calculate a result based on two numbers and an operation"""
        if operation == "add":
            return a + b
        elif operation == "subtract":
            return a - b
        elif operation == "multiply":
            return a * b
        elif operation == "divide":
            return a / b
        else:
            raise ValueError(f"Unknown operation: {operation}")
    
    return hub
```

#### Testing Tool Invocation

```python
@pytest.mark.asyncio
async def test_tool_invocation(mock_integration_hub):
    """Test invoking a tool through the integration hub"""
    # Invoke the calculator tool
    result = await mock_integration_hub.invoke_tool(
        "calculator",
        {
            "a": 5,
            "b": 3,
            "operation": "add"
        }
    )
    assert result == 8
    
    # Test with different operation
    result = await mock_integration_hub.invoke_tool(
        "calculator",
        {
            "a": 10,
            "b": 2,
            "operation": "multiply"
        }
    )
    assert result == 20
```

#### Testing Error Handling

```python
@pytest.mark.asyncio
async def test_integration_hub_error_handling(mock_integration_hub):
    """Test error handling in the integration hub"""
    # Test with invalid tool
    with pytest.raises(ToolNotFoundError):
        await mock_integration_hub.invoke_tool(
            "nonexistent_tool",
            {"param": "value"}
        )
    
    # Test with invalid parameters
    with pytest.raises(ValidationError):
        await mock_integration_hub.invoke_tool(
            "calculator",
            {"invalid": "params"}
        )
    
    # Test tool logic error
    with pytest.raises(ValueError):
        await mock_integration_hub.invoke_tool(
            "calculator",
            {"a": 5, "b": 0, "operation": "divide"}
        )
```

### 5. Testing Memory System

Test the Memory System implementation:

#### Memory System Tests

```python
@pytest.mark.asyncio
async def test_memory_store_retrieve():
    """Test storing and retrieving memory items"""
    # Create memory system with mock database
    db_session = MagicMock()
    memory_system = WhiteboardMemory(lambda: db_session)
    
    # Initialize with config
    await memory_system.initialize(MemoryConfig(
        storage_type="whiteboard",
        retention_policy=RetentionPolicy(default_ttl_days=30)
    ))
    
    # Create test memory item
    memory_item = MemoryItem(
        type="message",
        content={"text": "Hello, world!"},
        metadata={"conversation_id": "conv-123"},
        timestamp=datetime.now(timezone.utc)
    )
    
    # Configure mock db for the add operation
    async def mock_context_manager():
        class MockContextManager:
            async def __aenter__(self):
                return db_session
            async def __aexit__(self, *args):
                pass
        return MockContextManager()
    
    # Set the return value for the db_session factory
    memory_system.db_session_provider = mock_context_manager
    
    # Store the item
    item_id = await memory_system.store("workspace-123", memory_item)
    
    # Verify the item was stored
    assert item_id is not None
    db_session.add.assert_called_once()
    db_session.commit.assert_called_once()
```

#### Memory Query Testing

```python
@pytest.mark.asyncio
async def test_memory_query():
    """Test querying memory items"""
    # Create memory system with mock database
    db_session = MagicMock()
    memory_system = WhiteboardMemory(lambda: db_session)
    
    # Set up mock query results
    db_items = [
        MagicMock(
            id="mem-1",
            type="message",
            content=json.dumps({"text": "Hello"}),
            metadata=json.dumps({"conversation_id": "conv-123"}),
            timestamp_utc=datetime.now(timezone.utc)
        ),
        MagicMock(
            id="mem-2",
            type="message",
            content=json.dumps({"text": "World"}),
            metadata=json.dumps({"conversation_id": "conv-123"}),
            timestamp_utc=datetime.now(timezone.utc)
        )
    ]
    
    # Configure mock db query execution
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = db_items
    db_session.execute.return_value = mock_result
    
    # Mock async context manager
    async def mock_context_manager():
        class MockContextManager:
            async def __aenter__(self):
                return db_session
            async def __aexit__(self, *args):
                pass
        return MockContextManager()
    
    # Set the return value for the db_session factory
    memory_system.db_session_provider = mock_context_manager
    
    # Create query
    query = MemoryQuery(
        types=["message"],
        metadata_filters={"conversation_id": "conv-123"}
    )
    
    # Retrieve items
    items = await memory_system.retrieve("workspace-123", query)
    
    # Verify results
    assert len(items) == 2
    assert items[0].content["text"] == "Hello"
    assert items[1].content["text"] == "World"
```

#### Context Synthesis Testing

```python
@pytest.mark.asyncio
async def test_memory_synthesis():
    """Test memory context synthesis"""
    # Create memory system with mock implementation
    memory_system = MagicMock(spec=MemorySystemInterface)
    
    # Configure the retrieve method to return test items
    memory_items = [
        MemoryItem(
            id="mem-1",
            type="message",
            content={"role": "user", "text": "Hello"},
            metadata={"conversation_id": "conv-123"},
            timestamp=datetime.now(timezone.utc)
        ),
        MemoryItem(
            id="mem-2",
            type="message",
            content={"role": "assistant", "text": "Hi there"},
            metadata={"conversation_id": "conv-123"},
            timestamp=datetime.now(timezone.utc)
        )
    ]
    
    async def mock_retrieve(workspace_id, query):
        return memory_items
    
    memory_system.retrieve = mock_retrieve
    
    # Configure the synthesize_context method
    synthesized = SynthesizedMemory(
        raw_items=memory_items,
        summary="A greeting exchange",
        entities={},
        relevance_score=1.0
    )
    
    async def mock_synthesize(workspace_id, query):
        return synthesized
    
    memory_system.synthesize_context = mock_synthesize
    
    # Create query
    query = MemoryQuery(
        types=["message"],
        metadata_filters={"conversation_id": "conv-123"}
    )
    
    # Get context
    context = await memory_system.synthesize_context("workspace-123", query)
    
    # Verify result
    assert context.summary == "A greeting exchange"
    assert len(context.raw_items) == 2
    assert context.relevance_score == 1.0
```

## FastAPI Dependency Testing Best Practices

### Use Dependency Overrides, Not Patching

FastAPI uses a dependency injection system. When testing, it's best to override the dependencies directly rather than patching functions:

```python
# DON'T DO THIS:
with patch("app.api.auth.get_db", return_value=mock_db):
    response = test_client.post("/auth/login", json={"username": "test"})

# DO THIS INSTEAD:
app.dependency_overrides[get_db] = lambda: mock_db
client = TestClient(app)
response = client.post("/auth/login", json={"username": "test"})
```

### Clean Up After Tests

Always clean up dependency overrides after your test, using either a try/finally block or a fixture with yield:

```python
# Using try/finally
def test_with_cleanup():
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        response = client.get("/endpoint")
        assert response.status_code == 200
    finally:
        app.dependency_overrides = {}

# Using fixture with yield (PREFERRED)
@pytest.fixture
def client_with_override():
    app.dependency_overrides[get_db] = lambda: mock_db
    client = TestClient(app)
    yield client
    app.dependency_overrides = {}

def test_with_fixture(client_with_override):
    response = client_with_override.get("/endpoint")
    assert response.status_code == 200
```

### Create Reusable Fixtures

Create fixtures for common dependencies and test setups:

```python
@pytest.fixture
def mock_user():
    """Create a mock user for testing"""
    return User(
        id="test-user-id",
        email="test@example.com",
        name="Test User"
    )

@pytest.fixture
def client_with_auth_override(mock_db, mock_user):
    """Create a test client with DB and auth overrides"""
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user
    client = TestClient(app)
    yield client
    app.dependency_overrides = {}
```

## Testing Async Code

### Always Use @pytest.mark.asyncio

For tests involving async functions:

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

### Handle Coroutines Properly

Ensure you properly await async functions:

```python
# DON'T DO THIS (won't run the function):
user = get_current_user(token, db)  # Returns a coroutine, not a User

# DO THIS INSTEAD:
user = await get_current_user(token, db)
```

### Testing Streaming Endpoints (SSE, WebSockets)

When testing streaming endpoints like Server-Sent Events (SSE) or WebSockets:

1. **Focus on API Contracts, Not Streaming Behavior**:
   - Test only the HTTP status codes, headers, and initial connection
   - Don't attempt to test the full streaming functionality in unit tests

2. **Never Read From Streams in Tests Without Proper Controls**:
   - Reading from infinite streams will cause tests to hang
   - If you must test stream content, use strict timeouts and proper cancellation

3. **Use a Comprehensive Mock Response Class**:
   ```python
   class MockSSEResponse:
       """A mock SSE response that won't cause tests to hang"""
       def __init__(self):
           self.status_code = 200
           self.headers = {
               "content-type": "text/event-stream",
               "cache-control": "no-cache",
               "connection": "keep-alive"
           }
           self._content = b"data: {}\n\n"
           self._closed = False

       def __enter__(self):
           return self

       def __exit__(self, *args):
           self.close()

       def close(self):
           self._closed = True

       def json(self):
           raise ValueError("Cannot call json() on a streaming response")

       # For iterator protocol
       def __iter__(self):
           yield self._content

       def iter_lines(self):
           yield self._content
   ```

4. **Create a Dedicated SSE Test Client**:
   ```python
   @pytest.fixture
   def sse_test_client(monkeypatch):
       """Test client that safely tests SSE endpoints without hanging"""
       client = TestClient(app)
       original_get = client.get
       
       # Patch get method to return mock responses for SSE endpoints
       def mock_get(url, **kwargs):
           if "/events" in url and "token=" in url:
               # For any SSE endpoint with a token, return a mock response
               token = url.split("token=")[1].split("&")[0] if "token=" in url else None
               if token:
                   try:
                       # Verify token is valid
                       payload = jwt.decode(token, settings.security.jwt_secret, algorithms=["HS256"])
                       
                       # For user-specific endpoint, check the user ID matches
                       if "/users/" in url:
                           url_user_id = url.split("/users/")[1].split("/")[0]
                           token_user_id = payload.get("user_id")
                           
                           # If user IDs don't match, let the endpoint handle the authorization error
                           if url_user_id != token_user_id:
                               return original_get(url, **kwargs)
                       
                       # Valid token and matching user ID (if applicable)
                       return MockSSEResponse()
                   except Exception:
                       # If token is invalid, let the endpoint handle it
                       pass
           # For all other requests, use original implementation
           return original_get(url, **kwargs)
       
       monkeypatch.setattr(client, "get", mock_get)
       return client
   ```

5. **Separate Integration and Connection Management Tests**:
   - Test API contracts with mocked responses
   - Test connection tracking logic separately
   - Use the Circuit Breaker pattern for components that might fail

6. **Clean Up Resources Even for Cancelled Tests**:
   - Always use `try/finally` to ensure proper cleanup
   - When a streaming test is cancelled, make sure background tasks are terminated
   - Use backups of active connection maps for test isolation
   - Add explicit timeouts to all async operations

7. **Use Contemporary Timezone-Aware DateTime Handling**:
   ```python
   # Instead of
   timestamp = datetime.utcnow()
   
   # Use
   timestamp = datetime.now(timezone.utc)
   ```

## Mock Database Sessions Correctly

### Mock at the Right Level

Generally, mock the session rather than individual database calls:

```python
# Configure the mock DB to return a test user
query_mock = MagicMock()
filter_mock = MagicMock()
mock_db.query.return_value = query_mock
query_mock.filter.return_value = filter_mock
filter_mock.first.return_value = test_user
```

### Handle SQLAlchemy Operations

When mocking, beware of SQLAlchemy's behavior:

```python
# For filtering methods
query_mock.filter.return_value = query_mock  # For chained query methods
query_mock.first.return_value = test_user    # For the terminal method

# For count operations
query_mock.count.return_value = 5
```

## Testing Architectural Integrity

### Repository Pattern Tests

Tests to ensure the repository pattern is properly implemented:

```python
def test_repository_abstraction():
    """Test that repositories properly abstract database details"""
    # Initialize repositories
    user_repo = UserRepository(MagicMock())
    workspace_repo = WorkspaceRepository(MagicMock())
    
    # Check interface method signatures
    assert hasattr(user_repo, "get_user_by_id")
    assert hasattr(user_repo, "get_user_by_email")
    assert hasattr(user_repo, "create_user")
    
    assert hasattr(workspace_repo, "get_workspace_by_id")
    assert hasattr(workspace_repo, "create_workspace")
    assert hasattr(workspace_repo, "get_user_workspaces")
```

### Service Layer Tests

Tests to ensure services maintain clean separation:

```python
def test_service_layer_separation():
    """Test that services properly separate concerns"""
    # Initialize services with mocked dependencies
    user_service = UserService(
        user_repository=MagicMock(),
        token_service=MagicMock()
    )
    
    workspace_service = WorkspaceService(
        workspace_repository=MagicMock(),
        user_repository=MagicMock()
    )
    
    # Check that services expose domain concepts and not SQL models
    assert not hasattr(user_service, "query")
    assert not hasattr(workspace_service, "session")
```

## Integration Testing

### API Integration Tests

End-to-end API tests with actual database interactions:

```python
@pytest.mark.integration
def test_user_registration_integration():
    """Integration test for user registration"""
    # Use test_client with actual DB
    client = TestClient(app)
    
    # Generate unique email to avoid conflicts
    unique_email = f"test-{uuid.uuid4()}@example.com"
    
    # Register a new user
    response = client.post(
        "/auth/register",
        json={
            "email": unique_email,
            "password": "StrongPassword123!",
            "name": "Test User"
        }
    )
    
    # Verify successful registration
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == unique_email
    
    # Verify user can login
    login_response = client.post(
        "/auth/login",
        json={
            "email": unique_email,
            "password": "StrongPassword123!"
        }
    )
    
    assert login_response.status_code == 200
    login_data = login_response.json()
    assert "token" in login_data
```

### Database Integration Tests

Tests for database interactions:

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_integration():
    """Test database operations directly"""
    # Get actual DB session
    async with AsyncSession(engine) as session:
        # Create a test user
        db_user = UserDB(
            id=str(uuid.uuid4()),
            email=f"test-{uuid.uuid4()}@example.com",
            hashed_password="hashed_password",
            name="Test User"
        )
        
        # Add and commit
        session.add(db_user)
        await session.commit()
        
        # Query to verify
        result = await session.execute(
            select(UserDB).where(UserDB.id == db_user.id)
        )
        fetched_user = result.scalars().first()
        
        # Verify
        assert fetched_user is not None
        assert fetched_user.email == db_user.email
        
        # Clean up
        await session.delete(fetched_user)
        await session.commit()
```

## Further Resources

For more detailed information on testing in Python:

- [pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing Documentation](https://fastapi.tiangolo.com/tutorial/testing/)
- [Mocking with unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)