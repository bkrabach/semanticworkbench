# Development Guide

This document contains information for developers contributing to Cortex Core.

## Project Structure

```
cortex_core/
├── alembic/              # Database migrations
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI application
│   ├── config.py         # Configuration
│   ├── components/       # Core components
│   │   ├── __init__.py
│   │   └── security_manager.py
│   ├── interfaces/       # Interface definitions
│   │   ├── __init__.py
│   │   └── memory_system.py
│   ├── api/              # API endpoints
│   │   ├── __init__.py
│   │   └── auth.py
│   ├── modalities/       # Input/output modalities
│   │   └── __init__.py
│   ├── database/         # Database models and connection
│   │   ├── __init__.py
│   │   ├── connection.py
│   │   └── models.py
│   ├── cache/            # Redis cache
│   │   ├── __init__.py
│   │   └── redis_client.py
│   └── utils/            # Utility functions
│       ├── __init__.py
│       ├── json_helpers.py
│       └── logger.py
├── logs/                 # Log files
├── tests/                # Test cases
├── .env                  # Environment variables
└── pyproject.toml        # Project metadata and dependencies
```

## Key Components

### Session Manager

Handles user sessions and the association of sessions with specific workspaces, ensuring continuity and security across user interactions.

### Dispatcher

Routes incoming requests to the appropriate handlers, managing task delegation and coordination between different processing pathways.

### Context Manager

Interfaces with the memory system to retrieve, update, and maintain context across user interactions.

### Integration Hub

Facilitates communication with external services and tools, managing MCP client/server interactions.

### Workspace Manager

Handles the creation, retrieval, and organization of workspaces and associated conversations.

### Security Manager

Handles authentication, data encryption, and authorization processes to ensure all interactions are secure.

## Development Workflow

### Setting Up Development Environment

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/cortex-core.git
   cd cortex-core
   ```

2. Create and activate a virtual environment:

   ```bash
   uv venv
   # On Unix/macOS
   source .venv/bin/activate
   # On Windows
   .venv\Scripts\activate
   ```

3. Install dependencies in development mode:

   ```bash
   uv pip install -e ".[dev]"
   ```

4. Set up pre-commit hooks:
   ```bash
   pre-commit install
   ```

### Running Tests

```bash
# Run all tests
pytest

# Run specific tests
pytest tests/test_auth.py

# Run with coverage report
pytest --cov=app tests/

# Run only the event system tests
pytest tests/components/test_event_system.py
```

### Testing Best Practices

#### FastAPI Endpoint Testing

When testing FastAPI endpoints, use dependency overrides rather than patching:

```python
# BAD APPROACH (patching)
def test_login(test_client, mock_db):
    with patch("app.api.auth.get_db", return_value=mock_db):
        response = test_client.post("/auth/login", json={"username": "test"})
        assert response.status_code == 200

# GOOD APPROACH (dependency overrides)
@pytest.fixture
def client_with_db_override(mock_db):
    """Create a test client with DB dependency override"""
    app.dependency_overrides[get_db] = lambda: mock_db
    client = TestClient(app)
    yield client
    app.dependency_overrides = {}

def test_login(client_with_db_override):
    response = client_with_db_override.post("/auth/login", json={"username": "test"})
    assert response.status_code == 200
```

Key principles for effective API testing:

1. **Use dependency overrides**: Override FastAPI's dependency injection system rather than patching functions.
2. **Create specific fixtures**: Create fixtures that set up dependencies and clean up after tests.
3. **Handle async properly**: Use `@pytest.mark.asyncio` for async functions and properly await results.
4. **Clean up after tests**: Use `try/finally` or fixture yield patterns to clean up overrides.
5. **Mock at the right level**: Mock database sessions, not individual queries when possible.

## Simplification Principles

When working on the codebase, actively look for ways to simplify complex components. Follow these guidelines:

### Messaging and Real-time Components

1. **Prefer Asyncio over Threading**: 
   - Use `asyncio.Queue` instead of `queue.Queue`
   - Use `asyncio.create_task()` over thread creation
   - Implement a proper `cleanup()` method for any component with background tasks

2. **Direct Communication Paths**:
   - Prefer direct service calls over complex event chains for core flows
   - Only use the event system when true decoupling is needed
   - Keep the path from request to response as short as possible

3. **Smart Use of Required vs Optional Fields**:
   - Make fields required that are logically always needed
   - Eliminate unnecessary null checks for required fields  
   - Use appropriate type annotations to catch errors early

4. **Testing with Traceability**:
   - Test the complete flow from request to response
   - Focus on validating the end result, not implementation details
   - Use clear, direct tests that match the simplified architecture

### Complexity Evaluation

When evaluating whether to simplify a component, ask these questions:

1. **Core Purpose**: What is this component's essential purpose? Does its complexity serve that purpose?
2. **Cognitive Load**: How long does it take to understand the component and its interactions?
3. **Flow Visualization**: Can you easily diagram the component's interactions? If not, it's too complex.
4. **Error Scenarios**: How many potential failure points exist? Could they be reduced?
5. **Direct Path**: Is there a more direct way to achieve the same result?

The goal is to create components that are easy to understand, reason about, and maintain, while still fulfilling their core purposes.

#### Testing Async Components

For async components, always use the `asyncio` pytest plugin:

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

#### Testing the Event System

When testing the event system, consider these scenarios:

1. **Basic Pub/Sub Testing**:
   - Test publishing events and receiving them through subscribers
   - Verify that event payloads are correctly delivered

2. **Pattern Matching Testing**:
   - Test wildcard patterns like "domain.*" and "*"
   - Test exact matches and multi-level patterns

3. **Error Handling Testing**:
   - Verify that errors in one subscriber don't affect others
   - Test error counting in statistics

4. **Tracing and Correlation Testing**:
   - Test that trace IDs are properly generated and propagated
   - Verify correlation IDs link related events

5. **Performance Testing**:
   - Test with many subscribers
   - Test concurrent event publishing
   
Example test for the event system:

```python
@pytest.mark.asyncio
async def test_publish_subscribe(event_system):
    # Setup
    received_events = []
    
    async def callback(event_type, payload):
        received_events.append(payload)
    
    # Subscribe to events
    subscription_id = await event_system.subscribe("test.*", callback)
    
    # Publish an event
    await event_system.publish(
        event_type="test.event",
        data={"key": "value"},
        source="test_component"
    )
    
    # Verify
    assert len(received_events) == 1
    assert received_events[0].event_type == "test.event"
    assert received_events[0].data == {"key": "value"}
```

### Linting and Formatting

The project uses several tools to ensure code quality:

```bash
# Format code with Black
black app tests

# Sort imports with isort
isort app tests

# Run Ruff linter
ruff check app tests

# Run mypy type checking
mypy app tests
```

### Database Migrations

When you make changes to the database models, you need to create a new migration:

```bash
# Create a migration using the Makefile
make revision MSG="description of changes"

# Or directly with Alembic
alembic revision --autogenerate -m "description of changes"

# Apply migrations
alembic upgrade head
```

## Adding New Features

### Adding a New API Endpoint

1. Create a new file in the `app/api/` directory or add to an existing one:

   ```python
   # app/api/workspaces.py
   from fastapi import APIRouter, Depends, HTTPException
   from typing import List
   from app.database.connection import get_db
   from app.database.models import Workspace
   from app.components.security_manager import get_current_user

   router = APIRouter()

   @router.get("/")
   async def list_workspaces(user = Depends(get_current_user), db = Depends(get_db)):
       """List workspaces for the current user"""
       workspaces = db.query(Workspace).filter(Workspace.user_id == user.id).all()
       return {"workspaces": workspaces}
   ```

2. Include the router in the main application (`app/main.py`):

   ```python
   from app.api import workspaces

   app.include_router(workspaces.router, prefix="/workspaces", tags=["Workspaces"])
   ```

### Implementing a New Domain Expert Interface

1. Define the interface in `app/interfaces/`:

   ```python
   # app/interfaces/code_assistant.py
   from abc import ABC, abstractmethod
   from typing import Dict, Any, List

   class CodeAssistantInterface(ABC):
       @abstractmethod
       async def generate_code(self, prompt: str, language: str) -> str:
           """Generate code based on a prompt"""
           pass

       @abstractmethod
       async def review_code(self, code: str, language: str) -> List[Dict[str, Any]]:
           """Review code and provide suggestions"""
           pass
   ```

2. Implement the interface in `app/components/`:

   ```python
   # app/components/code_assistant.py
   from app.interfaces.code_assistant import CodeAssistantInterface

   class CodeAssistant(CodeAssistantInterface):
       async def generate_code(self, prompt: str, language: str) -> str:
           # Implementation
           pass

       async def review_code(self, code: str, language: str) -> List[Dict[str, Any]]:
           # Implementation
           pass
   ```

## Deployment

### Building Docker Images

```bash
# Build using the provided Dockerfile
docker build -f docker/Dockerfile.non_root -t cortex-core:latest .

# Run the container
docker run -p 4000:4000 \
    -v $(pwd)/proxy_config.yaml:/app/config.yaml \
    -e DATABASE_URL="postgresql://username:password@host:port/dbname" \
    -e SECURITY_JWT_SECRET="your-jwt-secret" \
    -e SECURITY_ENCRYPTION_KEY="your-encryption-key" \
    cortex-core:latest
```

### Using Docker Compose

A `docker-compose.yml` file is provided for local development:

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Continuous Integration

The project uses CircleCI for continuous integration. The configuration is defined in `.circleci/config.yml`.

The CI pipeline runs:

1. Linting checks (black, isort, ruff)
2. Type checking (mypy)
3. Unit tests
4. Integration tests

## Contributing Guidelines

1. Fork the repository and create a feature branch
2. Make your changes following the code style guidelines
3. Write tests for your changes
4. Ensure all tests pass and you've added appropriate documentation
5. Submit a pull request with a clear description of your changes

## Best Practices

- Follow the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- Use type hints for all function arguments and return values
- Document all public classes and methods with docstrings
- Write unit tests for new functionality
- Keep components modular and focused on a single responsibility
- Use dependency injection for better testability

## Core Development Principles

### Clean Implementation Over Backward Compatibility

**Important**: This codebase is currently in pre-production development. Therefore:

- **No Backward Compatibility Required**: When refactoring or redesigning components, do not maintain backward compatibility with previous implementations.
- **No Migration Path Needed**: Since the codebase and database are not yet in production use, you don't need to provide migration paths between versions.
- **Focus on Clean Design**: Prioritize creating clean, well-designed APIs and components without worrying about preserving old patterns or interfaces.
- **Delete Unused Code**: Remove deprecated or unused code entirely rather than keeping it around for compatibility.

This principle allows us to move quickly and maintain a clean codebase during initial development.

### Layered Architecture

```
┌─────────────────┐
│   API Layer     │ ← HTTP concerns only
├─────────────────┤
│  Service Layer  │ ← Business logic
├─────────────────┤
│ Repository Layer│ ← Data access
├─────────────────┤
│   Data Layer    │ ← Database/ORM
└─────────────────┘
```

This project follows a layered architecture to maintain separation of concerns:

- **API Layer**: Handles HTTP requests/responses, validation, authentication
- **Service Layer**: Contains business logic, orchestrates operations
- **Repository Layer**: Abstracts data access patterns
- **Data Layer**: ORM models, database connections

#### Service Layer Implementation Status

The Service Layer has been fully implemented across all major components:

- ✅ **SSE Components**: Fully implemented with proper domain-driven architecture
- ✅ **Conversation Components**: Fully implemented with service layer and domain models
- ✅ **User Components**: Fully implemented with proper authentication and event publishing
- ✅ **Workspace Components**: Fully implemented with complete CRUD operations

All major components now follow the domain-driven repository architecture with:
- Dedicated repository classes for data access
- Service layers for business logic
- Domain models for core entities
- API request and response models for HTTP concerns

### Domain-Driven Repository Architecture

We use a domain-driven repository architecture to maintain a clean separation between database models and business logic. This approach is built on three distinct model layers:

1. **Database Models** (SQLAlchemy): Represent the database schema
2. **Domain Models** (Pydantic): Represent business entities
3. **API Models** (Pydantic): Handle HTTP request/response concerns

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   API Models    │     │  Domain Models  │     │  Database Models│
│   (Pydantic)    │◄───►│   (Pydantic)    │◄───►│  (SQLAlchemy)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    API Layer    │     │  Service Layer  │     │Repository Layer │
│  (Controllers)  │     │(Business Logic) │     │ (Data Access)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

```python
# 1. Domain Model (Pydantic)
class UserDomain(BaseModel):
    """Domain model for a user"""
    id: str
    email: str
    name: str
    created_at: datetime
    
# 2. Repository Interface
class UserRepository(ABC):
    """Repository interface for user data access"""
    @abstractmethod
    def get_by_id(self, user_id: str) -> Optional[UserDomain]:
        """Get a user by ID"""
        pass
        
    @abstractmethod
    def create(self, email: str, name: str) -> UserDomain:
        """Create a new user"""
        pass

# 3. Repository Implementation
class SQLAlchemyUserRepository(UserRepository):
    """SQLAlchemy implementation of UserRepository"""
    def __init__(self, db_session: Session):
        self.db = db_session
        
    def get_by_id(self, user_id: str) -> Optional[UserDomain]:
        """Get a user by ID"""
        # Query the database model
        db_user = self.db.query(UserDB).filter(UserDB.id == user_id).first()
        if not db_user:
            return None
            
        # Convert to domain model
        return self._to_domain(db_user)
        
    def create(self, email: str, name: str) -> UserDomain:
        """Create a new user"""
        # Create a database model
        now = datetime.now(timezone.utc)
        db_user = UserDB(
            id=str(uuid.uuid4()),
            email=email, 
            name=name,
            created_at_utc=now
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        
        # Convert to domain model
        return self._to_domain(db_user)
        
    def _to_domain(self, db_user: UserDB) -> UserDomain:
        """Convert database model to domain model"""
        return UserDomain(
            id=db_user.id,
            email=db_user.email,
            name=db_user.name,
            created_at=db_user.created_at_utc
        )

# 4. Factory function for dependency injection
def get_user_repository(db_session: Session) -> UserRepository:
    """Get a user repository instance"""
    return SQLAlchemyUserRepository(db_session)
```

### Benefits of Domain-Driven Repository Architecture

1. **True Separation of Concerns**: 
   - API layer only handles HTTP concerns
   - Service layer contains pure business logic with domain models
   - Repository layer handles data access and model conversion
   - Database models remain focused on storage concerns

2. **Consistent Naming and Structure**:
   - Domain models use business terminology (e.g., `metadata`)
   - Database models use DB-specific terminology (e.g., `meta_data`)
   - No confusion about field names across layers

3. **Enhanced Testability**:
   - Each layer can be tested in isolation
   - Domain models can be unit tested without database
   - Services can be tested with mocked repositories
   - APIs can be tested with mocked services

4. **Type Safety**:
   - Pydantic provides validation and type checking for domain and API models
   - Clear interfaces between layers improves IDE support
   - Prevents data corruption across layer boundaries

### Implementation Guidelines

#### When to Use This Architecture

**ALWAYS** use this architecture for:
- All data access across the application
- Business logic that manipulates domain entities
- API endpoints that expose domain functionality
- Services that orchestrate operations

#### Implementation Steps

1. **Create Domain Models** in `app/models/domain/`:
   - Define Pydantic models representing business entities
   - Use domain terminology for field names
   - Include validation rules specific to domain

2. **Implement Repository Interfaces and Classes** in `app/database/repositories/`:
   - Create abstract base classes defining data access methods
   - Implement concrete classes for SQLAlchemy
   - Include conversion methods between DB and domain models
   - Return domain models from all repository methods

3. **Create Services** in `app/services/`:
   - Implement business logic using domain models
   - Inject repositories through constructors
   - Handle orchestration across multiple repositories

4. **Update API Endpoints** in `app/api/`:
   - Use services for all business logic
   - Convert between API models and domain models
   - Focus on HTTP-specific concerns

#### Example: Adding New Data Access Methods

When you need to access data in a way not covered by existing repositories:

```python
# 1. Create a domain model for the result
class WorkspaceMemberDomain(BaseModel):
    """Domain model for workspace member"""
    user_id: str
    workspace_id: str
    access_level: str
    added_at: datetime

# 2. Add to repository interface
class WorkspaceRepository(ABC):
    # Existing methods...
    
    @abstractmethod
    def get_workspace_members(self, workspace_id: str) -> List[WorkspaceMemberDomain]:
        """Get all members with access to a workspace"""
        pass

# 3. Implement in the concrete class with model conversion
class SQLAlchemyWorkspaceRepository(WorkspaceRepository):
    # Existing methods...
    
    def get_workspace_members(self, workspace_id: str) -> List[WorkspaceMemberDomain]:
        """Get all members with access to a workspace"""
        # Query database models
        sharing_records = self.db.query(WorkspaceSharingDB).filter(
            WorkspaceSharingDB.workspace_id == workspace_id
        ).all()
        
        # Convert to domain models
        return [self._sharing_to_domain(record) for record in sharing_records]
        
    def _sharing_to_domain(self, db_record: WorkspaceSharingDB) -> WorkspaceMemberDomain:
        """Convert DB model to domain model"""
        return WorkspaceMemberDomain(
            user_id=db_record.user_id,
            workspace_id=db_record.workspace_id,
            access_level=db_record.access_level,
            added_at=db_record.created_at_utc
        )
```

#### Example: Service with Multiple Repositories

Services orchestrate operations across multiple repositories:

```python
# Domain model for analytics results
class WorkspaceStatsDomain(BaseModel):
    """Domain model for workspace statistics"""
    workspace_id: str
    workspace_name: str
    total_conversations: int
    active_conversations: int
    total_messages: int
    memory_items_count: int
    last_activity: Optional[datetime] = None

# Service implementation
class WorkspaceAnalyticsService:
    """Service for workspace analytics"""
    
    def __init__(self, 
                 workspace_repo: WorkspaceRepository,
                 conversation_repo: ConversationRepository,
                 memory_repo: MemoryRepository):
        self.workspace_repo = workspace_repo
        self.conversation_repo = conversation_repo
        self.memory_repo = memory_repo
        
    def generate_workspace_stats(self, workspace_id: str) -> WorkspaceStatsDomain:
        """Generate statistics for a workspace"""
        # Fetch data using repositories
        workspace = self.workspace_repo.get_by_id(workspace_id)
        if not workspace:
            raise ValueError(f"Workspace not found: {workspace_id}")
            
        conversations = self.conversation_repo.get_by_workspace(workspace_id)
        memory_items = self.memory_repo.get_by_workspace(workspace_id)
        
        # Apply business logic to calculate statistics
        active_conversations = [c for c in conversations 
                               if c.last_active_at > (datetime.now() - timedelta(days=7))]
        
        # Create and return domain model
        return WorkspaceStatsDomain(
            workspace_id=workspace.id,
            workspace_name=workspace.name,
            total_conversations=len(conversations),
            active_conversations=len(active_conversations),
            total_messages=sum(len(c.messages) for c in conversations),
            memory_items_count=len(memory_items),
            last_activity=workspace.last_active_at
        )

# Factory function for service
def get_workspace_analytics_service(db: Session = Depends(get_db)) -> WorkspaceAnalyticsService:
    """Get workspace analytics service"""
    workspace_repo = get_workspace_repository(db)
    conversation_repo = get_conversation_repository(db)
    memory_repo = get_memory_repository(db)
    
    return WorkspaceAnalyticsService(
        workspace_repo=workspace_repo,
        conversation_repo=conversation_repo,
        memory_repo=memory_repo
    )
```

#### Navigating the Codebase

To understand how repositories are used:
- `app/database/repositories.py` - Repository interfaces and implementations
- `app/api/conversations.py` - Example of API using repositories
- `app/components/` - Service components using repositories

#### Troubleshooting

If you need to maintain backward compatibility with existing direct DB access:
- First implement the proper repository-based solution
- Then add a fallback mechanism that uses the repository when available
- Document the pattern you've chosen to help future developers

#### Common Integration Issues

When integrating with FastAPI, be aware of these common issues:

1. **Response Model Inference**:
   FastAPI tries to infer response types from function parameters. When repositories are injected directly as dependencies, this can cause errors about SQLAlchemy session types being included in response models. To avoid this:
   
   ```python
   # PROBLEMATIC:
   @router.get("/endpoint")
   async def endpoint(
       repo: SomeRepository = Depends(get_some_repository)  # This can cause issues
   ):
       # ...
   
   # CORRECT:
   @router.get("/endpoint")
   async def endpoint(
       db: Session = Depends(get_db)  # Inject session instead
   ):
       repo = get_some_repository(db)  # Create repository inside function
       # ...
   ```

2. **Type Conversion**:
   SQLAlchemy columns may need explicit conversion to Python types when used in function arguments:
   
   ```python
   # Remember to convert SQLAlchemy Column types to strings when needed
   repo.get_by_id(str(model.id))  # Not: repo.get_by_id(model.id)
   ```

### Common Anti-patterns to Avoid

1. **CRITICAL: SQLAlchemy models in API or service layers**: SQLAlchemy database models must NEVER be imported or used outside the repository layer
   ```python
   # INCORRECT - NEVER do this
   from app.database.models import User  # In API or service layer
   
   # CORRECT - Always use domain models in API and service layers
   from app.models.domain.user import User
   ```

2. **Mixing SQL queries with business logic**: Keep data access contained within repositories
3. **Direct JSON string manipulation in API layer**: Handle serialization consistently
4. **Heavy database logic in API handlers**: Move this to repositories
5. **Complex mocking in tests**: Mock at interface boundaries, not implementation details
6. **Direct boolean evaluation of SQLAlchemy Column objects**: This causes type errors since Column.__bool__ returns NoReturn
7. **Missing awaits for coroutines**: Failing to await async methods causes "unused coroutine" errors

### Layer Boundary Rules

These rules MUST be followed to maintain clean architecture:

1. **Database models (SQLAlchemy)**: 
   - MUST remain confined to the repositories layer
   - MUST NOT be imported in services, API, or components
   - MUST NOT be returned from repository methods

2. **Domain models (Pydantic)**:
   - MUST be used for all business logic
   - MUST be the only models used in the service layer
   - MUST be the only models used across layer boundaries

3. **API models (Pydantic)**:
   - MUST be used for all API endpoints
   - MUST be converted to/from domain models in API handlers
   - MUST NOT interact directly with repositories

### Testing with Domain-Driven Architecture

This architecture greatly simplifies testing by allowing each layer to be tested in isolation:

#### Domain Model Testing

```python
def test_user_domain_validation():
    """Test domain model validation rules"""
    # Valid user
    user = UserDomain(
        id="123",
        email="test@example.com",
        name="Test User",
        created_at=datetime.now()
    )
    assert user.id == "123"
    
    # Invalid email
    with pytest.raises(ValidationError):
        UserDomain(
            id="123",
            email="invalid-email",
            name="Test User",
            created_at=datetime.now()
        )
```

#### Repository Testing

```python
@pytest.mark.asyncio
async def test_user_repository():
    """Test user repository with test database"""
    # Setup test database
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    # Create repository
    repo = SQLAlchemyUserRepository(db)
    
    # Test create
    user = repo.create(email="test@example.com", name="Test User")
    assert isinstance(user, UserDomain)
    assert user.email == "test@example.com"
    
    # Test get by ID
    found = repo.get_by_id(user.id)
    assert found is not None
    assert found.id == user.id
    assert found.name == "Test User"
```

#### Service Testing

```python
def test_user_service():
    """Test user service with mocked repository"""
    # Create mock repository
    mock_repo = MagicMock(spec=UserRepository)
    mock_repo.get_by_id.return_value = UserDomain(
        id="123",
        email="test@example.com",
        name="Test User",
        created_at=datetime.now()
    )
    
    # Create service with mock repository
    service = UserService(mock_repo)
    
    # Test service method
    user = service.get_user("123")
    assert user is not None
    assert user.id == "123"
    assert user.name == "Test User"
    
    # Verify repository was called correctly
    mock_repo.get_by_id.assert_called_once_with("123")
```

#### API Testing

```python
def test_get_user_endpoint(client):
    """Test API endpoint with mocked service"""
    # Create mock service
    mock_service = MagicMock(spec=UserService)
    mock_service.get_user.return_value = UserDomain(
        id="123",
        email="test@example.com",
        name="Test User",
        created_at=datetime.now(timezone.utc)
    )
    
    # Override service dependency
    app.dependency_overrides[get_user_service] = lambda: mock_service
    
    try:
        # Call API endpoint
        response = client.get("/users/123")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "123"
        assert data["name"] == "Test User"
        
        # Verify service was called
        mock_service.get_user.assert_called_once_with("123")
    finally:
        # Clean up override
        app.dependency_overrides.pop(get_user_service)
```

### SQLAlchemy Column Handling Best Practices

When working with SQLAlchemy ORM models, follow these guidelines to avoid common type issues:

> ⚠️ **CRITICAL: SQLAlchemy models MUST be confined to repositories only!**
> 
> SQLAlchemy models must never cross layer boundaries:
> - Never import SQLAlchemy models in API, service, or components 
> - Always convert to domain models in repositories
> - Run `./check_imports.sh` to verify architectural boundaries
>
> Boundary violations cause:
> - Type errors with SQLAlchemy Column objects
> - Leakage of database concerns into business logic
> - Difficulty with testing and mocking

1. **Never directly evaluate Column objects as booleans**:
   ```python
   # INCORRECT - causes "Invalid conditional operand of type 'Column[str]'" error
   if db_model.name:
       # do something
   
   # CORRECT - explicitly check against None
   if db_model.name is not None:
       # do something
   ```

2. **Convert Column datetime objects to Python datetime objects**:
   ```python
   # INCORRECT - passes a Column[datetime] to a function expecting datetime
   created_at = db_model.created_at_utc
   
   # CORRECT - convert to Python datetime object first
   created_at = datetime.fromisoformat(str(db_model.created_at_utc)) if db_model.created_at_utc is not None else datetime.now(timezone.utc)
   ```

3. **Convert Column string objects to Python strings when necessary**:
   ```python
   # INCORRECT - uses Column[str] directly
   metadata_json = db_model.meta_data
   
   # CORRECT - convert to Python string first
   metadata_json = str(db_model.meta_data) if db_model.meta_data is not None else "{}"
   ```

4. **Handle JSON fields consistently**:
   ```python
   # CORRECT pattern for parsing JSON from Column objects
   try:
       # ALWAYS convert SQLAlchemy Column to string before passing to json.loads
       metadata_str = str(db_model.meta_data) if db_model.meta_data is not None else "{}"
       metadata = json.loads(metadata_str)
   except (json.JSONDecodeError, TypeError):
       metadata = {}
   ```
   
   **IMPORTANT**: The direct use of `json.loads(db_model.some_json)` will fail with `Argument of type "Column[str]" cannot be assigned to parameter "s" of type "str | bytes"` - Always convert to string first!

5. **When converting database models to domain models, always include proper type conversion**:
   ```python
   return User(
       id=str(db_model.id),
       email=str(db_model.email),
       name=str(db_model.name) if db_model.name is not None else None,
       created_at=created_at,  # Already converted to Python datetime
       # ...
   )
   ```

### Async/Await Consistency

When working with asynchronous code:

1. **Always await coroutine functions**:
   ```python
   # INCORRECT - causes "Value of type 'Coroutine[Any, Any, None]' must be used" error
   self.event_system.publish(event_type="user.created", data=data, source="user_service")
   
   # CORRECT - use await keyword
   await self.event_system.publish(event_type="user.created", data=data, source="user_service")
   ```

2. **Methods that call coroutines must also be async**:
   ```python
   # INCORRECT - method calls a coroutine but is not async itself
   def create_user(self, email: str, name: str):
       # ...
       self.event_system.publish(...)  # This is a coroutine
   
   # CORRECT - method is declared as async
   async def create_user(self, email: str, name: str):
       # ...
       await self.event_system.publish(...)
   ```

3. **Chain async method calls properly**:
   ```python
   # CORRECT pattern for calling async publish methods
   if self.event_system:
       await self._publish_user_created_event(user)
   ```

### Code Review Checklist

Before approving a PR, check:

#### Architecture Integrity
- [ ] **Layer Separation**: Is business logic separate from data access?
- [ ] **CRITICAL: No Database Model Leaks**: Are database models (SQLAlchemy) strictly confined to repositories?
- [ ] **Import Safety**: Do API and service files ONLY import domain models, never database models?
- [ ] **Repository Contracts**: Do all repository methods return only domain models, never database models?
- [ ] **Component Boundaries**: Is there clear separation between API handlers and business logic?

#### Quality Checks
- [ ] **Type Safety**: Are SQLAlchemy Column objects handled correctly (no direct boolean evaluation)?
- [ ] **Async Correctness**: Are all coroutine functions properly awaited?
- [ ] **Model Conversions**: Are domain models properly converted from database models with correct types?
- [ ] **JSON Handling**: Are JSON manipulations encapsulated in appropriate layers?
- [ ] **Test Approach**: Are tests mocking at interface boundaries, not implementation details?
- [ ] **Error Handling**: Is there proper error handling between layers?

#### Anti-Pattern Detection
- [ ] **No SQLAlchemy Imports**: Check all API and service files to ensure they never import from app.database.models
- [ ] **No Repository Access in API**: Ensure API endpoints use services, never repositories directly
- [ ] **No Database Logic**: Ensure database operations are contained within repositories only

### Refactoring Strategy

When refactoring existing code:

1. **Identify better designs**: Think about the cleanest possible implementation without constraints
2. **Make clean breaks**: Don't worry about maintaining backward compatibility 
3. **Extract repositories and services**: Move data access into repository classes and business logic into service classes
4. **Implement interfaces**: Define clear interfaces between components
5. **Update tests**: Rewrite tests to target public interfaces, not implementation details
6. **Remove old implementations**: Delete deprecated code completely rather than leaving it for compatibility

Remember: This is a pre-production codebase, so prioritize clean implementation over compatibility.

## Architecture Validation Tools

### SQLAlchemy Import Checker

To help prevent architectural boundary violations, you can use this script to detect improper imports:

```bash
#!/bin/bash
# Check for SQLAlchemy model imports in API and service layers

echo "Checking for SQLAlchemy model imports in API layer..."
grep -r "from app.database.models import" --include="*.py" app/api/

echo "Checking for SQLAlchemy model imports in service layer..."
grep -r "from app.database.models import" --include="*.py" app/services/

echo "Checking for SQLAlchemy model imports in components..."
grep -r "from app.database.models import" --include="*.py" app/components/

# Save as check_imports.sh and run with: bash check_imports.sh
```

Run this regularly to catch architecture violations early.
