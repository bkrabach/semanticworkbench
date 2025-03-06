import logging
from typing import Dict, List, Any, Optional, Union, Set, Callable, Awaitable
import asyncio
import json
from datetime import datetime
import uuid
from functools import lru_cache
import re
import weakref
import traceback
from fastapi import Request
from sse_starlette.sse import EventSourceResponse
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.core.router import message_router
from app.models.schemas import SSEConnection

# Setup logging
logger = logging.getLogger(__name__)
settings = get_settings()

class SSEManager:
    """
    Manager for Server-Sent Events (SSE) connections.
    
    This class is responsible for:
    - Managing SSE connections
    - Broadcasting real-time updates to clients
    - Ensuring correct message delivery to the appropriate clients
    - Managing connection lifecycle and error handling
    """
    
    def __init__(self):
        """Initialize the SSE Manager."""
        # Active connections
        # Key: connection_id, Value: connection_data
        self.connections: Dict[str, Dict[str, Any]] = {}
        
        # User connections
        # Key: user_id, Value: Set of connection_ids
        self.user_connections: Dict[str, Set[str]] = {}
        
        # Conversation connections
        # Key: conversation_id, Value: Set of connection_ids
        self.conversation_connections: Dict[str, Set[str]] = {}
        
        # Event queues
        # Key: connection_id, Value: asyncio.Queue
        self.event_queues: Dict[str, asyncio.Queue] = {}
        
        # Cleanup task
        self.cleanup_task = None
        
        # Connection timeout (seconds)
        self.connection_timeout = settings.sse_connection_timeout if hasattr(settings, 'sse_connection_timeout') else 300
        
        # Heartbeat interval (seconds)
        self.heartbeat_interval = settings.sse_heartbeat_interval if hasattr(settings, 'sse_heartbeat_interval') else 30
        
        # Register with router for events
        message_router.register_component("sse_manager", self)
        
        logger.info("SSEManager initialized")
    
    async def initialize(self) -> None:
        """Initialize the SSE Manager components and start background tasks."""
        # Initialize cleanup task
        self._initialize_cleanup_task()
        
        # Subscribe to relevant events
        await self._setup_event_subscriptions()
    
    def _initialize_cleanup_task(self) -> None:
        """Initialize the cleanup task."""
        self.cleanup_task = asyncio.create_task(self._cleanup_inactive_connections())
    
    async def _setup_event_subscriptions(self) -> None:
        """Set up subscriptions to relevant events."""
        try:
            # Message events
            await message_router.subscribe_to_event(
                "sse_manager",
                "message_created",
                self._handle_message_created
            )
            
            await message_router.subscribe_to_event(
                "sse_manager",
                "message_updated",
                self._handle_message_updated
            )
            
            # Conversation events
            await message_router.subscribe_to_event(
                "sse_manager",
                "conversation_updated",
                self._handle_conversation_updated
            )
            
            await message_router.subscribe_to_event(
                "sse_manager",
                "conversation_deleted",
                self._handle_conversation_deleted
            )
            
            # Tool events
            await message_router.subscribe_to_event(
                "sse_manager",
                "tool_execution_started",
                self._handle_tool_execution_started
            )
            
            await message_router.subscribe_to_event(
                "sse_manager",
                "tool_execution_completed",
                self._handle_tool_execution_completed
            )
            
            await message_router.subscribe_to_event(
                "sse_manager",
                "tool_execution_failed",
                self._handle_tool_execution_failed
            )
            
            logger.debug("Event subscriptions set up")
            
        except Exception as e:
            logger.error(f"Error setting up event subscriptions: {str(e)}")
            logger.error(traceback.format_exc())
    
    async def _handle_message_created(
        self,
        data: Dict[str, Any]
    ) -> None:
        """
        Handle message created event.
        
        Args:
            data: Event data
        """
        try:
            # Extract data
            message = data.get("message")
            
            if not message:
                logger.warning("Invalid message_created event data")
                return
            
            # Get conversation ID
            conversation_id = message.get("conversation_id")
            
            if not conversation_id:
                logger.warning("Message missing conversation_id")
                return
            
            # Create event data
            event_data = {
                "type": "message_created",
                "message": message
            }
            
            # Broadcast to conversation connections
            await self._broadcast_to_conversation(
                conversation_id,
                "message",
                event_data
            )
            
        except Exception as e:
            logger.error(f"Error handling message_created event: {str(e)}")
            logger.error(traceback.format_exc())
    
    async def _handle_message_updated(
        self,
        data: Dict[str, Any]
    ) -> None:
        """
        Handle message updated event.
        
        Args:
            data: Event data
        """
        try:
            # Extract data
            message = data.get("message")
            
            if not message:
                logger.warning("Invalid message_updated event data")
                return
            
            # Get conversation ID
            conversation_id = message.get("conversation_id")
            
            if not conversation_id:
                logger.warning("Message missing conversation_id")
                return
            
            # Create event data
            event_data = {
                "type": "message_updated",
                "message": message
            }
            
            # Broadcast to conversation connections
            await self._broadcast_to_conversation(
                conversation_id,
                "message",
                event_data
            )
            
        except Exception as e:
            logger.error(f"Error handling message_updated event: {str(e)}")
            logger.error(traceback.format_exc())
    
    async def _handle_conversation_updated(
        self,
        data: Dict[str, Any]
    ) -> None:
        """
        Handle conversation updated event.
        
        Args:
            data: Event data
        """
        try:
            # Extract data
            conversation = data.get("conversation")
            
            if not conversation:
                logger.warning("Invalid conversation_updated event data")
                return
            
            # Get conversation ID
            conversation_id = conversation.get("id")
            
            if not conversation_id:
                logger.warning("Conversation missing id")
                return
            
            # Create event data
            event_data = {
                "type": "conversation_updated",
                "conversation": conversation
            }
            
            # Broadcast to conversation connections
            await self._broadcast_to_conversation(
                conversation_id,
                "conversation",
                event_data
            )
            
        except Exception as e:
            logger.error(f"Error handling conversation_updated event: {str(e)}")
            logger.error(traceback.format_exc())
    
    async def _handle_conversation_deleted(
        self,
        data: Dict[str, Any]
    ) -> None:
        """
        Handle conversation deleted event.
        
        Args:
            data: Event data
        """
        try:
            # Extract data
            conversation_id = data.get("conversation_id")
            
            if not conversation_id:
                logger.warning("Invalid conversation_deleted event data")
                return
            
            # Create event data
            event_data = {
                "type": "conversation_deleted",
                "conversation_id": conversation_id
            }
            
            # Broadcast to conversation connections
            await self._broadcast_to_conversation(
                conversation_id,
                "conversation",
                event_data
            )
            
            # Remove conversation connections
            self._remove_conversation_connections(conversation_id)
            
        except Exception as e:
            logger.error(f"Error handling conversation_deleted event: {str(e)}")
            logger.error(traceback.format_exc())
    
    async def _handle_tool_execution_started(
        self,
        data: Dict[str, Any]
    ) -> None:
        """
        Handle tool execution started event.
        
        Args:
            data: Event data
        """
        try:
            # Extract data
            execution_id = data.get("execution_id")
            conversation_id = data.get("conversation_id")
            
            if not execution_id or not conversation_id:
                logger.warning("Invalid tool_execution_started event data")
                return
            
            # Create event data
            event_data = {
                "type": "tool_execution_started",
                "execution_id": execution_id,
                "conversation_id": conversation_id,
                "message_id": data.get("message_id"),
                "tool_id": data.get("tool_id"),
                "tool_name": data.get("tool_name"),
                "inputs": data.get("inputs")
            }
            
            # Broadcast to conversation connections
            await self._broadcast_to_conversation(
                conversation_id,
                "tool",
                event_data
            )
            
        except Exception as e:
            logger.error(f"Error handling tool_execution_started event: {str(e)}")
            logger.error(traceback.format_exc())
    
    async def _handle_tool_execution_completed(
        self,
        data: Dict[str, Any]
    ) -> None:
        """
        Handle tool execution completed event.
        
        Args:
            data: Event data
        """
        try:
            # Extract data
            execution_id = data.get("execution_id")
            conversation_id = data.get("conversation_id")
            
            if not execution_id or not conversation_id:
                logger.warning("Invalid tool_execution_completed event data")
                return
            
            # Create event data
            event_data = {
                "type": "tool_execution_completed",
                "execution_id": execution_id,
                "conversation_id": conversation_id,
                "message_id": data.get("message_id"),
                "tool_id": data.get("tool_id"),
                "tool_name": data.get("tool_name"),
                "inputs": data.get("inputs"),
                "outputs": data.get("outputs"),
                "status": data.get("status")
            }
            
            # Broadcast to conversation connections
            await self._broadcast_to_conversation(
                conversation_id,
                "tool",
                event_data
            )
            
        except Exception as e:
            logger.error(f"Error handling tool_execution_completed event: {str(e)}")
            logger.error(traceback.format_exc())
    
    async def _handle_tool_execution_failed(
        self,
        data: Dict[str, Any]
    ) -> None:
        """
        Handle tool execution failed event.
        
        Args:
            data: Event data
        """
        try:
            # Extract data
            execution_id = data.get("execution_id")
            conversation_id = data.get("conversation_id")
            
            if not execution_id or not conversation_id:
                logger.warning("Invalid tool_execution_failed event data")
                return
            
            # Create event data
            event_data = {
                "type": "tool_execution_failed",
                "execution_id": execution_id,
                "conversation_id": conversation_id,
                "message_id": data.get("message_id"),
                "tool_name": data.get("tool_name"),
                "inputs": data.get("inputs"),
                "error": data.get("error"),
                "status": data.get("status")
            }
            
            # Broadcast to conversation connections
            await self._broadcast_to_conversation(
                conversation_id,
                "tool",
                event_data
            )
            
        except Exception as e:
            logger.error(f"Error handling tool_execution_failed event: {str(e)}")
            logger.error(traceback.format_exc())
    
    async def _broadcast_to_conversation(
        self,
        conversation_id: str,
        event_type: str,
        data: Dict[str, Any]
    ) -> None:
        """
        Broadcast an event to all connections for a conversation.
        
        Args:
            conversation_id: Conversation ID
            event_type: Event type
            data: Event data
        """
        # Check if conversation has connections
        if conversation_id not in self.conversation_connections:
            logger.debug(f"No connections for conversation {conversation_id}")
            return
        
        # Get connection IDs
        connection_ids = self.conversation_connections[conversation_id]
        
        if not connection_ids:
            logger.debug(f"Empty connection set for conversation {conversation_id}")
            return
        
        # Create event message
        event_message = {
            "type": event_type,
            "data": data
        }
        
        # Convert to JSON
        event_json = json.dumps(event_message)
        
        # Broadcast to all connections
        for connection_id in list(connection_ids):
            await self._send_to_connection(connection_id, event_type, event_json)
    
    async def _send_to_connection(
        self,
        connection_id: str,
        event_type: str,
        data: str
    ) -> bool:
        """
        Send an event to a specific connection.
        
        Args:
            connection_id: Connection ID
            event_type: Event type
            data: Event data
            
        Returns:
            True if sent successfully
        """
        # Check if connection exists
        if connection_id not in self.event_queues:
            logger.warning(f"Connection {connection_id} not found")
            return False
        
        # Get queue
        queue = self.event_queues[connection_id]
        
        try:
            # Put event in queue
            await queue.put((event_type, data))
            
            # Update last active time
            if connection_id in self.connections:
                self.connections[connection_id]["last_active"] = datetime.utcnow()
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending to connection {connection_id}: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    async def create_connection(
        self,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new SSE connection.
        
        Args:
            data: Connection data
                user_id: User ID
                conversation_id: Optional conversation ID
                
        Returns:
            Connection details
        """
        try:
            # Extract data
            user_id = data.get("user_id")
            conversation_id = data.get("conversation_id")
            
            # Validate data
            if not user_id:
                raise ValueError("Missing user_id")
            
            # Create connection ID
            connection_id = str(uuid.uuid4())
            
            # Create event queue
            queue = asyncio.Queue()
            
            # Create connection
            connection = {
                "id": connection_id,
                "user_id": user_id,
                "conversation_id": conversation_id,
                "created_at": datetime.utcnow(),
                "last_active": datetime.utcnow()
            }
            
            # Add connection
            self.connections[connection_id] = connection
            self.event_queues[connection_id] = queue
            
            # Add to user connections
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            
            self.user_connections[user_id].add(connection_id)
            
            # Add to conversation connections if applicable
            if conversation_id:
                if conversation_id not in self.conversation_connections:
                    self.conversation_connections[conversation_id] = set()
                
                self.conversation_connections[conversation_id].add(connection_id)
            
            logger.info(f"Created SSE connection {connection_id} for user {user_id}")
            
            return {
                "connection_id": connection_id
            }
            
        except Exception as e:
            logger.error(f"Error creating SSE connection: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    async def remove_connection(
        self,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Remove an SSE connection.
        
        Args:
            data: Connection data
                connection_id: Connection ID
                
        Returns:
            Operation status
        """
        try:
            # Extract data
            connection_id = data.get("connection_id")
            
            # Validate data
            if not connection_id:
                raise ValueError("Missing connection_id")
            
            # Remove connection
            result = await self._remove_connection(connection_id)
            
            return {
                "success": result
            }
            
        except Exception as e:
            logger.error(f"Error removing SSE connection: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _remove_connection(
        self,
        connection_id: str
    ) -> bool:
        """
        Remove a connection.
        
        Args:
            connection_id: Connection ID
            
        Returns:
            True if removed successfully
        """
        # Check if connection exists
        if connection_id not in self.connections:
            logger.warning(f"Connection {connection_id} not found")
            return False
        
        try:
            # Get connection
            connection = self.connections[connection_id]
            user_id = connection.get("user_id")
            conversation_id = connection.get("conversation_id")
            
            # Remove from connections
            del self.connections[connection_id]
            
            # Remove from event queues
            if connection_id in self.event_queues:
                # Signal queue to close
                await self.event_queues[connection_id].put(("close", ""))
                del self.event_queues[connection_id]
            
            # Remove from user connections
            if user_id in self.user_connections:
                self.user_connections[user_id].discard(connection_id)
                
                # Remove user entry if empty
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
            
            # Remove from conversation connections
            if conversation_id and conversation_id in self.conversation_connections:
                self.conversation_connections[conversation_id].discard(connection_id)
                
                # Remove conversation entry if empty
                if not self.conversation_connections[conversation_id]:
                    del self.conversation_connections[conversation_id]
            
            logger.info(f"Removed SSE connection {connection_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error removing connection {connection_id}: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def _remove_conversation_connections(
        self,
        conversation_id: str
    ) -> int:
        """
        Remove all connections for a conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Number of connections removed
        """
        # Check if conversation has connections
        if conversation_id not in self.conversation_connections:
            return 0
        
        # Get connection IDs
        connection_ids = list(self.conversation_connections[conversation_id])
        
        # Remove each connection
        removed_count = 0
        
        for connection_id in connection_ids:
            # Create task to remove connection
            asyncio.create_task(self._remove_connection(connection_id))
            removed_count += 1
        
        logger.info(f"Removing {removed_count} connections for conversation {conversation_id}")
        
        return removed_count
    
    async def _cleanup_inactive_connections(self) -> None:
        """Cleanup inactive connections periodically."""
        try:
            while True:
                # Sleep for a while
                await asyncio.sleep(60)  # Check every minute
                
                # Get current time
                now = datetime.utcnow()
                
                # Find inactive connections
                inactive_connections = []
                
                for connection_id, connection in list(self.connections.items()):
                    last_active = connection.get("last_active")
                    
                    if not last_active:
                        continue
                    
                    # Check if inactive
                    if (now - last_active).total_seconds() > self.connection_timeout:
                        inactive_connections.append(connection_id)
                
                # Remove inactive connections
                for connection_id in inactive_connections:
                    logger.info(f"Cleaning up inactive connection {connection_id}")
                    await self._remove_connection(connection_id)
                
                if inactive_connections:
                    logger.info(f"Cleaned up {len(inactive_connections)} inactive connections")
                
        except asyncio.CancelledError:
            logger.info("Cleanup task cancelled")
        except Exception as e:
            logger.error(f"Error in cleanup task: {str(e)}")
            logger.error(traceback.format_exc())
    
    async def sse_endpoint(
        self,
        request: Request,
        connection_id: str
    ) -> EventSourceResponse:
        """
        SSE endpoint for clients.
        
        Args:
            request: FastAPI request
            connection_id: Connection ID
            
        Returns:
            EventSourceResponse
        """
        # Check if connection exists
        if connection_id not in self.connections:
            logger.warning(f"SSE endpoint: Connection {connection_id} not found")
            return EventSourceResponse(self._error_event_generator(connection_id))
        
        # Update last active time
        self.connections[connection_id]["last_active"] = datetime.utcnow()
        
        # Create event generator
        return EventSourceResponse(self._event_generator(request, connection_id))
    
    async def _event_generator(
        self,
        request: Request,
        connection_id: str
    ):
        """
        Generate SSE events for a connection.
        
        Args:
            request: FastAPI request
            connection_id: Connection ID
            
        Yields:
            SSE events
        """
        # Check if connection exists
        if connection_id not in self.connections or connection_id not in self.event_queues:
            yield {
                "event": "error",
                "data": "Connection not found"
            }
            return
        
        # Get queue
        queue = self.event_queues[connection_id]
        
        # Get connection
        connection = self.connections[connection_id]
        
        # Send initial event
        yield {
            "event": "connected",
            "data": json.dumps({
                "connection_id": connection_id,
                "user_id": connection.get("user_id"),
                "conversation_id": connection.get("conversation_id")
            })
        }
        
        # Setup heartbeat timer
        last_heartbeat = datetime.utcnow()
        
        try:
            # Process events until client disconnects
            while True:
                # Check if client is still connected
                if await request.is_disconnected():
                    logger.info(f"Client disconnected from SSE connection {connection_id}")
                    break
                
                # Check if connection still exists
                if connection_id not in self.connections:
                    logger.info(f"SSE connection {connection_id} was removed")
                    break
                
                # Check if we need to send a heartbeat
                now = datetime.utcnow()
                
                if (now - last_heartbeat).total_seconds() >= self.heartbeat_interval:
                    # Send heartbeat
                    yield {
                        "event": "heartbeat",
                        "data": now.isoformat()
                    }
                    
                    # Update last heartbeat
                    last_heartbeat = now
                    
                    # Update last active time
                    connection["last_active"] = now
                
                # Try to get event from queue with timeout
                try:
                    event_type, event_data = await asyncio.wait_for(
                        queue.get(),
                        timeout=1.0  # Short timeout to check for disconnection
                    )
                    
                    # Check if close event
                    if event_type == "close":
                        logger.info(f"Received close event for SSE connection {connection_id}")
                        break
                    
                    # Yield event
                    yield {
                        "event": event_type,
                        "data": event_data
                    }
                    
                    # Update last active time
                    connection["last_active"] = datetime.utcnow()
                    
                except asyncio.TimeoutError:
                    # No event available, continue to next iteration
                    continue
                    
        except Exception as e:
            logger.error(f"Error in SSE event generator for {connection_id}: {str(e)}")
            logger.error(traceback.format_exc())
            
        finally:
            # Remove connection if not already removed
            if connection_id in self.connections:
                asyncio.create_task(self._remove_connection(connection_id))
    
    async def _error_event_generator(
        self,
        connection_id: str
    ):
        """
        Generate error events for a connection.
        
        Args:
            connection_id: Connection ID
            
        Yields:
            Error SSE events
        """
        # Send error event
        yield {
            "event": "error",
            "data": json.dumps({
                "error": f"Connection {connection_id} not found"
            })
        }
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            # Cancel cleanup task
            if self.cleanup_task:
                self.cleanup_task.cancel()
                
                try:
                    await self.cleanup_task
                except asyncio.CancelledError:
                    pass
            
            # Close all connections
            for connection_id in list(self.connections.keys()):
                await self._remove_connection(connection_id)
            
            # Clear data
            self.connections.clear()
            self.user_connections.clear()
            self.conversation_connections.clear()
            self.event_queues.clear()
            
            logger.info("SSEManager cleaned up")
            
        except Exception as e:
            logger.error(f"Error in cleanup: {str(e)}")

# Create a global instance for use throughout the application
sse_manager = SSEManager()