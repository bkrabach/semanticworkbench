# Error Handling in Cortex Core

This document outlines the error handling approach used in Cortex Core, including exception hierarchy, error responses, and best practices for implementing error handling in new code.

## Error Response Format

All API errors follow a standardized format:

```json
{
  "error": {
    "code": "error_code",
    "message": "Human-readable error message",
    "status_code": 400,
    "details": {
      // Additional error-specific details
    }
  },
  "request_id": "unique-request-identifier"
}
```

Where:
- `code`: Machine-readable error code string
- `message`: Human-readable error description
- `status_code`: HTTP status code
- `details`: Optional object with additional error context
- `request_id`: Unique identifier for the request (useful for tracing/debugging)

## Exception Hierarchy

All custom exceptions inherit from `CortexException` which provides the basic structure for error responses.

```
CortexException
├── AuthException
│   ├── InvalidCredentialsException
│   ├── TokenExpiredException
│   └── PermissionDeniedException
├── EntityException
│   ├── EntityNotFoundError
│   ├── DuplicateEntityError
│   └── AccessDeniedError
├── ValidationException
│   └── InputValidationException
├── ConfigurationException
│   └── MissingConfigurationException
├── ServiceException
│   ├── ServiceUnavailableException
│   └── EventBusException
└── DatabaseException
    ├── ConnectionError
    ├── QueryError
    ├── TransactionError
    └── MigrationError
```

## Using Exceptions

When implementing API endpoints, use specific exceptions rather than generic HTTP exceptions:

```python
# Bad
raise HTTPException(status_code=404, detail="Workspace not found")

# Good
raise ResourceNotFoundException(
    message="Workspace not found",
    resource_type="workspace",
    resource_id=workspace_id
)
```

### Example: Authentication Error

```python
if not user or user["password"] != form_data.password:
    raise InvalidCredentialsException(
        message="Invalid email or password",
        details={"headers": {"WWW-Authenticate": "Bearer"}}
    )
```

### Example: Entity Not Found

```python
async with UnitOfWork.for_transaction() as uow:
    workspace_repo = uow.repositories.get_workspace_repository()
    workspace = await workspace_repo.get_by_id(workspace_id)
    
    if not workspace:
        raise EntityNotFoundError(
            message=f"Workspace not found: {workspace_id}",
            entity_type="Workspace",
            entity_id=workspace_id
        )
```

### Example: Permission Denied

```python
if workspace.owner_id != user_id:
    raise AccessDeniedError(
        message="You do not have access to this workspace",
        entity_type="Workspace",
        entity_id=workspace_id,
        user_id=user_id
    )
```

## Error Codes

The following error codes are defined:

| Error Code | Status Code | Description |
|------------|-------------|-------------|
| `internal_error` | 500 | Generic server error |
| `auth_error` | 401 | Generic authentication error |
| `invalid_credentials` | 401 | Invalid username/password |
| `token_expired` | 401 | JWT token has expired |
| `permission_denied` | 403 | User lacks permission |
| `entity_error` | 400 | Generic entity error |
| `entity_not_found` | 404 | Entity does not exist |
| `duplicate_entity` | 409 | Entity already exists |
| `access_denied` | 403 | Access to entity denied |
| `validation_error` | 422 | Input validation failed |
| `input_validation_error` | 422 | Specific input validation error |
| `config_error` | 500 | Configuration error |
| `missing_config` | 500 | Required configuration missing |
| `service_error` | 500 | Service-related error |
| `service_unavailable` | 503 | Service is unavailable |
| `event_bus_error` | 500 | Event bus error |
| `database_error` | 500 | Database-related error |
| `database_connection_error` | 500 | Database connection issue |
| `database_query_error` | 500 | Database query failed |
| `database_transaction_error` | 500 | Database transaction failed |
| `database_migration_error` | 500 | Database migration issue |

## Logging

All exceptions include automatic logging. The `log()` method is built into CortexException and can be used for customized logging:

```python
# Default ERROR level logging
exception.log()

# Custom log level
exception.log(level=logging.WARNING)

# Exceptions are also logged when raised in request handlers
@app.exception_handler(CortexException)
async def cortex_exception_handler(request: Request, exc: CortexException):
    request_id = str(uuid.uuid4())
    logger.error(
        f"Request {request_id} failed: {exc.message}",
        extra={
            "request_id": request_id,
            "error_code": exc.code,
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
            "details": exc.details
        }
    )
    
    # Log the exception with its built-in method
    exc.log()
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            },
            "request_id": request_id
        }
    )
```

## Best Practices

1. **Use Specific Exceptions**: Choose the most specific exception type for the error condition
2. **Include Context**: Provide context in the exception details to aid debugging
3. **Consistent Messages**: Use consistent, clear error messages
4. **Handle All Errors**: Ensure all error paths are handled appropriately
5. **Secure Error Messages**: Don't expose sensitive information in error messages
6. **Log Appropriately**: Ensure errors are logged with the right level and context

## Client Integration

Clients should:

1. Check for error responses and handle them appropriately
2. Display user-friendly error messages based on the `message` field
3. Use the `code` field for conditional handling of different error types
4. Store the `request_id` for reporting issues