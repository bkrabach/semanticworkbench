"""
Conversation Input Receiver and Output Publisher Implementations
"""

import logging
import uuid
from datetime import datetime, timezone

from app.interfaces.router import (
    InputReceiverInterface,
    OutputPublisherInterface,
    InputMessage,
    OutputMessage,
    ChannelType
)
from app.components.event_system import get_event_system
from app.components.cortex_router import get_router
from app.services.sse_service import get_sse_service


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

    async def receive_input(self, **kwargs) -> bool:
        """
        Receive a message from the conversation API using kwargs

        Args:
            **kwargs: Keyword arguments including:
                content: Message content
                user_id: User ID
                workspace_id: Workspace ID
                metadata: Additional metadata
                db: Database session

        Returns:
            Boolean indicating success
        """
        content = kwargs.get('content')
        user_id = kwargs.get('user_id')
        workspace_id = kwargs.get('workspace_id')
        metadata = kwargs.get('metadata', {})
        db = kwargs.get('db')

        # Format the message with safe content handling
        # If content is None, provide an empty string to avoid type errors
        safe_content = "" if content is None else str(content)

        message = InputMessage(
            message_id=str(uuid.uuid4()),
            channel_id=self.channel_id,
            channel_type=ChannelType.CONVERSATION,
            content=safe_content,
            user_id=user_id,
            workspace_id=workspace_id,
            conversation_id=self.conversation_id,
            timestamp=datetime.now(timezone.utc),
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
        self.subscriptions: list[str] = []

    async def _subscribe_to_events(self):
        """Subscribe to events for this channel"""
        from app.utils.logger import logger as main_logger

        main_logger.info(f"Setting up event subscriptions for conversation {self.conversation_id}")

        # Subscribe to the standard output event pattern - single clear path
        message_pattern = f"output.{ChannelType.CONVERSATION}.message"
        status_pattern = f"output.{ChannelType.CONVERSATION}.status"

        main_logger.info(f"Subscribing to patterns: {message_pattern}, {status_pattern}")

        # Add subscriptions and store subscription IDs
        message_sub_id = await self.event_system.subscribe(message_pattern, self._handle_message_event)
        status_sub_id = await self.event_system.subscribe(status_pattern, self._handle_status_event)

        # Add to our tracking list
        self.subscriptions.extend([message_sub_id, status_sub_id])

        # Check what subscribers the event system knows about
        subscribers = await self.event_system.get_subscribers(message_pattern)
        main_logger.info(f"Current subscribers for {message_pattern}: {len(subscribers)}")

        main_logger.info(f"Successfully subscribed to events for conversation {self.conversation_id}")

    async def _handle_message_event(self, event_type: str, payload):
        """
        Handle a message event - simplified for reliability

        Args:
            event_type: Type of the event
            payload: Event payload with full event data
        """
        from app.utils.logger import logger as main_logger

        main_logger.info(f"Conversation Publisher received event: {event_type} from {payload.source}")

        # Extract the output message from the event data
        data = payload.data.get("message")
        if not data or not isinstance(data, OutputMessage):
            main_logger.warning(f"Invalid message data in event payload: {payload.data}")
            return

        main_logger.info(f"Message in event: ID={data.message_id}, content={data.content}")

        # Simple, direct match on conversation_id - keeping the path clear and reliable
        if data.conversation_id:
            # Normalize both for comparison
            normalized_target = str(data.conversation_id).lower()
            normalized_ours = str(self.conversation_id).lower()

            if normalized_target != normalized_ours:
                main_logger.info(f"Skipping message for different conversation: expected={self.conversation_id}, actual={data.conversation_id}")
                return

        # Additional safety check - channel ID should also match
        if data.channel_id != self.channel_id:
            main_logger.warning(f"Channel ID mismatch: expected={self.channel_id}, actual={data.channel_id}")
            return

        main_logger.info(f"Handling message event for conversation {self.conversation_id}")

        # Publish the message - this is the most crucial step
        success = await self.publish(data)
        if success:
            main_logger.info(f"Successfully published message {data.message_id} to conversation {self.conversation_id}")
        else:
            main_logger.error(f"Failed to publish message {data.message_id} to conversation {self.conversation_id}")

            # Log detailed error info
            main_logger.error(f"Message failure details: channel={data.channel_type}/{data.channel_id}, conversation={data.conversation_id}")
            main_logger.error(f"This publisher: channel_id={self.channel_id}, conversation={self.conversation_id}")

    async def _handle_status_event(self, event_type: str, payload):
        """
        Handle a status event

        Args:
            event_type: Type of the event
            payload: Event payload with full event data
        """
        # Extract the output message from the event data
        data = payload.data.get("message")
        if not data or not isinstance(data, OutputMessage):
            return

        # Only handle messages for this channel
        if data.channel_id != self.channel_id:
            return

        self.logger.info(f"Received status event for conversation {self.conversation_id}")

        # Send status update using the new SSE service
        sse_service = get_sse_service()
        await sse_service.connection_manager.send_event(
            "conversation",
            self.conversation_id,
            "status_update",
            {
                "message": data.content,
                "timestamp": data.timestamp.isoformat(),
                "metadata": data.metadata
            },
            republish=True  # Enable republishing for better delivery
        )

    async def publish(self, message: OutputMessage) -> bool:
        """
        Publish a message to the conversation

        Args:
            message: The message to publish

        Returns:
            Boolean indicating success
        """
        from app.utils.logger import logger as main_logger

        main_logger.info(f"Publishing message to conversation {self.conversation_id}")
        main_logger.info(f"Message ID: {message.message_id}, content: {message.content}")

        try:
            # Get the SSE service
            sse_service = get_sse_service()

            # Prepare event data
            event_data = {
                "id": message.message_id,
                "content": message.content,
                "role": "assistant",  # Hardcoded for now
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "metadata": message.metadata or {},
                "conversation_id": self.conversation_id
            }

            # Log active connections for this conversation
            connection_manager = sse_service.connection_manager
            if hasattr(connection_manager, 'connections') and 'conversation' in connection_manager.connections:
                if self.conversation_id in connection_manager.connections['conversation']:
                    conn_count = len(connection_manager.connections['conversation'][self.conversation_id])
                    main_logger.info(f"Found {conn_count} active connections for conversation/{self.conversation_id}")
                else:
                    main_logger.warning(f"No active connections found for conversation/{self.conversation_id}")

            # This is the single path for sending messages to clients
            # The SSE connection manager is responsible for delivering to all connected clients
            await sse_service.connection_manager.send_event(
                "conversation",
                self.conversation_id,
                "message_received",
                event_data,
                republish=False  # No republishing - keep the path simple
            )

            main_logger.info(f"Message published successfully: {message.message_id}")

            return True

        except Exception as e:
            main_logger.error(f"Error publishing message: {e}")
            import traceback
            main_logger.error(f"Publishing error details: {traceback.format_exc()}")
            return False

    # Message persistence is now handled by the router before events are published
    # This eliminates duplicated persistence logic and dependency issues

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
            publisher = ConversationOutputPublisher(conversation_id)
            self.publishers[conversation_id] = publisher
            # Initialize its subscriptions
            await publisher._subscribe_to_events()
            self.logger.info(f"Created new output publisher for conversation {conversation_id}")

        # Explicitly cast to ensure type checking passes
        result: ConversationOutputPublisher = self.publishers[conversation_id]
        return result


# Global registry instance
publisher_registry = OutputPublisherRegistry()

async def get_conversation_publisher(conversation_id: str) -> ConversationOutputPublisher:
    """Get or create a conversation output publisher"""
    publisher = await publisher_registry.get_conversation_publisher(conversation_id)
    # The registry already ensures the return value is typed correctly
    return publisher