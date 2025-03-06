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

# Setup logging
logger = logging.getLogger(__name__)

class MessageRouter:
    """
    Central router for messages within the Cortex Core.
    
    This class is responsible for:
    - Directing messages between different parts of the system
    - Determining which components should process each message
    - Allowing components to subscribe to specific event types
    - Maintaining message flow throughout the conversation lifecycle
    """
    
    def __init__(self):
        """Initialize the Message Router."""
        # Registered components
        # Key: component_id, Value: component instance
        self.components: Dict[str, Any] = {}
        
        # Event subscriptions
        # Key: event_type, Value: Dict[component_id, callback]
        self.subscriptions: Dict[str, Dict[str, Callable[..., Awaitable[None]]]] = {}
        
        # Event history for debugging
        # Key: event_id, Value: event details
        self.event_history: Dict[str, Dict[str, Any]] = {}
        
        # Maximum event history size
        self.max_history_size = 100
        
        # Message type handlers
        # Key: message_type, Value: callable
        self.message_type_handlers: Dict[str, Callable] = {}
        
        logger.info("MessageRouter initialized")
    
    def register_component(
        self,
        component_id: str,
        component: Any
    ) -> None:
        """
        Register a component with the router.
        
        Args:
            component_id: Unique identifier for the component
            component: Component instance
        """
        if component_id in self.components:
            logger.warning(f"Component {component_id} already registered, replacing")
        
        self.components[component_id] = component
        logger.debug(f"Registered component: {component_id}")
    
    def unregister_component(
        self,
        component_id: str
    ) -> bool:
        """
        Unregister a component from the router.
        
        Args:
            component_id: Component ID
            
        Returns:
            True if unregistered successfully
        """
        if component_id not in self.components:
            logger.warning(f"Component {component_id} not registered")
            return False
        
        # Remove component
        del self.components[component_id]
        
        # Remove subscriptions
        for event_type, subscriptions in list(self.subscriptions.items()):
            if component_id in subscriptions:
                del subscriptions[component_id]
                
                # Remove event type if empty
                if not subscriptions:
                    del self.subscriptions[event_type]
        
        logger.debug(f"Unregistered component: {component_id}")
        return True
    
    async def subscribe_to_event(
        self,
        component_id: str,
        event_type: str,
        callback: Callable[[Dict[str, Any]], Awaitable[None]]
    ) -> bool:
        """
        Subscribe a component to an event type.
        
        Args:
            component_id: Component ID
            event_type: Event type to subscribe to
            callback: Async callback function to be called when event occurs
            
        Returns:
            True if subscribed successfully
        """
        # Check if component is registered
        if component_id not in self.components:
            logger.warning(f"Component {component_id} not registered")
            return False
        
        # Create subscription dict for event type if needed
        if event_type not in self.subscriptions:
            self.subscriptions[event_type] = {}
        
        # Add subscription
        self.subscriptions[event_type][component_id] = callback
        
        logger.debug(f"Component {component_id} subscribed to event: {event_type}")
        return True
    
    async def unsubscribe_from_event(
        self,
        component_id: str,
        event_type: str
    ) -> bool:
        """
        Unsubscribe a component from an event type.
        
        Args:
            component_id: Component ID
            event_type: Event type to unsubscribe from
            
        Returns:
            True if unsubscribed successfully
        """
        # Check if event type exists
        if event_type not in self.subscriptions:
            logger.warning(f"No subscriptions for event type: {event_type}")
            return False
        
        # Check if component is subscribed
        if component_id not in self.subscriptions[event_type]:
            logger.warning(f"Component {component_id} not subscribed to event: {event_type}")
            return False
        
        # Remove subscription
        del self.subscriptions[event_type][component_id]
        
        # Remove event type if empty
        if not self.subscriptions[event_type]:
            del self.subscriptions[event_type]
        
        logger.debug(f"Component {component_id} unsubscribed from event: {event_type}")
        return True
    
    async def trigger_event(
        self,
        event_type: str,
        data: Dict[str, Any]
    ) -> str:
        """
        Trigger an event for all subscribed components.
        
        Args:
            event_type: Event type
            data: Event data
            
        Returns:
            Event ID
        """
        # Create event ID
        event_id = str(uuid.uuid4())
        
        # Create event
        event = {
            "id": event_id,
            "type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Add to history
        self.event_history[event_id] = event
        
        # Trim history if needed
        if len(self.event_history) > self.max_history_size:
            # Remove oldest events
            oldest_events = sorted(self.event_history.keys(), 
                                  key=lambda k: self.event_history[k]["timestamp"])[:len(self.event_history) - self.max_history_size]
            
            for event_id in oldest_events:
                del self.event_history[event_id]
        
        # Check if anyone is subscribed
        if event_type not in self.subscriptions:
            logger.debug(f"No subscribers for event: {event_type}")
            return event_id
        
        # Notify subscribers
        for component_id, callback in list(self.subscriptions[event_type].items()):
            try:
                # Call callback asynchronously
                asyncio.create_task(callback(data))
                
            except Exception as e:
                logger.error(f"Error notifying component {component_id} of event {event_type}: {str(e)}")
                logger.error(traceback.format_exc())
        
        logger.debug(f"Triggered event {event_type} with ID {event_id}")
        return event_id
    
    async def route_message(
        self,
        message_type: str,
        message: Dict[str, Any],
        sender_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Route a message to the appropriate component.
        
        Args:
            message_type: Type of message
            message: Message content
            sender_id: Optional ID of the sender component
            
        Returns:
            Response from the component
        """
        # Determine which component should handle this message
        handler = self._get_message_handler(message_type)
        
        if not handler:
            logger.warning(f"No handler found for message type: {message_type}")
            return {"error": f"No handler for message type: {message_type}"}
        
        try:
            # Get component
            component_id, method_name = handler
            
            # Check if component is registered
            if component_id not in self.components:
                logger.warning(f"Handler component not registered: {component_id}")
                return {"error": f"Handler component not registered: {component_id}"}
            
            component = self.components[component_id]
            
            # Check if component has method
            if not hasattr(component, method_name):
                logger.warning(f"Component {component_id} has no method: {method_name}")
                return {"error": f"Component has no method: {method_name}"}
            
            method = getattr(component, method_name)
            
            # Call method
            response = await method(message)
            
            logger.debug(f"Routed message {message_type} to {component_id}.{method_name}")
            
            return response
            
        except Exception as e:
            logger.error(f"Error routing message {message_type}: {str(e)}")
            logger.error(traceback.format_exc())
            return {"error": str(e)}
    
    def register_message_type_handler(
        self,
        message_type: str,
        handler: Callable
    ) -> None:
        """
        Register a handler for a specific message type.
        
        Args:
            message_type: Type of message
            handler: Callable function/method to handle the message
        """
        self.message_type_handlers[message_type] = handler
        logger.debug(f"Registered handler for message type: {message_type}")
    
    def _get_message_handler(
        self,
        message_type: str
    ) -> Optional[tuple[str, str]]:
        """
        Get the handler for a message type.
        
        Args:
            message_type: Type of message
            
        Returns:
            Tuple of (component_id, method_name) or None if no handler
        """
        # First check if we have a direct handler registered
        if message_type in self.message_type_handlers:
            # We don't return this directly as it doesn't follow the expected return format
            # Instead, this is used in other routing methods
            return None
        
        # This is a simple implementation
        # In a more complex system, this would use a more sophisticated routing mechanism
        
        # For now, use a simple mapping
        handlers = {
            # Conversation messages
            "user_message": ("conversation_handler", "handle_user_message"),
            "system_message": ("conversation_handler", "handle_system_message"),
            "assistant_message": ("conversation_handler", "handle_assistant_message"),
            
            # Memory operations
            "memory_store": ("memory_adapter", "store_memory"),
            "memory_retrieve": ("memory_adapter", "retrieve_memory"),
            
            # Tool operations
            "tool_execute": ("mcp_client", "execute_tool"),
            "tool_result": ("conversation_handler", "handle_tool_result"),
            
            # User operations
            "user_authenticate": ("user_manager", "authenticate_user"),
            "user_session": ("user_manager", "get_user_session"),
            
            # SSE operations
            "sse_connect": ("sse_manager", "create_connection"),
            "sse_disconnect": ("sse_manager", "remove_connection"),
        }
        
        return handlers.get(message_type)
    
    async def get_message_type_handler(
        self,
        message_type: str
    ) -> Optional[Callable]:
        """
        Get the registered handler for a message type.
        
        Args:
            message_type: Type of message
            
        Returns:
            Handler callable if registered
        """
        return self.message_type_handlers.get(message_type)
    
    async def route_user_message(
        self,
        db: Any,
        conversation_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """
        Route a user message.
        
        Args:
            db: Database session
            conversation_id: ID of the conversation
            content: Message content
            metadata: Optional metadata
            
        Returns:
            Created message object or None
        """
        try:
            # Import here to avoid circular imports
            from app.models.schemas import Message, MessageRole
            from app.db.models import Message as MessageDB
            
            # Create message
            message_db = MessageDB(
                conversation_id=conversation_id,
                role=MessageRole.USER.value,
                content=content,
                metadata=metadata or {},
                is_complete=True
            )
            
            db.add(message_db)
            db.commit()
            db.refresh(message_db)
            
            # Convert to schema
            message = message_db.to_schema()
            
            # Trigger event
            await self.trigger_event("message_created", {
                "conversation_id": conversation_id,
                "message": message.dict()
            })
            
            # Call handler if registered
            handler = self.message_type_handlers.get("user_message")
            
            if handler:
                return await handler(db, message)
            
            return message
            
        except Exception as e:
            logger.error(f"Error routing user message: {str(e)}")
            db.rollback()
            return None
    
    async def route_system_message(
        self,
        db: Any,
        conversation_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """
        Route a system message.
        
        Args:
            db: Database session
            conversation_id: ID of the conversation
            content: Message content
            metadata: Optional metadata
            
        Returns:
            Created message object or None
        """
        try:
            # Import here to avoid circular imports
            from app.models.schemas import Message, MessageRole
            from app.db.models import Message as MessageDB
            
            # Create message
            message_db = MessageDB(
                conversation_id=conversation_id,
                role=MessageRole.SYSTEM.value,
                content=content,
                metadata=metadata or {},
                is_complete=True
            )
            
            db.add(message_db)
            db.commit()
            db.refresh(message_db)
            
            # Convert to schema
            message = message_db.to_schema()
            
            # Trigger event
            await self.trigger_event("message_created", {
                "conversation_id": conversation_id,
                "message": message.dict()
            })
            
            return message
            
        except Exception as e:
            logger.error(f"Error routing system message: {str(e)}")
            db.rollback()
            return None
    
    async def route_tool_message(
        self,
        db: Any,
        conversation_id: str,
        tool_name: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """
        Route a tool message.
        
        Args:
            db: Database session
            conversation_id: ID of the conversation
            tool_name: Name of the tool
            content: Message content
            metadata: Optional metadata
            
        Returns:
            Created message object or None
        """
        try:
            # Import here to avoid circular imports
            from app.models.schemas import Message, MessageRole
            from app.db.models import Message as MessageDB
            
            # Create combined metadata
            combined_metadata = {"tool_name": tool_name}
            
            if metadata:
                combined_metadata.update(metadata)
                
            # Create message
            message_db = MessageDB(
                conversation_id=conversation_id,
                role=MessageRole.TOOL.value,
                content=content,
                metadata=combined_metadata,
                is_complete=True
            )
            
            db.add(message_db)
            db.commit()
            db.refresh(message_db)
            
            # Convert to schema
            message = message_db.to_schema()
            
            # Trigger event
            await self.trigger_event("message_created", {
                "conversation_id": conversation_id,
                "message": message.dict()
            })
            
            # Call handler if registered
            handler = self.message_type_handlers.get("tool_message")
            
            if handler:
                await handler(db, message)
            
            return message
            
        except Exception as e:
            logger.error(f"Error routing tool message: {str(e)}")
            db.rollback()
            return None
    
    async def update_message(
        self,
        db: Any,
        message_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Any]:
        """
        Update a message.
        
        Args:
            db: Database session
            message_id: ID of the message
            updates: Updates to apply
            
        Returns:
            Updated message object or None
        """
        try:
            # Import here to avoid circular imports
            from app.db.models import Message as MessageDB
            
            # Get message
            message_db = db.query(MessageDB).filter_by(id=message_id).first()
            
            if not message_db:
                logger.warning(f"Message {message_id} not found")
                return None
            
            # Apply updates
            for key, value in updates.items():
                if hasattr(message_db, key) and key != "id":
                    setattr(message_db, key, value)
            
            db.commit()
            db.refresh(message_db)
            
            # Convert to schema
            message = message_db.to_schema()
            
            # Trigger event
            await self.trigger_event("message_updated", {
                "conversation_id": message.conversation_id,
                "message": message.dict()
            })
            
            return message
            
        except Exception as e:
            logger.error(f"Error updating message: {str(e)}")
            db.rollback()
            return None
    
    async def get_messages(
        self,
        db: Any,
        conversation_id: str,
        limit: int = 50,
        offset: int = 0,
        before_id: Optional[str] = None,
        after_id: Optional[str] = None
    ) -> tuple[List[Any], int]:
        """
        Get messages for a conversation.
        
        Args:
            db: Database session
            conversation_id: ID of the conversation
            limit: Maximum number of messages
            offset: Offset for pagination
            before_id: Get messages before this ID
            after_id: Get messages after this ID
            
        Returns:
            Tuple of (messages, total_count)
        """
        try:
            # Import here to avoid circular imports
            from app.db.models import Message as MessageDB
            from sqlalchemy import desc
            
            # Build query
            query = db.query(MessageDB).filter_by(conversation_id=conversation_id)
            
            # Add filters
            if before_id:
                # Find the message
                before_message = db.query(MessageDB).filter_by(id=before_id).first()
                if before_message:
                    # Filter messages created before this one
                    query = query.filter(MessageDB.created_at < before_message.created_at)
            
            if after_id:
                # Find the message
                after_message = db.query(MessageDB).filter_by(id=after_id).first()
                if after_message:
                    # Filter messages created after this one
                    query = query.filter(MessageDB.created_at > after_message.created_at)
            
            # Get total count
            total = query.count()
            
            # Get messages ordered by creation time
            messages = query.order_by(MessageDB.created_at).offset(offset).limit(limit).all()
            
            # Convert to schemas
            return [message.to_schema() for message in messages], total
            
        except Exception as e:
            logger.error(f"Error getting messages: {str(e)}")
            return [], 0
    
    async def get_component(
        self,
        component_id: str
    ) -> Optional[Any]:
        """
        Get a registered component.
        
        Args:
            component_id: Component ID
            
        Returns:
            Component if registered
        """
        return self.components.get(component_id)
    
    async def initialize(self) -> None:
        """
        Initialize the Message Router.
        
        This method is called during application startup.
        """
        try:
            # Reset internal state
            self.subscriptions.clear()
            self.event_history.clear()
            self.message_type_handlers.clear()
            
            # Register the router itself as a component
            self.register_component("message_router", self)
            
            logger.info("MessageRouter successfully initialized")
        except Exception as e:
            logger.error(f"Error initializing MessageRouter: {str(e)}")
            raise
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            # Clear data
            self.subscriptions.clear()
            self.event_history.clear()
            
            # Don't clear components - they might be needed for cleanup elsewhere
            
            logger.info("MessageRouter cleaned up")
            
        except Exception as e:
            logger.error(f"Error in cleanup: {str(e)}")

# Create a global instance for use throughout the application
message_router = MessageRouter()