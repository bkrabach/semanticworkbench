# Cortex Core Implementation Guide

This document provides comprehensive guidance for contributing to the Cortex Core implementation, including repository structure, contributing workflows, and troubleshooting guidance.

## Repository Structure

The Cortex Core repository is organized following a domain-driven design pattern with clean architectural boundaries:

```
cortex-core/
├── alembic/                # Database migration scripts
├── app/                    # Main application code
│   ├── api/                # API endpoints and routing definitions
│   ├── cache/              # Caching mechanisms (Redis implementation)
│   ├── components/         # Core components and business logic
│   │   ├── auth_schemes/   # Authentication implementations
│   │   ├── sse/            # Server-Sent Events implementation
│   │   └── ...             # Other business logic components
│   ├── database/           # Database models and repositories
│   │   └── repositories/   # Repository pattern implementations
│   ├── interfaces/         # Abstract base classes and interfaces
│   ├── models/             # Domain and API models
│   │   ├── api/            # API request/response models
│   │   │   ├── request/    # Request models
│   │   │   └── response/   # Response models
│   │   └── domain/         # Core domain models
│   ├── services/           # Service layer implementations
│   └── utils/              # Utility functions and helpers
├── docs/                   # Documentation
│   ├── adr/                # Architecture Decision Records
│   └── ...                 # Other documentation files
├── logs/                   # Log files
├── scripts/                # Utility scripts
└── tests/                  # Test suite
    ├── api/                # API tests
    ├── architecture/       # Architecture validation tests
    ├── components/         # Component tests
    ├── database/           # Database tests
    └── services/           # Service tests
```

## Key Components

### API Layer

The API layer is built using FastAPI and provides the following endpoints:

- `/auth`: Authentication endpoints
- `/conversations`: Conversation management
- `/workspaces`: Workspace management
- `/sse`: Server-Sent Events endpoints for real-time communication
- `/monitoring`: System monitoring endpoints
- `/integrations`: Domain expert integration endpoints

### Database Layer

The database layer uses SQLAlchemy with the following key abstractions:

- **Models**: SQLAlchemy ORM models in `app/database/models.py`
- **Repositories**: Domain-focused repositories in `app/database/repositories/`
- **Connection**: Database connection management in `app/database/connection.py`

### Component Layer

Core components implement the business logic:

- **CortexRouter**: Routes messages to appropriate handlers
- **SSE Manager**: Manages real-time connections with clients
- **IntegrationHub**: Connects to domain expert services
- **EventSystem**: Handles internal event publication and subscription
- **SecurityManager**: Manages permissions and access control

### Service Layer

Services orchestrate components and repositories:

- **ConversationService**: Manages conversations and messages
- **WorkspaceService**: Manages workspaces and resources
- **UserService**: Manages user accounts and settings
- **LLMService**: Interfaces with language models
- **SSEService**: Manages Server-Sent Events

## Development Workflow

### Setting Up Your Development Environment

1. **Clone the Repository**
   ```bash
   git clone https://github.com/your-org/cortex-core.git
   cd cortex-core
   ```

2. **Install Dependencies**
   ```bash
   uv pip install -e .
   uv add --dev pytest pytest-asyncio mypy ruff
   ```

3. **Environment Variables**
   Create a `.env` file with:
   ```
   LOG_LEVEL=DEBUG
   DATABASE_URL=sqlite:///cortex.db
   JWT_SECRET=your-secret-key
   REDIS_URL=redis://localhost:6379/0
   LLM_USE_MOCK=true
   ```

4. **Database Setup**
   ```bash
   uv run alembic upgrade head
   ```

5. **Run the Server**
   ```bash
   uv run -m app.main
   ```

### Development Commands

```bash
# Run the application
uv run -m app.main

# Run with auto-reload for development
uvicorn app.main:app --reload

# Run tests
python -m pytest

# Run specific tests
python -m pytest tests/api/test_auth.py::test_login

# Run type checking
mypy

# Run linting
ruff check

# Format code
ruff format

# Create database migrations
make revision MSG="description of change"
```

