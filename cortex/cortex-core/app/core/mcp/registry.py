import asyncio
import inspect
from typing import Any, Callable, Dict, List

from app.core.mcp.exceptions import ResourceNotFoundError, ServiceNotFoundError, ToolNotFoundError


class ToolDefinition:
    """Definition of an MCP tool."""

    def __init__(self, name: str, func: Callable, schema: Dict[str, Any], description: str):
        self.name = name
        self.func = func
        self.schema = schema
        self.description = description


class ResourceDefinition:
    """Definition of an MCP resource."""

    def __init__(self, name: str, func: Callable, schema: Dict[str, Any], description: str):
        self.name = name
        self.func = func
        self.schema = schema
        self.description = description


class ServiceDefinition:
    """Definition of an MCP service."""

    def __init__(self, name: str, service_instance: Any):
        self.name = name
        self.service_instance = service_instance
        self.tools: Dict[str, ToolDefinition] = {}
        self.resources: Dict[str, ResourceDefinition] = {}

        # Auto-register tools and resources based on decorators
        for attr_name, attr_value in inspect.getmembers(service_instance):
            if hasattr(attr_value, "_mcp_tool"):
                tool_def = attr_value._mcp_tool
                self.tools[tool_def.name] = tool_def

            if hasattr(attr_value, "_mcp_resource"):
                resource_def = attr_value._mcp_resource
                self.resources[resource_def.name] = resource_def

    async def shutdown(self) -> None:
        """
        Shutdown the service if the service instance has a shutdown method.
        """
        if hasattr(self.service_instance, "shutdown") and callable(self.service_instance.shutdown):
            self.service_instance.shutdown()


class ServiceRegistry:
    """Registry for MCP services, their tools and resources."""

    def __init__(self) -> None:
        self.services: Dict[str, ServiceDefinition] = {}
        self._lock = asyncio.Lock()

    async def register_service(self, name: str, service_instance: Any) -> None:
        """Register a new service with its tools and resources.

        Args:
            name: Name of the service
            service_instance: Instance of the service class
        """
        async with self._lock:
            self.services[name] = ServiceDefinition(name, service_instance)

    async def unregister_service(self, name: str) -> None:
        """Unregister a service.

        Args:
            name: Name of the service

        Raises:
            ServiceNotFoundError: If the service doesn't exist
        """
        async with self._lock:
            if name not in self.services:
                raise ServiceNotFoundError(name)
            del self.services[name]

    def get_service(self, name: str) -> ServiceDefinition:
        """Get a service by name.

        Args:
            name: Name of the service

        Returns:
            Service definition

        Raises:
            ServiceNotFoundError: If the service doesn't exist
        """
        if name not in self.services:
            raise ServiceNotFoundError(name)
        return self.services[name]

    def get_tool(self, service_name: str, tool_name: str) -> ToolDefinition:
        """Get a tool definition.

        Args:
            service_name: Name of the service
            tool_name: Name of the tool

        Returns:
            Tool definition

        Raises:
            ServiceNotFoundError: If the service doesn't exist
            ToolNotFoundError: If the tool doesn't exist
        """
        service = self.get_service(service_name)
        if tool_name not in service.tools:
            raise ToolNotFoundError(service_name, tool_name)
        return service.tools[tool_name]

    def get_resource(self, service_name: str, resource_name: str) -> ResourceDefinition:
        """Get a resource definition.

        Args:
            service_name: Name of the service
            resource_name: Name of the resource

        Returns:
            Resource definition

        Raises:
            ServiceNotFoundError: If the service doesn't exist
            ResourceNotFoundError: If the resource doesn't exist
        """
        service = self.get_service(service_name)
        if resource_name not in service.resources:
            raise ResourceNotFoundError(service_name, resource_name)
        return service.resources[resource_name]

    def list_services(self) -> List[str]:
        """List all registered services.

        Returns:
            List of service names
        """
        return list(self.services.keys())

    def list_tools(self, service_name: str) -> List[str]:
        """List all tools provided by a service.

        Args:
            service_name: Name of the service

        Returns:
            List of tool names

        Raises:
            ServiceNotFoundError: If the service doesn't exist
        """
        service = self.get_service(service_name)
        return list(service.tools.keys())

    def list_resources(self, service_name: str) -> List[str]:
        """List all resources provided by a service.

        Args:
            service_name: Name of the service

        Returns:
            List of resource names

        Raises:
            ServiceNotFoundError: If the service doesn't exist
        """
        service = self.get_service(service_name)
        return list(service.resources.keys())


# Global registry instance
registry = ServiceRegistry()
