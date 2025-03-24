"""
Response Handler module.

This module provides the ResponseHandler, which orchestrates the processing of
user messages through LLMs, including multi-step tool execution and streaming
output.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, cast

from ..database.unit_of_work import UnitOfWork
from ..models import Message
from .event_bus import event_bus
from .exceptions import ToolExecutionException
from .llm_adapter import llm_adapter
from .mcp.factory import get_mcp_client

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for tools that can be executed by the response handler."""

    def __init__(self) -> None:
        """Initialize an empty tool registry."""
        self._tools: Dict[str, Callable] = {}

    def register(self, name: str, tool_fn: Callable) -> None:
        """
        Register a tool function with the registry.

        Args:
            name: The name of the tool
            tool_fn: The callable function/method that implements the tool
        """
        self._tools[name] = tool_fn
        logger.info(f"Registered tool: {name}")

    def get(self, name: str) -> Optional[Callable]:
        """
        Get a tool function by name.

        Args:
            name: The name of the tool to retrieve

        Returns:
            The tool function or None if not found
        """
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        """
        Get a list of all registered tool names.

        Returns:
            List of tool names
        """
        return list(self._tools.keys())


# Global tool registry instance
tool_registry = ToolRegistry()


# Output queue registry for managing SSE connections
output_queues: Dict[str, asyncio.Queue] = {}


def get_output_queue(conversation_id: str) -> asyncio.Queue:
    """
    Get or create an output queue for a conversation.

    Args:
        conversation_id: The ID of the conversation

    Returns:
        An asyncio Queue for sending SSE messages
    """
    if conversation_id not in output_queues:
        output_queues[conversation_id] = asyncio.Queue()
    return output_queues[conversation_id]


def register_tool(name: str) -> Callable:
    """
    Decorator to register a tool function.

    Args:
        name: The name of the tool

    Returns:
        Decorator function
    """

    def decorator(tool_fn: Callable) -> Callable:
        tool_registry.register(name, tool_fn)
        return tool_fn

    return decorator


