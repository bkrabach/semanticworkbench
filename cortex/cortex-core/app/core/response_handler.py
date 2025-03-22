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

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for tools that can be executed by the response handler."""

    def __init__(self):
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

    def __init__(self):
        """Initialize the response handler."""
        self.system_prompt = os.getenv("SYSTEM_PROMPT", "")
        if not self.system_prompt:
            self.system_prompt = (
                "You are a helpful assistant. When you need to use a tool, "
                "respond with a JSON object that includes 'tool' and 'input' fields. "
                'For example: {"tool": "tool_name", "input": {"param": "value"}}. '
                "Otherwise, provide a direct response."
            )

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

            history = []
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

        tool_fn = tool_registry.get(tool_name)
        if not tool_fn:
            raise ToolExecutionException(message=f"Tool not found: {tool_name}", tool_name=tool_name)

        try:
            # Check if the tool requires the user_id
            import inspect

            sig = inspect.signature(tool_fn)

            if "user_id" in sig.parameters:
                # Include user_id in the arguments
                result = await tool_fn(user_id=user_id, **tool_args)
            else:
                # Just pass the tool arguments
                result = await tool_fn(**tool_args)

            return result
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name} - {str(e)}")
            raise ToolExecutionException(
                message=f"Error executing {tool_name}: {str(e)}", tool_name=tool_name, details={"error": str(e)}
            )

    async def _stream_response(self, conversation_id: str, final_text: str) -> None:
        """
        Stream the final response text to the client via SSE.

        Args:
            conversation_id: The ID of the conversation
            final_text: The text to stream
        """
        if not final_text:
            final_text = ""

        # Get the output queue for this conversation
        queue = get_output_queue(conversation_id)

        # Stream the text in chunks
        chunk_size = 50  # characters per chunk
        for i in range(0, len(final_text), chunk_size):
            chunk = final_text[i : i + chunk_size]

            event = {
                "type": "response_chunk",
                "data": chunk,
                "conversation_id": conversation_id,
                "timestamp": datetime.now().isoformat(),
                "is_final": False,
            }

            # Send as SSE data event
            await queue.put(json.dumps(event))

            # Brief pause for realistic streaming
            await asyncio.sleep(0.05)

        # Send the [DONE] marker
        done_event = {
            "type": "response_complete",
            "conversation_id": conversation_id,
            "timestamp": datetime.now().isoformat(),
            "is_final": True,
        }

        await queue.put(json.dumps(done_event))

    async def handle_message(
        self, user_id: str, conversation_id: str, message_content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Process a user message and produce a response (possibly with tool calls).

        Args:
            user_id: The ID of the user
            conversation_id: The ID of the conversation
            message_content: The content of the user's message
            metadata: Optional metadata
        """
        logger.info(f"Handling message from user {user_id} in conversation {conversation_id}")

        try:
            # 1. Store the user input
            await self._store_message(
                conversation_id=conversation_id,
                sender_id=user_id,
                content=message_content,
                role="user",
                metadata=metadata,
            )

            # 2. Retrieve conversation history
            history = await self._get_conversation_history(conversation_id)
            
            # 2a. Try to get relevant context from Cognition Service
            try:
                # Get tool function by name
                context_tool = tool_registry.get("get_context")
                if context_tool:
                    # Try to get context with user query
                    context_result = await context_tool(
                        user_id=user_id,
                        query=message_content,
                        limit=5  # Limit context items to avoid overwhelming the LLM
                    )
                    
                    # If we have context items, format them for inclusion
                    if context_result and "context" in context_result and context_result["context"]:
                        context_items = context_result["context"]
                        logger.info(f"Retrieved {len(context_items)} context items from Cognition Service")
                    else:
                        context_items = []
                else:
                    context_items = []
            except Exception as e:
                logger.warning(f"Failed to retrieve context from Cognition Service: {e}")
                context_items = []

            # 3. Prepare initial messages list for LLM
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

            # 4. Iteratively call LLM and handle tool requests
            final_answer = None
            max_iterations = 5  # Limit iterations to prevent infinite loops
            iterations = 0

            while iterations < max_iterations:
                iterations += 1
                logger.debug(f"LLM iteration {iterations} for conversation {conversation_id}")

                # Call the LLM to generate a response
                result = await llm_adapter.generate(messages)

                if result is None:
                    final_answer = "ERROR: Failed to generate a response from the AI service."
                    logger.error(f"LLM call failed for conversation {conversation_id}")
                    break

                # Check if the LLM indicates a tool call
                if "tool" in result:
                    tool_name = result["tool"]
                    tool_args = result.get("input", {})

                    try:
                        # Execute the requested tool
                        tool_result = await self._execute_tool(tool_name, tool_args, user_id)

                        # Convert tool result to string if it's not already
                        if not isinstance(tool_result, str):
                            if isinstance(tool_result, dict):
                                tool_result_str = json.dumps(tool_result)
                            else:
                                tool_result_str = str(tool_result)
                        else:
                            tool_result_str = tool_result

                        # Insert the tool result into the conversation
                        tool_message = {"role": "assistant", "content": f"I need to use the {tool_name} tool."}
                        tool_result_message = {
                            "role": "user",
                            "content": f"Tool '{tool_name}' returned: {tool_result_str}",
                        }

                        messages.append(tool_message)
                        messages.append(tool_result_message)

                        # Don't store tool interactions in the database to keep history clean
                        # Continue to the next iteration with the tool result
                        continue

                    except ToolExecutionException as e:
                        # Tool execution failed
                        final_answer = f"ERROR: Tool '{tool_name}' failed: {str(e)}"
                        logger.error(final_answer)
                        break
                else:
                    # LLM returned a final answer
                    final_answer = result.get("content", "")

                    # Store the assistant's answer in the DB
                    if final_answer:
                        await self._store_message(
                            conversation_id=conversation_id,
                            sender_id="assistant",  # Use a special ID for the assistant
                            content=final_answer,
                            role="assistant",
                            metadata={"iterations": iterations},
                        )

                        # Publish an event
                        event = {
                            "type": "response",
                            "data": {
                                "content": final_answer,
                                "conversation_id": conversation_id,
                            },
                            "user_id": user_id,
                            "timestamp": datetime.now().isoformat(),
                            "metadata": {"iterations": iterations},
                        }

                        await event_bus.publish(event)
                    break

            # If we reached the iteration limit without a final answer
            if iterations >= max_iterations and final_answer is None:
                final_answer = "I apologize, but I'm having trouble completing this request. Please try again with a simpler question."
                logger.warning(
                    f"Reached max iterations ({max_iterations}) without final answer for conversation {conversation_id}"
                )

            # 5. Stream the final answer via SSE
            await self._stream_response(
                conversation_id, final_answer or "I apologize, but I wasn't able to generate a response."
            )

        except Exception as e:
            logger.error(f"Error handling message: {str(e)}", exc_info=True)

            # Send error response to client
            error_msg = f"An error occurred while processing your request: {str(e)}"

            # Try to stream the error if possible
            try:
                await self._stream_response(conversation_id, error_msg)
            except Exception as stream_error:
                logger.error(f"Failed to stream error response: {str(stream_error)}")

            # At least try to publish an event
            try:
                error_event = {
                    "type": "error",
                    "data": {"message": error_msg, "conversation_id": conversation_id},
                    "user_id": user_id,
                    "timestamp": datetime.now().isoformat(),
                }
                await event_bus.publish(error_event)
            except Exception:
                pass  # Suppress any errors from publishing the event


# Create a global instance
response_handler = ResponseHandler()
