"""
Factory module for creating MCP clients.

This module provides factory functions to create the appropriate 
MCP client implementation based on configuration.
"""

import logging
import os
from typing import Dict, Optional

from app.core.mcp.client import MCPClient
from app.core.mcp.in_process_client import InProcessMCPClient
from app.core.mcp.network_client import NetworkMcpClient, ServiceDiscovery
from app.core.mcp.service_discovery import service_discovery

logger = logging.getLogger(__name__)


async def create_mcp_client(distributed: Optional[bool] = None) -> MCPClient:
    """
    Create an MCP client based on configuration.
    
    Args:
        distributed: Override to force distributed or in-process mode
                    If None, uses CORTEX_DISTRIBUTED_MODE environment variable
    
    Returns:
        An MCP client implementation
    """
    # Determine mode from environment or parameter
    if distributed is None:
        distributed_mode = os.getenv("CORTEX_DISTRIBUTED_MODE", "false").lower() in ("true", "1", "yes")
    else:
        distributed_mode = distributed
    
    # Create client based on mode
    if distributed_mode:
        logger.info("Creating network MCP client for distributed mode")
        # Initialize service discovery
        await service_discovery.initialize()
        # Create network client
        return NetworkMcpClient(service_discovery)
    else:
        logger.info("Creating in-process MCP client")
        # Create in-process client
        return InProcessMCPClient()


# Global client instance
mcp_client: Optional[MCPClient] = None


async def get_mcp_client() -> MCPClient:
    """
    Get the global MCP client instance, creating it if needed.
    
    Returns:
        The global MCP client
    """
    global mcp_client
    
    if mcp_client is None:
        mcp_client = await create_mcp_client()
        
    return mcp_client


async def close_mcp_client() -> None:
    """Close the global MCP client if it exists."""
    global mcp_client
    
    if mcp_client and isinstance(mcp_client, NetworkMcpClient):
        await mcp_client.close()
        mcp_client = None