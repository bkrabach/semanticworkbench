from typing import Any, Dict, Optional


class MCPError(Exception):
    """Base exception for all MCP-related errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class ServiceNotFoundError(MCPError):
    """Raised when attempting to get a client for a non-existent service."""
    
    def __init__(self, service_name: str):
        message = f"Service '{service_name}' not found"
        super().__init__(message, {"service_name": service_name})


class ToolNotFoundError(MCPError):
    """Raised when attempting to call a non-existent tool."""
    
    def __init__(self, service_name: str, tool_name: str):
        message = f"Tool '{tool_name}' not found in service '{service_name}'"
        super().__init__(message, {
            "service_name": service_name,
            "tool_name": tool_name
        })


class ResourceNotFoundError(MCPError):
    """Raised when attempting to access a non-existent resource."""
    
    def __init__(self, service_name: str, resource_name: str):
        message = f"Resource '{resource_name}' not found in service '{service_name}'"
        super().__init__(message, {
            "service_name": service_name,
            "resource_name": resource_name
        })


class ToolExecutionError(MCPError):
    """Raised when a tool execution fails."""
    
    def __init__(
        self, 
        service_name: str, 
        tool_name: str, 
        original_error: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        message = f"Error executing tool '{tool_name}' in service '{service_name}'"
        if original_error:
            message += f": {str(original_error)}"
        
        error_details = {
            "service_name": service_name,
            "tool_name": tool_name,
        }
        if details:
            error_details.update(details)
        
        super().__init__(message, error_details)
        self.original_error = original_error


class ResourceAccessError(MCPError):
    """Raised when resource access fails."""
    
    def __init__(
        self, 
        service_name: str, 
        resource_name: str, 
        original_error: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        message = f"Error accessing resource '{resource_name}' in service '{service_name}'"
        if original_error:
            message += f": {str(original_error)}"
        
        error_details = {
            "service_name": service_name,
            "resource_name": resource_name,
        }
        if details:
            error_details.update(details)
        
        super().__init__(message, error_details)
        self.original_error = original_error


class ValidationError(MCPError):
    """Raised when input or output validation fails."""
    
    def __init__(
        self, 
        message: str, 
        field_errors: Optional[Dict[str, str]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if field_errors:
            error_details["field_errors"] = field_errors
        
        super().__init__(message, error_details)
        self.field_errors = field_errors


class ServiceInitializationError(MCPError):
    """Raised when a service fails to initialize."""
    
    def __init__(
        self, 
        service_name: str, 
        original_error: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        message = f"Failed to initialize service '{service_name}'"
        if original_error:
            message += f": {str(original_error)}"
        
        error_details = {"service_name": service_name}
        if details:
            error_details.update(details)
        
        super().__init__(message, error_details)
        self.original_error = original_error


class TransportError(MCPError):
    """Raised when there's an error in the transport layer."""
    
    def __init__(
        self, 
        message: str, 
        original_error: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if original_error:
            message += f": {str(original_error)}"
        
        super().__init__(message, details)
        self.original_error = original_error