"""
Cortex Router Implementation
Core component for processing inputs and routing messages
"""

import asyncio
import uuid
import logging
import threading
import queue
from datetime import datetime, timezone
from queue import Queue

from app.interfaces.router import (
    RouterInterface,
    InputMessage,
    OutputMessage,
    RoutingDecision,
    ChannelType,
    ActionType
)
from app.components.event_system import get_event_system


class CortexRouter(RouterInterface):
    """
    Implementation of the Cortex Router
    
    The Router processes input messages, makes routing decisions,
    and optionally sends messages to output channels. It maintains
    a queue of messages and processes them asynchronously.
    """
    
    def __init__(self):
        """Initialize the router"""
        # Get the event system
        self.event_system = get_event_system()
        
        # Setup message queue for processing
        self.message_queue = Queue()
        self.processing_thread = None
        self.running = False
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Start the processing thread
        self.start_processing_thread()
    
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
            self.message_queue.put(message)
            
            self.logger.info(
                f"Queued message {message.message_id} from channel {message.channel_id} "
                f"type {message.channel_type}"
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Error queuing message: {e}")
            return False
    
    def start_processing_thread(self):
        """Start the asynchronous message processing thread"""
        if self.processing_thread is None or not self.running:
            self.running = True
            self.processing_thread = threading.Thread(
                target=self._process_messages_thread,
                daemon=True
            )
            self.processing_thread.start()
            self.logger.info("Started message processing thread")
    
    def _process_messages_thread(self):
        """Background thread that processes messages from the queue"""
        while self.running:
            try:
                # Get message from queue with timeout
                try:
                    message = self.message_queue.get(timeout=1.0)
                except queue.Empty:
                    # No messages to process
                    continue
                
                # Create asyncio event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Process the message
                loop.run_until_complete(self._handle_message(message))
                
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
        
        This is the main method that handles all message processing.
        """
        try:
            # Log the message
            self.logger.info(f"Processing message: {message.message_id}")
            
            # Make a routing decision
            decision = await self._make_routing_decision(message)
            
            # Log the decision
            self.logger.info(
                f"Routing decision for message {message.message_id}: {decision.action_type} "
                f"priority {decision.priority}"
            )
            
            # Send a status message if one is provided
            if decision.status_message:
                await self._send_status_message(message, decision)
            
            # Handle the message based on the decision
            if decision.action_type == ActionType.RESPOND:
                # For now, we'll just echo the message
                await self._handle_respond_action(message, decision)
                
            elif decision.action_type == ActionType.PROCESS:
                # This would involve more complex processing, potentially
                # across multiple systems before generating a response
                await self._handle_process_action(message, decision)
                
            elif decision.action_type == ActionType.DELEGATE:
                # This would forward the message to another system
                await self._handle_delegate_action(message, decision)
                
            elif decision.action_type == ActionType.IGNORE:
                # Do nothing
                self.logger.info(f"Ignoring message {message.message_id}")
                
            else:
                # Unknown action type
                self.logger.warning(
                    f"Unknown action type {decision.action_type} "
                    f"for message {message.message_id}"
                )
                
        except Exception as e:
            self.logger.error(f"Error handling message {message.message_id}: {e}")
    
    async def _make_routing_decision(self, message: InputMessage) -> RoutingDecision:
        """
        Make a routing decision for a message
        
        This is a placeholder implementation that returns a basic decision.
        In a real implementation, this would involve more sophisticated logic,
        potentially including ML models.
        
        Args:
            message: The input message
            
        Returns:
            A routing decision
        """
        # Generate a unique reference ID
        reference_id = str(uuid.uuid4())
        
        # For now, always decide to respond to the same channel
        # In a real implementation, this would be more sophisticated
        
        # Check if this is a special echo request
        if message.metadata and message.metadata.get('is_echo_request'):
            # Use RESPOND for echo requests
            action = ActionType.RESPOND
        else:
            # Use RESPOND by default
            action = ActionType.RESPOND
        
        decision = RoutingDecision(
            action_type=action,
            priority=3,
            target_channels=[message.channel_id],
            status_message="Processing your request...",
            reference_id=reference_id,
            metadata={
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "input_length": len(message.content)
            }
        )
        
        return decision
    
    async def _send_status_message(self, message: InputMessage, decision: RoutingDecision):
        """
        Send a status message to indicate processing is happening
        
        Args:
            message: The input message
            decision: The routing decision
        """
        # Only send status if we have a message
        if not decision.status_message:
            return
            
        # Create a status message
        status_message = OutputMessage(
            channel_id=message.channel_id,
            channel_type=message.channel_type,
            content=decision.status_message,
            reference_message_id=message.message_id,
            context_ids=[message.conversation_id] if message.conversation_id else [],
            metadata={
                "message_type": "status",
                "priority": decision.priority,
                "reference_id": decision.reference_id
            }
        )
        
        # Send via the event system
        event_name = f"output.{message.channel_type}.status"
        await self.event_system.publish(
            event_type=event_name, 
            data={"message": status_message}, 
            source="cortex_router"
        )
    
    async def _handle_respond_action(self, message: InputMessage, decision: RoutingDecision):
        """
        Handle a 'respond' action
        
        This simply returns a response to the input channel.
        
        Args:
            message: The input message
            decision: The routing decision
        """
        # Send typing indicator first
        if message.channel_type == ChannelType.CONVERSATION and message.conversation_id:
            from app.services.sse_service import get_sse_service
            sse_service = get_sse_service()
            
            # Ensure typing indicator stays visible for a moment
            await sse_service.connection_manager.send_event(
                "conversation",
                message.conversation_id,
                "typing",
                {
                    "conversation_id": message.conversation_id,
                    "active": True,
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                },
                republish=True
            )
        
        # For demo, sleep based on priority 
        wait_time = max(2.0, 6 - decision.priority)  # Increased minimum to 2 seconds
        self.logger.info(f"Waiting {wait_time} seconds before sending response via router")
        await asyncio.sleep(wait_time)
        
        # Generate response - use predefined echo content if available 
        echo_content = message.metadata.get('echo_content') if message.metadata.get('is_echo_request') else None
        response_content = echo_content if echo_content is not None else f"ECHO: {message.content}"
        
        # Ensure content is a string, never None
        if response_content is None:
            response_content = ""
        
        # Create response message
        response = OutputMessage(
            message_id=str(uuid.uuid4()),  # Generate new ID
            channel_id=message.channel_id,
            channel_type=message.channel_type,
            content=str(response_content),  # Ensure string type
            user_id=message.user_id,  # Pass user ID if available
            workspace_id=message.workspace_id,  # Pass workspace ID if available
            conversation_id=message.conversation_id,  # Pass conversation ID
            timestamp=datetime.now(timezone.utc),
            reference_message_id=message.message_id,
            context_ids=[message.conversation_id] if message.conversation_id else [],
            metadata={
                "message_type": "response",
                "action_type": decision.action_type,
                "priority": decision.priority,
                "reference_id": decision.reference_id,
                "source": "cortex_router"
            }
        )
        
        # Turn off typing indicator if applicable
        if message.channel_type == ChannelType.CONVERSATION and message.conversation_id:
            from app.services.sse_service import get_sse_service
            sse_service = get_sse_service()
            
            await sse_service.connection_manager.send_event(
                "conversation",
                message.conversation_id,
                "typing",
                {
                    "conversation_id": message.conversation_id,
                    "active": False,
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                },
                republish=True
            )
            
            # Save the assistant message to the conversation
            try:
                from app.services.conversation_service import get_conversation_service
                conversation_service = get_conversation_service()
                await conversation_service.add_message(
                    conversation_id=message.conversation_id,
                    content=response.content,
                    role="assistant",
                    metadata={
                        "source": "router_respond",
                        "router_action_type": str(decision.action_type)
                    }
                )
                self.logger.info(f"Saved router response to conversation {message.conversation_id}")
            except Exception as e:
                self.logger.error(f"Error saving response to conversation: {e}")
        
        # Send via the event system
        event_name = f"output.{message.channel_type}.message"
        await self.event_system.publish(
            event_type=event_name, 
            data={"message": response}, 
            source="cortex_router"
        )
    
    async def _handle_process_action(self, message: InputMessage, decision: RoutingDecision):
        """
        Handle a 'process' action
        
        This represents more complex processing that might involve
        multiple systems and eventual responses.
        
        Args:
            message: The input message
            decision: The routing decision
        """
        # Placeholder for more complex processing
        # In a real implementation, this would involve:
        # - Querying memory systems
        # - Calling external APIs
        # - Running ML models
        # - Potentially sending multiple responses
        self.logger.info(
            f"Processing message {message.message_id} with decision {decision.action_type}"
        )
        
        # For demo purposes, after a longer delay, we'll send a response anyway
        await asyncio.sleep(3.0)
        
        # Generate a response
        response_content = f"After processing: {message.content}"
        
        # Create response message
        response = OutputMessage(
            channel_id=message.channel_id,
            channel_type=message.channel_type,
            content=response_content,
            reference_message_id=message.message_id,
            context_ids=[message.conversation_id] if message.conversation_id else [],
            metadata={
                "message_type": "response",
                "action_type": decision.action_type,
                "priority": decision.priority,
                "reference_id": decision.reference_id
            }
        )
        
        # Save the assistant message to the conversation if applicable
        if message.channel_type == ChannelType.CONVERSATION and message.conversation_id:
            try:
                from app.services.conversation_service import get_conversation_service
                conversation_service = get_conversation_service()
                await conversation_service.add_message(
                    conversation_id=message.conversation_id,
                    content=response.content,
                    role="assistant", 
                    metadata={
                        "source": "router_process",
                        "router_action_type": str(decision.action_type)
                    }
                )
                self.logger.info(f"Saved processed response to conversation {message.conversation_id}")
            except Exception as e:
                self.logger.error(f"Error saving processed response to conversation: {e}")
        
        # Send via the event system
        event_name = f"output.{message.channel_type}.message"
        await self.event_system.publish(
            event_type=event_name, 
            data={"message": response}, 
            source="cortex_router"
        )
    
    async def _handle_delegate_action(self, message: InputMessage, decision: RoutingDecision):
        """
        Handle a 'delegate' action
        
        This would forward the message to another system for handling.
        
        Args:
            message: The input message
            decision: The routing decision
        """
        # Placeholder for delegation logic
        # In a real implementation, this would:
        # - Forward the message to another system
        # - Potentially track the delegation for follow-up
        self.logger.info(
            f"Delegating message {message.message_id} with decision {decision.action_type}"
        )


# Global router instance
router = CortexRouter()

def get_router() -> RouterInterface:
    """Get the global router instance"""
    return router