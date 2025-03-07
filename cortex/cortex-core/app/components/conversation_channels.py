"""
Conversation Input Receiver and Output Publisher Implementations
"""

import json
import logging
from typing import Dict, Any, Optional
from uuid import uuid4
from datetime import datetime

from app.interfaces.router import (
    InputReceiverInterface,
    OutputPublisherInterface,
    InputMessage,
    OutputMessage,
    ChannelType
)
from app.components.event_system import get_event_system
from app.components.cortex_router import get_router
from app.api.sse import send_event_to_conversation
from app.database.models import Conversation
from sqlalchemy.orm import Session


class ConversationInputReceiver(InputReceiverInterface):
    """
    Input receiver for conversation messages
    
    Receives messages from the conversation API and forwards them to the Router.
    """
    
    def __init__(self, conversation_id: str):
        """
        Initialize the input receiver
        
        Args:
            conversation_id: Conversation ID
        """
        self.conversation_id = conversation_id
        self.channel_id = f"conversation-{conversation_id}"
        self.logger = logging.getLogger(__name__)
    
    async def receive_input(
        self,
        content: str,
        user_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None
    ) -> bool:
        """
        Receive a message from the conversation API
        
        Args:
            content: Message content
            user_id: User ID
            workspace_id: Workspace ID
            metadata: Additional metadata
            db: Database session
            
        Returns:
            Boolean indicating success
        """
        # Format the message
        message = InputMessage(
            message_id=str(uuid4()),
            channel_id=self.channel_id,
            channel_type=ChannelType.CONVERSATION,
            content=content,
            user_id=user_id,
            workspace_id=workspace_id,
            conversation_id=self.conversation_id,
            timestamp=datetime.utcnow(),
            metadata=metadata or {}
        )
        
        # Add DB session to metadata for potential use by the router
        if db is not None:
            message.metadata["db_session"] = db
        
        # Pass to the router for processing
        router = get_router()
        success = await router.process_input(message)
        
        if success:
            self.logger.info(f"Forwarded message from conversation {self.conversation_id} to router")
        else:
            self.logger.error(f"Failed to forward message from conversation {self.conversation_id}")
            
        return success
    
    def get_channel_id(self) -> str:
        """Get the channel ID"""
        return self.channel_id
    
    def get_channel_type(self) -> ChannelType:
        """Get the channel type"""
        return ChannelType.CONVERSATION


