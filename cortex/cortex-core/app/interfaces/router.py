"""
Router Interface for Cortex Core.

This module defines the interface for the message router, which is responsible for
processing input messages and routing them to the appropriate handlers. The router
provides a queue-based processing system for messages.
"""

from typing import Dict, Any, Protocol
from enum import Enum
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class MessagePriority(int, Enum):
    """Priority levels for messages."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class MessageDirection(str, Enum):
    """Direction of a message."""
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    INTERNAL = "internal"


class MessageType(str, Enum):
    """Types of messages."""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    ACTION = "action"
    SYSTEM = "system"


class MessageSource(str, Enum):
    """Sources of messages."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    DOMAIN_EXPERT = "domain_expert"


class RouterMessage(BaseModel):
    """Base message model for router."""
    
    id: UUID
    timestamp: datetime
    conversation_id: UUID
    workspace_id: UUID
    direction: MessageDirection
    type: MessageType
    source: MessageSource
    content: Any
    metadata: Dict[str, Any] = {}
    priority: MessagePriority = MessagePriority.NORMAL


class RouterInterface(Protocol):
    """
    Interface for the message router.
    
    The router is responsible for processing input messages, making routing decisions,
    and dispatching the messages to the appropriate handlers.
    """
    
    async def process_message(self, message: RouterMessage) -> bool:
        """
        Process a message through the router.
        
        Args:
            message: The message to process
            
        Returns:
            True if the message was successfully queued, False otherwise
        """
        ...
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """
        Get the current status of the message queue.
        
        Returns:
            A dictionary containing queue statistics
        """
        ...
    
    async def shutdown(self) -> None:
        """
        Shut down the router and clean up resources.
        
        This method should ensure that all queued messages are processed
        before completing, or handle them appropriately.
        """
        ...