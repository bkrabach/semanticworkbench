"""
Cortex Core exception hierarchy for standardized error handling
"""

from typing import Dict, Any, Optional


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


class AuthenticationError(CortexException):
    """Exception raised for authentication errors"""

    def __init__(
        self,
        detail: str = "Authentication failed",
        code: str = "AUTH_REQUIRED",
        params: Optional[Dict[str, Any]] = None,
        status_code: int = 401
    ):
        super().__init__(detail, code, params, status_code)


class TokenError(AuthenticationError):
    """Exception raised for token-related errors"""

    def __init__(
        self,
        detail: str = "Invalid token",
        code: str = "INVALID_TOKEN",
        params: Optional[Dict[str, Any]] = None
    ):
        super().__init__(detail, code, params)


class AuthorizationError(CortexException):
    """Exception raised for authorization errors"""

    def __init__(
        self,
        detail: str = "Not authorized",
        code: str = "PERMISSION_DENIED",
        params: Optional[Dict[str, Any]] = None,
        status_code: int = 403
    ):
        super().__init__(detail, code, params, status_code)


class ResourceError(CortexException):
    """Base exception for resource-related errors"""

    def __init__(
        self,
        detail: str = "Resource error",
        code: str = "RESOURCE_ERROR",
        params: Optional[Dict[str, Any]] = None,
        status_code: int = 400
    ):
        super().__init__(detail, code, params, status_code)


class ResourceNotFoundError(ResourceError):
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


class ValidationError(CortexException):
    """Exception raised for validation errors"""

    def __init__(
        self,
        detail: str = "Validation failed",
        code: str = "VALIDATION_FAILED",
        params: Optional[Dict[str, Any]] = None,
        status_code: int = 422
    ):
        super().__init__(detail, code, params, status_code)


class ServiceError(CortexException):
    """Exception raised for service-related errors"""

    def __init__(
        self,
        detail: str = "Service error",
        code: str = "SERVICE_UNAVAILABLE",
        params: Optional[Dict[str, Any]] = None,
        status_code: int = 503
    ):
        super().__init__(detail, code, params, status_code)


class InternalError(CortexException):
    """Exception raised for internal server errors"""

    def __init__(
        self,
        detail: str = "An unexpected error occurred",
        params: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            detail=detail,
            code="INTERNAL_ERROR",
            params=params,
            status_code=500
        )