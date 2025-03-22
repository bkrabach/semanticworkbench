from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Union

T = TypeVar("T")
ResourceDataType = Union[Dict[str, Any], List[Dict[str, Any]]]


class MCPClient(ABC):
    """Abstract interface for an MCP client.

    MCP clients provide access to MCP services through tools and resources.
    """

    @abstractmethod
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
        pass

    @abstractmethod
    async def get_resource(
        self, service_name: str, resource_name: str, params: Optional[Dict[str, Any]] = None
    ) -> ResourceDataType:
        """Get a resource from the specified service.

        Args:
            service_name: Name of the service
            resource_name: Name of the resource to access
            params: Optional parameters for resource access

        Returns:
            Resource data

        Raises:
            ServiceNotFoundError: If the service doesn't exist
            ResourceNotFoundError: If the resource doesn't exist
            ValidationError: If parameters validation fails
            ResourceAccessError: If resource access fails
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def list_services(self) -> List[str]:
        """List all available services.

        Returns:
            List of service names
        """
        pass

    @abstractmethod
    def list_tools(self, service_name: str) -> List[str]:
        """List all tools provided by a service.

        Args:
            service_name: Name of the service

        Returns:
            List of tool names

        Raises:
            ServiceNotFoundError: If the service doesn't exist
        """
        pass

    @abstractmethod
    def list_resources(self, service_name: str) -> List[str]:
        """List all resources provided by a service.

        Args:
            service_name: Name of the service

        Returns:
            List of resource names

        Raises:
            ServiceNotFoundError: If the service doesn't exist
        """
        pass
