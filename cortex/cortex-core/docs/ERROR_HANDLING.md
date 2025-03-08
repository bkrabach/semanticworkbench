# Error Handling Guide

This document details the error handling patterns and practices in Cortex Core.

## Error Philosophy

Cortex Core follows these principles for error handling:

1. **Fail Fast, Fail Clearly** - Errors should be detected as early as possible with clear messages
2. **Graceful Degradation** - The system should continue to operate even when some components fail
3. **Structured Error Information** - Errors should include structured data for both humans and machines
4. **Consistent Error Format** - All APIs should return errors in a consistent format
5. **Appropriate Error Codes** - HTTP status codes should accurately reflect the error type

## Error Response Format

All API error responses follow a standard JSON format:

```json
{
  "detail": "Description of the error",
  "code": "ERROR_CODE",
  "params": {
    "param_name": "Additional context about the error"
  },
  "trace_id": "unique-trace-id-for-debugging"
}
```

### Field Definitions

- **detail**: Human-readable description of the error
- **code**: Machine-readable error code (upper snake case)
- **params**: Additional context-specific parameters
- **trace_id**: Unique identifier for tracing the error through logs

## HTTP Status Codes

Cortex Core uses standard HTTP status codes for error responses:

| Status Code | Meaning | Example Scenario |
|-------------|---------|-----------------|
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Valid authentication but insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Resource state conflict (e.g., concurrent modification) |
| 422 | Unprocessable Entity | Valid request but semantically incorrect |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Unexpected server-side error |
| 503 | Service Unavailable | System overloaded or under maintenance |

## Error Codes

Cortex Core defines a set of standardized error codes:

### Authentication Errors

- `AUTH_REQUIRED`: Authentication is required
- `INVALID_CREDENTIALS`: Invalid username or password
- `EXPIRED_TOKEN`: Authentication token has expired
- `INVALID_TOKEN`: Authentication token is malformed or invalid
- `INSUFFICIENT_SCOPE`: Token does not have required scopes

### Authorization Errors

- `PERMISSION_DENIED`: User lacks permission for the operation
- `RESOURCE_FORBIDDEN`: User cannot access the resource
- `OWNERSHIP_REQUIRED`: Operation requires resource ownership

### Resource Errors

- `RESOURCE_NOT_FOUND`: Requested resource does not exist
- `RESOURCE_ALREADY_EXISTS`: Resource already exists (during creation)
- `RESOURCE_MODIFIED`: Resource was modified since retrieval
- `INVALID_RESOURCE_STATE`: Resource in invalid state for operation

### Validation Errors

- `INVALID_PARAMETER`: Parameter value is invalid
- `MISSING_PARAMETER`: Required parameter is missing
- `INVALID_FORMAT`: Parameter format is incorrect
- `VALIDATION_FAILED`: Request failed validation (general)

### Service Errors

- `SERVICE_UNAVAILABLE`: Underlying service is unavailable
- `INTEGRATION_ERROR`: Error in external integration
- `RATE_LIMIT_EXCEEDED`: Too many requests in time period
- `QUOTA_EXCEEDED`: Usage quota has been exceeded
- `INTERNAL_ERROR`: Unexpected internal error

## Exception Hierarchy

Cortex Core implements a structured exception hierarchy:

```
BaseException
└── Exception
    └── CortexException (base for all application exceptions)
        ├── AuthenticationError
        │   ├── CredentialsError
        │   ├── TokenError
        │   └── SessionError
        ├── AuthorizationError
        │   ├── PermissionError
        │   └── OwnershipError
        ├── ResourceError
        │   ├── ResourceNotFoundError
        │   ├── ResourceConflictError
        │   └── ResourceStateError
        ├── ValidationError
        │   ├── ParameterError
        │   └── FormatError
        ├── ServiceError
        │   ├── IntegrationError
        │   ├── RateLimitError
        │   └── QuotaError
        └── InternalError
```

### Using Custom Exceptions

All API endpoints should use these custom exceptions rather than FastAPI's HTTPException for consistent error handling:

```python
from app.exceptions import ResourceNotFoundError, AuthorizationError

@router.get("/resources/{resource_id}")
async def get_resource(resource_id: str):
    resource = repository.get_by_id(resource_id)
    
    if resource is None:
        # Use custom exception instead of HTTPException
        raise ResourceNotFoundError(
            detail=f"Resource with ID {resource_id} not found",
            resource_type="resource",
            resource_id=resource_id
        )
    
    return resource
```

The application has global exception handlers that convert these exceptions to properly formatted HTTP responses with consistent structure, status codes, and tracing information.

## Exception Handling in FastAPI

Cortex Core uses FastAPI's exception handling mechanisms:

