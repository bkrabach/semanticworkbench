"""
LLM Response Orchestrator for Cortex Core.

This module implements the LLM Response Orchestrator, which handles the processing
of user input events and produces AI responses. It follows the implementation
philosophy of ruthless simplicity and integrates with Pydantic-AI.
"""

import asyncio
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional, cast, TypedDict
from contextvars import ContextVar

from pydantic_ai import Agent
from pydantic_ai.messages import ToolCallPart

from app.backend.memory_client import MemoryClient
from app.core.event_bus import EventBus
from app.core.config import LLM_MODEL

# Configure logger
logger = logging.getLogger(__name__)

# Create and cache the Pydantic-AI agent for better performance
_pydantic_ai_agent = None

def get_pydantic_ai_agent() -> Agent:
    """
    Create or return a cached Pydantic-AI agent.
    
    Returns:
        A configured Pydantic-AI Agent instance
    """
    global _pydantic_ai_agent
    
    if _pydantic_ai_agent is None:
        # Initialize a basic memory tool
        memory_tool = async_memory_tool
        
        # Create the agent with tools
        # Using cast to handle the model name type checking
        # This is safe because pydantic-ai will validate at runtime
        _pydantic_ai_agent = Agent(
            model=cast(Any, LLM_MODEL),  # Cast to bypass literal type checking
            tools=[memory_tool]
            # We'll add model_settings in the actual implementation
            # when pydantic-ai is properly installed
        )
        logger.info(f"Initialized Pydantic-AI agent with model: {LLM_MODEL}")
    
    return _pydantic_ai_agent


class ConversationContext(TypedDict):
    """Type definition for conversation context."""
    user_id: str
    conversation_id: str

# Create a context variable to store the conversation info
conversation_context: ContextVar[Optional[ConversationContext]] = ContextVar(
    'conversation_context', default=None
)

def set_conversation_context(user_id: str, conversation_id: str) -> None:
    """Set the conversation context for the current thread."""
    conversation_context.set({"user_id": user_id, "conversation_id": conversation_id})

def get_conversation_context() -> Optional[ConversationContext]:
    """Get the conversation context for the current thread."""
    return conversation_context.get()

async def async_memory_tool(query: str = "recent_messages", limit: int = 5) -> str:
    """
    Retrieve memory information from the conversation.
    
    Args:
        query: Type of query to perform (e.g., "recent_messages")
        limit: Maximum number of messages to retrieve
        
    Returns:
        The requested memory information as text
    """
    try:
        # Get the conversation context
        context = get_conversation_context()
        if not context:
            return "Error: No conversation context available for memory retrieval."
        
        user_id = context["user_id"]
        conversation_id = context["conversation_id"]
        
        # Create a memory client
        memory_client = MemoryClient()
        
        try:
            # Connect to the memory service
            await memory_client.ensure_connected()
            
            # Get recent messages
            if query == "recent_messages":
                messages = await memory_client.get_recent_messages(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    limit=limit
                )
                
                # Format messages for the LLM
                result = f"Recent messages (limit={limit}):\n\n"
                for msg in messages:
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")
                    timestamp = msg.get("timestamp", "")
                    result += f"{role} ({timestamp}): {content}\n\n"
                
                return result
            else:
                return f"Unknown memory query type: {query}"
        finally:
            # Close the memory client
            await memory_client.close()
    except Exception as e:
        logger.error(f"Error calling memory tool: {e}", exc_info=True)
        return f"Error retrieving memory: {str(e)}"

