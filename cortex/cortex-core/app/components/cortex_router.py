"""
Cortex Router Implementation
Core component for processing inputs and routing messages
"""

import asyncio
import uuid
import logging
from datetime import datetime, timezone

from app.interfaces.router import (
    RouterInterface,
    InputMessage,
    RoutingDecision,
    ActionType
)
from app.components.event_system import get_event_system
from app.services.sse_service import get_sse_service


class CortexRouter(RouterInterface):
    """
    Implementation of the Cortex Router

    The Router processes input messages, makes routing decisions,
    and optionally sends messages to output channels. It maintains
    a queue of messages and processes them asynchronously.
    """

    def __init__(self):
        """Initialize the router"""
        self.event_system = get_event_system()
        self.message_queue = asyncio.Queue()
        self.logger = logging.getLogger(__name__)
        self.running = True

        # Start async task to process messages
        self.processing_task = asyncio.create_task(self._process_messages())

    async def cleanup(self):
        """Cleanup resources when shutting down"""
        self.running = False

        # Cancel processing task
        if self.processing_task and not self.processing_task.done():
            self.processing_task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(self.processing_task), timeout=0.5)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

    async def process_input(self, message: InputMessage) -> bool:
        """
        Process an input message

        Args:
            message: The input message

        Returns:
            Boolean indicating message was successfully queued
        """
        try:
            # Queue the message for asynchronous processing
            await self.message_queue.put(message)
            self.logger.info(f"Queued message {message.message_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error queuing message: {e}")
            return False

    async def _process_messages(self):
        """Process messages from the queue asynchronously"""
        while self.running:
            try:
                # Get message from queue (with timeout for clean shutdown)
                message = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)

                # Process the message
                await self._handle_message(message)

                # Mark task as done
                self.message_queue.task_done()

            except asyncio.TimeoutError:
                # This is expected when the queue is empty
                pass
            except Exception as e:
                self.logger.error(f"Error processing message: {e}")

    async def _handle_message(self, message: InputMessage):
        """
        Process a message from the queue
        """
        try:
            # Make a routing decision
            decision = await self._make_routing_decision(message)

            # Handle the message based on the decision
            if decision.action_type == ActionType.RESPOND:
                await self._handle_respond_action(message, decision)
            elif decision.action_type == ActionType.PROCESS:
                await self._handle_process_action(message, decision)
            elif decision.action_type == ActionType.DELEGATE:
                await self._handle_delegate_action(message, decision)
            elif decision.action_type == ActionType.IGNORE:
                self.logger.info(f"Ignoring message {message.message_id}")
            else:
                self.logger.warning(f"Unknown action type {decision.action_type}")

        except Exception as e:
            self.logger.error(f"Error handling message {message.message_id}: {e}")

    async def _make_routing_decision(self, message: InputMessage) -> RoutingDecision:
        """
        Make a routing decision for a message

        Args:
            message: The input message

        Returns:
            A routing decision
        """
        # Simple decision logic - always respond to the same channel
        return RoutingDecision(
            action_type=ActionType.RESPOND,
            priority=3,
            target_channels=[message.channel_id],
            status_message="Processing your request...",
            reference_id=str(uuid.uuid4()),
            metadata={"timestamp": datetime.now(timezone.utc).isoformat()}
        )

    async def _handle_respond_action(self, message: InputMessage, decision: RoutingDecision):
        """
        Handle a 'respond' action

        Args:
            message: The input message
            decision: The routing decision
        """
        # Show typing indicator
        await self._send_typing_indicator(message.conversation_id, True)

        # Wait 5 seconds
        await asyncio.sleep(5)

        # Generate response
        response_content = f"ECHO: {message.content}"

        # Save to database and get message_id
        message_id = await self._save_message_to_database(
            message.conversation_id,
            response_content,
            "assistant",
            {"source": "cortex_router"}
        )

        # Turn off typing indicator
        await self._send_typing_indicator(message.conversation_id, False)

        # Send message to client
        await self._send_message_to_client(
            message.conversation_id,
            message_id,
            response_content,
            "assistant",
            {"source": "cortex_router"}
        )

    async def _handle_process_action(self, message: InputMessage, decision: RoutingDecision):
        """
        Handle a 'process' action

        Args:
            message: The input message
            decision: The routing decision
        """
        # Process actions would involve more complex logic
        # For now, we'll use the same flow as respond
        await self._handle_respond_action(message, decision)

    async def _handle_delegate_action(self, message: InputMessage, decision: RoutingDecision):
        """
        Handle a 'delegate' action

        Args:
            message: The input message
            decision: The routing decision
        """
        # Placeholder for delegation logic
        self.logger.info(f"Delegating message {message.message_id}")

    async def _send_typing_indicator(self, conversation_id: str, is_typing: bool):
        """Send typing indicator directly via SSE"""
        sse_service = get_sse_service()
        await sse_service.connection_manager.send_event(
            "conversation",
            conversation_id,
            "typing_indicator",
            {
                "conversation_id": conversation_id,
                "isTyping": is_typing,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            },
            republish=False
        )

    async def _save_message_to_database(self, conversation_id: str, content: str,
                                       role: str, metadata: dict) -> str:
        """Save message to database and return message_id"""
        try:
            from app.database.connection import db
            from app.database.repositories.conversation_repository import ConversationRepository

            with db.get_db() as db_session:
                repo = ConversationRepository(db_session)
                message = repo.add_message(
                    conversation_id=conversation_id,
                    content=content,
                    role=role,
                    metadata=metadata
                )

                return message.id if message and hasattr(message, 'id') else str(uuid.uuid4())

        except Exception as e:
            self.logger.error(f"Error saving message to database: {e}")
            return str(uuid.uuid4())

    async def _send_message_to_client(self, conversation_id: str, message_id: str,
                                     content: str, role: str, metadata: dict):
        """Send message directly to client via SSE"""
        sse_service = get_sse_service()
        await sse_service.connection_manager.send_event(
            "conversation",
            conversation_id,
            "message_received",
            {
                "id": message_id,
                "content": content,
                "role": role,
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "metadata": metadata,
                "conversation_id": conversation_id
            },
            republish=False
        )


# Global router instance
router = CortexRouter()

def get_router() -> RouterInterface:
    """Get the global router instance"""
    return router