```python
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from app.exceptions import CortexException

app = FastAPI()

@app.exception_handler(CortexException)
async def cortex_exception_handler(request: Request, exc: CortexException):
    """Handle application-specific exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "code": exc.code,
            "params": exc.params,
            "trace_id": request.state.trace_id
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle FastAPI HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "code": "HTTP_ERROR",
            "params": {},
            "trace_id": request.state.trace_id
        }
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    # Log the exception with traceback
    logger.exception(f"Unhandled exception: {str(exc)}")
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected error occurred",
            "code": "INTERNAL_ERROR",
            "params": {},
            "trace_id": request.state.trace_id
        }
    )
```

## Custom Exception Classes

Cortex Core defines custom exception classes:

```python
class CortexException(Exception):
    """Base exception for all application-specific exceptions"""
    
    def __init__(
        self,
        detail: str,
        code: str = "INTERNAL_ERROR",
        params: Optional[Dict[str, Any]] = None,
        status_code: int = 500
    ):
        self.detail = detail
        self.code = code
        self.params = params or {}
        self.status_code = status_code
        super().__init__(self.detail)

class ResourceNotFoundError(CortexException):
    """Exception raised when a resource is not found"""
    
    def __init__(
        self,
        detail: str = "Resource not found",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None
    ):
        params = {}
        if resource_type:
            params["resource_type"] = resource_type
        if resource_id:
            params["resource_id"] = resource_id
            
        super().__init__(
            detail=detail,
            code="RESOURCE_NOT_FOUND",
            params=params,
            status_code=404
        )
```

## Raising Exceptions

Example of raising exceptions in application code:

```python
async def get_workspace(workspace_id: str, current_user: User) -> Workspace:
    """Get a workspace by ID"""
    workspace = await db.workspaces.get(workspace_id)
    
    if not workspace:
        raise ResourceNotFoundError(
            detail=f"Workspace with ID {workspace_id} not found",
            resource_type="workspace",
            resource_id=workspace_id
        )
    
    if workspace.user_id != current_user.id:
        # Check if workspace is shared with user
        shared = await db.workspace_sharing.exists(
            workspace_id=workspace_id,
            user_id=current_user.id
        )
        
        if not shared:
            raise AuthorizationError(
                detail="You do not have access to this workspace",
                code="RESOURCE_FORBIDDEN",
                params={"workspace_id": workspace_id},
                status_code=403
            )
    
    return workspace
```

## Error Handling in API Routes

Example of error handling in FastAPI route handlers:

```python
@router.get("/workspaces/{workspace_id}")
async def get_workspace_endpoint(
    workspace_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get workspace by ID"""
    try:
        # Attempt to get workspace
        workspace = await get_workspace(workspace_id, current_user)
        
        # Return workspace data
        return {
            "id": workspace.id,
            "name": workspace.name,
            "created_at": workspace.created_at,
            "last_active_at": workspace.last_active_at,
            "meta_data": workspace.meta_data
        }
    
    except ResourceNotFoundError as e:
        # Already structured appropriately, will be caught by global handler
        raise
    
    except AuthorizationError as e:
        # Already structured appropriately, will be caught by global handler
        raise
    
    except Exception as e:
        # Log unexpected error and translate to internal error
        logger.exception(f"Unexpected error getting workspace {workspace_id}: {str(e)}")
        raise InternalError(
            detail="An error occurred while retrieving the workspace",
            params={"workspace_id": workspace_id}
        )
```

## Validation Errors

Cortex Core uses Pydantic for request validation, with custom error handling:

```python
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors from Pydantic models"""
    errors = exc.errors()
    error_details = []
    
    for error in errors:
        error_details.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Request validation failed",
            "code": "VALIDATION_FAILED",
            "params": {"errors": error_details},
            "trace_id": request.state.trace_id
        }
    )
```

## Database Errors

Example of handling database errors:

```python
async def create_workspace(user_id: str, name: str) -> Workspace:
    """Create a new workspace"""
    try:
        workspace = Workspace(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=name,
            created_at=datetime.utcnow(),
            last_active_at=datetime.utcnow()
        )
        
        await db.workspaces.create(workspace)
        return workspace
    
    except IntegrityError as e:
        # Handle database integrity errors
        if "unique constraint" in str(e).lower():
            raise ResourceConflictError(
                detail=f"Workspace with name '{name}' already exists",
                params={"name": name}
            )
        
        # Handle other database errors
        logger.error(f"Database error creating workspace: {str(e)}")
        raise InternalError(
            detail="An error occurred while creating the workspace",
            params={"user_id": user_id}
        )
```

## Async Error Handling

Example of error handling in async code:

```python
async def process_conversation_messages(conversation_id: str) -> None:
    """Process messages for a conversation"""
    try:
        # Get messages
        messages = await db.messages.list(conversation_id=conversation_id)
        
        # Process batch with error handling for individual messages
        for message in messages:
            try:
                await process_message(message)
            except Exception as e:
                logger.error(f"Error processing message {message.id}: {str(e)}")
                # Continue processing other messages
    
    except Exception as e:
        logger.exception(f"Failed to process conversation {conversation_id}: {str(e)}")
        # Re-raise as service error
        raise ServiceError(
            detail="Failed to process conversation messages",
            params={"conversation_id": conversation_id}
        )
```

