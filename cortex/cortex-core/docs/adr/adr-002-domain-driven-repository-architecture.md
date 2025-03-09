# ADR-002: Domain-Driven Repository Architecture

## Status

Accepted

## Context

Early versions of the Cortex Core codebase faced several challenges:

1. **Tight Coupling**: Direct use of SQLAlchemy models throughout the codebase created tight coupling between database implementation and business logic
2. **Type Safety Issues**: SQLAlchemy models have special type characteristics that can cause subtle bugs when used directly in business logic
3. **Testing Difficulties**: Mocking database models was cumbersome and led to brittle tests
4. **Inconsistent Serialization**: JSON serialization of SQLAlchemy models required special handling
5. **Layer Violations**: Business logic was often mixed with data access concerns

These issues resulted in:
- Frequent bugs related to type errors
- Difficulty understanding the codebase
- Tests that broke when database schema changed
- Challenges in evolving the system cleanly

For a system expected to grow in complexity and be maintained by different team members, we needed a more structured approach to separate concerns and improve maintainability.

## Decision

We have adopted a domain-driven repository architecture with these key components:

1. **Three Model Types**:
   - **Database Models (SQLAlchemy)**: Represent database schema
   - **Domain Models (Pydantic)**: Represent business entities
   - **API Models (Pydantic)**: Handle HTTP request/response concerns

2. **Repository Pattern**: 
   - Repositories abstract data access
   - Repositories translate between database and domain models
   - Repositories are the only components that directly interact with database models

3. **Service Layer**:
   - Services contain business logic
   - Services work exclusively with domain models
   - Services orchestrate operations across multiple repositories

4. **API Layer**:
   - API endpoints handle HTTP concerns
   - API endpoints translate between API and domain models
   - API endpoints delegate business logic to services

The architecture can be represented as:

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

## Consequences

### Positive

1. **Clear Separation of Concerns**: Each layer has a specific responsibility
2. **Improved Type Safety**: All models are strongly typed with explicit conversions
3. **Better Testability**: Each layer can be tested in isolation
4. **Flexible Evolution**: Database schema can change independently of business logic
5. **Consistent Patterns**: Common patterns for data access, validation, and business logic
6. **Developer Guidance**: Clear boundaries for developers to respect
7. **More Expressive Domain Models**: Domain models represent business concepts directly

### Negative

1. **Increased Boilerplate**: More code required for model conversions
2. **Learning Curve**: New developers need to understand the architecture
3. **Development Overhead**: More files and classes to navigate
4. **Performance Cost**: Multiple model conversions add some overhead
5. **Integration Complexity**: Ensuring proper integration between layers

## Example Implementation

Here's a simplified example of the architecture in action:

1. **Database Model** (SQLAlchemy):
   ```python
   class UserDB(Base):
       __tablename__ = "users"
       id = Column(String, primary_key=True)
       email = Column(String, unique=True)
       name = Column(String)
       password_hash = Column(String)
       meta_data = Column(String)  # Stored as JSON string
   ```

2. **Domain Model** (Pydantic):
   ```python
   class User(BaseModel):
       id: str
       email: str
       name: Optional[str] = None
       password_hash: str
       metadata: Dict[str, Any] = Field(default_factory=dict)
   ```

3. **Repository** (SQLAlchemy to Domain conversion):
   ```python
   class UserRepository:
       def __init__(self, db_session: Session):
           self.db = db_session
           
       def get_by_id(self, user_id: str) -> Optional[User]:
           db_user = self.db.query(UserDB).filter(UserDB.id == user_id).first()
           if not db_user:
               return None
           return self._to_domain(db_user)
           
       def _to_domain(self, db_model: UserDB) -> User:
           # Convert SQLAlchemy model to domain model
           metadata = json.loads(str(db_model.meta_data)) if db_model.meta_data else {}
           return User(
               id=str(db_model.id),
               email=str(db_model.email),
               name=str(db_model.name) if db_model.name else None,
               password_hash=str(db_model.password_hash),
               metadata=metadata
           )
   ```

4. **Service** (Business logic):
   ```python
   class UserService:
       def __init__(self, repository: UserRepository):
           self.repository = repository
           
       def authenticate_user(self, email: str, password: str) -> Optional[User]:
           user = self.repository.get_by_email(email)
           if not user:
               return None
           if not verify_password(password, user.password_hash):
               return None
           return user
   ```

5. **API Endpoint** (HTTP concerns):
   ```python
   @router.post("/login", response_model=UserResponse)
   async def login(
       credentials: UserLoginRequest,
       service: UserService = Depends(get_user_service)
   ):
       user = service.authenticate_user(credentials.email, credentials.password)
       if not user:
           raise HTTPException(401, "Invalid credentials")
       return UserResponse(
           id=user.id,
           email=user.email,
           name=user.name
       )
   ```

## Alternatives Considered

### Using SQLAlchemy Models Directly

We considered using SQLAlchemy models throughout the codebase, which would have resulted in:
- Less code (no separate domain models or conversions)
- Single source of truth for data structures
- No need for repositories

However, this approach would have maintained all the problems described in the Context section, particularly around type safety and testing.

### ORM with Pydantic Integration

We considered tools that integrate SQLAlchemy and Pydantic more directly, such as `SQLModel`. Benefits would include:
- Less boilerplate code
- Automatic conversion between ORM and Pydantic
- Single model definition for both database and domain concerns

We rejected this approach because:
- It would still couple database and domain concerns
- Custom business logic in domain models would be mixed with database concerns
- The codebase was already using SQLAlchemy and Pydantic separately
- The technology is relatively new with evolving patterns

### Alternative Repository Patterns

We considered alternative repository patterns:
- Generic repositories with type parameters
- Query object pattern
- Transaction script pattern

We chose our specific implementation because it:
- Provides explicit control over model conversions
- Makes domain models the central focus
- Has clear patterns for data access
- Is easier to understand and extend

## References

- [Domain-Driven Design principles](https://martinfowler.com/books/evans.html)
- [Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html)
- [SQLAlchemy documentation](https://docs.sqlalchemy.org/)
- [Pydantic documentation](https://docs.pydantic.dev/)