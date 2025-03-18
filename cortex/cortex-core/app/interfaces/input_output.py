"""
Input/Output Interfaces for Cortex Core.

This module defines the interfaces for input receivers and output publishers,
which are responsible for handling messages from and to external channels.
"""

from typing import Dict, Any, Protocol, Optional
from enum import Enum
from uuid import UUID

from pydantic import BaseModel


class ChannelType(str, Enum):
    """Types of input/output channels."""
    
    CONVERSATION = "conversation"  # Text-based conversation
    VOICE = "voice"                # Voice interaction
    WEBHOOK = "webhook"            # External webhook
    API = "api"                    # API endpoint
    NOTIFICATION = "notification"  # System notification
    CUSTOM = "custom"              # Custom channel type


class InputMessage(BaseModel):
    """Message received from an input channel."""
    
    id: UUID
    channel_id: str
    channel_type: ChannelType
    content: Any
    user_id: Optional[UUID] = None
    workspace_id: UUID
    conversation_id: UUID
    metadata: Dict[str, Any] = {}


class OutputMessage(BaseModel):
    """Message to be sent to an output channel."""
    
    id: UUID
    channel_id: str
    channel_type: ChannelType
    content: Any
    user_id: Optional[UUID] = None
    workspace_id: UUID
    conversation_id: UUID
    reference_message_id: Optional[UUID] = None
    metadata: Dict[str, Any] = {}


class InputReceiverInterface(Protocol):
    """
    Interface for components that receive inputs from external sources.
    
    Input Receivers are responsible for accepting inputs from specific channels,
    converting them to InputMessages, and forwarding them to the Router.
    """
    
    async def receive_input(self, **kwargs) -> bool:
        """
        Process incoming input and forward it to the Router.
        
        Each implementation will have its own specific parameters.
        
        Returns:
            True if the input was successfully processed, False otherwise
        """
        ...
    
    def get_channel_id(self) -> str:
        """
        Get the unique ID for this input channel.
        
        Returns:
            The channel ID
        """
        ...
    
    def get_channel_type(self) -> ChannelType:
        """
        Get the type of this input channel.
        
        Returns:
            The channel type
        """
        ...


class OutputPublisherInterface(Protocol):
    """
    Interface for components that send outputs to external destinations.
    
    Output Publishers maintain connections to client channels and are responsible
    for formatting and delivering messages.
    """
    
    async def publish(self, message: OutputMessage) -> bool:
        """
        Publish a message to this output channel.
        
        Args:
            message: The message to publish
            
        Returns:
            True if the message was successfully published, False otherwise
        """
        ...
    
    def get_channel_id(self) -> str:
        """
        Get the unique ID for this output channel.
        
        Returns:
            The channel ID
        """
        ...
    
    def get_channel_type(self) -> ChannelType:
        """
        Get the type of this output channel.
        
        Returns:
            The channel type
        """
        ...