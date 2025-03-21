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
├── ResourceException
│   ├── ResourceNotFoundException
│   └── ResourceAlreadyExistsException
├── ValidationException
│   └── InputValidationException
├── ConfigurationException
│   └── MissingConfigurationException
└── ServiceException
    ├── ServiceUnavailableException
    └── EventBusException
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

### Example: Resource Not Found

```python
workspace = storage.get_workspace(workspace_id)
if not workspace:
    raise ResourceNotFoundException(
        message="Workspace not found",
        resource_type="workspace",
        resource_id=workspace_id
    )
```

### Example: Permission Denied

```python
if workspace["owner_id"] != user_id:
    raise PermissionDeniedException(
        message="You do not have access to this workspace",
        details={
            "resource_type": "workspace",
            "resource_id": workspace_id,
            "user_id": user_id
        }
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
| `resource_error` | 400 | Generic resource error |
| `resource_not_found` | 404 | Resource does not exist |
| `resource_already_exists` | 409 | Resource already exists |
| `validation_error` | 422 | Input validation failed |
| `input_validation_error` | 422 | Specific input validation error |
| `config_error` | 500 | Configuration error |
| `missing_config` | 500 | Required configuration missing |
| `service_error` | 500 | Service-related error |
| `service_unavailable` | 503 | Service is unavailable |
| `event_bus_error` | 500 | Event bus error |

## Logging

All exceptions include automatic logging. The `log()` method can be used for customized logging:

```python
# Default ERROR level logging
exception.log()

# Custom log level
exception.log(level=logging.WARNING)
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