## Client-Side Error Handling

Guidelines for client applications consuming the Cortex Core API:

```typescript
// Example TypeScript code for client-side error handling

interface ErrorResponse {
  detail: string;
  code: string;
  params: Record<string, any>;
  trace_id: string;
}

async function fetchWorkspace(workspaceId: string): Promise<Workspace> {
  try {
    const response = await fetch(`/api/workspaces/${workspaceId}`, {
      headers: {
        'Authorization': `Bearer ${getToken()}`
      }
    });
    
    if (!response.ok) {
      const errorData: ErrorResponse = await response.json();
      
      switch (errorData.code) {
        case 'RESOURCE_NOT_FOUND':
          throw new ResourceNotFoundError(errorData.detail);
        
        case 'RESOURCE_FORBIDDEN':
          throw new AccessDeniedError(errorData.detail);
        
        case 'EXPIRED_TOKEN':
          // Handle token refresh
          await refreshToken();
          return fetchWorkspace(workspaceId);
        
        default:
          throw new ApiError(errorData.detail, errorData.code, errorData.trace_id);
      }
    }
    
    return await response.json();
  } catch (error) {
    // Handle network or parsing errors
    if (error instanceof ApiError) {
      // Already handled API errors
      throw error;
    }
    
    throw new ConnectionError('Failed to connect to the server');
  }
}
```

## Logging and Tracing

Cortex Core implements comprehensive error logging and tracing:

```python
@app.middleware("http")
async def request_middleware(request: Request, call_next):
    """Add tracing and logging to requests"""
    # Generate trace ID for request
    trace_id = str(uuid.uuid4())
    request.state.trace_id = trace_id
    
    # Set up logging context
    with logging_context(trace_id=trace_id, path=request.url.path):
        try:
            # Process request
            response = await call_next(request)
            return response
        
        except Exception as exc:
            # Unhandled exception - will be caught by global handler
            logger.exception(f"Unhandled exception in request: {str(exc)}")
            raise
```

## Best Practices

1. **Be Specific**: Use the most specific exception type for the error
2. **Provide Context**: Include relevant information in the exception
3. **Catch Only What You Can Handle**: Only catch exceptions you know how to handle
4. **Preserve Stack Traces**: When re-raising exceptions, preserve the original stack trace
5. **Log Before Raising**: Log errors before raising them to the client
6. **Consistent Status Codes**: Use appropriate HTTP status codes consistently
7. **Graceful Degradation**: Design services to continue functioning when dependencies fail
8. **Idempotent Operations**: Design operations to be safely retryable
9. **Circuit Breakers**: Implement circuit breakers for external dependencies
10. **Error Metrics**: Track error rates and patterns

## Error Recovery Strategies

### Retry Logic

```python
async def retry_with_backoff(func, *args, max_retries=3, base_delay=1, **kwargs):
    """Retry a function with exponential backoff"""
    retries = 0
    while True:
        try:
            return await func(*args, **kwargs)
        except (ConnectionError, TimeoutError) as e:
            retries += 1
            if retries > max_retries:
                logger.error(f"Max retries ({max_retries}) reached for {func.__name__}")
                raise
            
            # Calculate backoff delay
            delay = base_delay * (2 ** (retries - 1))
            logger.warning(f"Retry {retries}/{max_retries} for {func.__name__} after {delay}s: {str(e)}")
            await asyncio.sleep(delay)
```

### Circuit Breaker

```python
class CircuitBreaker:
    """Simple circuit breaker implementation"""
    
    def __init__(self, name, failure_threshold=5, recovery_timeout=30):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def execute(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        # Check if circuit is open
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                # Try to recover
                logger.info(f"Circuit {self.name} transitioning to HALF_OPEN")
                self.state = "HALF_OPEN"
            else:
                raise ServiceError(
                    detail=f"Service {self.name} is unavailable",
                    code="SERVICE_UNAVAILABLE",
                    status_code=503
                )
        
        try:
            result = await func(*args, **kwargs)
            
            # Success, reset if in half-open state
            if self.state == "HALF_OPEN":
                logger.info(f"Circuit {self.name} recovered, transitioning to CLOSED")
                self.failure_count = 0
                self.state = "CLOSED"
            
            return result
        
        except Exception as e:
            # Track failure
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.state == "CLOSED" and self.failure_count >= self.failure_threshold:
                logger.warning(f"Circuit {self.name} tripped open after {self.failure_count} failures")
                self.state = "OPEN"
            
            raise
```

## Related Documentation

- [API Reference](API_REFERENCE.md): Complete API documentation
- [Development Guide](DEVELOPMENT.md): Development guidelines
- [Operational Handbook](OPERATIONS.md): Operations and troubleshooting

