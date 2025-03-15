"""
Integration Hub for connecting with Domain Expert services via MCP.

This component manages connections to Domain Expert services using the Model Context Protocol (MCP),
providing a standardized interface for discovering and executing tools from these services.
"""

import asyncio
from typing import Dict, Any, List, Optional, Set, Tuple
from app.config import settings
from app.utils.logger import logger
from app.utils.circuit_breaker import CircuitBreaker
from app.exceptions import ServiceError


logger = logger.getChild("integration_hub")

from app.components.mcp.cortex_mcp_client import CortexMcpClient, ConnectionState


class DomainExpertConnectionStatus:
    """Status information for a domain expert connection"""
    
    def __init__(self, name: str, endpoint: str, expert_type: str):
        self.name = name
        self.endpoint = endpoint
        self.type = expert_type
        self.available = False
        self.state = ConnectionState.DISCONNECTED
        self.last_error: Optional[str] = None
        self.capabilities: Set[str] = set()
        
    def update_from_client(self, client: CortexMcpClient) -> None:
        """Update status information from client state"""
        self.state = client.state
        self.available = client.is_connected
        
        if client.last_error:
            self.last_error = str(client.last_error)
        else:
            self.last_error = None
            
        # Update capabilities from server info
        if client.server_info:
            server_info = client.server_info
            # Extract capabilities from server info
            if "serverInfo" in server_info and "capabilities" in server_info["serverInfo"]:
                capabilities = server_info["serverInfo"]["capabilities"]
                self.capabilities = set(capabilities.keys())
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "name": self.name,
            "endpoint": self.endpoint,
            "type": self.type,
            "available": self.available,
            "state": self.state,
            "last_error": self.last_error,
            "capabilities": list(self.capabilities)
        }


