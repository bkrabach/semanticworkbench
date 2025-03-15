"""
Cortex Router Implementation
Core component for processing inputs and routing messages
"""

import asyncio
import uuid
import logging
from typing import Optional
from datetime import datetime, timezone

from app.interfaces.router import (
    RouterInterface,
    InputMessage,
    RoutingDecision,
    ActionType
)
from app.components.event_system import get_event_system
from app.services.sse_service import get_sse_service
from app.services.llm_service import get_llm_service


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

        try:
            # Get LLM service
            llm_service = get_llm_service()
            
            # Get integration hub to fetch domain expert tools
            from app.components.integration_hub import get_integration_hub
            integration_hub = get_integration_hub()
            
            # Get available tools from all domain experts
            tools = []
            available_experts = []
            
            try:
                # List all available domain experts
                experts = await integration_hub.list_experts()
                
                # Get status of domain experts to check which ones are actually available
                # This is important since we know from looking at the server logs that 
                # we might have situations where the server thinks it's connected but
                # the client hasn't completed initialization
                expert_status = await integration_hub.get_expert_status()
                
                # For debugging output
                for name, status in expert_status.items():
                    self.logger.info(f"Expert {name} status: available={status.get('available', False)}, "
                                    f"state={status.get('state', 'unknown')}, "
                                    f"capabilities={status.get('capabilities', [])}")
                
                # Only consider experts that are marked as fully available
                available_experts = [name for name, status in expert_status.items() 
                                    if status.get("available", False)]
                
                self.logger.info(f"Found {len(available_experts)}/{len(experts)} available domain experts")
                
                # Only try to fetch tools from experts that are marked as available
                self.logger.info(f"Available experts: {available_experts}")
                
                # Check for specific expert types that should handle this request
                request_keywords = message.content.lower()
                prioritized_experts = []
                
                # Log the message content to help debug tool selection
                first_20_words = ' '.join(message.content.split()[:20])
                self.logger.info(f"Processing message starting with: {first_20_words}...")
                
                if "code" in request_keywords or "check" in request_keywords or "lint" in request_keywords:
                    # This looks like a request that the Code Assistant could handle
                    code_experts = [name for name in available_experts 
                                  if "code" in name.lower() or "assistant" in name.lower()]
                    if code_experts:
                        self.logger.info(f"This appears to be a code-related request. Prioritizing experts: {code_experts}")
                        # Move code experts to the front of the list
                        prioritized_experts = code_experts + [e for e in available_experts if e not in code_experts]
                    else:
                        self.logger.info("This appears to be a code-related request but no code experts are available")
                        prioritized_experts = available_experts
                else:
                    # No special prioritization needed
                    prioritized_experts = available_experts
                
                for expert_name in prioritized_experts:
                    try:
                        # We need a longer timeout for the first request to each expert
                        # since it might need to establish/validate the connection
                        self.logger.info(f"Fetching tools from expert {expert_name}")
                        expert_tools = await asyncio.wait_for(
                            integration_hub.list_expert_tools(expert_name),
                            timeout=10.0  # Longer timeout for tool fetching
                        )
                        
                        # Format tools in OpenAI compatible format
                        if "tools" in expert_tools:
                            for tool_name, tool_info in expert_tools["tools"].items():
                                # Create tool definition in the format expected by LiteLLM/OpenAI
                                formatted_tool = {
                                    "type": "function",
                                    "function": {
                                        "name": f"{expert_name}.{tool_name}",
                                        "description": tool_info.get("description", f"Tool {tool_name} from {expert_name}"),
                                        "parameters": tool_info.get("parameters", {})
                                    }
                                }
                                tools.append(formatted_tool)
                                
                            self.logger.info(f"Added {len(expert_tools.get('tools', {}))} tools from expert {expert_name}")
                        else:
                            self.logger.info(f"No tools found in response from expert {expert_name}")
                            
                    except asyncio.TimeoutError:
                        self.logger.warning(f"Timeout fetching tools from expert {expert_name}")
                    except Exception as tool_error:
                        self.logger.warning(f"Failed to fetch tools from expert {expert_name}: {tool_error}")
            except Exception as expert_error:
                self.logger.warning(f"Failed to fetch domain experts: {expert_error}")
            
            # Add helpful log for debugging
            if tools:
                self.logger.info(f"Providing {len(tools)} tools from {len(available_experts)} experts to LLM")
            else:
                self.logger.info("No domain expert tools available for this request")
            
            # Construct an appropriate system prompt that encourages tool use
            system_prompt = (
                "You are a helpful AI assistant with access to specialized tools. "
                "When a user's request can be addressed using one of your tools, you should choose "
                "the appropriate tool rather than attempting to provide the information directly. "
                "This is especially important for tasks like code checking, data processing, "
                "or accessing specialized knowledge. "
                "Respond accurately and clearly to the user's request, using tools when appropriate."
            )
            
            # Get response from LLM with tools
            self.logger.info(f"Sending request to LLM with {len(tools) if tools else 0} tools")
            response_content = await llm_service.get_completion(
                prompt=message.content,
                system_prompt=system_prompt,
                tools=tools if tools else None
            )
            
            # If response is empty, provide a fallback
            if not response_content:
                response_content = "I'm sorry, I couldn't process your request. Please try again."
                
            # Save metadata about this interaction
            metadata = {
                "source": "cortex_router",
                "llm_enabled": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tools_provided": bool(tools),
                "tool_count": len(tools)
            }
            
            # Save to database and get message_id
            message_id = await self._save_message_to_database(
                message.conversation_id,
                response_content,
                "assistant",
                metadata
            )
            
            # Send message to client
            await self._send_message_to_client(
                message.conversation_id,
                message_id,
                response_content,
                "assistant",
                metadata
            )
            
        except Exception as e:
            # Handle errors gracefully
            self.logger.error(f"Error generating LLM response: {e}")
            error_content = "I apologize, but I encountered an error processing your request."
            
            # Save error message to database
            message_id = await self._save_message_to_database(
                message.conversation_id,
                error_content,
                "assistant",
                {"source": "cortex_router", "error": str(e)}
            )
            
            # Send error message to client
            await self._send_message_to_client(
                message.conversation_id,
                message_id,
                error_content,
                "assistant",
                {"source": "cortex_router", "error": str(e)}
            )
            
        finally:
            # Always turn off typing indicator
            await self._send_typing_indicator(message.conversation_id, False)

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
        # Prepare payload
        payload = {
            "conversation_id": conversation_id,
            "isTyping": is_typing,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }
        
        # First publish to event system to ensure delivery
        event_system = get_event_system()
        await event_system.publish(
            "conversation.typing_indicator",
            payload,
            source="cortex_router"
        )
        
        # Also try direct SSE path for active connections
        sse_service = get_sse_service()
        await sse_service.connection_manager.send_event(
            "conversation",
            conversation_id,
            "typing_indicator",
            payload,
            republish=False  # Already published through event system
        )

    async def _save_message_to_database(self, conversation_id: str, content: str,
                                       role: str, metadata: dict) -> str:
        """Save message to database and return message_id"""
        try:
            # Import here to avoid circular imports
            from app.database.connection import db
            from app.database.repositories.conversation_repository import ConversationRepository
            
            # Create a new database session
            with db.get_db() as db_session:
                repo = ConversationRepository(db_session)
                message = repo.add_message(
                    conversation_id=conversation_id,
                    content=content,
                    role=role,
                    metadata=metadata
                )
                
                # Get the message ID or generate a random one if missing
                if message and hasattr(message, 'id'):
                    return message.id
                else:
                    self.logger.warning(f"Message saved but no ID returned for conversation {conversation_id}")
                    return str(uuid.uuid4())
                    
        except Exception as e:
            self.logger.error(f"Error saving message to database: {e}")
            return str(uuid.uuid4())

    async def _send_message_to_client(self, conversation_id: str, message_id: str,
                                     content: str, role: str, metadata: dict):
        """Send message directly to client via SSE"""
        self.logger.info(f"Sending message {message_id} to conversation {conversation_id}")
        
        # Create the standard message payload
        payload = {
            "id": message_id,
            "content": content,
            "role": role,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata,
            "conversation_id": conversation_id
        }
        
        # First, send event to clients through system events
        # This ensures proper delivery across all connection paths
        event_system = get_event_system()
        await event_system.publish(
            f"conversation.message_received",
            payload,
            source="cortex_router"
        )
        
        # Also try to send directly through the SSE service's connection manager
        # This is a direct path for clients with active connections
        sse_service = get_sse_service()
        await sse_service.connection_manager.send_event(
            "conversation",
            conversation_id,
            "message_received",
            payload,
            republish=False  # Already published through event system
        )


# Global router instance
_router: Optional[CortexRouter] = None

def get_router() -> RouterInterface:
    """Get the global router instance"""
    global _router
    if _router is None:
        _router = CortexRouter()
    return _router