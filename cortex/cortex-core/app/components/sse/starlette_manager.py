"""
SSE Connection Manager implementation using sse-starlette for Cortex Core.

This implementation replaces the custom SSE implementation with the robust
sse-starlette library, addressing connection stability issues while maintaining
compatibility with our domain-driven architecture.
"""

from typing import Dict, Any, AsyncGenerator, Callable, Tuple, Awaitable
import asyncio
import uuid
from datetime import datetime, timezone
import json

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
        # Structure is consistent: for each channel type, we use a dictionary where
        # keys are resource IDs and values are lists of connection objects
        self.connections = {
            "global": {"global": []},  # Key is always "global", value is list of connections
            "user": {},    # Key is user_id, value is list of connections
            "workspace": {},  # Key is workspace_id, value is list of connections
            "conversation": {}  # Key is conversation_id, value is list of connections
        }

        # Store event callbacks by channel type/resource ID with the same structure
        self.event_callbacks = {
            "global": {"global": []},
            "user": {},
            "workspace": {},
            "conversation": {}
        }

        # Map connection IDs to their queues - keeping implementation details separate from domain models
        self.connection_queues: Dict[str, asyncio.Queue[Dict[str, Any]]] = {}

        # Log structure setup for debugging
        logger.info("SSE Starlette Manager initialized with connection structure:")
        for channel_type in self.connections:
            logger.info(f"- {channel_type} channel initialized")
            if channel_type == "global":
                logger.info("  - global resource initialized with empty list")

        logger.info(f"Connection structures: {self.connections}")
        logger.info(f"Callback structures: {self.event_callbacks}")

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
        queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()

        # Normalize resource_id to ensure consistent lookup
        normalized_resource_id = str(resource_id)

        # Create domain model for the connection with the queue attached
        connection = SSEConnection(
            id=connection_id,
            channel_type=channel_type,
            resource_id=normalized_resource_id,  # Use normalized ID
            user_id=user_id,
            connected_at=datetime.now(timezone.utc),
            last_active_at=datetime.now(timezone.utc)
        )

        # Store the queue in our connection mapping instead of on the domain model
        self.connection_queues[connection_id] = queue

        # Log the connection details before adding
        logger.info(f"Registering connection {connection_id} for {channel_type}/{normalized_resource_id}")

        # Add to appropriate channel
        if channel_type == "global":
            self.connections["global"]["global"].append(connection)
        else:
            # Make sure the dictionary has an entry for this resource
            if normalized_resource_id not in self.connections[channel_type]:
                self.connections[channel_type][normalized_resource_id] = []
            self.connections[channel_type][normalized_resource_id].append(connection)  # Use normalized ID

        # Log updated counts
        active_count = 0
        if channel_type == "global":
            active_count = len(self.connections["global"]["global"])
            logger.info(f"After registration: {active_count} global connections")
        else:
            active_count = len(self.connections[channel_type][normalized_resource_id])
            logger.info(f"After registration: {active_count} connections for {channel_type}/{normalized_resource_id}")

        # Always log a complete connection map after registration for debugging
        logger.info("Current connection mapping:")
        for ch_type, resources in self.connections.items():
            for res_id, conns in resources.items():
                logger.info(f"  - {ch_type}/{res_id}: {len(conns)} connections")
                for conn in conns:
                    logger.info(f"    - {conn.id} (user={conn.user_id})")

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
        # Normalize resource_id to ensure consistent lookup
        normalized_resource_id = str(resource_id)

        # Debug connections before removal
        if channel_type == "conversation" and normalized_resource_id in self.connections[channel_type]:
            logger.info(f"Before removal: {len(self.connections[channel_type][normalized_resource_id])} connections for {channel_type}/{normalized_resource_id}")

        # Clean up the queue from our mapping
        if connection_id in self.connection_queues:
            del self.connection_queues[connection_id]
            logger.debug(f"Removed queue for connection {connection_id}")

        # Handle global connections
        if channel_type == "global":
            self.connections["global"]["global"] = [
                conn for conn in self.connections["global"]["global"]
                if conn.id != connection_id
            ]
            logger.info(f"Removed SSE connection {connection_id} for global channel")
            return

        # Handle typed connections
        if normalized_resource_id not in self.connections[channel_type] or not self.connections[channel_type][normalized_resource_id]:
            logger.warning(f"Attempted to remove non-existent connection: {channel_type}/{normalized_resource_id}/{connection_id}")
            return

        # Remove the connection
        self.connections[channel_type][normalized_resource_id] = [
            conn for conn in self.connections[channel_type][normalized_resource_id]
            if conn.id != connection_id
        ]

        # Clean up empty resource entries
        if not self.connections[channel_type][normalized_resource_id]:
            del self.connections[channel_type][normalized_resource_id]

            # Do NOT clear callbacks - other systems might still be using them
            # Just log that we're keeping them
            if normalized_resource_id in self.event_callbacks[channel_type]:
                logger.info(f"Keeping {len(self.event_callbacks[channel_type][normalized_resource_id])} callbacks for {channel_type}/{normalized_resource_id} for future connections")

        logger.info(f"Removed SSE connection {connection_id} for {channel_type} {normalized_resource_id}")

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
        # Normalize resource_id to ensure consistent lookup
        normalized_resource_id = str(resource_id)

        # Get reference to event system (imported at module level to avoid circular imports)

        if channel_type == "global":
            self.event_callbacks["global"]["global"].append(callback)
            logger.info(f"Now have {len(self.event_callbacks['global']['global'])} callbacks for global channel")

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
            # Make sure we have a list for this resource
            if normalized_resource_id not in self.event_callbacks[channel_type]:
                self.event_callbacks[channel_type][normalized_resource_id] = []

            self.event_callbacks[channel_type][normalized_resource_id].append(callback)
            logger.info(f"Now have {len(self.event_callbacks[channel_type][normalized_resource_id])} callbacks for {channel_type}/{normalized_resource_id}")

            # Register with the event system directly
            async def event_system_callback(event_type, payload):
                # Check if this is our own event to prevent loops
                if payload.source == "sse_manager":
                    logger.debug(f"Skipping our own event: {event_type}")
                    return

                # Check if this is for our resource
                logger.debug(f"Event for {channel_type}: {event_type}, checking for {normalized_resource_id}")
                event_resource = str(payload.data.get(f"{channel_type}_id", ""))

                # Either exact match or normalized match
                if event_resource == normalized_resource_id or str(event_resource).lower() == str(normalized_resource_id).lower():
                    logger.info(f"Event match: {event_type} for {channel_type}/{normalized_resource_id}")
                    # Call our callback properly based on whether it's async or not
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event_type, payload.data)
                    else:
                        callback(event_type, payload.data)

            # Directly await the subscription
            pattern = f"{channel_type}.*"
            logger.info(f"Subscribing to {pattern} events for {channel_type}/{normalized_resource_id}")
            await get_event_system().subscribe(pattern, event_system_callback)

    async def send_event(self,
                      channel_type: str,
                      resource_id: str,
                      event_type: str,
                      data: Dict[str, Any],
                      republish: bool = False) -> None:
        """
        Send an event to a specific channel.

        Args:
            channel_type: Type of channel (global, user, workspace, conversation)
            resource_id: ID of the resource
            event_type: Type of event to send
            data: Event data payload
            republish: Whether to republish to the event system (ignored in simplified version)
        """
        # Normalize resource_id for consistent lookup
        normalized_resource_id = str(resource_id)

        # Log the event being sent (concise)
        logger.info(f"Sending {event_type} to {channel_type}/{normalized_resource_id}")

        # Add the resource_id to the data if not present
        data_with_id = dict(data)
        resource_id_key = f"{channel_type}_id"
        if resource_id_key not in data_with_id:
            data_with_id[resource_id_key] = normalized_resource_id

        # Create formatted event
        event_data = {
            "event": event_type,
            "data": json.dumps(data_with_id)
        }

        # Get connections for this resource
        active_connections = []
        if channel_type == "global":
            active_connections = self.connections["global"].get("global", [])
        elif normalized_resource_id in self.connections.get(channel_type, {}):
            active_connections = self.connections[channel_type][normalized_resource_id]

        # Send to all active connections
        sent_count = 0
        for conn in active_connections:
            queue = self.connection_queues.get(conn.id)
            if queue:
                try:
                    await queue.put(event_data)
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Failed to send event to queue: {e}")

        # Log success or failure (concise)
        conn_count = len(active_connections)
        if conn_count > 0:
            logger.info(f"Sent {event_type} to {sent_count}/{conn_count} connections")
        else:
            logger.info(f"No active connections for {channel_type}/{normalized_resource_id}")

        return

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about active connections

        Returns:
            Dictionary with connection statistics formatted for SSEConnectionStats
        """
        # Count connections by channel and user
        global_connections = len(self.connections["global"].get("global", []))
        connections_by_channel = {"global": global_connections}
        total_connections = global_connections
        connections_by_user: Dict[str, int] = {}

        # Debug the current connection state in detail
        logger.info(f"Connection stats - Global connections: {global_connections}")
        logger.info(f"Global connection details: {[conn.id for conn in self.connections['global'].get('global', [])]}")
        for channel_type in ["user", "workspace", "conversation"]:
            logger.info(f"Connection stats - {channel_type} channels: {len(self.connections[channel_type])}")
            # List all resource IDs to help with debugging
            if self.connections[channel_type]:
                logger.info(f"All {channel_type} resource IDs: {list(self.connections[channel_type].keys())}")
            for resource_id, connections in self.connections[channel_type].items():
                logger.info(f"Connection stats - {channel_type}/{resource_id}: {len(connections)} connections")
                # Log connection IDs for this resource
                logger.info(f"Connection IDs for {channel_type}/{resource_id}: {[conn.id for conn in connections]}")

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
        for conn in self.connections["global"].get("global", []):
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

        Args:
            channel_type: Type of channel (global, user, workspace, conversation)
            resource_id: ID of the resource
            user_id: ID of the user
            connection_id: Unique connection ID
            request: FastAPI request object

        Yields:
            Event dictionaries for sse-starlette
        """
        # Get or create queue for this connection
        queue = self.connection_queues.get(connection_id)
        if queue is None:
            queue = asyncio.Queue()
            self.connection_queues[connection_id] = queue

        # Normalize resource_id
        normalized_resource_id = str(resource_id)
        
        # Create connection object
        connection = SSEConnection(
            id=connection_id,
            channel_type=channel_type,
            resource_id=normalized_resource_id,
            user_id=user_id,
            connected_at=datetime.now(timezone.utc),
            last_active_at=datetime.now(timezone.utc)
        )
        
        # Add to appropriate collection
        if channel_type == "global":
            self.connections["global"]["global"].append(connection)
        else:
            if normalized_resource_id not in self.connections[channel_type]:
                self.connections[channel_type][normalized_resource_id] = []
            self.connections[channel_type][normalized_resource_id].append(connection)
        
        logger.info(f"Connection registered: {channel_type}/{normalized_resource_id}")

        # Send initial connection event
        yield {
            "event": "connect",
            "data": json.dumps({"connected": True})
        }

        # Create heartbeat task
        heartbeat_interval = 15.0  # seconds

        async def send_heartbeats():
            try:
                while True:
                    await asyncio.sleep(heartbeat_interval)
                    await queue.put({
                        "event": "heartbeat",
                        "data": json.dumps({
                            "timestamp_utc": datetime.now(timezone.utc).isoformat()
                        })
                    })
            except asyncio.CancelledError:
                # Clean exit
                raise

        heartbeat_task = asyncio.create_task(send_heartbeats())

        try:
            # Process events from the queue until disconnect
            while True:
                try:
                    # Wait for events with timeout
                    event = await asyncio.wait_for(queue.get(), timeout=5.0)
                    yield event
                    queue.task_done()
                except asyncio.TimeoutError:
                    # No event, continue waiting
                    continue
                except Exception as e:
                    logger.error(f"Error in event generator: {e}")
                    continue

        except asyncio.CancelledError:
            # Client disconnected
            logger.info(f"Client disconnected: {channel_type}/{normalized_resource_id}")

        finally:
            # Clean up
            heartbeat_task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(heartbeat_task), timeout=0.1)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

            # Remove the connection when client disconnects
            await self.remove_connection(channel_type, normalized_resource_id, connection_id)

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
        # Normalize resource_id for consistent lookup
        normalized_resource_id = str(resource_id)

        # Log initial connection request details
        logger.info(f"SSE connection request from user {user_id} for {channel_type}/{normalized_resource_id}")
        logger.info(f"Request client: {request.client}, headers: {request.headers.get('user-agent', 'unknown')}")

        # Register the connection - this will be called from an async context
        queue, connection_id = await self.register_connection(channel_type, normalized_resource_id, user_id)

        # Verify that connection was registered properly
        if channel_type == "global":
            connections_for_resource = self.connections.get("global", {}).get("global", [])
        else:
            connections_for_resource = self.connections.get(channel_type, {}).get(normalized_resource_id, [])

        connection_exists = any(conn.id == connection_id for conn in connections_for_resource)
        logger.info(f"Connection registration verified: {connection_exists}")

        if not connection_exists:
            logger.error(f"CRITICAL: Connection {connection_id} not registered properly")
            logger.info(f"Current connections: {self.connections}")
            # Fix the problem by re-registering explicitly
            logger.info("Re-registering missing connection")

            connection = SSEConnection(
                id=connection_id,
                channel_type=channel_type,
                resource_id=normalized_resource_id if channel_type != "global" else "global",
                user_id=user_id,
                connected_at=datetime.now(timezone.utc),
                last_active_at=datetime.now(timezone.utc)
            )

            # Add to the right place
            if channel_type == "global":
                self.connections["global"]["global"].append(connection)
            else:
                if normalized_resource_id not in self.connections[channel_type]:
                    self.connections[channel_type][normalized_resource_id] = []
                self.connections[channel_type][normalized_resource_id].append(connection)

            # Verify the fix worked
            if channel_type == "global":
                conn_check = any(conn.id == connection_id for conn in self.connections["global"]["global"])
            else:
                conn_check = any(conn.id == connection_id for conn in self.connections[channel_type].get(normalized_resource_id, []))

            logger.info(f"Connection re-registration successful: {conn_check}")

        # Log connection state in detail after registration
        try:
            if channel_type == "global":
                connection_count = len(self.connections.get(channel_type, {}).get("global", []))
                connection_ids = [conn.id for conn in self.connections.get(channel_type, {}).get("global", [])]
            else:
                connection_count = len(self.connections.get(channel_type, {}).get(normalized_resource_id, []))
                connection_ids = [
                    conn.id for conn in self.connections.get(channel_type, {}).get(normalized_resource_id, [])
                ]
        except Exception as e:
            logger.error(f"Error getting connection state: {e}")
            connection_count = 0
            connection_ids = []
            # Let's log the actual structure to help debug
            logger.error(f"Connections structure: {self.connections}")
            if channel_type in self.connections:
                logger.error(f"Type of self.connections[{channel_type}]: {type(self.connections[channel_type])}")
        logger.info(f"After registration in create_sse_response: {connection_count} connections for {channel_type}/{normalized_resource_id}")
        logger.info(f"Connection IDs after registration: {connection_ids}")

        # Verify queue is created properly
        if connection_id not in self.connection_queues:
            logger.error(f"CRITICAL: No queue found for connection {connection_id}")
            # Fix by creating a queue
            self.connection_queues[connection_id] = queue
            logger.info(f"Created missing queue for connection {connection_id}")

        # Log complete queue info
        queue_sizes = {conn_id: q.qsize() for conn_id, q in self.connection_queues.items()
                      if conn_id in [c.id for c in connections_for_resource]}
        logger.info(f"Queue status - sizes: {queue_sizes}")

        # Create the generator and store reference to ensure it's not garbage collected
        logger.info(f"Creating event generator for {channel_type}/{normalized_resource_id}")
        generator = self.event_generator(channel_type, normalized_resource_id, user_id, connection_id, request)
        logger.info(f"Successfully created event generator for {channel_type}/{normalized_resource_id}")

        # Create and return the EventSourceResponse
        logger.info("Creating EventSourceResponse with generator")
        response = EventSourceResponse(
            generator,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )

        logger.info(f"Created EventSourceResponse for {channel_type}/{normalized_resource_id}")

        # Add a reference to the connection ID to avoid it getting garbage collected
        # This is a critical step to ensure the connection remains active
        setattr(response, '_connection_id', connection_id)
        setattr(response, '_resource_id', normalized_resource_id)
        setattr(response, '_channel_type', channel_type)

        # Log connection reference
        logger.info(f"Added connection reference {connection_id} to response for {channel_type}/{normalized_resource_id}")

        # Send a test event immediately to verify the connection is working
        from uuid import uuid4
        test_event_id = str(uuid4())
        try:
            await queue.put({
                "event": "connection_test",
                "data": json.dumps({
                    "test_id": test_event_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "message": "Testing SSE connection"
                })
            })
            logger.info(f"Added test event {test_event_id} to queue for {connection_id}")
        except Exception as e:
            logger.error(f"Failed to add test event to queue: {e}")

        return response