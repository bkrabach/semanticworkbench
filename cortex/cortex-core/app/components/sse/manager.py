"""
SSE Connection Manager implementation for Cortex Core.

Manages the lifecycle of Server-Sent Events connections, including registration,
removal, and communication with connected clients. Uses domain models for
internal state management.
"""

from typing import Dict, List, Any, Tuple, AsyncGenerator, Callable, Awaitable
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
    Internal class to attach a queue to a connection
    
    This provides a way to store an asyncio.Queue with the connection
    since Pydantic models don't support dynamic attributes
    """
    
    def __init__(self, connection: SSEConnection, queue: asyncio.Queue):
        self._connection = connection
        self.queue = queue
        
    @property
    def connection(self):
        return self._connection
        
    # Pass through all connection properties
    @property
    def id(self):
        return self._connection.id
        
    @property
    def user_id(self):
        return self._connection.user_id
        
    @property
    def channel_type(self):
        return self._connection.channel_type
        
    @property
    def resource_id(self):
        return self._connection.resource_id
        
    @property
    def connected_at(self):
        return self._connection.connected_at
        
    @property
    def last_active_at(self):
        return self._connection.last_active_at
        
    def __str__(self):
        return f"ConnectionInfo(id={self.id}, user={self.user_id})"


class SSEConnectionManager:
    """
    Manages Server-Sent Event connections for real-time messaging.
    
    This base class provides the core connection lifecycle management,
    with support for channel types and resource-based subscriptions.
    """
    
    def __init__(self):
        """Initialize the connection manager with empty connection collections"""
        # Store connection objects by type and resource
        self.connections = {
            "global": [],  # List of SSEConnection for global connections
            "user": collections.defaultdict(list),  # Dict of resource_id to list of SSEConnection
            "workspace": collections.defaultdict(list),
            "conversation": collections.defaultdict(list)
        }
        
    async def register_connection(self,
                             channel_type: str,
                             resource_id: str,
                             user_id: str) -> Tuple[asyncio.Queue, str]:
        """
        Register an SSE connection and return the connection ID
        
        Args:
            channel_type: Type of channel (global, user, workspace, conversation)
            resource_id: ID of the resource to subscribe to
            user_id: ID of the user establishing the connection
            
        Returns:
            Tuple containing the event queue and unique connection ID
        """
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
        
        # Create event queue
        queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
        
        # Create combined connection object that has the queue
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
                if conn.id != connection_id
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
            if conn.id != connection_id
        ]
        
        # Clean up empty resource entries
        if not self.connections[channel_type][resource_id]:
            del self.connections[channel_type][resource_id]
            
        logger.info(f"Removed SSE connection {connection_id} for {channel_type} {resource_id}")
        
    async def register_event_callback(self, channel_type: str, resource_id: str, callback: Callable[[str, Dict[str, Any]], None] | Callable[[str, Dict[str, Any]], Awaitable[None]]):
        """
        Register a callback for events on a specific channel.
        Base implementation does nothing - this is provided for interface compatibility.
        Implementations should override this method if they support callbacks.
        
        Args:
            channel_type: Type of channel (global, user, workspace, conversation)
            resource_id: ID of the resource
            callback: Function to call when an event is sent to this channel
        """
        # Base implementation does nothing
        logger.warning("register_event_callback not implemented in base SSEConnectionManager")
        
    async def send_event(self,
                      channel_type: str,
                      resource_id: str,
                      event_type: str,
                      data: Dict[str, Any],
                      republish: bool = False):
        """
        Send an event to a specific channel
        
        Args:
            channel_type: Type of channel (global, user, workspace, conversation)
            resource_id: ID of the resource
            event_type: Type of event to send
            data: Event data payload
            republish: Whether to republish to the event system (used by subclasses)
        """
        # Log the event being sent
        logger.info(f"Sending {event_type} event to {channel_type}/{resource_id}")
        
        if channel_type == "global":
            if not self.connections["global"]:
                logger.warning(f"No global connections to send {event_type} event to")
            await self.broadcast_to_channel(
                self.connections["global"], event_type, data
            )
        elif resource_id in self.connections[channel_type]:
            logger.info(f"Found {len(self.connections[channel_type][resource_id])} connections for {channel_type}/{resource_id}")
            await self.broadcast_to_channel(
                self.connections[channel_type][resource_id], event_type, data
            )
        else:
            # Don't broadcast to all channel types - this causes message leakage
            # Just log that no connections were found
            logger.info(f"No active connections found for {channel_type}/{resource_id}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about active connections
        
        Returns:
            Dictionary with connection statistics
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
                for conn in connections:
                    user_id = conn.user_id
                    connections_by_user[user_id] = connections_by_user.get(user_id, 0) + 1
                    
            # Add total for this channel type
            connections_by_channel[channel_type] = channel_count
            total_connections += channel_count
            
        # For global connections, add their users
        for conn in self.connections["global"]:
            user_id = conn.user_id
            connections_by_user[user_id] = connections_by_user.get(user_id, 0) + 1
            
        return {
            "total_connections": total_connections,
            "connections_by_channel": connections_by_channel,
            "connections_by_user": connections_by_user,
            "generated_at": datetime.now(timezone.utc)
        }
        
    async def broadcast_to_channel(self,
                              connections: List[SSEConnection],
                              event_type: str,
                              data: Dict[str, Any]):
        """
        Broadcast an event to all connections in a channel
        
        Args:
            connections: List of SSE connections to send to
            event_type: Type of event to send
            data: Event data payload
        """
        # Format the event as SSE format
        event_data = {
            "event": event_type,
            "data": data
        }
        
        # Put the event on each connection's queue
        for conn in connections:
            # Get the queue directly from the connection object
            queue = getattr(conn, "queue", None)
            if queue:
                try:
                    await queue.put(event_data)
                    logger.debug(f"Added {event_type} event to queue for connection {conn.id}")
                except Exception as e:
                    logger.error(f"Failed to add event to queue: {e}")
                
    async def create_heartbeat_task(self, queue: asyncio.Queue, interval: float = 30.0):
        """
        Create a heartbeat task that sends periodic heartbeats to a queue
        
        Args:
            queue: Queue to send heartbeats to
            interval: Time in seconds between heartbeats
        
        Returns:
            Heartbeat task
        """
        try:
            while True:
                # Send a heartbeat with the current timestamp
                timestamp = datetime.now(timezone.utc).isoformat()
                await queue.put({
                    "event": "heartbeat",
                    "data": {"timestamp_utc": timestamp}
                })
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            # Clean exit on cancellation
            logger.debug("Heartbeat task cancelled")
            raise
            
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
        # Send initial connection event
        yield f"event: connect\ndata: {json.dumps({'connected': True})}\n\n"
        
        # Create heartbeat task
        heartbeat_task = asyncio.create_task(
            self.create_heartbeat_task(queue, heartbeat_interval)
        )
        
        try:
            # Process events from the queue
            while True:
                try:
                    # Wait for the next event with a small timeout
                    # Don't block forever in case of connection issues
                    event = await asyncio.wait_for(queue.get(), timeout=5.0)
                    
                    # Format the event as SSE
                    event_name = event.get("event", "message")
                    event_data = json.dumps(event.get("data", {}))
                    
                    # Yield the formatted SSE event
                    yield f"event: {event_name}\ndata: {event_data}\n\n"
                    
                    # Mark as processed
                    queue.task_done()
                    
                except asyncio.TimeoutError:
                    # No event received, continue loop
                    continue
                    
        except asyncio.CancelledError:
            # This is expected when client disconnects
            logger.info("SSE event generator cancelled")
            
        finally:
            # Clean up the heartbeat task
            heartbeat_task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(heartbeat_task), timeout=0.1)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass