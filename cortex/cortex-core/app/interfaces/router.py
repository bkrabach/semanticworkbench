"""
Cortex Architecture Core Interfaces
Defines the core interfaces for the Cortex system's messaging architecture
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Protocol, Tuple, Callable, TYPE_CHECKING
from enum import Enum
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

if TYPE_CHECKING:
    from app.components.event_system import EventPayload


# ===== Channel Types =====

class ChannelType(str, Enum):
    """Types of input/output channels"""
    CONVERSATION = "conversation"  # Text chat
    VOICE = "voice"                # Voice interaction
    CANVAS = "canvas"              # Visual workspace
    APP = "app"                    # Application UI
    WEBHOOK = "webhook"            # External webhook
    API = "api"                    # API endpoint
    EMAIL = "email"                # Email communication
    SMS = "sms"                    # SMS/text messages
    NOTIFICATION = "notification"  # System notifications
    CLI = "cli"                    # Command line interface
    CUSTOM = "custom"              # Custom channel type


# ===== Message Models =====

class CortexMessage(BaseModel):
    """Base message model for all Cortex messages"""
    
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class InputMessage(CortexMessage):
    """Message received from an input channel"""
    
    # Source identification
    channel_id: str
    channel_type: ChannelType
    
    # Content
    content: str
    
    # Context
    user_id: Optional[str] = None
    workspace_id: Optional[str] = None
    conversation_id: Optional[str] = None
    

class OutputMessage(CortexMessage):
    """Message to be sent to an output channel"""
    
    # Destination
    channel_id: str
    channel_type: ChannelType
    
    # Content
    content: str
    
    # Relationship
    reference_message_id: Optional[str] = None  # ID of a message this is responding to
    context_ids: List[str] = Field(default_factory=list)  # Related context IDs (conversation, workspace, etc.)


# ===== Core Interfaces =====

class InputReceiverInterface(Protocol):
    """
    Interface for components that receive inputs from external sources
    
    Input Receivers are responsible for accepting inputs from specific
    modalities, packaging them into InputMessages, and forwarding them
    to the Router. They have no knowledge of how or when responses will
    be generated.
    """
    
    async def receive_input(self, **kwargs) -> bool:
        """
        Process incoming input and forward it to the Router
        
        Each implementation will have its own specific parameters,
        but all should return a boolean indicating success.
        """
        ...
    
    def get_channel_id(self) -> str:
        """Get the unique ID for this input channel"""
        ...
    
    def get_channel_type(self) -> ChannelType:
        """Get the type of this input channel"""
        ...


class OutputPublisherInterface(Protocol):
    """
    Interface for components that send outputs to external destinations
    
    Output Publishers maintain connections to client channels and are
    responsible for formatting and delivering messages. They register
    with the EventSystem to receive messages targeted at their channel.
    """
    
    async def publish(self, message: OutputMessage) -> bool:
        """
        Publish a message to this output channel
        
        Args:
            message: The message to publish
            
        Returns:
            Boolean indicating success
        """
        ...
    
    def get_channel_id(self) -> str:
        """Get the unique ID for this output channel"""
        ...
    
    def get_channel_type(self) -> ChannelType:
        """Get the type of this output channel"""
        ...


class EventCallback(Protocol):
    """Callback protocol for event system subscribers"""
    
    async def __call__(self, event_type: str, payload: EventPayload) -> None:
        """
        Handle an event
        
        Args:
            event_type: Type of the event
            payload: Event payload with full event data
        """
        ...


class EventSystemInterface(Protocol):
    """
    Interface for the event system that connects components
    
    The Event System acts as a message bus that allows components
    to communicate without direct coupling. It supports publishing
    events and subscribing to event types.
    """
    
    async def publish(self, event_type: str, data: Dict[str, Any], source: str,
                     trace_id: Optional[str] = None,
                     correlation_id: Optional[str] = None) -> None:
        """
        Publish an event to all subscribers
        
        Args:
            event_type: Type of the event (e.g., 'conversation.message.created')
            data: Event data
            source: Component that generated the event
            trace_id: Optional ID for tracing event chains
            correlation_id: Optional ID to correlate related events
        """
        ...
    
    async def subscribe(self, event_pattern: str, callback: EventCallback) -> str:
        """
        Subscribe to events matching a pattern
        
        Args:
            event_pattern: Pattern to match event types (can use wildcards)
            callback: Async function to call when matching events occur
            
        Returns:
            Subscription ID that can be used to unsubscribe
        """
        ...
    
    async def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe from events
        
        Args:
            subscription_id: ID returned from subscribe
            
        Returns:
            Boolean indicating success
        """
        ...
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about event processing
        
        Returns:
            Dictionary with event statistics
        """
        ...


class RouterInterface(Protocol):
    """
    Interface for the Cortex Router
    
    The Router is responsible for processing inputs, making routing
    decisions, and optionally producing outputs. It has complete
    autonomy over how and when to respond to inputs.
    """
    
    async def process_input(self, message: InputMessage) -> bool:
        """
        Process an input message
        
        The router receives the message for processing but makes no
        guarantees about if or when responses will be generated.
        
        Args:
            message: The input message
            
        Returns:
            Boolean indicating message was successfully received
        """
        ...


class RoutingDecision(BaseModel):
    """
    Represents a decision made by the Router about how to handle an input
    
    This is an internal model used by the Router to track its decisions.
    """
    
    # Core decision info
    action_type: str = "process"  # "respond", "process", "delegate", "ignore", etc.
    priority: int = 3             # 1 (lowest) to 5 (highest)
    
    # Destinations
    target_channels: List[str] = Field(default_factory=list)  # Channel IDs
    
    # Processing info
    status_message: Optional[str] = None  # Message to show while processing
    reference_id: Optional[str] = None    # ID for tracking
    metadata: Dict[str, Any] = Field(default_factory=dict)