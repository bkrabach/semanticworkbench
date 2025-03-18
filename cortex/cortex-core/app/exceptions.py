"""Custom exceptions for the Cortex application."""
from typing import Any, Dict, Optional


class CortexException(Exception):
    """Base exception for all Cortex-specific exceptions."""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        detail: Optional[Dict[str, Any]] = None
    ):
        """Initialize the exception with a message, status code, and optional details.
        
        Args:
            message: The error message
            status_code: HTTP status code to return
            detail: Additional error details
        """
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(message)


class AuthenticationError(CortexException):
    """Raised when authentication fails."""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        detail: Optional[Dict[str, Any]] = None
    ):
        """Initialize the exception.
        
        Args:
            message: The error message
            detail: Additional error details
        """
        super().__init__(message, status_code=401, detail=detail)


class AuthorizationError(CortexException):
    """Raised when a user doesn't have permission to access a resource."""
    
    def __init__(
        self,
        message: str = "Not authorized to access this resource",
        detail: Optional[Dict[str, Any]] = None
    ):
        """Initialize the exception.
        
        Args:
            message: The error message
            detail: Additional error details
        """
        super().__init__(message, status_code=403, detail=detail)


class ResourceNotFoundError(CortexException):
    """Raised when a requested resource is not found."""
    
    def __init__(
        self,
        message: str = "Resource not found",
        detail: Optional[Dict[str, Any]] = None
    ):
        """Initialize the exception.
        
        Args:
            message: The error message
            detail: Additional error details
        """
        super().__init__(message, status_code=404, detail=detail)


class ValidationError(CortexException):
    """Raised when input validation fails."""
    
    def __init__(
        self,
        message: str = "Validation error",
        detail: Optional[Dict[str, Any]] = None
    ):
        """Initialize the exception.
        
        Args:
            message: The error message
            detail: Additional error details
        """
        super().__init__(message, status_code=422, detail=detail)


class DuplicateResourceError(CortexException):
    """Raised when attempting to create a resource that already exists."""
    
    def __init__(
        self,
        message: str = "Resource already exists",
        detail: Optional[Dict[str, Any]] = None
    ):
        """Initialize the exception.
        
        Args:
            message: The error message
            detail: Additional error details
        """
        super().__init__(message, status_code=409, detail=detail)


class ServiceUnavailableError(CortexException):
    """Raised when a required service is unavailable."""
    
    def __init__(
        self,
        message: str = "Service unavailable",
        detail: Optional[Dict[str, Any]] = None
    ):
        """Initialize the exception.
        
        Args:
            message: The error message
            detail: Additional error details
        """
        super().__init__(message, status_code=503, detail=detail)