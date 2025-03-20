"""
Input/Output Manager implementation for Cortex platform.

This module provides implementations for the input and output interfaces, enabling
the separation of input and output channels in the Cortex architecture.
"""

import uuid
from typing import Dict, Any, List, Optional, Set, Callable, Awaitable

from app.interfaces.event_system import EventSystemInterface
from app.interfaces.input_output import (
    InputReceiverInterface, 
    OutputPublisherInterface,
    InputMessage,
    OutputMessage,
    ChannelType
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class IoManager:
    """
    Manager for input receivers and output publishers.
    
    This class provides a central point for registering and accessing
    input receivers and output publishers, allowing for flexible routing
    of messages between components.
    """
    
    def __init__(self, event_system: EventSystemInterface):
        """
        Initialize the I/O manager.
        
        Args:
            event_system: The event system for publishing I/O events
        """
        self.event_system = event_system
        self._input_receivers: Dict[str, InputReceiverInterface] = {}
        self._output_publishers: Dict[str, OutputPublisherInterface] = {}
        self._input_listeners: Dict[str, Set[Callable[[InputMessage], Awaitable[None]]]] = {}
        logger.info("I/O Manager initialized")
    
    def register_input_receiver(self, receiver: InputReceiverInterface) -> None:
        """
        Register an input receiver.
        
        Args:
            receiver: The input receiver to register
        """
        channel_id = receiver.get_channel_id()
        self._input_receivers[channel_id] = receiver
        logger.info(f"Registered input receiver for channel '{channel_id}' of type {receiver.get_channel_type()}")
    
    def register_output_publisher(self, publisher: OutputPublisherInterface) -> None:
        """
        Register an output publisher.
        
        Args:
            publisher: The output publisher to register
        """
        channel_id = publisher.get_channel_id()
        self._output_publishers[channel_id] = publisher
        logger.info(f"Registered output publisher for channel '{channel_id}' of type {publisher.get_channel_type()}")
    
    def unregister_input_receiver(self, channel_id: str) -> bool:
        """
        Unregister an input receiver.
        
        Args:
            channel_id: The ID of the input channel to unregister
            
        Returns:
            True if the channel was found and removed, False otherwise
        """
        if channel_id in self._input_receivers:
            del self._input_receivers[channel_id]
            logger.info(f"Unregistered input receiver for channel '{channel_id}'")
            return True
        return False
    
    def unregister_output_publisher(self, channel_id: str) -> bool:
        """
        Unregister an output publisher.
        
        Args:
            channel_id: The ID of the output channel to unregister
            
        Returns:
            True if the channel was found and removed, False otherwise
        """
        if channel_id in self._output_publishers:
            del self._output_publishers[channel_id]
            logger.info(f"Unregistered output publisher for channel '{channel_id}'")
            return True
        return False
    
    async def add_input_listener(
        self, 
        listener: Callable[[InputMessage], Awaitable[None]],
        channel_type: Optional[ChannelType] = None
    ) -> str:
        """
        Add a listener for input messages.
        
        Args:
            listener: The function to call when a message is received
            channel_type: Optional type of channel to listen to
            
        Returns:
            A unique listener ID that can be used to remove the listener
        """
        listener_id = str(uuid.uuid4())
        channel_key = channel_type.value if channel_type else "*"
        
        if channel_key not in self._input_listeners:
            self._input_listeners[channel_key] = set()
            
        self._input_listeners[channel_key].add(listener)
        logger.debug(f"Added input listener ({listener_id}) for channel type '{channel_key}'")
        
        # Subscribe to input events
        await self.event_system.subscribe(
            f"io.input.{channel_key}",
            lambda topic, data: self._handle_input_event(topic, data, listener)
        )
        
        return listener_id
    
    async def remove_input_listener(
        self, 
        listener: Callable[[InputMessage], Awaitable[None]],
        channel_type: Optional[ChannelType] = None
    ) -> bool:
        """
        Remove an input listener.
        
        Args:
            listener: The listener function to remove
            channel_type: Optional type of channel the listener is registered for
            
        Returns:
            True if the listener was found and removed, False otherwise
        """
        channel_key = channel_type.value if channel_type else "*"
        
        if channel_key in self._input_listeners and listener in self._input_listeners[channel_key]:
            self._input_listeners[channel_key].remove(listener)
            logger.debug(f"Removed input listener for channel type '{channel_key}'")
            
            # Clean up empty listener sets
            if not self._input_listeners[channel_key]:
                del self._input_listeners[channel_key]
                
            return True
        
        return False
    
    async def handle_input(self, message: InputMessage) -> bool:
        """
        Process an input message and notify listeners.
        
        Args:
            message: The input message to process
            
        Returns:
            True if the message was processed, False otherwise
        """
        try:
            # Publish event for all inputs
            await self.event_system.publish(
                "io.input.*",
                {"message": message.model_dump()},
                "io_manager"
            )
            
            # Publish event for specific channel type
            await self.event_system.publish(
                f"io.input.{message.channel_type}",
                {"message": message.model_dump()},
                "io_manager"
            )
            
            logger.debug(f"Processed input message from channel '{message.channel_id}'")
            return True
            
        except Exception as e:
            logger.error(f"Error handling input message: {str(e)}")
            return False
    
    async def send_output(self, message: OutputMessage) -> bool:
        """
        Send an output message to the appropriate publisher.
        
        Args:
            message: The output message to send
            
        Returns:
            True if the message was sent, False otherwise
        """
        try:
            # Get the publisher for this channel
            publisher = self._output_publishers.get(message.channel_id)
            
            if not publisher:
                logger.warning(f"No output publisher found for channel '{message.channel_id}'")
                return False
                
            # Send the message
            result = await publisher.publish(message)
            
            if result:
                # Publish event
                await self.event_system.publish(
                    "io.output.sent",
                    {
                        "message_id": str(message.id),
                        "channel_id": message.channel_id,
                        "channel_type": message.channel_type
                    },
                    "io_manager"
                )
                
                logger.debug(f"Sent output message to channel '{message.channel_id}'")
                
            return result
            
        except Exception as e:
            logger.error(f"Error sending output message: {str(e)}")
            return False
    
    async def broadcast_output(
        self, 
        channel_type: ChannelType, 
        content: Any,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[uuid.UUID] = None,
        workspace_id: Optional[uuid.UUID] = None,
        conversation_id: Optional[uuid.UUID] = None
    ) -> List[bool]:
        """
        Broadcast a message to all output publishers of a specific type.
        
        Args:
            channel_type: The type of channels to broadcast to
            content: The content to send
            metadata: Optional metadata for the message
            user_id: Optional user ID for the message
            workspace_id: Optional workspace ID for the message
            conversation_id: Optional conversation ID for the message
            
        Returns:
            A list of results for each publisher (True if sent successfully)
        """
        results = []
        
        # Find all publishers of this type
        for channel_id, publisher in self._output_publishers.items():
            if publisher.get_channel_type() == channel_type:
                # Create a message for this publisher
                message = OutputMessage(
                    id=uuid.uuid4(),
                    channel_id=channel_id,
                    channel_type=channel_type,
                    content=content,
                    user_id=user_id,
                    workspace_id=workspace_id if workspace_id else uuid.uuid4(),  # Required field
                    conversation_id=conversation_id if conversation_id else uuid.uuid4(),  # Required field
                    metadata=metadata or {}
                )
                
                # Send the message
                result = await self.send_output(message)
                results.append(result)
                
        return results
    
    async def _handle_input_event(
        self, 
        topic: str, 
        data: Dict[str, Any],
        listener: Callable[[InputMessage], Awaitable[None]]
    ) -> None:
        """
        Handle an input event and notify the listener.
        
        Args:
            topic: The event topic
            data: The event data
            listener: The listener to notify
        """
        try:
            # Extract the message from the event data
            message_data = data.get("message", {})
            message = InputMessage(**message_data)
            
            # Notify the listener
            await listener(message)
            
        except Exception as e:
            logger.error(f"Error in input listener: {str(e)}")


# Singleton instance
_io_manager: Optional[IoManager] = None


def get_io_manager(event_system: Optional[EventSystemInterface] = None) -> IoManager:
    """
    Get the singleton I/O manager instance.
    
    Args:
        event_system: The event system to use (only required on first call)
        
    Returns:
        The I/O manager instance
        
    Raises:
        ValueError: If event_system is not provided on first call
    """
    global _io_manager
    
    if _io_manager is None:
        if event_system is None:
            raise ValueError("event_system must be provided when initializing the I/O manager")
        _io_manager = IoManager(event_system)
        
    return _io_manager