"""
Network implementation of the MCP client.

This module provides the NetworkMcpClient that enables communication with distributed 
MCP services over the network via HTTP and Server-Sent Events (SSE).
"""

import asyncio
import json
import logging
import time
from enum import Enum
from typing import Any, AsyncIterable, Awaitable, Callable, Coroutine, Dict, List, Optional, Set, TypeVar, Union

T = TypeVar('T')

import httpx

from app.core.mcp.service_discovery import ServiceDiscovery

from app.core.mcp.client import MCPClient, ResourceDataType
from app.core.mcp.exceptions import (
    MCPError,
    ResourceAccessError,
    ResourceNotFoundError,
    ServiceInitializationError,
    ServiceNotFoundError,
    ToolExecutionError,
    ToolNotFoundError,
    TransportError,
    CircuitOpenError,
)

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "CLOSED"        # Normal operation
    OPEN = "OPEN"            # Service is failing, not accepting requests
    HALF_OPEN = "HALF_OPEN"  # Testing if service is back online


class CircuitBreaker:
    """
    Circuit breaker for service call protection.

    Implements the circuit breaker pattern to prevent cascading failures when a
    service is experiencing issues. When too many failures occur, the circuit
    "opens" and prevents further calls for a set recovery period.
    """

    def __init__(self, failure_threshold: int = 5, recovery_time: Union[int, float] = 30):
        """
        Initialize the circuit breaker.

        Args:
            failure_threshold: Number of failures before opening the circuit
            recovery_time: Time in seconds before checking if service is back online
        """
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_time = recovery_time
        self.state = CircuitState.CLOSED
        self.last_failure_time: Optional[float] = None

    def record_success(self) -> None:
        """Record a successful call."""
        if self.state == CircuitState.HALF_OPEN:
            # Reset on success in half-open state
            self.failure_count = 0
            self.state = CircuitState.CLOSED
            logger.info("Circuit half-open call succeeded, circuit closed")

    def record_failure(self) -> None:
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.CLOSED and self.failure_count >= self.failure_threshold:
            # Open the circuit
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit opened after {self.failure_count} failures")

    def is_open(self) -> bool:
        """
        Check if circuit is open.

        Returns:
            True if circuit is open and calls should be prevented, False otherwise
        """
        if self.state == CircuitState.OPEN:
            # Check if recovery time has elapsed
            if self.last_failure_time and time.time() - self.last_failure_time >= self.recovery_time:
                # Move to half-open state
                self.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit moved to half-open state after {self.recovery_time}s")
                return False
            return True

        return False


class ConnectionPool:
    """
    Pool of HTTP connections for a service.

    Manages a pool of httpx.AsyncClient instances for efficient connection reuse.
    Implements connection limiting and automatic cleanup.
    """

    def __init__(self, endpoint: str, max_size: int = 10, min_size: int = 2):
        """
        Initialize the connection pool.

        Args:
            endpoint: Service endpoint URL
            max_size: Maximum number of connections in the pool
            min_size: Minimum number of connections to maintain
        """
        self.endpoint = endpoint
        self.max_size = max_size
        self.min_size = min_size
        self.connections: List[httpx.AsyncClient] = []
        self.semaphore = asyncio.Semaphore(max_size)
        self._closed = False

    async def initialize(self) -> None:
        """Initialize the connection pool with min_size connections."""
        # Create initial connections
        for _ in range(self.min_size):
            client = httpx.AsyncClient(base_url=self.endpoint, timeout=10.0)
            self.connections.append(client)

        logger.debug(f"Initialized connection pool for {self.endpoint} with {self.min_size} connections")

    async def get_connection(self) -> httpx.AsyncClient:
        """
        Get a connection from the pool.

        Returns:
            An httpx.AsyncClient connection

        Raises:
            RuntimeError: If the pool is closed
        """
        if self._closed:
            raise RuntimeError("Connection pool is closed")

        await self.semaphore.acquire()

        try:
            # Get existing connection or create new one
            if self.connections:
                return self.connections.pop()
            else:
                logger.debug(f"Creating new connection to {self.endpoint}")
                return httpx.AsyncClient(base_url=self.endpoint, timeout=10.0)
        except Exception as e:
            # Release semaphore on error
            self.semaphore.release()
            raise e

    def release_connection(self, connection: httpx.AsyncClient) -> None:
        """
        Return a connection to the pool.

        Args:
            connection: The connection to return
        """
        if self._closed:
            # Close the connection if pool is closed
            asyncio.create_task(connection.aclose())
            return

        # Add back to pool if we're under max_size
        if len(self.connections) < self.max_size:
            self.connections.append(connection)
        else:
            # Close the connection if pool is full
            asyncio.create_task(connection.aclose())

        # Release semaphore
        self.semaphore.release()

    async def close_all(self) -> None:
        """Close all connections in the pool."""
        self._closed = True

        for connection in self.connections:
            await connection.aclose()

        self.connections.clear()
        logger.debug(f"Closed all connections in pool for {self.endpoint}")


class NetworkMcpClient(MCPClient):
    """
    Client for communicating with distributed MCP services over the network.

    Implements the Model Context Protocol client interface for making tool calls
    and streaming resources from remote MCP servers over HTTP and SSE.
    """

    def __init__(self, service_discovery: ServiceDiscovery) -> None:
        """
        Initialize the client.

        Args:
            service_discovery: Service discovery interface for resolving service endpoints
        """
        self.service_discovery = service_discovery
        self.connection_pools: Dict[str, ConnectionPool] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._active_tasks: Set[asyncio.Task[Any]] = set()
        self._tool_schemas: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._resource_schemas: Dict[str, Dict[str, Dict[str, Any]]] = {}

    async def connect(self, service_name: str) -> None:
        """
        Connect to a specific MCP service.

        Args:
            service_name: Name of the service to connect to

        Raises:
            ServiceNotFoundError: If the service cannot be found or connected to
        """
        if service_name in self.connection_pools:
            return  # Already connected

        # Get service endpoint from discovery
        endpoint = await self.service_discovery.resolve(service_name)
        if not endpoint:
            raise ServiceNotFoundError(service_name)

        # Initialize connection pool for this service
        pool = ConnectionPool(endpoint)
        await pool.initialize()
        self.connection_pools[service_name] = pool

        # Initialize circuit breaker for this service
        self.circuit_breakers[service_name] = CircuitBreaker()

        logger.info(f"Connected to MCP service {service_name} at {endpoint}")

    async def call_tool(
        self,
        service_name: str,
        tool_name: str,
        input_data: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Call a tool on a specific MCP service.

        Makes an HTTP POST request to the tool endpoint on the specified service.
        Handles retries, circuit breaking, and error recovery.

        Args:
            service_name: Name of the service
            tool_name: Name of the tool to call
            input_data: Tool arguments
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries

        Returns:
            Tool result

        Raises:
            ServiceNotFoundError: If the service doesn't exist
            ToolNotFoundError: If the tool doesn't exist
            ToolExecutionError: If the tool execution fails
            CircuitOpenError: If circuit breaker is open
        """
        await self.connect(service_name)

        # Check circuit breaker
        circuit = self.circuit_breakers.get(service_name)
        if circuit and circuit.is_open():
            raise CircuitOpenError(f"Circuit open for {service_name}", details={"service_name": service_name})

        retries = 0
        last_error = None

        while retries <= max_retries:
            connection = None
            try:
                # Get connection from pool
                connection = await self._get_connection(service_name)

                # Prepare arguments
                arguments = input_data or {}

                # Make HTTP request to tool endpoint
                response = await connection.post(
                    f"/tool/{tool_name}",
                    json={"arguments": arguments},
                    timeout=timeout
                )

                # Return connection to pool
                if connection:
                    self.connection_pools[service_name].release_connection(connection)
                    connection = None

                # Handle response
                if response.status_code == 200:
                    # Record success for circuit breaker
                    if circuit:
                        circuit.record_success()

                    # Extract result from response
                    response_data = response.json()
                    result = response_data.get("result", {})

                    # Return result
                    return dict(result) if isinstance(result, dict) else {}

                elif response.status_code == 404:
                    # Tool not found
                    error_message = self._handle_error(service_name, response)
                    raise ToolNotFoundError(service_name, tool_name)
                    
                else:
                    # Handle error response
                    error_message = self._handle_error(service_name, response)
                    last_error = ToolExecutionError(
                        service_name=service_name, 
                        tool_name=tool_name, 
                        details={"error": error_message},
                        original_error=Exception(error_message)  # Include the error message in the original error
                    )

            except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as e:
                # Network or timeout error - retry
                # Create a ToolExecutionError from TransportError to maintain type compatibility
                last_error = ToolExecutionError(
                    service_name=service_name,
                    tool_name=tool_name,
                    details={"error": f"Network error: {str(e)}"},
                    original_error=e
                )
                logger.warning(f"Retryable error in call to {service_name}.{tool_name}: {e}")

            except (ServiceNotFoundError, ToolNotFoundError):
                # Re-raise these exceptions without retry
                raise

            except Exception as e:
                # Other exception
                last_error = ToolExecutionError(
                    service_name=service_name, 
                    tool_name=tool_name, 
                    original_error=e
                )
                logger.error(f"Error in call to {service_name}.{tool_name}: {e}", exc_info=True)

            finally:
                # Return connection to pool if not already done
                if connection:
                    self.connection_pools[service_name].release_connection(connection)

            # Record failure for circuit breaker
            if circuit:
                circuit.record_failure()

            # Should we retry?
            retries += 1
            if retries <= max_retries:
                # Exponential backoff
                wait_time = 0.1 * (2 ** retries)
                logger.info(f"Retrying {service_name}.{tool_name} in {wait_time:.2f}s (attempt {retries}/{max_retries})")
                await asyncio.sleep(wait_time)
            else:
                break

        # All retries failed
        raise last_error or ToolExecutionError(service_name=service_name, tool_name=tool_name, 
                                            details={"error": f"Unknown error calling {service_name}.{tool_name}"})

    async def get_resource(
        self,
        service_name: str,
        resource_name: str,
        params: Optional[Dict[str, Any]] = None,
        resource_id: Optional[str] = None,
        service: Optional[str] = None,
        timeout: float = 60.0
    ) -> ResourceDataType:
        """
        Get a resource from a specific MCP service.

        Creates an SSE connection to the resource endpoint on the specified service.
        Collects all items from the SSE stream and returns them.

        Args:
            service_name: Name of the service
            resource_name: Name of the resource to access
            params: Optional parameters for resource access
            resource_id: Optional resource ID
            service: Optional service name (synonym for service_name for API compatibility)
            timeout: Connection timeout in seconds

        Returns:
            Resource data (list or dictionary)

        Raises:
            ServiceNotFoundError: If the service doesn't exist
            ResourceNotFoundError: If the resource doesn't exist
            ResourceAccessError: If the resource access fails
            CircuitOpenError: If circuit breaker is open
        """
        # If both service_name and service are provided, service takes precedence
        effective_service_name = service or service_name
        
        await self.connect(effective_service_name)

        # Check circuit breaker
        circuit = self.circuit_breakers.get(effective_service_name)
        if circuit and circuit.is_open():
            raise CircuitOpenError(f"Circuit open for {effective_service_name}", 
                                   details={"service_name": effective_service_name})

        # Prepare resource path
        path = resource_name
        if resource_id:
            path = f"{path}/{resource_id}"
            
        # Prepare query parameters
        query_params = params or {}
        query_string = ""
        if query_params:
            query_string = "?" + "&".join(f"{k}={v}" for k, v in query_params.items())
            
        # Assemble full resource path with query parameters
        resource_path = f"{path}{query_string}"

        connection = None
        stream = None
        result_items = []

        try:
            # Get connection from pool
            connection = await self._get_connection(effective_service_name)

            # Create SSE connection to resource endpoint
            response = await connection.request(
                "GET",
                f"/resource/{resource_path}",
                timeout=timeout,
                headers={"Accept": "text/event-stream"}
            )
            stream = response.aiter_raw()

            # Never return connection to pool while streaming
            # We'll close it manually when done

            # Stream data from SSE connection
            async for raw_bytes in stream:
                line = raw_bytes.decode('utf-8')
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        result_items.append(data)
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in SSE stream: {line[6:]}")

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Resource not found
                if circuit:
                    circuit.record_failure()
                raise ResourceNotFoundError(effective_service_name, resource_name)
            else:
                # Other HTTP error
                if circuit:
                    circuit.record_failure()
                raise ResourceAccessError(
                    service_name=effective_service_name, 
                    resource_name=resource_name, 
                    original_error=e
                )
                
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as e:
            # Network or timeout error
            if circuit:
                circuit.record_failure()
            raise TransportError(
                f"Network error accessing {effective_service_name}/{resource_path}: {str(e)}",
                original_error=e,
                details={"service_name": effective_service_name, "resource_name": resource_name}
            )

        except Exception as e:
            # Other exception
            if circuit:
                circuit.record_failure()
            logger.error(f"Error streaming resource {effective_service_name}/{resource_path}: {e}", exc_info=True)
            raise ResourceAccessError(
                service_name=effective_service_name, 
                resource_name=resource_name, 
                original_error=e
            )

        finally:
            # Clean up resources
            if stream:
                # Nothing to do, the context manager handles it
                pass

            if connection:
                # Return connection to pool when streaming is done or failed
                self.connection_pools[effective_service_name].release_connection(connection)

        # Record success for circuit breaker
        if circuit:
            circuit.record_success()
            
        # Return collected items as a list (or a single item if there's only one)
        if len(result_items) == 1 and isinstance(result_items[0], dict):
            return result_items[0]  # Return single dict
        # Return list of items
        return result_items if result_items else []

    def get_tool_schema(self, service_name: str, tool_name: str) -> Dict[str, Any]:
        """
        Get the JSON schema for a tool's input parameters.

        Args:
            service_name: Name of the service
            tool_name: Name of the tool

        Returns:
            JSON schema for the tool

        Raises:
            ServiceNotFoundError: If the service doesn't exist
            ToolNotFoundError: If the tool doesn't exist
        """
        # Check if we have cached schema
        if service_name in self._tool_schemas and tool_name in self._tool_schemas[service_name]:
            return self._tool_schemas[service_name][tool_name]
            
        # We don't have the schema, need to fetch it
        raise NotImplementedError("Tool schema fetching not implemented yet")

    def get_resource_schema(self, service_name: str, resource_name: str) -> Dict[str, Any]:
        """
        Get the JSON schema for a resource's parameters.

        Args:
            service_name: Name of the service
            resource_name: Name of the resource

        Returns:
            JSON schema for the resource parameters

        Raises:
            ServiceNotFoundError: If the service doesn't exist
            ResourceNotFoundError: If the resource doesn't exist
        """
        # Check if we have cached schema
        if service_name in self._resource_schemas and resource_name in self._resource_schemas[service_name]:
            return self._resource_schemas[service_name][resource_name]
            
        # We don't have the schema, need to fetch it
        raise NotImplementedError("Resource schema fetching not implemented yet")

    def list_services(self) -> List[str]:
        """
        List all available services.

        Returns:
            List of service names
        """
        return list(self.service_discovery.services.keys())

    def list_tools(self, service_name: str) -> List[str]:
        """
        List all tools provided by a service.

        Args:
            service_name: Name of the service

        Returns:
            List of tool names

        Raises:
            ServiceNotFoundError: If the service doesn't exist
        """
        if service_name not in self.service_discovery.services:
            raise ServiceNotFoundError(service_name)
            
        # We need to fetch the tool list from the service
        raise NotImplementedError("Tool listing not implemented yet")

    def list_resources(self, service_name: str) -> List[str]:
        """
        List all resources provided by a service.

        Args:
            service_name: Name of the service

        Returns:
            List of resource names

        Raises:
            ServiceNotFoundError: If the service doesn't exist
        """
        if service_name not in self.service_discovery.services:
            raise ServiceNotFoundError(service_name)
            
        # We need to fetch the resource list from the service
        raise NotImplementedError("Resource listing not implemented yet")

    def create_background_task(self, coroutine: Coroutine[Any, Any, T]) -> asyncio.Task[T]:
        """
        Create a tracked background task.

        Args:
            coroutine: Coroutine to run as a task

        Returns:
            The created task
        """
        task = asyncio.create_task(coroutine)
        self._active_tasks.add(task)
        task.add_done_callback(self._remove_task)
        return task

    def _remove_task(self, task: asyncio.Task[Any]) -> None:
        """Remove a task from the active tasks set."""
        self._active_tasks.discard(task)

    async def close(self) -> None:
        """
        Close all connections.

        Closes all connection pools and cancels any active tasks.
        """
        # Cancel all active tasks
        for task in self._active_tasks:
            if not task.done():
                task.cancel()

        # Wait for all tasks to complete
        if self._active_tasks:
            await asyncio.gather(*self._active_tasks, return_exceptions=True)

        # Close all connection pools
        for service_name, pool in list(self.connection_pools.items()):
            logger.info(f"Closing connections to {service_name}")
            await pool.close_all()

        self.connection_pools.clear()
        self.circuit_breakers.clear()
        logger.info("NetworkMcpClient closed")

    async def _get_connection(self, service_name: str) -> httpx.AsyncClient:
        """
        Get a connection from the pool for a service.

        Args:
            service_name: Name of the service

        Returns:
            An httpx.AsyncClient connection

        Raises:
            ServiceNotFoundError: If not connected to the service
        """
        pool = self.connection_pools.get(service_name)
        if not pool:
            raise ServiceNotFoundError(service_name)

        return await pool.get_connection()

    def _handle_error(self, service_name: str, response: httpx.Response) -> str:
        """
        Handle error response from service.

        Args:
            service_name: Name of the service
            response: HTTP response

        Returns:
            Error message
        """
        status = response.status_code
        try:
            error_data = response.json()
            error_message = error_data.get("error", {}).get("message", 
                           error_data.get("detail", "Unknown error"))
        except Exception:
            error_message = response.text or f"HTTP {status}"

        logger.error(f"Error from {service_name}: HTTP {status} - {error_message}")
        return f"Service error ({status}): {error_message}"