"""
Integration Hub for connecting with Domain Expert services via MCP.

This component manages connections to Domain Expert services using the Model Context Protocol (MCP),
providing a standardized interface for discovering and executing tools from these services.
"""

from typing import Dict, Any, List, Optional
from app.config import settings
from app.utils.logger import logger
from app.utils.circuit_breaker import CircuitBreaker


logger = logger.getChild("integration_hub")

from app.components.mcp.cortex_mcp_client import CortexMcpClient


class IntegrationHub:
    """Manages connections to Domain Expert services via MCP"""

    def __init__(self) -> None:
        self.settings = settings
        self.clients: Dict[str, CortexMcpClient] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}

    async def startup(self) -> None:
        """Initialize connections to all configured MCP endpoints"""
        for endpoint in self.settings.mcp.endpoints:
            try:
                client = CortexMcpClient(
                    endpoint=endpoint["endpoint"],
                    service_name=endpoint["name"]
                )
                await client.connect()
                self.clients[endpoint["name"]] = client

                # Create circuit breaker for this endpoint
                self.circuit_breakers[endpoint["name"]] = CircuitBreaker(
                    name=f"mcp-{endpoint['name']}",
                    failure_threshold=3,
                    recovery_timeout=60.0
                )

                logger.info(f"Registered MCP endpoint: {endpoint['name']}")
            except Exception as e:
                logger.error(f"Failed to register MCP endpoint {endpoint['name']}: {str(e)}")

    async def shutdown(self) -> None:
        """Close all MCP connections"""
        for name, client in self.clients.items():
            try:
                await client.close()
                logger.info(f"Closed connection to MCP endpoint: {name}")
            except Exception as e:
                logger.error(f"Error closing MCP connection to {name}: {str(e)}")

    async def list_experts(self) -> List[str]:
        """List all available domain experts"""
        return list(self.clients.keys())

    async def list_expert_tools(self, expert_name: str) -> Dict[str, Any]:
        """List all tools available from a specific domain expert"""
        if expert_name not in self.clients:
            raise ValueError(f"Unknown domain expert: {expert_name}")

        client = self.clients[expert_name]
        circuit_breaker = self.circuit_breakers[expert_name]

        return await circuit_breaker.execute(client.list_tools)

    async def invoke_expert_tool(
        self, expert_name: str, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Invoke a tool on a specific domain expert"""
        if expert_name not in self.clients:
            raise ValueError(f"Unknown domain expert: {expert_name}")

        client = self.clients[expert_name]
        circuit_breaker = self.circuit_breakers[expert_name]

        return await circuit_breaker.execute(
            client.call_tool, name=tool_name, arguments=arguments
        )

    async def read_expert_resource(self, expert_name: str, uri: str) -> Dict[str, Any]:
        """Read a resource from a specific domain expert"""
        if expert_name not in self.clients:
            raise ValueError(f"Unknown domain expert: {expert_name}")

        client = self.clients[expert_name]
        circuit_breaker = self.circuit_breakers[expert_name]

        return await circuit_breaker.execute(client.read_resource, uri=uri)


# Singleton instance
_integration_hub: Optional[IntegrationHub] = None


def get_integration_hub() -> IntegrationHub:
    """Get the singleton IntegrationHub instance"""
    global _integration_hub
    if _integration_hub is None:
        _integration_hub = IntegrationHub()
    return _integration_hub