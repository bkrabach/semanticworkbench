"""
SSE Connection Manager implementation for Cortex Core.

Manages the lifecycle of Server-Sent Events connections, including registration,
removal, and communication with connected clients. Uses domain models for
internal state management.
"""

from typing import Dict, List, Any, Tuple, AsyncGenerator
import asyncio
import uuid
from datetime import datetime, timezone
import json
import collections

from app.utils.logger import logger
from app.models.domain.sse import SSEConnection

# Type for internal connection tracking with queue
class ConnectionInfo:
    """
    Internal class to track connection information with queue.
    
    This class encapsulates the relationship between a domain model connection
    and its associated queue for event delivery, ensuring type safety and
    following the domain-driven design pattern.
    
    Attributes:
        connection: The domain model representing the connection
        queue: The asyncio queue used for event delivery to this connection
    """
    def __init__(self, connection: SSEConnection, queue: asyncio.Queue):
        """
        Initialize a new connection info object.
        
        Args:
            connection: The domain model representing the connection
            queue: The asyncio queue for this connection
        """
        self.connection = connection
        self.queue = queue


class SSEConnectionManager:
    """
    Manages SSE connections with proper lifecycle handling.
    
    Uses domain models for internal state management following the domain-driven
    repository architecture. Instead of using raw dictionaries to store connection
    information, this manager uses strongly-typed domain models (SSEConnection)
    encapsulated in ConnectionInfo objects.
    
    This approach provides several benefits:
    1. Type safety and validation through Pydantic models
    2. Clear separation of concerns with domain model encapsulation
    3. Better maintainability with consistent naming conventions
    4. Improved testability with well-defined interfaces
    """
    
    def __init__(self):
        """Initialize the connection manager with empty connection collections"""
        # Store connection objects by type and resource
        self.connections = {
            "global": [],  # List of ConnectionInfo for global connections
            "user": collections.defaultdict(list),  # Dict of resource_id to list of ConnectionInfo
            "workspace": collections.defaultdict(list),
            "conversation": collections.defaultdict(list)
        }
        
    async def register_connection(self, 
                               channel_type: str, 
                               resource_id: str, 
                               user_id: str) -> Tuple[asyncio.Queue, str]:
        """
        Register an SSE connection and return the queue and connection ID
        
        Args:
            channel_type: Type of channel (global, user, workspace, conversation)
            resource_id: ID of the resource to subscribe to
            user_id: ID of the user establishing the connection
            
        Returns:
            Tuple containing the event queue and unique connection ID
        """
        # Create new queue for this connection
        queue: asyncio.Queue = asyncio.Queue()
        connection_id = str(uuid.uuid4())
        
        # Create domain model for the connection
        connection = SSEConnection(
            id=connection_id,
            channel_type=channel_type,
            resource_id=resource_id,
            user_id=user_id,
            connected_at=datetime.now(timezone.utc),
            last_active_at=datetime.now(timezone.utc)
        )
        
        # Create internal connection info
        connection_info = ConnectionInfo(connection, queue)
        
        # Add to appropriate channel
        if channel_type == "global":
            self.connections["global"].append(connection_info)
        else:
            self.connections[channel_type][resource_id].append(connection_info)
        
        logger.info(f"SSE connection {connection_id} established: user={user_id}, {channel_type}={resource_id}")
        return queue, connection_id
        
    async def remove_connection(self, 
                             channel_type: str, 
                             resource_id: str, 
                             connection_id: str):
        """
        Remove an SSE connection
        
        Args:
            channel_type: Type of channel (global, user, workspace, conversation)
            resource_id: ID of the resource
            connection_id: Unique ID of the connection to remove
        """
        # Handle global connections
        if channel_type == "global":
            self.connections["global"] = [
                conn for conn in self.connections["global"] 
                if conn.connection.id != connection_id
            ]
            logger.info(f"Removed SSE connection {connection_id} for global channel")
            return
        
        # Handle typed connections
        if not self.connections[channel_type][resource_id]:
            logger.warning(f"Attempted to remove non-existent connection: {channel_type}/{resource_id}/{connection_id}")
            return
            
        # Remove the connection
        self.connections[channel_type][resource_id] = [
            conn for conn in self.connections[channel_type][resource_id]
            if conn.connection.id != connection_id
        ]
        
        # Clean up empty resource entries
        if not self.connections[channel_type][resource_id]:
            del self.connections[channel_type][resource_id]
        
        logger.info(f"Removed SSE connection {connection_id} for {channel_type} {resource_id}")
        
    async def broadcast_to_channel(self, 
                                connections: List[ConnectionInfo], 
                                event_type: str, 
                                data: Dict[str, Any]):
        """
        Broadcast an event to all connections in a channel
        
        Args:
            connections: List of connection info objects
            event_type: Type of event to broadcast
            data: Event data payload
        """
        for conn_info in connections:
            try:
                # Create a domain event model
                event = {
                    "event": event_type, 
                    "data": data
                }
                
                # Update the last_active_at timestamp
                conn_info.connection.last_active_at = datetime.now(timezone.utc)
                
                # Send to the connection's queue
                await conn_info.queue.put(event)
            except Exception as e:
                logger.error(f"Failed to send event to queue: {e}")
    
    async def send_event(self,
                      channel_type: str,
                      resource_id: str,
                      event_type: str,
                      data: Dict[str, Any]):
        """
        Send an event to a specific channel
        
        Args:
            channel_type: Type of channel (global, user, workspace, conversation)
            resource_id: ID of the resource
            event_type: Type of event to send
            data: Event data payload
        """
        if channel_type == "global":
            await self.broadcast_to_channel(
                self.connections["global"], event_type, data
            )
        elif resource_id in self.connections[channel_type]:
            await self.broadcast_to_channel(
                self.connections[channel_type][resource_id], event_type, data
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about active connections
        
        Returns:
            Dictionary with connection statistics formatted for SSEConnectionStats
        """
        # Count connections by channel and user
        connections_by_channel = {"global": len(self.connections["global"])}
        total_connections = len(self.connections["global"])
        connections_by_user: Dict[str, int] = {}
        
        # Process each channel type
        for channel_type in ["user", "workspace", "conversation"]:
            channel_count = 0
            
            # Process each resource in this channel
            for resource_id, connections in self.connections[channel_type].items():
                count = len(connections)
                channel_count += count
                
                # Track counts by resource
                key = f"{channel_type}:{resource_id}"
                connections_by_channel[key] = count
                
                # Track counts by user
                for conn_info in connections:
                    user_id = conn_info.connection.user_id
                    connections_by_user[user_id] = connections_by_user.get(user_id, 0) + 1
            
            # Add total for this channel type
            connections_by_channel[channel_type] = channel_count
            total_connections += channel_count
            
        # For global connections, add their users
        for conn_info in self.connections["global"]:
            user_id = conn_info.connection.user_id
            connections_by_user[user_id] = connections_by_user.get(user_id, 0) + 1
        
        return {
            "total_connections": total_connections,
            "connections_by_channel": connections_by_channel,
            "connections_by_user": connections_by_user,
            "generated_at": datetime.now(timezone.utc)
        }
        
    async def generate_sse_events(self,
                              queue: asyncio.Queue,
                              heartbeat_interval: float = 30.0) -> AsyncGenerator[str, None]:
        """
        Generate SSE events from a queue
        
        Args:
            queue: Event queue for SSE messages
            heartbeat_interval: Time in seconds between heartbeats
            
        Yields:
            Formatted SSE event strings
        """
        # Send initial connection message
        yield f"event: connect\ndata: {json.dumps({'connected': True})}\n\n"
        
        # Create a heartbeat task
        heartbeat_task = asyncio.create_task(self._send_heartbeats(queue, heartbeat_interval))
        
        try:
            # Process events from the queue
            while True:
                try:
                    # Wait for a message with a timeout
                    event = await asyncio.wait_for(
                        queue.get(), 
                        timeout=heartbeat_interval + 5  # Longer than heartbeat interval
                    )
                    
                    # Format SSE message
                    event_type = event.get("event", "message")
                    data = event.get("data", {})
                    yield f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
                    
                    # Mark as processed
                    queue.task_done()
                    
                except asyncio.TimeoutError:
                    # No events received, but that's ok - heartbeats are handled separately
                    # Just check if client is still connected
                    continue
        finally:
            # Clean up heartbeat task
            heartbeat_task.cancel()
            try:
                await asyncio.wait_for(
                    asyncio.shield(heartbeat_task), 
                    timeout=0.1
                )
            except (asyncio.CancelledError, asyncio.TimeoutError):
                # Expected during cancellation
                pass
                
    async def _send_heartbeats(self, queue: asyncio.Queue, heartbeat_interval: float = 30.0):
        """
        Send periodic heartbeats to an SSE connection
        
        Args:
            queue: Event queue for the connection
            heartbeat_interval: Time in seconds between heartbeats
        """
        try:
            while True:
                # Create a task that will let us detect cancellation
                sleep_task = asyncio.create_task(asyncio.sleep(heartbeat_interval))
                await sleep_task
                
                # Send heartbeat
                timestamp = datetime.now(timezone.utc).isoformat()
                await queue.put({
                    "event": "heartbeat",
                    "data": {"timestamp_utc": timestamp}
                })
        except asyncio.CancelledError:
            # Clean exit on cancellation
            logger.debug("Heartbeat task cancelled")
            raise