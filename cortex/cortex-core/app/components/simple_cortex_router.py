"""
Simple Cortex Router Implementation
A basic implementation of the Cortex Router interface that decouples inputs from outputs
"""

from typing import Dict, List, Optional, Any, Tuple, Set
import uuid
import json
import asyncio
import threading
from queue import Queue
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.utils.logger import logger
from app.interfaces.router import (
    RouterInterface, 
    RoutingDecision,
    InputMessage,
    ChannelType
)

# Define channel classes for this implementation
class InputChannel:
    def __init__(self, channel_id: str, channel_type: ChannelType, metadata=None):
        self.channel_id = channel_id
        self.channel_type = channel_type
        self.metadata = metadata or {}

class OutputChannel:
    def __init__(self, channel_id: str, channel_type: ChannelType, metadata=None):
        self.channel_id = channel_id
        self.channel_type = channel_type
        self.metadata = metadata or {}
from app.api.sse import send_event_to_conversation
from app.database.models import Conversation


class SimpleCortexRouter(RouterInterface):
    """
    Simple implementation of the Cortex Router
    
    This is a placeholder implementation that decouples inputs from outputs.
    It processes messages asynchronously and can decide whether or not to respond.
    """
    
    def __init__(self):
        """Initialize the router with message queue and registered output channels"""
        # Message queue for asynchronous processing
        self.message_queue = Queue()
        
        # Thread to process messages asynchronously
        self.processing_thread = None
        self.running = False
        
        # Track registered output channels
        self.output_channels: Dict[str, OutputChannel] = {}
        
        # For demo: map conversation IDs to their output channels
        self.conversation_output_map: Dict[str, str] = {}
        
        # Start message processing thread
        self.start_processing_thread()
    
    def start_processing_thread(self):
        """Start the asynchronous message processing thread"""
        if self.processing_thread is None or not self.running:
            self.running = True
            self.processing_thread = threading.Thread(
                target=self._process_messages_thread,
                daemon=True
            )
            self.processing_thread.start()
            logger.info("Started message processing thread")
    
    def _process_messages_thread(self):
        """Background thread that processes messages from the queue"""
        while self.running:
            try:
                # Get message from queue with timeout
                message = self.message_queue.get(timeout=1.0)
                
                # Create asyncio event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Process the message
                loop.run_until_complete(self._process_message(message))
                
                # Mark task as done
                self.message_queue.task_done()
                
            except Exception as e:
                if not isinstance(e, asyncio.TimeoutError):
                    logger.error(f"Error processing message: {e}")
    
    async def process_input(self, message: InputMessage) -> bool:
        """
        Accept an input message for asynchronous processing
        
        Args:
            message: The incoming message
            
        Returns:
            True if message was queued successfully
        """
        logger.info(f"Accepting message from channel {message.channel_id} of type {message.channel_type}")
        
        try:
            # Map conversation ID to input channel ID for potential responses
            if message.conversation_id:
                self.conversation_output_map[message.conversation_id] = message.channel_id
            
            # Queue the message for asynchronous processing
            self.message_queue.put(message)
            return True
            
        except Exception as e:
            logger.error(f"Error queuing message: {e}")
            return False
    
    async def route(self, message: InputMessage) -> RoutingDecision:
        """
        Determine how to route an incoming message
        
        Args:
            message: The incoming message
            
        Returns:
            Routing decision
        """
        logger.info(f"Routing message from channel {message.channel_id}")
        
        # Generate a unique request ID for tracking
        request_id = str(uuid.uuid4())
        
        # For now, we just echo the input with a simple decision
        # In the future, this will be enhanced with LLM-based routing
        return RoutingDecision(
            action_type="respond",
            priority=3,
            status_message="Processing your request...",
            metadata={
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "input_length": len(message.content)
            }
        )
    
    async def send_to_output_channel(
        self, 
        channel: OutputChannel, 
        content: str, 
        metadata: Dict[str, Any] = {},
        reference_message_id: Optional[str] = None
    ) -> bool:
        """
        Send a message to an output channel
        
        Args:
            channel: The output channel to send to
            content: The content of the message
            metadata: Additional metadata for the message
            reference_message_id: Optional ID of the message this is in response to
            
        Returns:
            Boolean indicating if the message was successfully sent
        """
        logger.info(f"Sending message to channel {channel.channel_id} of type {channel.channel_type}")
        
        try:
            # Handle different channel types
            if channel.channel_type == ChannelType.CONVERSATION:
                # For conversation channels, use the SSE mechanism
                conversation_id = channel.metadata.get("conversation_id")
                if not conversation_id:
                    logger.error("No conversation_id in channel metadata")
                    return False
                
                # Send as a message
                message_id = str(uuid.uuid4())
                now = datetime.now(timezone.utc)
                
                await send_event_to_conversation(
                    conversation_id,
                    "message_received",
                    {
                        "id": message_id,
                        "content": content,
                        "role": "assistant",
                        "created_at_utc": now.isoformat(),
                        "metadata": {
                            "router_decision": metadata.get("action_type", "respond"),
                            "router_priority": metadata.get("priority", 3),
                            "reference_message_id": reference_message_id,
                            **metadata
                        }
                    }
                )
                
                # Also update the database if we have access
                if "db_session" in channel.metadata:
                    db = channel.metadata["db_session"]
                    conversation = db.query(Conversation).filter(
                        Conversation.id == conversation_id
                    ).first()
                    
                    if conversation:
                        # Parse entries
                        try:
                            entries = json.loads(conversation.entries)
                        except json.JSONDecodeError:
                            entries = []
                        
                        # Add new entry
                        entries.append({
                            "id": message_id,
                            "content": content,
                            "role": "assistant",
                            "created_at_utc": now,
                            "metadata": {
                                "router_decision": metadata.get("action_type", "respond"),
                                "router_priority": metadata.get("priority", 3),
                                "reference_message_id": reference_message_id,
                                **metadata
                            }
                        })
                        
                        # Update conversation
                        conversation.entries = json.dumps(entries, cls=DateTimeEncoder)
                        conversation.last_active_at_utc = now
                        db.commit()
                
                return True
                
            elif channel.channel_type == ChannelType.NOTIFICATION:
                # Send as a notification
                conversation_id = channel.metadata.get("conversation_id")
                if conversation_id:
                    await send_event_to_conversation(
                        conversation_id,
                        "notification",
                        {
                            "message": content,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "metadata": metadata
                        }
                    )
                return True
                
            else:
                # Other channel types would be implemented here
                logger.warning(f"Unimplemented output channel type: {channel.channel_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending to output channel: {e}")
            return False
    
    async def process_feedback(self, request_id: str, success: bool, metadata: Dict[str, Any]) -> None:
        """
        Process feedback about a previous routing decision
        
        Args:
            request_id: ID of the original request
            success: Whether the routing was successful
            metadata: Additional information about the result
        """
        logger.info(f"Received feedback for request {request_id}: success={success}")
        # In the future, this will be used for learning and improving routing decisions
    
    async def register_output_channel(self, channel: OutputChannel) -> bool:
        """
        Register a new output channel
        
        Args:
            channel: The output channel to register
            
        Returns:
            Boolean indicating if the channel was successfully registered
        """
        try:
            self.output_channels[channel.channel_id] = channel
            logger.info(f"Registered output channel {channel.channel_id} of type {channel.channel_type}")
            return True
        except Exception as e:
            logger.error(f"Error registering output channel: {e}")
            return False
            
    async def _process_message(self, message: InputMessage) -> None:
        """
        Process a message from the queue
        
        This is the main message processing logic that:
        1. Routes the message
        2. Determines if/how to respond
        3. Sends responses to appropriate output channels
        
        Args:
            message: The message to process
        """
        try:
            # First, route the message to determine what to do
            decision = await self.route(message)
            
            # Log the decision
            logger.info(f"Routing decision for message {message.message_id}: {decision.action_type}")
            
            # Here we could make more sophisticated decisions based on the message content
            # For now, we'll just echo messages back if the action_type is "respond"
            if decision.action_type == "respond":
                # Get or create an output channel for the response
                output_channel = self._get_output_channel_for_response(message)
                
                if output_channel:
                    # Wait based on priority (higher priority = less wait)
                    wait_time = self._get_wait_time(decision.priority)
                    await asyncio.sleep(wait_time)
                    
                    # For now, just echo the message
                    response_content = f"ECHO: {message.content}"
                    
                    # Send the response to the output channel
                    await self.send_to_output_channel(
                        channel=output_channel,
                        content=response_content,
                        metadata=decision.metadata,
                        reference_message_id=message.message_id
                    )
                    
                    # Send feedback to improve future routing
                    await self.process_feedback(
                        decision.metadata.get("request_id", "unknown"),
                        True,
                        {"response_length": len(response_content)}
                    )
                else:
                    logger.warning(f"No output channel available for message {message.message_id}")
            
            # For other action types, we might do different things
            # For example, "retrieve_memory" might involve querying a memory system
            # "delegate" might involve sending the message to a domain expert
            # "ignore" would mean we don't do anything
                
        except Exception as e:
            logger.error(f"Error processing message {message.message_id}: {e}")
            
    def _get_output_channel_for_response(self, message: InputMessage) -> Optional[OutputChannel]:
        """
        Get or create an appropriate output channel for responding to a message
        
        Args:
            message: The input message
            
        Returns:
            Output channel or None if no suitable channel is available
        """
        # For conversation messages, use a conversation output channel
        if message.conversation_id:
            # Check if we already have a registered channel for this conversation
            for channel_id, channel in self.output_channels.items():
                if (channel.channel_type == ChannelType.CONVERSATION and 
                    channel.metadata.get("conversation_id") == message.conversation_id):
                    return channel
            
            # Create a new conversation output channel
            channel_id = f"conversation-{message.conversation_id}"
            channel = OutputChannel(
                channel_id=channel_id,
                channel_type=ChannelType.CONVERSATION,
                metadata={
                    "conversation_id": message.conversation_id,
                    # We would normally get this from a DB connection pool
                    # For demo purposes, we'll add it if available in the input message
                    "db_session": message.metadata.get("db_session", None)
                }
            )
            
            # Register the channel
            self.output_channels[channel_id] = channel
            return channel
        
        # If we can't determine an output channel, return None
        return None
        
    def _get_wait_time(self, priority: int) -> float:
        """
        Get wait time based on priority level
        
        Args:
            priority: Priority level (1-5)
            
        Returns:
            Wait time in seconds
        """
        # Higher priority = less wait time
        return max(0.5, 6 - priority)  # 1-5 seconds based on priority (5-1)
        
    async def _send_typing_indicator(self, conversation_id: str, is_typing: bool) -> None:
        """
        Send typing indicator to the conversation
        
        Args:
            conversation_id: ID of the conversation
            is_typing: Whether typing is active
        """
        await send_event_to_conversation(
            conversation_id,
            "typing_indicator",
            {
                "isTyping": is_typing,
                "role": "assistant"
            }
        )
        logger.info(f"{'Started' if is_typing else 'Stopped'} typing indicator for conversation {conversation_id}")


# Custom JSON encoder for datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)