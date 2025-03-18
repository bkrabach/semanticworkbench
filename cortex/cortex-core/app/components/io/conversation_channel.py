"""
Conversation channel implementations for the Cortex platform.

This module provides concrete implementations of input receivers and output publishers
for conversation-based communication channels.
"""

import uuid
from datetime import datetime

from app.components.io.io_manager import get_io_manager
from app.components.sse.manager import get_sse_manager
from app.interfaces.input_output import (
    InputReceiverInterface,
    OutputPublisherInterface,
    InputMessage,
    OutputMessage,
    ChannelType
)
from app.interfaces.router import RouterInterface, RouterMessage, MessageType, MessageSource, MessageDirection
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ConversationInputReceiver(InputReceiverInterface):
    """
    Input receiver for conversation messages.
    
    This class handles messages from conversation API endpoints and forwards them
    to the router for processing.
    """
    
    def __init__(self, router: RouterInterface):
        """
        Initialize the conversation input receiver.
        
        Args:
            router: The message router for processing inputs
        """
        self.router = router
        self.channel_id = "conversation_api"
        logger.info(f"Initialized conversation input receiver with channel ID: {self.channel_id}")
    
    async def receive_input(self, **kwargs) -> bool:
        """
        Process incoming conversation input and forward it to the router.
        
        Expected kwargs:
            conversation_id: The ID of the conversation
            workspace_id: The ID of the workspace
            user_id: The ID of the user sending the message
            content: The message content
            metadata: Optional message metadata
            
        Returns:
            True if the input was successfully processed, False otherwise
        """
        try:
            # Extract arguments from kwargs
            conversation_id = kwargs.get("conversation_id")
            workspace_id = kwargs.get("workspace_id")
            user_id = kwargs.get("user_id")
            content = kwargs.get("content")
            metadata = kwargs.get("metadata", {})
            
            # Validate required arguments
            if not all([conversation_id, workspace_id, user_id, content]):
                logger.error("Missing required argument for conversation input")
                return False
            
            # Create input message
            message_id = uuid.uuid4()
            
            # Ensure we have proper UUID objects
            conversation_id_uuid = conversation_id if isinstance(conversation_id, uuid.UUID) else uuid.UUID(str(conversation_id))
            workspace_id_uuid = workspace_id if isinstance(workspace_id, uuid.UUID) else uuid.UUID(str(workspace_id))
            user_id_uuid = user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))
            
            input_message = InputMessage(
                id=message_id,
                channel_id=self.get_channel_id(),
                channel_type=self.get_channel_type(),
                content=content,
                user_id=user_id_uuid,
                workspace_id=workspace_id_uuid,
                conversation_id=conversation_id_uuid,
                metadata=metadata or {}
            )
            
            # Get I/O manager and send to router via I/O manager
            io_manager = get_io_manager()
            result = await io_manager.handle_input(input_message)
            
            # Create and process router message
            router_message = RouterMessage(
                id=message_id,
                timestamp=datetime.now(),
                conversation_id=conversation_id_uuid,
                workspace_id=workspace_id_uuid,
                direction=MessageDirection.INBOUND,
                type=MessageType.TEXT,
                source=MessageSource.USER,
                content=content,
                metadata=metadata or {}
            )
            
            # Process through router
            await self.router.process_message(router_message)
            
            logger.debug(f"Processed conversation input: {message_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing conversation input: {str(e)}")
            return False
    
    def get_channel_id(self) -> str:
        """
        Get the unique ID for this input channel.
        
        Returns:
            The channel ID
        """
        return self.channel_id
    
    def get_channel_type(self) -> ChannelType:
        """
        Get the type of this input channel.
        
        Returns:
            The channel type
        """
        return ChannelType.CONVERSATION


class ConversationOutputPublisher(OutputPublisherInterface):
    """
    Output publisher for conversation messages.
    
    This class handles delivering messages to clients via SSE.
    """
    
    def __init__(self, conversation_id: uuid.UUID):
        """
        Initialize the conversation output publisher.
        
        Args:
            conversation_id: The ID of the conversation this publisher is for
        """
        self.conversation_id = conversation_id
        self.channel_id = f"conversation_{conversation_id}"
        self.sse_manager = get_sse_manager()
        logger.info(f"Initialized conversation output publisher for conversation: {conversation_id}")
    
    async def publish(self, message: OutputMessage) -> bool:
        """
        Publish a message to this output channel.
        
        Args:
            message: The message to publish
            
        Returns:
            True if the message was successfully published, False otherwise
        """
        try:
            # Verify the message is for this conversation
            if message.conversation_id != self.conversation_id:
                logger.warning(
                    f"Message conversation ID {message.conversation_id} does not match publisher conversation ID {self.conversation_id}"
                )
                return False
            
            # Prepare event data
            event_data = {
                "id": str(message.id),
                "conversation_id": str(message.conversation_id),
                "content": message.content,
                "metadata": message.metadata
            }
            
            # Add user ID if present
            if message.user_id:
                event_data["user_id"] = str(message.user_id)
            
            # Send event via SSE
            count = await self.sse_manager.send_event(
                resource_type="conversation",
                resource_id=str(message.conversation_id),
                event_type="message",
                data=event_data
            )
            
            if count > 0:
                logger.debug(f"Published message {message.id} to {count} clients")
                return True
            else:
                logger.debug(f"No active clients for conversation {message.conversation_id}")
                # Return True even if no clients are currently connected
                # The message was "published" successfully, just no one was listening
                return True
                
        except Exception as e:
            logger.error(f"Error publishing message: {str(e)}")
            return False
    
    def get_channel_id(self) -> str:
        """
        Get the unique ID for this output channel.
        
        Returns:
            The channel ID
        """
        return self.channel_id
    
    def get_channel_type(self) -> ChannelType:
        """
        Get the type of this output channel.
        
        Returns:
            The channel type
        """
        return ChannelType.CONVERSATION


# Factory functions to create channels

def create_conversation_input_receiver(router: RouterInterface) -> ConversationInputReceiver:
    """
    Create a conversation input receiver.
    
    Args:
        router: The message router
        
    Returns:
        A configured conversation input receiver
    """
    return ConversationInputReceiver(router)


def create_conversation_output_publisher(conversation_id: uuid.UUID) -> ConversationOutputPublisher:
    """
    Create a conversation output publisher.
    
    Args:
        conversation_id: The ID of the conversation
        
    Returns:
        A configured conversation output publisher
    """
    return ConversationOutputPublisher(conversation_id)