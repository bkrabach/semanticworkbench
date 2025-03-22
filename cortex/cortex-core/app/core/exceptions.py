"""
Exception handling for Cortex Core.

This module defines a custom exception hierarchy for Cortex Core.
All exceptions raised by the application should inherit from CortexException.
"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class CortexException(Exception):
    """Base exception for all Cortex errors."""

    def __init__(
        self,
        message: str,
        code: str = "internal_error",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the exception.

        Args:
            message: Human-readable error message
            code: Machine-readable error code
            status_code: HTTP status code to return
            details: Additional error details
        """
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the exception to a dictionary for API responses.

        Returns:
            Dictionary representation of the exception
        """
        result = {
            "error": {
                "code": self.code,
                "message": self.message,
                "status_code": self.status_code,
            }
        }

        if self.details:
            result["error"]["details"] = self.details

        return result

    def log(self, level: int = logging.ERROR) -> None:
        """
        Log the exception.

        Args:
            level: Logging level (defaults to ERROR)
        """
        logger.log(level, f"{self.__class__.__name__}: {self.message}", extra={
            "error_code": self.code,
            "status_code": self.status_code,
            "details": self.details
        })


# Authentication Exceptions

class AuthException(CortexException):
    """Base class for authentication errors."""

    def __init__(
        self,
        message: str,
        code: str = "auth_error",
        status_code: int = 401,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, code, status_code, details)


class InvalidCredentialsException(AuthException):
    """Exception raised when credentials are invalid."""

    def __init__(
        self,
        message: str = "Invalid authentication credentials",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message,
            code="invalid_credentials",
            status_code=401,
            details=details,
        )


class TokenExpiredException(AuthException):
    """Exception raised when a token has expired."""

    def __init__(
        self,
        message: str = "Authentication token has expired",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message,
            code="token_expired",
            status_code=401,
            details=details,
        )


class PermissionDeniedException(AuthException):
    """Exception raised when a user doesn't have permission."""

    def __init__(
        self,
        message: str = "Permission denied",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message,
            code="permission_denied",
            status_code=403,
            details=details,
        )


# Resource Exceptions

class ResourceException(CortexException):
    """Base class for resource errors."""

    def __init__(
        self,
        message: str,
        code: str = "resource_error",
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, code, status_code, details)


class ResourceNotFoundException(ResourceException):
    """Exception raised when a resource is not found."""

    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ):
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id

        super().__init__(
            message,
            code="resource_not_found",
            status_code=404,
            details=details,
        )


class ResourceAlreadyExistsException(ResourceException):
    """Exception raised when a resource already exists."""

    def __init__(
        self,
        message: str = "Resource already exists",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ):
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id

        super().__init__(
            message,
            code="resource_already_exists",
            status_code=409,
            details=details,
        )


# Validation Exceptions

class ValidationException(CortexException):
    """Base class for validation errors."""

    def __init__(
        self,
        message: str,
        code: str = "validation_error",
        status_code: int = 422,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, code, status_code, details)


class InputValidationException(ValidationException):
    """Exception raised when input validation fails."""

    def __init__(
        self,
        message: str = "Invalid input",
        validation_errors: Optional[Dict[str, Any]] = None,
    ):
        details = {}
        if validation_errors:
            details["validation_errors"] = validation_errors

        super().__init__(
            message,
            code="input_validation_error",
            status_code=422,
            details=details,
        )


# Configuration Exceptions

class ConfigurationException(CortexException):
    """Base class for configuration errors."""

    def __init__(
        self,
        message: str,
        code: str = "config_error",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, code, status_code, details)


class MissingConfigurationException(ConfigurationException):
    """Exception raised when a required configuration is missing."""

    def __init__(
        self,
        message: str = "Missing required configuration",
        config_key: Optional[str] = None,
    ):
        details = {}
        if config_key:
            details["config_key"] = config_key

        super().__init__(
            message,
            code="missing_config",
            status_code=500,
            details=details,
        )


# Service Exceptions

class ServiceException(CortexException):
    """Base class for service errors."""

    def __init__(
        self,
        message: str,
        code: str = "service_error",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, code, status_code, details)


class ServiceUnavailableException(ServiceException):
    """Exception raised when a service is unavailable."""

    def __init__(
        self,
        message: str = "Service unavailable",
        service_name: Optional[str] = None,
    ):
        details = {}
        if service_name:
            details["service_name"] = service_name

        super().__init__(
            message,
            code="service_unavailable",
            status_code=503,
            details=details,
        )


class EventBusException(ServiceException):
    """Exception raised for event bus errors."""

    def __init__(
        self,
        message: str = "Event bus error",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message,
            code="event_bus_error",
            status_code=500,
            details=details,
        )


# Database Exceptions

class DatabaseException(CortexException):
    """Base class for database errors."""

    def __init__(
        self,
        message: str,
        code: str = "database_error",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, code, status_code, details)


class DatabaseError(DatabaseException):
    """Exception raised when a database operation fails."""

    def __init__(
        self,
        message: str = "Database operation failed",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message,
            code="database_error",
            status_code=500,
            details=details,
        )


class EntityNotFoundError(DatabaseException):
    """Exception raised when an entity is not found in the database."""

    def __init__(
        self,
        message: str = "Entity not found",
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
    ):
        details = {}
        if entity_type:
            details["entity_type"] = entity_type
        if entity_id:
            details["entity_id"] = entity_id

        super().__init__(
            message,
            code="entity_not_found",
            status_code=404,
            details=details,
        )


class AccessDeniedError(DatabaseException):
    """Exception raised when access to an entity is denied."""

    def __init__(
        self,
        message: str = "Access denied",
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        details = {}
        if entity_type:
            details["entity_type"] = entity_type
        if entity_id:
            details["entity_id"] = entity_id
        if user_id:
            details["user_id"] = user_id

        super().__init__(
            message,
            code="access_denied",
            status_code=403,
            details=details,
        )


class DuplicateEntityError(DatabaseException):
    """Exception raised when an entity already exists."""

    def __init__(
        self,
        message: str = "Entity already exists",
        entity_type: Optional[str] = None,
        field: Optional[str] = None,
        value: Optional[str] = None,
    ):
        details = {}
        if entity_type:
            details["entity_type"] = entity_type
        if field:
            details["field"] = field
        if value:
            details["value"] = value

        super().__init__(
            message,
            code="duplicate_entity",
            status_code=409,
            details=details,
        )