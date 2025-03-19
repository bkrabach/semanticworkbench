"""
Message Router implementation for Cortex platform.

This module provides a simplified router component for processing messages.
It uses a queue-based approach for handling messages and routing them to
appropriate handlers.
"""

import asyncio
import time
from typing import Dict, Any, Optional, Callable, Awaitable

from app.interfaces.event_system import EventSystemInterface
from app.interfaces.router import RouterInterface, RouterMessage
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MessageRouter(RouterInterface):
    """
    Message router implementation that processes messages through a queue.
    
    This router prioritizes messages based on their priority and processes
    them in order. It provides a simple, reliable way to handle messages
    without complex routing logic.
    """
    
    def __init__(self, event_system: EventSystemInterface):
        """
        Initialize the message router.
        
        Args:
            event_system: The event system for publishing routing events
        """
        self.event_system = event_system
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._processing = False
        self._handler_task: Optional[asyncio.Task] = None
        self._stats = {
            "messages_received": 0,
            "messages_processed": 0,
            "messages_failed": 0,
            "queue_max_size": 0,
            "start_time": time.time()
        }
        
        # Set up handlers for different message types
        self._handlers: Dict[str, Callable[[RouterMessage], Awaitable[bool]]] = {}
        
        logger.info("Message Router initialized")
        
    async def route_message(self, message_type: str, payload: Dict[str, Any], priority: int = 2) -> bool:
        """
        Route a message to the appropriate handler.
        
        This is a convenience method that creates a RouterMessage from the provided
        parameters and routes it to the appropriate handler.
        
        Args:
            message_type: The type of message to route
            payload: The message payload
            priority: The message priority (1-4, higher is more urgent)
            
        Returns:
            True if the message was successfully queued, False otherwise
        """
        try:
            # Extract conversation_id from payload
            conversation_id = payload.get("conversation_id")
            if not conversation_id:
                logger.error("Missing conversation_id in message payload")
                return False
                
            # Create a message ID
            import uuid as uuid_module
            message_id = uuid_module.uuid4()
            
            # Create router message
            from app.interfaces.router import RouterMessage, MessageDirection, MessageType, MessageSource, MessagePriority
            from datetime import datetime
            
            # For now, assume a mapping from string type to enum values
            # This could be more sophisticated in the future
            msg_type = MessageType.TEXT
            if message_type == "text":
                msg_type = MessageType.TEXT
            elif message_type == "action":
                msg_type = MessageType.ACTION
            elif message_type == "system":
                msg_type = MessageType.SYSTEM
                
            # Convert priority int to enum
            msg_priority = MessagePriority.NORMAL
            if priority == 1:
                msg_priority = MessagePriority.LOW
            elif priority == 2:
                msg_priority = MessagePriority.NORMAL
            elif priority == 3:
                msg_priority = MessagePriority.HIGH
            elif priority == 4:
                msg_priority = MessagePriority.URGENT
                
            # Ensure we have a valid workspace_id
            workspace_id = payload.get("workspace_id")
            if not workspace_id:
                logger.error("Missing workspace_id in message payload")
                return False
                
            # Convert to UUID if it's a string
            if isinstance(workspace_id, str):
                try:
                    workspace_id = uuid_module.UUID(workspace_id)
                except ValueError:
                    logger.error(f"Invalid workspace_id: {workspace_id}")
                    return False
            elif not isinstance(workspace_id, uuid_module.UUID):
                logger.error(f"workspace_id must be a UUID or string, got {type(workspace_id)}")
                return False
                
            # Same for conversation_id
            if isinstance(conversation_id, str):
                try:
                    conversation_id = uuid_module.UUID(conversation_id)
                except ValueError:
                    logger.error(f"Invalid conversation_id: {conversation_id}")
                    return False
            elif not isinstance(conversation_id, uuid_module.UUID):
                logger.error(f"conversation_id must be a UUID or string, got {type(conversation_id)}")
                return False
                
            router_message = RouterMessage(
                id=message_id,
                timestamp=datetime.now(),
                conversation_id=conversation_id,
                workspace_id=workspace_id,
                direction=MessageDirection.INBOUND,
                type=msg_type,
                source=MessageSource.USER,
                content=payload.get("content", payload),
                metadata=payload.get("metadata", {}),
                priority=msg_priority
            )
            
            # Process the message
            return await self.process_message(router_message)
            
        except Exception as e:
            logger.error(f"Error routing message: {str(e)}")
            return False
    
    async def process_message(self, message: RouterMessage) -> bool:
        """
        Process a message through the router.
        
        Args:
            message: The message to process
            
        Returns:
            True if the message was successfully queued, False otherwise
        """
        try:
            # Update stats
            self._stats["messages_received"] += 1
            
            # Queue the message with its priority
            priority = 5 - message.priority.value  # Convert to inverse priority for queue (lower = higher priority)
            await self._queue.put((priority, message))
            
            # Start processing if not already running
            if not self._processing:
                self._start_processing()
                
            # Update queue stats
            queue_size = self._queue.qsize()
            if queue_size > self._stats["queue_max_size"]:
                self._stats["queue_max_size"] = queue_size
                
            # Publish event
            await self.event_system.publish(
                "router.message.queued",
                {
                    "message_id": str(message.id),
                    "priority": message.priority.value,
                    "queue_size": queue_size
                },
                "message_router"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error queueing message: {str(e)}")
            return False
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """
        Get the current status of the message queue.
        
        Returns:
            A dictionary containing queue statistics
        """
        queue_size = self._queue.qsize()
        uptime = time.time() - self._stats["start_time"]
        
        return {
            "queue_size": queue_size,
            "processing": self._processing,
            "messages_received": self._stats["messages_received"],
            "messages_processed": self._stats["messages_processed"],
            "messages_failed": self._stats["messages_failed"],
            "queue_max_size": self._stats["queue_max_size"],
            "uptime_seconds": uptime
        }
    
    async def shutdown(self) -> None:
        """
        Shut down the router and clean up resources.
        
        This method ensures that all queued messages are processed
        before completing, or handles them appropriately.
        """
        logger.info("Shutting down Message Router")
        
        # Complete processing of remaining messages
        remaining = self._queue.qsize()
        if remaining > 0:
            logger.info(f"Processing {remaining} remaining messages before shutdown")
            
            # Wait for the queue to empty with a timeout
            try:
                await asyncio.wait_for(self._queue.join(), timeout=30)
                logger.info("All messages processed successfully")
            except asyncio.TimeoutError:
                logger.warning("Timeout waiting for message queue to empty")
        
        # Cancel the processing task if it's running
        if self._handler_task and not self._handler_task.done():
            self._handler_task.cancel()
            try:
                await self._handler_task
            except asyncio.CancelledError:
                pass
            
        self._processing = False
        logger.info("Message Router shutdown complete")
    
    def register_handler(self, message_type: str, handler: Callable[[RouterMessage], Awaitable[bool]]) -> None:
        """
        Register a handler for a specific message type.
        
        Args:
            message_type: The type of message to handle
            handler: The handler function
        """
        self._handlers[message_type] = handler
        logger.info(f"Registered handler for message type: {message_type}")
    
    def _start_processing(self) -> None:
        """Start the message processing task."""
        if not self._processing:
            self._processing = True
            self._handler_task = asyncio.create_task(self._process_queue())
            logger.debug("Started message processing task")
    
    async def _process_queue(self) -> None:
        """
        Process messages from the queue.
        
        This method runs in a separate task and continuously processes
        messages from the queue until it's empty or the router is shut down.
        """
        try:
            while self._processing:
                # Get the next message from the queue
                try:
                    _, message = await self._queue.get()
                except asyncio.CancelledError:
                    logger.debug("Message processing task cancelled")
                    break
                
                try:
                    # Process the message
                    success = await self._handle_message(message)
                    
                    # Update stats
                    if success:
                        self._stats["messages_processed"] += 1
                    else:
                        self._stats["messages_failed"] += 1
                    
                    # Publish event
                    await self.event_system.publish(
                        "router.message.processed",
                        {
                            "message_id": str(message.id),
                            "success": success
                        },
                        "message_router"
                    )
                    
                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}")
                    self._stats["messages_failed"] += 1
                finally:
                    # Mark the message as done regardless of success/failure
                    self._queue.task_done()
                    
            logger.debug("Message processing complete")
            
        except asyncio.CancelledError:
            logger.debug("Message processing task cancelled")
        finally:
            self._processing = False
    
    async def _handle_message(self, message: RouterMessage) -> bool:
        """
        Handle a single message based on its type.
        
        Args:
            message: The message to handle
            
        Returns:
            True if the message was handled successfully, False otherwise
        """
        # Look for a specific handler for this message type
        handler = self._handlers.get(message.type.value)
        
        if handler:
            try:
                return await handler(message)
            except Exception as e:
                logger.error(f"Error in message handler for type {message.type}: {str(e)}")
                return False
        else:
            logger.warning(f"No handler registered for message type: {message.type}")
            return False


# Singleton instance
_router: Optional[MessageRouter] = None


def get_router(event_system: Optional[EventSystemInterface] = None) -> MessageRouter:
    """
    Get the singleton message router instance.
    
    Args:
        event_system: The event system to use (only required on first call)
        
    Returns:
        The message router instance
        
    Raises:
        ValueError: If event_system is not provided on first call
    """
    global _router
    
    if _router is None:
        if event_system is None:
            raise ValueError("event_system must be provided when initializing the router")
        _router = MessageRouter(event_system)
        
    return _router