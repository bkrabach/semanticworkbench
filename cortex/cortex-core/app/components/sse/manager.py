"""
Server-Sent Events (SSE) manager for handling real-time connection management.

This module provides a simple, focused SSE manager that handles connection lifecycle
and event delivery.
"""
import asyncio
import uuid
from typing import Any, Dict, Optional, Tuple

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SseManager:
    """
    Manages SSE connections and event delivery.
    
    This class provides a simplified implementation of SSE connection management
    following the core design principle of ruthless simplicity. It handles:
    
    1. Connection registration and removal
    2. Event delivery to specific resources
    3. Periodic heartbeats to keep connections alive
    
    Attributes:
        connections: Dictionary mapping connection IDs to connection details
        heartbeat_task: Optional background task for sending heartbeats
    """
    
    def __init__(self):
        """Initialize the SSE manager."""
        self.connections: Dict[str, Dict[str, Any]] = {}
        self.heartbeat_task: Optional[asyncio.Task] = None
    
    async def register_connection(
        self,
        resource_type: str,
        resource_id: str,
        user_id: str,
    ) -> Tuple[asyncio.Queue, str]:
        """
        Register a new SSE connection.
        
        Args:
            resource_type: The type of resource (workspace, conversation)
            resource_id: The ID of the resource
            user_id: The ID of the user
            
        Returns:
            A tuple containing the event queue and connection ID
        """
        # Create a unique connection ID
        connection_id = str(uuid.uuid4())
        
        # Create a queue for the connection
        queue = asyncio.Queue()
        
        # Store connection details
        self.connections[connection_id] = {
            "resource_type": resource_type,
            "resource_id": resource_id,
            "user_id": user_id,
            "queue": queue,
        }
        
        logger.info(f"SSE connection registered: {connection_id} for {resource_type}/{resource_id} by user {user_id}")
        
        # Start the heartbeat task if not already running
        if not self.heartbeat_task or self.heartbeat_task.done():
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        return queue, connection_id
    
    async def remove_connection(
        self,
        resource_type: str,
        resource_id: str,
        connection_id: str,
    ) -> None:
        """
        Remove an SSE connection.
        
        Args:
            resource_type: The type of resource
            resource_id: The ID of the resource
            connection_id: The ID of the connection
        """
        if connection_id in self.connections:
            del self.connections[connection_id]
            logger.info(f"SSE connection removed: {connection_id} for {resource_type}/{resource_id}")
        
        # Cancel heartbeat task if no connections left
        if not self.connections and self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
            self.heartbeat_task = None
    
    async def send_event(
        self,
        resource_type: str,
        resource_id: str,
        event_type: str,
        data: Dict[str, Any],
    ) -> int:
        """
        Send an event to all connections for a specific resource.
        
        Args:
            resource_type: The type of resource
            resource_id: The ID of the resource
            event_type: The type of event
            data: The event data
            
        Returns:
            The number of connections the event was sent to
        """
        count = 0
        for conn_id, conn in self.connections.items():
            if conn["resource_type"] == resource_type and conn["resource_id"] == resource_id:
                await conn["queue"].put({
                    "type": event_type,
                    "data": data,
                })
                count += 1
        
        if count > 0:
            logger.debug(f"Sent event {event_type} to {count} connections for {resource_type}/{resource_id}")
        
        return count
    
    async def _heartbeat_loop(self) -> None:
        """
        Send periodic heartbeats to all connections.
        
        This keeps connections alive and allows clients to detect disconnections.
        """
        try:
            while True:
                # Wait for the configured interval
                await asyncio.sleep(settings.SSE_HEARTBEAT_INTERVAL)
                
                # Send heartbeat to all connections
                for conn_id, conn in list(self.connections.items()):
                    try:
                        await conn["queue"].put({
                            "type": "heartbeat",
                            "data": "",
                        })
                    except Exception as e:
                        logger.error(f"Failed to send heartbeat to {conn_id}: {str(e)}")
                        
                # Log heartbeat sent
                if self.connections:
                    logger.debug(f"Sent heartbeat to {len(self.connections)} connections")
        except asyncio.CancelledError:
            logger.debug("Heartbeat task cancelled")
            raise
        except Exception as e:
            logger.exception(f"Error in heartbeat loop: {str(e)}")
    
    async def cleanup(self) -> None:
        """
        Clean up all connections and tasks.
        
        This should be called when shutting down the application.
        """
        # Cancel heartbeat task
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
            self.heartbeat_task = None
        
        # Clear all connections
        self.connections.clear()
        logger.info("SSE manager cleaned up")


# Global SSE manager instance
_sse_manager: Optional[SseManager] = None


def get_sse_manager() -> SseManager:
    """
    Get the global SSE manager instance.
    
    Returns:
        The SSE manager instance
    """
    global _sse_manager
    if _sse_manager is None:
        _sse_manager = SseManager()
    return _sse_manager