## Contributing to Major Components

### Adding New API Endpoints

1. Create appropriate API models in `app/models/api/`
2. Create domain models in `app/models/domain/`
3. Implement repository methods in `app/database/repositories/`
4. Implement service methods in `app/services/`
5. Create API endpoint in `app/api/`
6. Add tests in `tests/api/`

Example of a new API endpoint:

```python
# app/api/my_feature.py
from fastapi import APIRouter, Depends, HTTPException
from app.models.api.request.my_feature import MyFeatureRequest
from app.models.api.response.my_feature import MyFeatureResponse
from app.services.my_feature_service import MyFeatureService, get_my_feature_service

router = APIRouter(prefix="/my-feature", tags=["my-feature"])

@router.post("/", response_model=MyFeatureResponse)
async def create_my_feature(
    request: MyFeatureRequest,
    service: MyFeatureService = Depends(get_my_feature_service)
):
    """Create a new instance of MyFeature"""
    result = await service.create(request.dict())
    if not result:
        raise HTTPException(status_code=400, detail="Could not create MyFeature")
    return result
```

### Extending CortexRouter

The CortexRouter is responsible for message routing and processing:

1. Create new action handlers in `app/components/cortex_router.py`
2. Register new routing decisions in `_make_routing_decision`
3. Add new output targets if needed
4. Test with the SSE system end-to-end

Example of adding a new router action:

```python
async def _handle_custom_action(self, message: InputMessage, decision: RoutingDecision):
    """Handle a custom action type"""
    # Show typing indicator
    await self._send_typing_indicator(message.conversation_id, True)
    
    try:
        # Implement custom logic
        result = await self._process_custom_action(message.content)
        
        # Send result to the client
        await self._save_and_send_response(
            message.conversation_id,
            result,
            "assistant"
        )
    finally:
        # Turn off typing indicator
        await self._send_typing_indicator(message.conversation_id, False)
```

### Adding Domain Expert Integrations

1. Create integration interface in `app/interfaces/`
2. Implement integration client in `app/components/integration_hub.py`
3. Register tools in the `IntegrationHub`
4. Add tool handling in the CortexRouter

Example of registering a new tool:

```python
# In your initialization code
integration_hub = IntegrationHub()

@integration_hub.register_tool("calculator")
async def calculator(a: float, b: float, operation: str = "add"):
    """Perform basic calculator operations"""
    if operation == "add":
        return a + b
    elif operation == "subtract":
        return a - b
    elif operation == "multiply":
        return a * b
    elif operation == "divide":
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
    else:
        raise ValueError(f"Unknown operation: {operation}")
```

### SSE Feature Implementation

1. Define event model in `app/models/domain/sse.py`
2. Implement event handling in `app/components/sse/`
3. Create SSE endpoint in `app/api/sse.py`
4. Add client subscription in web interface

Example of sending an SSE event:

```python
# Get SSE service
sse_service = get_sse_service()

# Send event to a specific conversation
await sse_service.send_event(
    channel_type="conversation",
    resource_id=conversation_id,
    event_type="status_update",
    data={
        "status": "processing",
        "progress": 50,
        "message": "Processing your request..."
    }
)
```

## Testing Best Practices

Follow these practices for testing Cortex Core components:

1. **Use Dependency Overrides**: Override FastAPI dependencies directly
2. **Mock at the Right Level**: Mock the session or repository, not database calls
3. **Test Async Properly**: Use `@pytest.mark.asyncio` for async tests
4. **Isolate SSE Tests**: Test SSE endpoints without reading streams
5. **Integration Tests**: Test the complete flow of major features
6. **Architecture Tests**: Verify architectural boundaries are maintained

## Common Issues and Troubleshooting

### Database Connections

**Issue**: SQLAlchemy connection issues or "connection already closed"
**Solution**: Make sure to use the correct session management:

