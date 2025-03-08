"""
SSE Connection Manager implementation for Cortex Core.

Manages the lifecycle of Server-Sent Events connections, including registration,
removal, and communication with connected clients.
"""

from typing import Dict, List, Any, Tuple, Optional, AsyncGenerator
import asyncio
import uuid
from datetime import datetime, timezone
import json
import logging

from app.utils.logger import logger

class SSEConnectionManager:
    """
    Manages SSE connections with proper lifecycle handling.
    """
    
    def __init__(self):
        """Initialize the connection manager with empty connection dictionaries"""
        self.connections = {
            "global": [],
            "user": {},
            "workspace": {},
            "conversation": {}
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
        queue = asyncio.Queue()
        connection_id = str(uuid.uuid4())
        
        connection_info = {
            "id": connection_id,
            "user_id": user_id,
            "queue": queue,
            "connected_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Add to appropriate channel
        if channel_type == "global":
            self.connections["global"].append(connection_info)
        else:
            if resource_id not in self.connections[channel_type]:
                self.connections[channel_type][resource_id] = []
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
                if conn["id"] != connection_id
            ]
            logger.info(f"Removed SSE connection {connection_id} for global channel")
            return
        
        # Handle typed connections
        if resource_id not in self.connections[channel_type]:
            logger.warning(f"Attempted to remove non-existent connection: {channel_type}/{resource_id}/{connection_id}")
            return
            
        # Remove the connection
        self.connections[channel_type][resource_id] = [
            conn for conn in self.connections[channel_type][resource_id]
            if conn["id"] != connection_id
        ]
        
        # Clean up empty resource entries
        if not self.connections[channel_type][resource_id]:
            del self.connections[channel_type][resource_id]
        
        logger.info(f"Removed SSE connection {connection_id} for {channel_type} {resource_id}")
        
    async def broadcast_to_channel(self, 
                                connections: List[Dict[str, Any]], 
                                event_type: str, 
                                data: Dict[str, Any]):
        """
        Broadcast an event to all connections in a channel
        
        Args:
            connections: List of connection info dictionaries
            event_type: Type of event to broadcast
            data: Event data payload
        """
        for connection in connections:
            if connection.get("queue"):
                try:
                    await connection["queue"].put({
                        "event": event_type, 
                        "data": data
                    })
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
            Dictionary with connection statistics by channel type
        """
        # Calculate counts for each channel type
        channel_counts = {}
        total_count = len(self.connections["global"])
        
        for channel_type in ["user", "workspace", "conversation"]:
            type_counts = {}
            type_total = 0
            
            for resource_id, connections in self.connections[channel_type].items():
                count = len(connections)
                type_counts[resource_id] = count
                type_total += count
                
            channel_counts[channel_type] = type_counts
            total_count += type_total
        
        return {
            "global": len(self.connections["global"]),
            "channels": channel_counts,
            "total": total_count
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