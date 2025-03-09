"""
SSE Connection Manager implementation using sse-starlette for Cortex Core.

This implementation replaces the custom SSE implementation with the robust
sse-starlette library, addressing connection stability issues while maintaining
compatibility with our domain-driven architecture.
"""

from typing import Dict, Any, AsyncGenerator, Callable, Tuple, Awaitable
import asyncio
import inspect
import uuid
from datetime import datetime, timezone
import json
import collections

from sse_starlette.sse import EventSourceResponse
from fastapi import Request

from app.utils.logger import logger
from app.models.domain.sse import SSEConnection
from app.components.sse.manager import SSEConnectionManager
from app.components.event_system import get_event_system


class SSEStarletteManager(SSEConnectionManager):
    """
    Manages SSE connections using the sse-starlette library with proper lifecycle handling.

    This implementation addresses the connection stability issues identified in the
    custom implementation by leveraging an established, production-ready SSE library
    while maintaining compatibility with our domain-driven repository architecture.
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

        # Store event callbacks by channel type/resource ID
        self.event_callbacks = {
            "global": [],
            "user": collections.defaultdict(list),
            "workspace": collections.defaultdict(list),
            "conversation": collections.defaultdict(list)
        }
        
        # Map connection IDs to their queues - keeping implementation details separate from domain models
        self.connection_queues = {}

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
        
        # Create a real queue that will be used to send events
        queue: asyncio.Queue = asyncio.Queue()

        # Create domain model for the connection with the queue attached
        connection = SSEConnection(
            id=connection_id,
            channel_type=channel_type,
            resource_id=resource_id,
            user_id=user_id,
            connected_at=datetime.now(timezone.utc),
            last_active_at=datetime.now(timezone.utc)
        )
        
        # Store the queue in our connection mapping instead of on the domain model
        self.connection_queues[connection_id] = queue

        # Add to appropriate channel
        if channel_type == "global":
            self.connections["global"].append(connection)
        else:
            self.connections[channel_type][resource_id].append(connection)

        # Debug the connections after adding
        if channel_type == "conversation":
            channel_connections = len(self.connections[channel_type][resource_id])
            logger.info(f"After registration: {channel_connections} connections for {channel_type}/{resource_id}")

        logger.info(f"SSE connection {connection_id} established: user={user_id}, {channel_type}={resource_id}")
        return queue, connection_id

    async def remove_connection(self,
                           channel_type: str,
                           resource_id: str,
                           connection_id: str):
        """
        Remove an SSE connection and clear its callbacks

        Args:
            channel_type: Type of channel (global, user, workspace, conversation)
            resource_id: ID of the resource
            connection_id: Unique ID of the connection to remove
        """
        # Debug connections before removal
        if channel_type == "conversation" and resource_id in self.connections[channel_type]:
            logger.info(f"Before removal: {len(self.connections[channel_type][resource_id])} connections for {channel_type}/{resource_id}")

        # Clean up the queue from our mapping
        if connection_id in self.connection_queues:
            del self.connection_queues[connection_id]
            logger.debug(f"Removed queue for connection {connection_id}")

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
            
            # Do NOT clear callbacks - other systems might still be using them
            # Just log that we're keeping them
            if resource_id in self.event_callbacks[channel_type]:
                logger.info(f"Keeping {len(self.event_callbacks[channel_type][resource_id])} callbacks for {channel_type}/{resource_id} for future connections")

        logger.info(f"Removed SSE connection {connection_id} for {channel_type} {resource_id}")

    async def register_event_callback(self,
                              channel_type: str,
                              resource_id: str,
                              callback: Callable[[str, Dict[str, Any]], None] | Callable[[str, Dict[str, Any]], Awaitable[None]]):
        """
        Register a callback for events on a specific channel

        Args:
            channel_type: Type of channel (global, user, workspace, conversation)
            resource_id: ID of the resource
            callback: Function to call when an event is sent to this channel
        """
        # Get reference to event system (imported at module level to avoid circular imports)
        
        if channel_type == "global":
            self.event_callbacks["global"].append(callback)
            logger.info(f"Now have {len(self.event_callbacks['global'])} callbacks for global channel")
            
            # Register with the event system directly
            async def event_system_callback(event_type, payload):
                # Check if this is our own event to prevent loops
                if payload.source == "sse_manager":
                    logger.debug(f"Skipping our own event: {event_type}")
                    return
                    
                # Call our callback properly based on whether it's async or not
                if asyncio.iscoroutinefunction(callback):
                    await callback(event_type, payload.data)
                else:
                    callback(event_type, payload.data)
                
            # Directly await the subscription
            await get_event_system().subscribe("global.*", event_system_callback)
        else:
            self.event_callbacks[channel_type][resource_id].append(callback)
            logger.info(f"Now have {len(self.event_callbacks[channel_type][resource_id])} callbacks for {channel_type}/{resource_id}")
            
            # Register with the event system directly
            async def event_system_callback(event_type, payload):
                # Check if this is our own event to prevent loops
                if payload.source == "sse_manager":
                    logger.debug(f"Skipping our own event: {event_type}")
                    return
                    
                # Check if this is for our resource
                logger.debug(f"Event for {channel_type}: {event_type}, checking for {resource_id}")
                event_resource = payload.data.get(f"{channel_type}_id")
                if event_resource == resource_id:
                    logger.info(f"Event match: {event_type} for {channel_type}/{resource_id}")
                    # Call our callback properly based on whether it's async or not
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event_type, payload.data)
                    else:
                        callback(event_type, payload.data)
                
            # Directly await the subscription
            pattern = f"{channel_type}.*"
            logger.info(f"Subscribing to {pattern} events for {channel_type}/{resource_id}")
            await get_event_system().subscribe(pattern, event_system_callback)

    async def send_event(self,
                      channel_type: str,
                      resource_id: str,
                      event_type: str,
                      data: Dict[str, Any],
                      republish: bool = False):
        """
        Send an event to a specific channel and optionally through the event system.
        
        This method triggers all registered callbacks for the specified channel,
        allowing subscribers to handle the event.

        Args:
            channel_type: Type of channel (global, user, workspace, conversation)
            resource_id: ID of the resource
            event_type: Type of event to send
            data: Event data payload
            republish: Whether to republish to the event system (default: False)
                       Set to False to prevent event feedback loops
        """
        # Log the event being sent
        logger.info(f"Sending {event_type} event to {channel_type}/{resource_id} (republish={republish})")

        # Add the resource_id to the data if it's not already there
        data_with_id = dict(data)
        resource_id_key = f"{channel_type}_id"
        if resource_id_key not in data_with_id:
            data_with_id[resource_id_key] = resource_id
            
        # Create a well-formatted event
        event_data = {
            "event": event_type,
            "data": json.dumps(data_with_id)
        }
           
        # First send event to any connected clients via active connections
        if channel_type == "global":
            connections = self.connections["global"]
            if connections:
                # Find the active connections
                active_connections = self.connections["global"]
                logger.info(f"Sending {event_type} to {len(active_connections)} global connections")
                for conn in active_connections:
                    # Get queue from our mapping, not from the connection object
                    queue = self.connection_queues.get(conn.id)
                    if queue:
                        try:
                            await queue.put(event_data)
                        except Exception as e:
                            logger.error(f"Failed to send event to queue: {e}")
            else:
                logger.info(f"No active global connections to send {event_type} event to")
        elif resource_id in self.connections[channel_type]:
            # Find the active connections
            active_connections = self.connections[channel_type][resource_id]
            logger.info(f"Sending {event_type} to {len(active_connections)} {channel_type}/{resource_id} connections")
            for conn in active_connections:
                # Get queue from our mapping, not from the connection object
                queue = self.connection_queues.get(conn.id)
                if queue:
                    try:
                        await queue.put(event_data)
                    except Exception as e:
                        logger.error(f"Failed to send event to queue: {e}")
        else:
            logger.info(f"No active connections for {channel_type}/{resource_id}")
            
        # Now handle republishing through the event system if requested
        if republish:
            # Make a normalized event type
            normalized_event_type = f"{channel_type}.{event_type}" if not event_type.startswith(f"{channel_type}.") else event_type
            
            # Directly await the event publication
            await get_event_system().publish(
                event_type=normalized_event_type,
                data=data_with_id,
                source="sse_manager"
            )
            
        # Now execute any registered callbacks
        if channel_type == "global" and self.event_callbacks["global"]:
            for callback in self.event_callbacks["global"]:
                try:
                    logger.debug(f"Executing global callback for {event_type}")
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event_type, data_with_id)
                    else:
                        callback(event_type, data_with_id)
                except Exception as e:
                    logger.error(f"Error in global callback: {e}")
        elif resource_id in self.event_callbacks[channel_type]:
            for callback in self.event_callbacks[channel_type][resource_id]:
                try:
                    logger.debug(f"Executing {channel_type}/{resource_id} callback for {event_type}")
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event_type, data_with_id)
                    else:
                        callback(event_type, data_with_id)
                except Exception as e:
                    logger.error(f"Error in {channel_type}/{resource_id} callback: {e}")

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

        # Debug the current connection state
        logger.info(f"Connection stats - Global connections: {len(self.connections['global'])}")
        for channel_type in ["user", "workspace", "conversation"]:
            logger.info(f"Connection stats - {channel_type} channels: {len(self.connections[channel_type])}")
            for resource_id, connections in self.connections[channel_type].items():
                logger.info(f"Connection stats - {channel_type}/{resource_id}: {len(connections)} connections")

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

    async def event_generator(self,
                         channel_type: str,
                         resource_id: str,
                         user_id: str,
                         connection_id: str,
                         request: Request) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate events for a specific SSE connection

        This generator is used by sse-starlette to create the event stream.

        Args:
            channel_type: Type of channel (global, user, workspace, conversation)
            resource_id: ID of the resource
            user_id: ID of the user
            connection_id: Unique connection ID
            request: FastAPI request object

        Yields:
            Event dictionaries for sse-starlette
        """
        # Find this connection's queue in our mapping
        queue = self.connection_queues.get(connection_id)
        
        if queue is None:
            # This should never happen since we create the queue during registration
            logger.error(f"No queue found for connection {connection_id}, creating a new one")
            queue = asyncio.Queue()
        
        # Send initial connection event
        yield {
            "event": "connect",
            "data": json.dumps({"connected": True})
        }

        # Register callback to send events to this connection
        async def event_callback(event_type: str, data: Dict[str, Any]):
            try:
                event_json = json.dumps(data) if isinstance(data, dict) else data
                await queue.put({
                    "event": event_type,
                    "data": event_json
                })
                logger.debug(f"Added {event_type} event to queue for {channel_type}/{resource_id}")
            except Exception as e:
                logger.error(f"Error adding event to queue: {e}")

        # Register the callback - now awaiting since it's async
        await self.register_event_callback(channel_type, resource_id, event_callback)

        # Create a heartbeat task
        heartbeat_interval = 30.0  # seconds

        async def send_heartbeats():
            try:
                while True:
                    await asyncio.sleep(heartbeat_interval)
                    timestamp = datetime.now(timezone.utc).isoformat()
                    await queue.put({
                        "event": "heartbeat",
                        "data": json.dumps({"timestamp_utc": timestamp})
                    })
                    logger.debug(f"Added heartbeat for {channel_type}/{resource_id}")
            except asyncio.CancelledError:
                logger.debug("Heartbeat task cancelled")
                raise

        heartbeat_task = asyncio.create_task(send_heartbeats())

        try:
            # Process events from the queue until disconnect
            while True:
                try:
                    # Wait for the next event with a reasonable timeout
                    event = await asyncio.wait_for(queue.get(), timeout=5.0)
                    logger.debug(f"Yielding {event.get('event', 'unknown')} event to {channel_type}/{resource_id}")
                    yield event
                    queue.task_done()
                except asyncio.TimeoutError:
                    # No event received, just continue waiting
                    continue

        except asyncio.CancelledError:
            # This is expected when client disconnects
            logger.info(f"Event generator for {channel_type}/{resource_id} cancelled")

        finally:
            # Clean up
            heartbeat_task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(heartbeat_task), timeout=0.1)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

            # Remove the connection when client disconnects
            await self.remove_connection(channel_type, resource_id, connection_id)

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
        # This method is included for compatibility with the SSEConnectionManager interface
        # but it's not used in this implementation as we use EventSourceResponse directly
        yield f"event: connect\ndata: {json.dumps({'connected': True})}\n\n"

    async def create_sse_response(self,
                         channel_type: str,
                         resource_id: str,
                         user_id: str,
                         request: Request) -> EventSourceResponse:
        """
        Create an SSE response for a specific channel

        Args:
            channel_type: Type of channel (global, user, workspace, conversation)
            resource_id: ID of the resource
            user_id: ID of the user
            request: FastAPI request object

        Returns:
            EventSourceResponse from sse-starlette
        """
        # Register the connection - this will be called from an async context
        _, connection_id = await self.register_connection(channel_type, resource_id, user_id)

        # Create the generator and store reference to ensure it's not garbage collected
        generator = self.event_generator(channel_type, resource_id, user_id, connection_id, request)
        logger.info(f"Created event generator for {channel_type}/{resource_id}")

        # Create and return the EventSourceResponse
        return EventSourceResponse(
            generator,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )