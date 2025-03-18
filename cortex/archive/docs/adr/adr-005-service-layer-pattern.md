# ADR-005: Service Layer Pattern

## Status

Accepted

## Context

In the early stages of the Cortex Core development, business logic was often placed directly in API endpoints, leading to several issues:

1. **Logic Duplication**: Similar business logic appeared in multiple endpoints
2. **Mixed Concerns**: HTTP handling was mixed with business rules and data access
3. **Testing Complexity**: API endpoints became difficult to test in isolation
4. **Poor Code Organization**: As endpoints grew, they became difficult to maintain
5. **Inconsistent Error Handling**: Error handling varied across endpoints
6. **Limited Reusability**: Business logic couldn't be reused across different interfaces
7. **Event Publishing**: Event publishing was inconsistently implemented

These issues made the codebase less maintainable and more prone to bugs. As the system grew in complexity, we needed a better approach to organizing business logic.

## Decision

We've decided to implement a dedicated Service Layer between the API endpoints and repositories. This Service Layer:

1. **Contains Business Logic**: Services implement all business rules and workflows
2. **Orchestrates Operations**: Services coordinate operations across multiple repositories
3. **Handles Domain Events**: Services publish domain events when significant actions occur
4. **Is Domain-Focused**: Services work exclusively with domain models, not database or API models
5. **Provides Error Consistency**: Services standardize error handling patterns

A typical service pattern looks like:

```python
class UserService:
    """Service for user-related operations"""
    
    def __init__(self, repository: UserRepository, event_system: Optional[EventSystem] = None):
        self.repository = repository
        self.event_system = event_system
        
    def get_user(self, user_id: str) -> Optional[User]:
        """Get a user by ID"""
        return self.repository.get_by_id(user_id)
        
    async def create_user(self, email: str, name: str, password_hash: str) -> User:
        """Create a new user"""
        # Business logic - pre-creation validations
        if not is_valid_email(email):
            raise ValueError("Invalid email format")
            
        # Check if user exists
        existing_user = self.repository.get_by_email(email)
        if existing_user:
            raise ValueError("User with this email already exists")
        
        # Create the user
        user = self.repository.create(
            email=email,
            name=name,
            password_hash=password_hash
        )
        
        # Publish event
        if self.event_system:
            await self._publish_user_created_event(user)
            
        return user
        
    async def _publish_user_created_event(self, user: User) -> None:
        """Publish an event when a user is created"""
        if not self.event_system:
            return
            
        await self.event_system.publish(
            event_type="user.created",
            data={"user_id": user.id, "email": user.email},
            source="user_service"
        )
```

API endpoints now focus purely on HTTP concerns, delegating business logic to services:

```python
@router.post("/users", response_model=UserResponse)
async def create_user(
    request: CreateUserRequest,
    service: UserService = Depends(get_user_service)
):
    try:
        # Delegate to service
        user = await service.create_user(
            email=request.email,
            name=request.name,
            password_hash=get_password_hash(request.password)
        )
        
        # Convert domain model to response model
        return UserResponse(
            id=user.id,
            email=user.email,
            name=user.name
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

## Consequences

### Positive

1. **Cleaner Separation of Concerns**: API handlers focus on HTTP, services on business logic, repositories on data access
2. **Improved Testability**: Services can be tested independently of HTTP concerns
3. **Better Code Organization**: Business logic has a dedicated location
4. **Consistent Error Handling**: Standard patterns across all services
5. **Reusable Logic**: Services can be used by different interfaces (API, CLI, etc.)
6. **Event Publishing**: Consistent event publishing patterns
7. **Clear Dependency Chain**: API → Service → Repository → Database

### Negative

1. **Additional Abstraction Layer**: One more layer in the architecture
2. **Potential Overhead**: Services add some overhead to simple operations
3. **Dependency Management**: Need to inject repositories and other dependencies
4. **More Files**: Codebase has more files to navigate

## Implementation Guidelines

1. **Service Structure**:
   - Each domain entity gets its own service (`UserService`, `WorkspaceService`, etc.)
   - Services should be stateless and take dependencies via constructor injection
   - Only domain models should be used within services, never database or API models

2. **Service Methods**:
   - Follow a consistent naming pattern (`get_x`, `create_x`, `update_x`, `delete_x`)
   - Methods should do one thing and do it well
   - Methods should be properly type-annotated
   - Async methods should be used where appropriate, especially for event publishing

3. **Error Handling**:
   - Services should raise domain-specific exceptions, not HTTP exceptions
   - Services should validate inputs and preconditions
   - Services should handle errors from repositories appropriately

4. **Event Publishing**:
   - Services should publish domain events for significant state changes
   - Event publishing methods should be private (`_publish_x_event`)
   - Events should include all relevant context but avoid sensitive data

5. **Factory Functions**:
   - Each service should have a factory function for dependency injection
   - Factory functions should be used with FastAPI's dependency injection system

## Alternatives Considered

### Transaction Script Pattern

We considered using a simpler Transaction Script pattern where operations are handled by standalone functions. This would have:
- Reduced the abstraction level
- Made the code potentially simpler
- Required less boilerplate

We rejected this approach because:
- It scales poorly with increasing complexity
- It tends to lead to duplication over time
- It lacks the organization benefits of dedicated service classes
- It makes dependency injection more challenging

### Active Record Pattern

We considered using an Active Record pattern where domain models have methods for persistence. This would have:
- Reduced the number of classes needed
- Put business logic closer to the data it operates on
- Made simple operations more straightforward

We rejected this approach because:
- It mixes data access and business logic concerns
- It makes testing more difficult
- It contradicts our goal of clean separation between domain and database models

### Direct Repository Use in API Endpoints

We considered continuing to use repositories directly in API endpoints. This would have:
- Removed a layer of abstraction
- Simplified the codebase in the short term
- Required less migration work

We rejected this approach because:
- It fails to address the issues mentioned in the Context section
- It doesn't scale well as the system grows
- It doesn't provide a clean location for business logic

## References

- [Domain-Driven Design](https://martinfowler.com/bliki/DomainDrivenDesign.html)
- [Service Layer Pattern](https://martinfowler.com/eaaCatalog/serviceLayer.html)
- [Organizing Services in Hexagonal Architecture](https://herbertograca.com/2017/11/16/explicit-architecture-01-ddd-hexagonal-onion-clean-cqrs-how-i-put-it-all-together/)