class ConversationOutputPublisher(OutputPublisherInterface):
    """
    Output publisher for conversation messages
    
    Publishes messages to conversations via SSE.
    """
    
    def __init__(self, conversation_id: str):
        """
        Initialize the output publisher
        
        Args:
            conversation_id: Conversation ID
        """
        self.conversation_id = conversation_id
        self.channel_id = f"conversation-{conversation_id}"
        self.logger = logging.getLogger(__name__)
        
        # Get event system
        self.event_system = get_event_system()
        
        # We'll store subscription IDs for cleanup
        self.subscriptions = []
    
    async def _subscribe_to_events(self):
        """Subscribe to events for this channel"""
        # Subscribe to both message and status events
        message_pattern = f"output.{ChannelType.CONVERSATION}.message"
        status_pattern = f"output.{ChannelType.CONVERSATION}.status"
        
        # Add subscriptions and store subscription IDs
        message_sub_id = await self.event_system.subscribe(message_pattern, self._handle_message_event)
        status_sub_id = await self.event_system.subscribe(status_pattern, self._handle_status_event)
        
        self.subscriptions.extend([message_sub_id, status_sub_id])
        
        self.logger.info(f"Subscribed to events for conversation {self.conversation_id}")
    
    async def _handle_message_event(self, event_name: str, data: OutputMessage):
        """
        Handle a message event
        
        Args:
            event_name: Event name
            data: Output message
        """
        # Only handle messages for this channel
        if data.channel_id != self.channel_id:
            return
            
        self.logger.info(f"Received message event for conversation {self.conversation_id}")
        
        # Publish the message
        await self.publish(data)
    
    async def _handle_status_event(self, event_name: str, data: OutputMessage):
        """
        Handle a status event
        
        Args:
            event_name: Event name
            data: Output message
        """
        # Only handle messages for this channel
        if data.channel_id != self.channel_id:
            return
            
        self.logger.info(f"Received status event for conversation {self.conversation_id}")
        
        # Send status update
        await send_event_to_conversation(
            self.conversation_id,
            "status_update",
            {
                "message": data.content,
                "timestamp": data.timestamp.isoformat(),
                "metadata": data.metadata
            }
        )
    
    async def publish(self, message: OutputMessage) -> bool:
        """
        Publish a message to the conversation
        
        Args:
            message: The message to publish
            
        Returns:
            Boolean indicating success
        """
        try:
            # Send the message via SSE
            await send_event_to_conversation(
                self.conversation_id,
                "message_received",
                {
                    "id": message.message_id,
                    "content": message.content,
                    "role": "assistant",  # Hardcoded for now
                    "created_at_utc": message.timestamp.isoformat(),
                    "metadata": message.metadata
                }
            )
            
            self.logger.info(f"Published message {message.message_id} to conversation {self.conversation_id}")
            
            # Check if we have a DB session in metadata to persist the message
            db = message.metadata.get("db_session")
            if db:
                try:
                    await self._persist_message(message, db)
                except Exception as e:
                    self.logger.error(f"Error persisting message: {e}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error publishing message: {e}")
            return False
    
    async def _persist_message(self, message: OutputMessage, db: Session):
        """
        Persist a message to the database
        
        Args:
            message: The message to persist
            db: Database session
        """
        # Get the conversation
        conversation = db.query(Conversation).filter(
            Conversation.id == self.conversation_id
        ).first()
        
        if not conversation:
            self.logger.warning(f"Conversation {self.conversation_id} not found")
            return
            
        # Parse entries
        try:
            entries = json.loads(conversation.entries)
        except json.JSONDecodeError:
            entries = []
            
        # Add new entry
        entries.append({
            "id": message.message_id,
            "content": message.content,
            "role": "assistant",  # Hardcoded for now
            "created_at_utc": message.timestamp,
            "metadata": message.metadata
        })
        
        # Update conversation
        conversation.entries = json.dumps(entries, cls=DateTimeEncoder)
        conversation.last_active_at_utc = message.timestamp
        
        # Commit to DB
        db.commit()
        
        self.logger.info(f"Persisted message {message.message_id} to conversation {self.conversation_id}")
    
    def get_channel_id(self) -> str:
        """Get the channel ID"""
        return self.channel_id
    
    def get_channel_type(self) -> ChannelType:
        """Get the channel type"""
        return ChannelType.CONVERSATION
        
    async def cleanup(self):
        """Unsubscribe from events and clean up resources"""
        # Unsubscribe from all events
        for sub_id in self.subscriptions:
            try:
                await self.event_system.unsubscribe(sub_id)
            except Exception as e:
                self.logger.error(f"Error unsubscribing from event {sub_id}: {e}")
                
        self.subscriptions = []
        self.logger.info(f"Cleaned up publisher for conversation {self.conversation_id}")


# Custom JSON encoder for datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


# Global registry of output publishers
class OutputPublisherRegistry:
    """Registry for output publishers to avoid creating duplicates"""
    
    def __init__(self):
        """Initialize the registry"""
        self.publishers = {}
        self.logger = logging.getLogger(__name__)
        
    async def get_conversation_publisher(self, conversation_id: str) -> ConversationOutputPublisher:
        """
        Get or create a conversation output publisher
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Output publisher for the conversation
        """
        if conversation_id not in self.publishers:
            # Create a new publisher
            self.publishers[conversation_id] = ConversationOutputPublisher(conversation_id)
            # Initialize its subscriptions
            await self.publishers[conversation_id]._subscribe_to_events()
            self.logger.info(f"Created new output publisher for conversation {conversation_id}")
            
        return self.publishers[conversation_id]


# Global registry instance
publisher_registry = OutputPublisherRegistry()

async def get_conversation_publisher(conversation_id: str) -> ConversationOutputPublisher:
    """Get or create a conversation output publisher"""
    return await publisher_registry.get_conversation_publisher(conversation_id)