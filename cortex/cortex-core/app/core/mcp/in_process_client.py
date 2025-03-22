from typing import Any, Dict, List, Optional

from app.core.mcp.client import MCPClient, ResourceDataType
from app.core.mcp.exceptions import (
    ResourceAccessError,
    ResourceNotFoundError,
    ServiceNotFoundError,
    ToolExecutionError,
    ToolNotFoundError,
)
from app.core.mcp.registry import registry


class InProcessMCPClient(MCPClient):
    """In-process implementation of the MCP client.

    Uses direct method calls rather than network transport.
    """

    async def call_tool(
        self, service_name: str, tool_name: str, input_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Call a tool on the specified service.

        Args:
            service_name: Name of the service
            tool_name: Name of the tool to call
            input_data: Input data for the tool

        Returns:
            Tool execution result

        Raises:
            ServiceNotFoundError: If the service doesn't exist
            ToolNotFoundError: If the tool doesn't exist
            ValidationError: If input validation fails
            ToolExecutionError: If the tool execution fails
        """
        # Ensure service exists
        service_def = registry.get_service(service_name)

        # Ensure tool exists
        tool_def = registry.get_tool(service_name, tool_name)

        # Prepare input data
        data = input_data or {}

        try:
            # Call the tool function directly
            result = await tool_def.func(service_def.service_instance, **data)

            # Ensure result is a dictionary
            if result is None:
                return {}
            elif isinstance(result, dict):
                return result
            else:
                return {"result": result}

        except Exception as e:
            # Re-raise our own exceptions
            if isinstance(e, (ServiceNotFoundError, ToolNotFoundError, ResourceNotFoundError)):
                raise

            # Wrap other exceptions
            raise ToolExecutionError(service_name=service_name, tool_name=tool_name, original_error=e)

    async def get_resource(
        self, service_name: str, resource_name: str, params: Optional[Dict[str, Any]] = None, 
        resource_id: Optional[str] = None, service: Optional[str] = None
    ) -> ResourceDataType:
        """Get a resource from the specified service.

        Args:
            service_name: Name of the service
            resource_name: Name of the resource to access
            params: Optional parameters for resource access
            resource_id: Optional resource ID
            service: Optional service name (synonym for service_name for API compatibility)

        Returns:
            Resource data

        Raises:
            ServiceNotFoundError: If the service doesn't exist
            ResourceNotFoundError: If the resource doesn't exist
            ValidationError: If parameters validation fails
            ResourceAccessError: If resource access fails
        """
        # If both service_name and service are provided, service takes precedence
        effective_service_name = service or service_name
        
        # Ensure service exists
        service_def = registry.get_service(effective_service_name)

        # Ensure resource exists
        resource_def = registry.get_resource(effective_service_name, resource_name)

        # Prepare parameters
        p = params or {}

        try:
            # Call the resource function directly
            result = await resource_def.func(service_def.service_instance, **p)

            # Ensure result is a dictionary or list of dictionaries
            if result is None:
                return {}
            elif isinstance(result, (dict, list)):
                return result
            else:
                return {"result": result}

        except Exception as e:
            # Re-raise our own exceptions
            if isinstance(e, (ServiceNotFoundError, ResourceNotFoundError)):
                raise

            # Wrap other exceptions
            raise ResourceAccessError(service_name=effective_service_name, resource_name=resource_name, original_error=e)

    def get_tool_schema(self, service_name: str, tool_name: str) -> Dict[str, Any]:
        """Get the JSON schema for a tool's input parameters.

        Args:
            service_name: Name of the service
            tool_name: Name of the tool

        Returns:
            JSON schema for the tool

        Raises:
            ServiceNotFoundError: If the service doesn't exist
            ToolNotFoundError: If the tool doesn't exist
        """
        tool_def = registry.get_tool(service_name, tool_name)
        return tool_def.schema

    def get_resource_schema(self, service_name: str, resource_name: str) -> Dict[str, Any]:
        """Get the JSON schema for a resource's parameters.

        Args:
            service_name: Name of the service
            resource_name: Name of the resource

        Returns:
            JSON schema for the resource parameters

        Raises:
            ServiceNotFoundError: If the service doesn't exist
            ResourceNotFoundError: If the resource doesn't exist
        """
        resource_def = registry.get_resource(service_name, resource_name)
        return resource_def.schema

    def list_services(self) -> List[str]:
        """List all available services.

        Returns:
            List of service names
        """
        return registry.list_services()

    def list_tools(self, service_name: str) -> List[str]:
        """List all tools provided by a service.

        Args:
            service_name: Name of the service

        Returns:
            List of tool names

        Raises:
            ServiceNotFoundError: If the service doesn't exist
        """
        return registry.list_tools(service_name)

    def list_resources(self, service_name: str) -> List[str]:
        """List all resources provided by a service.

        Args:
            service_name: Name of the service

        Returns:
            List of resource names

        Raises:
            ServiceNotFoundError: If the service doesn't exist
        """
        return registry.list_resources(service_name)