```python
# Good pattern
async with AsyncSession(engine) as session:
    # Use session here
    
# Bad pattern (session may leak)
session = AsyncSession(engine)
try:
    # Use session
finally:
    await session.close()
```

### SSE Connection Issues

**Issue**: SSE connections drop or don't receive events
**Solution**: Verify the connection manager is properly tracking connections:

1. Check that the global connection state is being used
2. Ensure events are published with the correct channel type and resource ID
3. Check that SSE endpoints return proper headers
4. Verify client reconnection logic is working

### Async Event Loop Issues

**Issue**: "Event loop is closed" or coroutine issues
**Solution**: Make sure all async tasks are properly managed:

1. Cancel background tasks in cleanup handlers
2. Use try/finally blocks for cleanup
3. Don't mix sync and async code without proper transitions
4. Add explicit timeouts to all async operations

### LLM Service Errors

**Issue**: LLM API calls fail or time out
**Solution**: Implement proper error handling and fallbacks:

1. Add timeouts to all API calls
2. Implement retries with exponential backoff
3. Use mock mode for development
4. Add detailed error logging

## Performance Optimization

### Database Optimization

1. **Use Indexing**: Ensure all frequently queried columns are indexed
2. **Limit Results**: Always use limit clauses for large result sets
3. **Pagination**: Implement cursor-based pagination for large collections
4. **Efficient Joins**: Use join instead of separate queries when possible

### Async Optimization

1. **Concurrent Operations**: Use `asyncio.gather` for parallel operations
2. **Avoid Blocking Calls**: Move blocking operations to background tasks
3. **Connection Pooling**: Configure proper connection pool sizes
4. **Task Priorities**: Consider task priority for important operations

### Memory Management

1. **Cache Invalidation**: Implement proper cache TTLs and invalidation
2. **Limit Resources**: Set reasonable limits on memory usage per request
3. **Garbage Collection**: Monitor GC performance and tune if needed
4. **Resource Cleanup**: Ensure all resources are properly released

## Component-Specific Guidelines

### CortexRouter

The router is the heart of the messaging system:

- Keep action handlers small and focused
- Separate routing decisions from action handling
- Maintain proper error boundaries between actions
- Add detailed logging for debugging
- Use proper type validation for all messages

### SSE System

The SSE system handles real-time communication:

- Minimize shared state between connections
- Implement heartbeat messages to keep connections alive
- Use explicit queue size limits to prevent memory issues
- Implement proper client disconnection detection
- Document all event types and formats

### LLM Service

The LLM service integrates with language models:

- Use streaming for better user experience
- Implement proper prompt engineering
- Add caching for identical requests
- Configure fallback models for reliability
- Track token usage for cost management

## Onboarding Flow for New Developers

1. **Environment Setup**: Follow the setup instructions above
2. **Architectural Overview**: Read the architecture documentation
3. **Component Examination**: Study each major component
4. **Simple Enhancement**: Add a small feature or fix a bug
5. **Testing Practice**: Write tests for your changes
6. **Documentation Update**: Update docs to reflect your changes
7. **Code Review**: Submit a PR and participate in code review

## Further Documentation

For more detailed information, refer to:

- [ARCHITECTURE.md](./docs/ARCHITECTURE.md): System architecture overview
- [API_REFERENCE.md](./docs/API_REFERENCE.md): API documentation
- [TESTING.md](./docs/TESTING.md): Testing best practices
- [ROUTER.md](./docs/ROUTER.md): CortexRouter documentation
- [SSE.md](./docs/SSE.md): SSE system documentation
- [MEMORY_SYSTEM.md](./docs/MEMORY_SYSTEM.md): Memory system documentation
- [LLM_INTEGRATION.md](./docs/LLM_INTEGRATION.md): LLM integration guide
- [DOMAIN_EXPERTS.md](./docs/DOMAIN_EXPERTS.md): Domain expert documentation