# Response Handler Cleanup Plan

This document outlines the steps to simplify and optimize the ResponseHandler implementation by removing unnecessary complexity and streamlining its functionality.

## Current Issues

1. **Dynamic Inspection**: The _execute_tool method uses dynamic inspection to determine if the user_id parameter should be passed to tools.

2. **Complex Streaming Logic**: The streaming implementation has some redundancy and complexity.

3. **Redundant Code Paths**: There are multiple similar code paths for handling different message types.

4. **Complex Message Delivery**: Message delivery logic is spread across multiple methods with some duplicated functionality.

## Implementation Plan

### 1. Optimize the _execute_tool Method

Replace the dynamic inspection with a simpler approach, assuming all tools accept a user_id parameter (which they should):

```python
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
        # Always include user_id in the arguments
        # All tools should accept user_id, even if they don't use it
        tool_args_with_user = {"user_id": user_id, **tool_args}
        result = await tool_fn(**tool_args_with_user)
        return result
    except Exception as e:
        logger.error(f"Tool execution failed: {tool_name} - {str(e)}")
        raise ToolExecutionException(
            message=f"Error executing {tool_name}: {str(e)}", tool_name=tool_name, details={"error": str(e)}
        )
```

### 2. Simplify the Streaming Implementation

Create a utility function to handle streaming events, reducing the redundancy in the code:

```python
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
```

Then update the streaming method to use this utility function:

```python
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
```

### 3. Consolidate Tool Event Handling

Create a dedicated method for tool events to reduce code duplication:

```python
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
        
        # Convert tool result to string if it's not already
        if not isinstance(tool_result, str):
            if isinstance(tool_result, dict):
                tool_result_str = json.dumps(tool_result)
            else:
                tool_result_str = str(tool_result)
        else:
            tool_result_str = tool_result
        
        # Generate a unique tool result message ID
        tool_result_id = f"tool-result-{conversation_id}-{datetime.now().timestamp()}"
        
        # Send a tool result notification event
        await self._send_event(
            conversation_id=conversation_id,
            event_type="tool_result",
            message_id=tool_result_id,
            content=str(tool_result),
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
```

### 4. Optimize the handle_message Method

Use the consolidated utility methods to streamline the handle_message logic:

```python
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
```

## Required Changes

1. Replace the dynamic inspection in _execute_tool with a simpler approach
2. Create utility methods to handle repeated event sending logic
3. Split the large handle_message method into smaller, focused methods
4. Consolidate the tool execution and notification logic
5. Standardize the streaming implementation
6. Improve error handling and logging

## Testing Updates

1. Update tests to reflect the simplified interface
2. Add tests for the new utility methods
3. Ensure the refactored methods maintain the same behavior
4. Test edge cases like error handling

## Benefits

1. **Reduced Complexity**: The response handler will be more maintainable with smaller, focused methods
2. **Improved Readability**: Code logic will be clearer and more consistent
3. **Better Error Handling**: Centralized error handling will improve reliability
4. **Easier Maintenance**: Isolated functionality will be easier to update and test
5. **Improved Performance**: Eliminating redundant code paths may improve performance