class IntegrationHub:
    """
    Manages connections to Domain Expert services via MCP.
    
    This component acts as the central hub for all MCP-based communication 
    with Domain Expert services in the Cortex platform. It manages the lifecycle
    of MCP client connections, handles connection failures gracefully, and provides
    a unified interface for interacting with various domain experts.
    
    Key responsibilities:
    - Establishing and maintaining connections to MCP endpoints
    - Providing circuit breaker protection for service calls
    - Exposing domain expert tools and resources through a unified API
    - Monitoring connection health and status
    """

    def __init__(self) -> None:
        self.settings = settings
        self.clients: Dict[str, CortexMcpClient] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.expert_status: Dict[str, DomainExpertConnectionStatus] = {}
        self._startup_complete = False

    async def startup(self) -> None:
        """Initialize connections to all configured MCP endpoints in the background"""
        # Create client instances, circuit breakers, and status tracking first
        for endpoint in self.settings.mcp.endpoints:
            name = endpoint["name"]
            endpoint_url = endpoint["endpoint"]
            expert_type = endpoint.get("type", "unknown")
            
            # Log endpoint configuration
            logger.info(f"Configuring MCP endpoint: {name} at {endpoint_url} (type: {expert_type})")
            
            # Create client
            client = CortexMcpClient(
                endpoint=endpoint_url,
                service_name=name
            )
            self.clients[name] = client
            
            # Create circuit breaker
            self.circuit_breakers[name] = CircuitBreaker(
                name=f"mcp-{name}",
                failure_threshold=3,
                recovery_timeout=60.0
            )
            
            # Create status tracker
            self.expert_status[name] = DomainExpertConnectionStatus(
                name=name,
                endpoint=endpoint_url,
                expert_type=expert_type
            )
            
        # Mark as startup complete before starting connections
        # This ensures the application can continue while connections are established
        self._startup_complete = True
        
        logger.info(f"Integration Hub setup complete. Starting connections to {len(self.clients)} endpoints.")
        
        # Start connection tasks in the background
        # This way they won't block the application startup
        for name, client in self.clients.items():
            # Start each connection in a separate background task
            asyncio.create_task(
                self._connect_endpoint_with_status_update(name, client),
                name=f"connect-{name}"
            )
        
        # Return immediately, letting connections proceed in the background
        # This resolves the blocking issue during application startup
                    
    async def _connect_endpoint_with_status_update(self, name: str, client: CortexMcpClient) -> None:
        """Connect to endpoint and update status regardless of outcome"""
        try:
            await self._connect_endpoint(name, client)
            logger.info(f"Successfully connected to MCP endpoint: {name}")
            
            # Update status after successful connection
            if name in self.expert_status:
                self.expert_status[name].update_from_client(client)
                
            # Log successful connection
            connected_count = sum(1 for status in self.expert_status.values() if status.available)
            total_count = len(self.expert_status)
            logger.info(f"Domain Expert connection status: {connected_count}/{total_count} connected")
            
        except Exception as e:
            # Connection errors are already logged in _connect_endpoint
            # Just update the status here
            if name in self.expert_status:
                self.expert_status[name].available = False
                self.expert_status[name].last_error = str(e)
                
            # Log connection failure
            logger.error(f"Failed to connect to Domain Expert {name}: {str(e)}")
            
            # Don't re-raise, as we want the task to complete without errors
        
    async def _connect_endpoint(self, name: str, client: CortexMcpClient) -> None:
        """Connect to a single endpoint with error handling"""
        try:
            await client.connect()
            # Update status after successful connection
            if name in self.expert_status:
                self.expert_status[name].update_from_client(client)
        except Exception as e:
            logger.error(f"Failed to connect to MCP endpoint {name}: {str(e)}")
            # Exception will be propagated up to the caller
            raise

    def _update_expert_status(self) -> None:
        """Update status information for all experts"""
        for name, client in self.clients.items():
            if name in self.expert_status:
                self.expert_status[name].update_from_client(client)

    async def shutdown(self) -> None:
        """Close all MCP connections"""
        close_tasks = []
        
        for name, client in self.clients.items():
            close_tasks.append(self._close_endpoint(name, client))
            
        # Close all connections in parallel
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
            
        logger.info("Integration Hub shutdown complete.")
        
    async def _close_endpoint(self, name: str, client: CortexMcpClient) -> None:
        """Close a single endpoint connection with error handling"""
        try:
            await client.close()
            logger.info(f"Closed connection to MCP endpoint: {name}")
            # Update status after closing
            if name in self.expert_status:
                self.expert_status[name].state = ConnectionState.DISCONNECTED
                self.expert_status[name].available = False
        except Exception as e:
            logger.error(f"Error closing MCP connection to {name}: {str(e)}")

    async def list_experts(self) -> List[str]:
        """List all available domain experts"""
        return list(self.clients.keys())
        
    async def get_expert_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status information for all domain experts"""
        # Update status information first
        self._update_expert_status()
        
        # Convert to dictionary format
        return {
            name: status.to_dict() 
            for name, status in self.expert_status.items()
        }

    async def list_expert_tools(self, expert_name: str) -> Dict[str, Any]:
        """List all tools available from a specific domain expert"""
        if expert_name not in self.clients:
            logger.error(f"Unknown domain expert requested: {expert_name}")
            raise ValueError(f"Unknown domain expert: {expert_name}")

        client = self.clients[expert_name]
        circuit_breaker = self.circuit_breakers[expert_name]
        
        logger.info(f"Listing tools for domain expert: {expert_name}")
        logger.info(f"Current client state: {client.state}, connected: {client.is_connected}")
        
        try:
            # Include detailed logging around the tool listing process
            logger.info(f"Executing list_tools via circuit breaker for {expert_name}")
            tools_result = await circuit_breaker.execute(client.list_tools)
            
            # Log the result to see what tools we got
            if isinstance(tools_result, dict) and "tools" in tools_result:
                tools_count = len(tools_result["tools"])
                
                # Check if tools is a dictionary or a list
                if isinstance(tools_result["tools"], dict):
                    logger.info(f"Successfully listed {tools_count} tools from {expert_name}: {list(tools_result['tools'].keys())}")
                elif isinstance(tools_result["tools"], list):
                    # Handle the case when tools is a list of dictionaries
                    tool_names = [tool.get("name", "unnamed") for tool in tools_result["tools"] if isinstance(tool, dict)]
                    logger.info(f"Successfully listed {tools_count} tools from {expert_name}: {tool_names}")
                else:
                    logger.warning(f"Unexpected tools format from {expert_name}: {type(tools_result['tools'])}")
            else:
                logger.warning(f"Unexpected tools result format from {expert_name}: {type(tools_result)}")
                
            return tools_result
        except Exception as e:
            # Update status on error
            if expert_name in self.expert_status:
                self.expert_status[expert_name].update_from_client(client)
            
            # Log the error with more context
            logger.error(f"Failed to list tools from {expert_name}: {str(e)}")
            # Re-raise the exception
            raise

    async def invoke_expert_tool(
        self, expert_name: str, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Invoke a tool on a specific domain expert"""
        if expert_name not in self.clients:
            raise ValueError(f"Unknown domain expert: {expert_name}")

        client = self.clients[expert_name]
        circuit_breaker = self.circuit_breakers[expert_name]

        try:
            return await circuit_breaker.execute(
                client.call_tool, name=tool_name, arguments=arguments
            )
        except Exception as e:
            # Update status on error
            if expert_name in self.expert_status:
                self.expert_status[expert_name].update_from_client(client)
                
            # If this is a circuit breaker error, convert it to a service error
            if isinstance(e, ServiceError):
                raise
                
            # Otherwise, wrap in a service error
            raise ServiceError(
                detail=f"Error invoking tool {tool_name} on {expert_name}: {str(e)}",
                code="DOMAIN_EXPERT_ERROR",
                status_code=503
            ) from e

    async def read_expert_resource(self, expert_name: str, uri: str) -> Dict[str, Any]:
        """Read a resource from a specific domain expert"""
        if expert_name not in self.clients:
            raise ValueError(f"Unknown domain expert: {expert_name}")

        client = self.clients[expert_name]
        circuit_breaker = self.circuit_breakers[expert_name]

        try:
            return await circuit_breaker.execute(client.read_resource, uri=uri)
        except Exception as e:
            # Update status on error
            if expert_name in self.expert_status:
                self.expert_status[expert_name].update_from_client(client)
                
            # If this is a circuit breaker error, convert it to a service error
            if isinstance(e, ServiceError):
                raise
                
            # Otherwise, wrap in a service error
            raise ServiceError(
                detail=f"Error reading resource {uri} from {expert_name}: {str(e)}",
                code="DOMAIN_EXPERT_ERROR",
                status_code=503
            ) from e


# Singleton instance
_integration_hub: Optional[IntegrationHub] = None


def get_integration_hub() -> IntegrationHub:
    """Get the singleton IntegrationHub instance"""
    global _integration_hub
    if _integration_hub is None:
        _integration_hub = IntegrationHub()
    return _integration_hub