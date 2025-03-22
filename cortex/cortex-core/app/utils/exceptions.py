from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status


class CortexException(HTTPException):
    """Base exception class for Cortex Core."""

    def __init__(self, status_code: int, error_code: str, message: str, details: Optional[Dict[str, Any]] = None):
        self.error_code = error_code
        self.error_message = message
        self.error_details = details or {}
        super().__init__(
            status_code=status_code,
            detail={"error": {"code": error_code, "message": message, "details": self.error_details}},
        )


class ResourceNotFoundException(CortexException):
    """Exception raised when a requested resource is not found."""

    def __init__(self, resource_id: str, resource_type: str = "resource"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="resource_not_found",
            message=f"{resource_type.capitalize()} not found",
            details={"resource_id": resource_id, "resource_type": resource_type},
        )


class ValidationErrorException(CortexException):
    """Exception raised when input validation fails."""

    def __init__(self, validation_errors: List[str]):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="validation_error",
            message="Validation error",
            details={"validation_errors": validation_errors},
        )


class AuthenticationException(CortexException):
    """Exception raised when authentication fails."""

    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, error_code="invalid_credentials", message=message)


class PermissionDeniedException(CortexException):
    """Exception raised when user doesn't have permission for an operation."""

    def __init__(self, resource_id: Optional[str] = None, message: str = "Permission denied"):
        details = {}
        if resource_id:
            details["resource_id"] = resource_id

        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN, error_code="permission_denied", message=message, details=details
        )