# Define async LLM call interface
async def call_llm(messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
    """
    Send messages to the LLM and yield the response.
    
    This implementation uses Pydantic-AI to directly interact with LLM providers
    like Anthropic's Claude.
    
    Args:
        messages: List of message dictionaries with role and content
        
    Yields:
        Chunks of the LLM response as they become available
    """
    try:
        # Get the Pydantic-AI agent
        agent = get_pydantic_ai_agent()
        
        # Extract the user message
        user_message = ""
        system_instruction = ""
        
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            if role == "user":
                user_message = content
            elif role == "system":
                system_instruction = content
        
        # Run the agent with the message
        # For now, we'll just use the user message and add system as a prefix
        # This is a simplification - Pydantic-AI has better ways to handle
        # message sequences which we'll implement in a future update
        prompt_text = user_message
        if system_instruction:
            prompt_text = f"{system_instruction}\n\n{user_message}"
        
        # Using run() instead of run_sync() to maintain async flow
        result = await agent.run(prompt_text)
        
        # Yield the result
        # In the future, we can support streaming by using a streaming-enabled agent
        yield result.data
        
        logger.debug("LLM response generated successfully")
        
    except Exception as e:
        logger.error(f"Error calling LLM via Pydantic-AI: {e}", exc_info=True)
        yield f"Error generating response: {str(e)}"

async def fetch_tool_result(tool_name: str, args: Dict[str, Any], 
                           user_id: str, conversation_id: str) -> str:
    """
    Fetch results from a tool based on the tool name and arguments.
    
    Args:
        tool_name: The name of the tool to use
        args: Arguments for the tool
        user_id: The user ID for context
        conversation_id: The conversation ID for context
        
    Returns:
        The tool result as a string
    """
    if tool_name == "memory":
        # Call the memory service
        memory_client = MemoryClient()
        try:
            await memory_client.ensure_connected()
            
            # Determine which memory operation to perform based on args
            if "query" in args and args["query"] == "recent_messages":
                # Get recent messages
                limit = args.get("limit", 10)
                messages = await memory_client.get_recent_messages(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    limit=limit
                )
                
                # Format messages for LLM consumption
                result = "Recent messages:\n"
                for msg in messages:
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")
                    result += f"{role}: {content}\n"
                
                return result
            else:
                # Default memory search
                messages = await memory_client.get_recent_messages(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    limit=5
                )
                
                result = "Memory context:\n"
                for msg in messages:
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")
                    result += f"{role}: {content}\n"
                
                return result
        finally:
            await memory_client.close()
    
    # Add other tools here as they are implemented
    
    # Return error for unknown tools
    return f"Tool '{tool_name}' is not available or not recognized."

class LLMOrchestrator:
    """
    Orchestrates the LLM-driven response generation process.
    Subscribes to input events, processes them, and publishes output events.
    """
    
    def __init__(self, event_bus: EventBus):
        """
        Initialize the LLM orchestrator with dependencies.
        
        Args:
            event_bus: Event bus for publishing and subscribing to events
        """
        self.event_bus = event_bus
        self.input_queue: asyncio.Queue = asyncio.Queue()
        self.running = False
        self.memory_client = MemoryClient()
        self.task: Optional[asyncio.Task] = None
        
    async def start(self) -> None:
        """
        Start the orchestrator.
        Subscribes to user_message events and begins processing events.
        """
        if self.running:
            return
            
        self.running = True
        # Use the same event type as the existing response handler
        self.input_queue = self.event_bus.subscribe(event_type="user_message")
        
        # Start processing events in a background task
        self.task = asyncio.create_task(self.process_events())
        logger.info("LLM Orchestrator started")
    
    async def stop(self) -> None:
        """
        Stop the orchestrator and clean up resources.
        """
        if not self.running:
            return
            
        self.running = False
        
        # Unsubscribe from the event bus
        self.event_bus.unsubscribe(self.input_queue)
        
        # Cancel the task if it's running
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        logger.info("LLM Orchestrator stopped")
    
    async def process_events(self) -> None:
        """
        Process events from the input queue.
        This is the main loop that handles user messages.
        """
        while self.running:
            try:
                # Get the next event with a timeout
                try:
                    event = await asyncio.wait_for(self.input_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                
                # Process the event
                await self.handle_input_event(event)
                
                # Mark the task as done
                self.input_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error processing event: {e}", exc_info=True)
    
    async def handle_input_event(self, event: Dict[str, Any]) -> None:
        """
        Handle an input event by orchestrating LLM calls and tool usage.
        
        Args:
            event: The event data containing user_id, conversation_id, and message content
        """
        # Extract needed info from the event
        user_id = event.get("user_id")
        conversation_id = event.get("conversation_id")
        message_data = event.get("data", {})
        message_content = message_data.get("content", "")
        
        if not user_id or not conversation_id or not message_content:
            logger.warning(f"Missing required fields in event: {event}")
            return
        
        logger.info(f"Processing message from user {user_id} in conversation {conversation_id}")
        
        try:
            # 1. Store the user message in memory (if not already done by the API)
            await self.memory_client.ensure_connected()
            await self.memory_client.store_message(
                user_id=user_id,
                conversation_id=conversation_id,
                content=message_content,
                role="user",
                metadata=message_data.get("metadata", {})
            )
            
            # 2. Format initial messages for the LLM
            initial_messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an AI assistant in the Cortex Platform. "
                        "Your job is to help users with their questions and tasks. "
                        "If you need information from past conversations, you can use the memory tool. "
                        "Be concise, helpful, and accurate in your responses."
                    )
                },
                {
                    "role": "user",
                    "content": message_content
                }
            ]
            
            # 3. Call the Pydantic-AI agent
            # Tool use is handled automatically by Pydantic-AI
            agent = get_pydantic_ai_agent()
            
            # Set conversation context for the memory tool
            set_conversation_context(user_id, conversation_id)
            
            # Extract the messages for the prompt
            system_content = ""
            user_content = message_content
            
            if len(initial_messages) > 0:
                for msg in initial_messages:
                    if msg["role"] == "system":
                        system_content = msg["content"]
            
            # Create a combined prompt
            prompt = user_content
            if system_content:
                prompt = f"{system_content}\n\n{user_content}"
            
            # Call the agent with the prompt
            result = await agent.run(prompt)
            
            # Extract the final answer from the result
            answer_text = result.data
            
            # 4. Store the assistant response in memory
            await self.memory_client.store_message(
                user_id=user_id,
                conversation_id=conversation_id,
                content=answer_text,
                role="assistant"
            )
            
            # 5. Publish the output event
            output_event = {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "content": answer_text,
                "role": "assistant"
            }
            
            # Use the standard event type
            await self.event_bus.publish("output", output_event)
            logger.info(f"Published response for user {user_id} in conversation {conversation_id}")
            
            # Log tool uses if any
            if hasattr(result, 'all_messages'):
                # Extract tool calls for logging
                for message in result.all_messages():
                    if message.kind == 'response' and message.parts:
                        for part in message.parts:
                            # Check if it's a tool call part
                            if getattr(part, 'part_kind', None) == 'tool-call':
                                # Type check before accessing attributes
                                if isinstance(part, ToolCallPart):
                                    logger.info(f"Tool used: {part.tool_name} with args: {part.args}")
            
        except Exception as e:
            logger.error(f"Error handling input event: {e}", exc_info=True)
            
            # Publish error event
            error_event = {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "message": f"Error processing message: {str(e)}"
            }
            await self.event_bus.publish("error", error_event)
        finally:
            # Ensure memory client is closed
            await self.memory_client.close()


# Factory function to create and start an LLM orchestrator
async def create_llm_orchestrator(event_bus: EventBus) -> LLMOrchestrator:
    """
    Factory function to create and start an LLM orchestrator.
    
    Args:
        event_bus: The event bus instance to use.
        
    Returns:
        An initialized and started LLMOrchestrator instance
    """
    orchestrator = LLMOrchestrator(event_bus=event_bus)
    
    # Start the orchestrator
    await orchestrator.start()
    
    return orchestrator