class ResponseHandler:
    """
    Handler for processing user input and generating responses.

    The ResponseHandler orchestrates the end-to-end processing of user messages,
    including calling LLMs, executing tools, and streaming responses.
    """

    def __init__(self) -> None:
        """Initialize the response handler."""
        self.system_prompt = os.getenv("SYSTEM_PROMPT", "")
        if not self.system_prompt:
            self.system_prompt = (
                "You are a helpful assistant. When you need to use a tool, "
                "respond with a JSON object that includes 'tool' and 'input' fields. "
                'For example: {"tool": "tool_name", "input": {"param": "value"}}. '
                "Otherwise, provide a direct response."
            )
            
    async def _send_event(self, conversation_id: str, event_type: str, message_id: Optional[str],
                       content: str, sender: Dict[str, str], metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Send an event to the client through the SSE queue.

        Args:
            conversation_id: The ID of the conversation
            event_type: The type of event (chunk, complete, tool, etc.)
            message_id: Optional message ID
            content: The content of the message
            sender: Information about the sender
            metadata: Optional additional metadata
        """
        # Get the output queue for this conversation
        queue = get_output_queue(conversation_id)
        
        # Create the event
        event = {
            "type": "message",
            "message_type": event_type,
            "data": {
                "content": content,
                "conversation_id": conversation_id,
                "message_id": message_id,
                "timestamp": datetime.now().isoformat(),
                "sender": sender
            },
            "metadata": metadata or {}
        }
        
        # Send the event
        await queue.put(json.dumps(event))

    async def _store_message(
        self, conversation_id: str, sender_id: str, content: str, role: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """
        Store a message in the database.

        Args:
            conversation_id: The ID of the conversation
            sender_id: The ID of the message sender
            content: The message content
            role: The role of the message (user/assistant)
            metadata: Optional metadata for the message

        Returns:
            The created message object
        """
        async with UnitOfWork.for_transaction() as uow:
            timestamp = datetime.now().isoformat()

            message = Message(
                conversation_id=conversation_id,
                sender_id=sender_id,
                content=content,
                timestamp=timestamp,
                metadata=metadata or {},
            )

            # Add role to metadata
            message.metadata["role"] = role

            message_repo = uow.repositories.get_message_repository()
            created_message = await message_repo.create(message)
            await uow.commit()

            # Cast to help mypy understand the type
            return cast(Message, created_message)

    async def _get_conversation_history(self, conversation_id: str, limit: int = 10) -> List[Dict[str, str]]:
        """
        Retrieve conversation history from the database.

        Args:
            conversation_id: The ID of the conversation
            limit: Maximum number of messages to retrieve

        Returns:
            List of messages formatted for the LLM
        """
        async with UnitOfWork.for_transaction() as uow:
            message_repo = uow.repositories.get_message_repository()
            messages = await message_repo.list_by_conversation(conversation_id, limit=limit)

            # Convert Message objects to dict format expected by LLM
            history: List[Dict[str, str]] = []
            for msg in messages:
                # Default to user role if not specified
                role = msg.metadata.get("role", "user") if msg.metadata else "user"
                history.append({"role": role, "content": msg.content})

            return history

    async def _execute_tool(self, tool_name: str, tool_args: Dict[str, Any], user_id: str) -> Any:
        """
        Execute a tool by name with the given arguments.

        Args:
            tool_name: The name of the tool to execute
            tool_args: The arguments to pass to the tool
            user_id: The ID of the user

        Returns:
            The tool execution result

        Raises:
            ToolExecutionException: If the tool execution fails
        """
        logger.info(f"Executing tool: {tool_name} with args: {tool_args}")

        # Try local tool registry first
        tool_fn = tool_registry.get(tool_name)
        if tool_fn:
            try:
                # Always include user_id in the arguments
                # All tools should accept user_id, even if they don't use it
                tool_args_with_user = {"user_id": user_id, **tool_args}
                result = await tool_fn(**tool_args_with_user)
                logger.info(f"Tool {tool_name} executed successfully using local registry")
                return result
            except Exception as e:
                logger.error(f"Local tool execution failed: {tool_name} - {str(e)}")
                # Don't raise here, try MCP client next
        
        # Try MCP client - distributed mode support
        try:
            # Always include user_id in the arguments
            tool_args_with_user = {"user_id": user_id, **tool_args}
            
            mcp_client = await get_mcp_client()
            result = await mcp_client.call_tool(
                service_name="cognition" if tool_name.startswith("get_") else "memory",
                tool_name=tool_name,
                input_data=tool_args_with_user
            )
            logger.info(f"Tool {tool_name} executed successfully using MCP client")
            return result
        except Exception as e:
            logger.error(f"MCP tool execution failed: {tool_name} - {str(e)}")
            
            # If we get here, both local and MCP tool execution failed
            if not tool_fn:
                # Tool not found in either local registry or MCP
                raise ToolExecutionException(
                    message=f"Tool not found: {tool_name}", 
                    tool_name=tool_name
                )
            else:
                # Tool found in local registry but execution failed, and MCP execution also failed
                raise ToolExecutionException(
                    message=f"Error executing {tool_name}: {str(e)}", 
                    tool_name=tool_name, 
                    details={"error": str(e)}
                )

    async def _handle_tool_execution(self, conversation_id: str, tool_name: str, 
                                tool_args: Dict[str, Any], user_id: str) -> Optional[Any]:
        """
        Handle a tool execution including event notifications.

        Args:
            conversation_id: The ID of the conversation
            tool_name: The name of the tool to execute
            tool_args: The arguments for the tool
            user_id: The ID of the user

        Returns:
            The tool execution result or None if execution fails
        """
        # Generate unique IDs for tool events
        tool_message_id = f"tool-{conversation_id}-{datetime.now().timestamp()}"
        
        # Send a tool use notification event
        await self._send_event(
            conversation_id=conversation_id,
            event_type="tool",
            message_id=tool_message_id,
            content=f"Executing tool: {tool_name}",
            sender={
                "id": "tool_executor",
                "name": "Tool Executor",
                "role": "tool"
            },
            metadata={
                "tool_name": tool_name,
                "tool_args": tool_args
            }
        )
        
        try:
            # Execute the requested tool
            tool_result = await self._execute_tool(tool_name, tool_args, user_id)
            
            # Convert tool result to string for the event message
            tool_result_str = tool_result
            if not isinstance(tool_result, str):
                if isinstance(tool_result, dict):
                    tool_result_str = json.dumps(tool_result)
                else:
                    tool_result_str = str(tool_result)
            
            # Generate a unique tool result message ID
            tool_result_id = f"tool-result-{conversation_id}-{datetime.now().timestamp()}"
            
            # Send a tool result notification event
            await self._send_event(
                conversation_id=conversation_id,
                event_type="tool_result",
                message_id=tool_result_id,
                content=tool_result_str,
                sender={
                    "id": f"tool_{tool_name}",
                    "name": f"Tool: {tool_name}",
                    "role": "tool"
                },
                metadata={
                    "tool_name": tool_name,
                    "tool_message_id": tool_message_id,
                    "result": tool_result
                }
            )
            
            return tool_result
        except ToolExecutionException as e:
            logger.error(f"Tool execution failed: {str(e)}")
            
            # Send error event
            await self._send_event(
                conversation_id=conversation_id,
                event_type="error",
                message_id=None,
                content=f"Error executing tool {tool_name}: {str(e)}",
                sender={
                    "id": "system_error",
                    "name": "System Error",
                    "role": "system"
                },
                metadata={"error": True}
            )
            
            return None

    async def _handle_final_response(
        self, conversation_id: str, final_answer: str, streaming: bool, user_message_id: Optional[str] = None
    ) -> None:
        """
        Handle the final response based on streaming preference.

        Args:
            conversation_id: The ID of the conversation
            final_answer: The final answer text
            streaming: Whether to stream the response
            user_message_id: Optional ID of the user message
        """
        # First, store the assistant's answer in the DB
        assistant_message = await self._store_message(
            conversation_id=conversation_id,
            sender_id="assistant",
            content=final_answer,
            role="assistant",
            metadata={"in_reply_to": user_message_id} if user_message_id else {},
        )
        assistant_message_id = assistant_message.id

        # Publish an event via the event bus
        event = {
            "type": "message",
            "message_type": "assistant",
            "data": {
                "content": final_answer,
                "conversation_id": conversation_id,
                "message_id": assistant_message_id,
                "timestamp": datetime.now().isoformat(),
                "sender": {
                    "id": "cortex-core",
                    "name": "Cortex",
                    "role": "assistant"
                }
            },
            "metadata": {}
        }
        await event_bus.publish(event)

        # Handle based on streaming preference
        if streaming:
            # Stream the response in chunks
            await self._stream_response(conversation_id, final_answer)
        else:
            # Send the complete response in a single message
            await self._send_event(
                conversation_id=conversation_id,
                event_type="complete",
                message_id=assistant_message_id,
                content=final_answer,
                sender={
                    "id": "cortex-core",
                    "name": "Cortex",
                    "role": "assistant"
                }
            )
    
    async def _handle_error(self, conversation_id: str, error: Exception) -> None:
        """
        Handle an error that occurred during message processing.

        Args:
            conversation_id: The ID of the conversation
            error: The exception that occurred
        """
        logger.error(f"Error handling message: {str(error)}", exc_info=True)

        # Create error message
        error_msg = f"An error occurred while processing your request: {str(error)}"

        # Try to send an error event
        try:
            await self._send_event(
                conversation_id=conversation_id,
                event_type="error",
                message_id=None,
                content=error_msg,
                sender={
                    "id": "system_error",
                    "name": "System Error",
                    "role": "system"
                },
                metadata={"error": True}
            )
        except Exception as e:
            logger.error(f"Failed to send error event: {str(e)}")

        # Also publish through the event bus as a fallback
        try:
            error_event = {
                "type": "message",
                "message_type": "error",
                "data": {
                    "content": error_msg,
                    "conversation_id": conversation_id,
                    "timestamp": datetime.now().isoformat(),
                    "sender": {
                        "id": "system_error",
                        "name": "System Error",
                        "role": "system"
                    }
                },
                "metadata": {
                    "error": True
                }
            }
            await event_bus.publish(error_event)
        except Exception:
            # If this fails too, just log it
            logger.error("Failed to publish error event to event bus", exc_info=True)

    async def _get_cognition_context(self, user_id: str, query: str) -> List[Dict[str, Any]]:
        """
        Get relevant context items from Cognition Service.

        Args:
            user_id: The ID of the user
            query: The user's query to find relevant context for

        Returns:
            List of context items or empty list if none found
        """
        try:
            # Try both approaches - local tool registry and MCP client
            
            # 1. Try local tool registry first
            context_tool = tool_registry.get("get_context")
            if context_tool:
                # Try to get context with user query
                context_result = await context_tool(
                    user_id=user_id,
                    query=query,
                    limit=5,  # Limit context items to avoid overwhelming the LLM
                )

                # If we have context items, return them
                if context_result and "context" in context_result and context_result["context"]:
                    context_items = context_result["context"]
                    logger.info(f"Retrieved {len(context_items)} context items from local Cognition Service")
                    return list(context_items)
            
            # 2. Try MCP client - distributed mode support
            try:
                mcp_client = await get_mcp_client()
                context_result = await mcp_client.call_tool(
                    service_name="cognition",
                    tool_name="get_context",
                    input_data={
                        "user_id": user_id,
                        "query": query,
                        "limit": 5  # Limit context items to avoid overwhelming the LLM
                    }
                )
                
                # If we have context items, return them
                if context_result and "context" in context_result and context_result["context"]:
                    context_items = context_result["context"]
                    logger.info(f"Retrieved {len(context_items)} context items from distributed Cognition Service")
                    return list(context_items)
                    
            except Exception as e:
                logger.warning(f"Failed to retrieve context from MCP Cognition Service: {e}")
                
        except Exception as e:
            logger.warning(f"Failed to retrieve context from Cognition Service: {e}")
        
        # Return empty list if anything fails
        return []

    async def _prepare_messages_with_context(
        self, history: List[Dict[str, str]], message_content: str, context_items: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """
        Prepare the messages list for the LLM with context.

        Args:
            history: The conversation history
            message_content: The current user message
            context_items: Relevant context items from Cognition Service

        Returns:
            The prepared messages list for the LLM
        """
        messages = []

        # Add system instruction if available
        if self.system_prompt:
            base_system_prompt = self.system_prompt

            # Add context to system prompt if available
            if context_items:
                context_text = "Here is some relevant context that might help you respond:\n\n"
                for item in context_items:
                    if "content" in item:
                        context_text += f"- {item['content']}\n"

                # Append context to system prompt
                enhanced_system_prompt = f"{base_system_prompt}\n\n{context_text}"
                messages.append({"role": "system", "content": enhanced_system_prompt})
            else:
                messages.append({"role": "system", "content": base_system_prompt})
        elif context_items:
            # No system prompt but we have context, add it as a system message
            context_text = "Here is some relevant context that might help you respond:\n\n"
            for item in context_items:
                if "content" in item:
                    context_text += f"- {item['content']}\n"

            messages.append({"role": "system", "content": context_text})

        # Add conversation history
        messages.extend(history)

        # Ensure the latest user message is included if not already in history
        if not history or history[-1]["role"] != "user" or history[-1]["content"] != message_content:
            messages.append({"role": "user", "content": message_content})

        return messages

    async def _process_llm_conversation(
        self, user_id: str, conversation_id: str, messages: List[Dict[str, str]], user_message_id: str
    ) -> Optional[str]:
        """
        Process a conversation with the LLM, handling tool calls as needed.

        Args:
            user_id: The ID of the user
            conversation_id: The ID of the conversation
            messages: The prepared messages list for the LLM
            user_message_id: The ID of the user's message

        Returns:
            The final answer text or None if processing failed
        """
        final_answer = None
        max_iterations = 5  # Limit iterations to prevent infinite loops
        iterations = 0

        while iterations < max_iterations:
            iterations += 1
            logger.debug(f"LLM iteration {iterations} for conversation {conversation_id}")

            # Call the LLM to generate a response
            logger.info(f"Calling LLM in iteration {iterations} with {len(messages)} messages")
            result = await llm_adapter.generate(messages)

            if result is None:
                final_answer = "ERROR: Failed to generate a response from the AI service."
                logger.error(f"LLM call failed for conversation {conversation_id}")
                break

            # Check if the LLM indicates a tool call
            if "tool" in result:
                tool_name = result["tool"]
                tool_args = result.get("input", {})

                # Execute the tool and get results
                tool_result = await self._handle_tool_execution(conversation_id, tool_name, tool_args, user_id)
                
                if tool_result is not None:
                    # Convert tool result to string if needed
                    if not isinstance(tool_result, str):
                        if isinstance(tool_result, dict):
                            tool_result_str = json.dumps(tool_result)
                        else:
                            tool_result_str = str(tool_result)
                    else:
                        tool_result_str = tool_result

                    # Format as an OpenAI-style tool call message
                    tool_message: Dict[str, Any] = {
                        "role": "assistant",
                        "content": None,
                        "function_call": {
                            "name": tool_name,
                            "arguments": json.dumps(tool_args)
                        }
                    }
                    
                    # Format as OpenAI-style tool result message
                    tool_result_message: Dict[str, Any] = {
                        "role": "function",
                        "name": tool_name,
                        "content": tool_result_str
                    }

                    messages.append(tool_message)
                    messages.append(tool_result_message)

                    # Log the next step for debugging
                    logger.info(f"Tool '{tool_name}' executed successfully, continuing to get final response")
                    
                    # Continue to the next iteration with the tool result
                    continue
                else:
                    # Tool execution failed
                    final_answer = f"I apologize, but I couldn't complete the requested operation using the '{tool_name}' tool."
                    logger.error(f"Tool execution failed for {tool_name} in conversation {conversation_id}")
                    break
            else:
                # LLM returned a final answer
                final_answer = result.get("content", "")
                break

        # If we reached the iteration limit without a final answer
        if iterations >= max_iterations and final_answer is None:
            final_answer = "I apologize, but I'm having trouble completing this request. Please try again with a simpler question."
            logger.warning(
                f"Reached max iterations ({max_iterations}) without final answer for conversation {conversation_id}"
            )

        return final_answer

    async def _stream_response(self, conversation_id: str, final_text: str) -> None:
        """
        Stream the final response text to the client via SSE.

        Args:
            conversation_id: The ID of the conversation
            final_text: The text to stream
        """
        if not final_text:
            final_text = ""
            
        # Get the current assistant message ID for this streaming session
        assistant_message_id: Optional[str] = None
        try:
            async with UnitOfWork.for_transaction() as uow:
                message_repo = uow.repositories.get_message_repository()
                # Get the most recent assistant message for this conversation
                assistant_messages: List[Message] = await message_repo.list_by_conversation(
                    conversation_id, limit=1, role="assistant"
                )
                if assistant_messages and len(assistant_messages) > 0:
                    assistant_message_id = assistant_messages[0].id
        except Exception as e:
            logger.warning(f"Failed to get assistant message ID for streaming: {e}")
            # Continue without message ID if we can't get it
        
        # Define sender info once
        sender = {
            "id": "cortex-core",
            "name": "Cortex",
            "role": "assistant"
        }
        
        # Stream the text in chunks
        chunk_size = 50  # characters per chunk
        for i in range(0, len(final_text), chunk_size):
            chunk = final_text[i : i + chunk_size]
            
            # Send chunk event
            await self._send_event(
                conversation_id=conversation_id,
                event_type="chunk",
                message_id=assistant_message_id,
                content=chunk,
                sender=sender
            )
            
            # Brief pause for realistic streaming
            await asyncio.sleep(0.05)
        
        # Send the final message with complete content
        await self._send_event(
            conversation_id=conversation_id,
            event_type="complete",
            message_id=assistant_message_id,
            content=final_text,
            sender=sender
        )

    async def handle_message(
        self, 
        user_id: str, 
        conversation_id: str, 
        message_content: str, 
        metadata: Optional[Dict[str, Any]] = None, 
        streaming: bool = True
    ) -> None:
        """
        Process a user message and produce a response (possibly with tool calls).

        Args:
            user_id: The ID of the user
            conversation_id: The ID of the conversation
            message_content: The content of the user's message
            metadata: Optional metadata
            streaming: Whether to stream the response
        """
        logger.info(f"Handling message from user {user_id} in conversation {conversation_id}")

        try:
            # 1. Store the user input and get the message ID
            user_message = await self._store_message(
                conversation_id=conversation_id,
                sender_id=user_id,
                content=message_content,
                role="user",
                metadata=metadata,
            )
            user_message_id = user_message.id

            # 2. Retrieve conversation history
            history = await self._get_conversation_history(conversation_id)

            # 3. Try to get relevant context from Cognition Service
            context_items = await self._get_cognition_context(user_id, message_content)

            # 4. Prepare messages list for LLM with context
            messages = await self._prepare_messages_with_context(
                history, message_content, context_items
            )

            # 5. Iteratively call LLM and handle tool requests
            final_answer = await self._process_llm_conversation(
                user_id, conversation_id, messages, user_message_id
            )

            # 6. Handle the final response based on streaming preference
            if final_answer:
                await self._handle_final_response(
                    conversation_id, final_answer, streaming, user_message_id
                )
            else:
                # Fallback response if no final answer was generated
                fallback_message = "I apologize, but I wasn't able to generate a response."
                await self._handle_final_response(
                    conversation_id, fallback_message, streaming, user_message_id
                )

        except Exception as e:
            await self._handle_error(conversation_id, e)


# Create a global instance
response_handler = ResponseHandler()
