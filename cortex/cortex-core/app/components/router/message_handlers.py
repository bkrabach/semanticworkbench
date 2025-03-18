"""
Message handlers for the Cortex platform router.

This module provides handlers for different message types that can be
registered with the MessageRouter.
"""

import uuid

from app.components.io import get_io_manager
from app.components.mcp import get_mcp_client
from app.components.memory.memory_manager import get_memory_manager
from app.interfaces.input_output import OutputMessage, ChannelType
from app.interfaces.router import RouterMessage, MessageType
from app.models.domain.memory import MemoryItemCreate
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def handle_text_message(message: RouterMessage) -> bool:
    """
    Handle a text message.
    
    This handler processes text messages by:
    1. Retrieving conversation context from memory
    2. Sending the message to the appropriate MCP client
    3. Publishing the response to the output channel
    
    Args:
        message: The router message to handle
        
    Returns:
        True if the message was handled successfully, False otherwise
    """
    try:
        logger.debug(f"Handling text message: {message.id}")
        
        # Get services and managers
        memory_manager = get_memory_manager()
        io_manager = get_io_manager()
        mcp_client = get_mcp_client()
        
        # Get conversation context - not using it yet but will in future enhancements
        # This call ensures the context exists and is initialized
        _ = await memory_manager.get_context(
            workspace_id=message.workspace_id,
            conversation_id=message.conversation_id
        )
        
        # Prepare message for MCP client
        mcp_args = {
            "conversation_id": str(message.conversation_id),
            "message": message.content,
            "history": [],  # We'll add history from context in the future
            "context": {
                "workspace_id": str(message.workspace_id),
                "user_id": str(message.metadata.get("user_id", "unknown"))
            }
        }
        
        # Call MCP client
        response = {"content": "This is a placeholder response."}
        try:
            # If MCP client is connected, use it
            if mcp_client.is_connected:
                response = await mcp_client.call_tool("generate_response", mcp_args)
            else:
                logger.warning("MCP client not connected, using placeholder response")
        except Exception as e:
            logger.error(f"Error calling MCP client: {str(e)}")
            response = {"content": "I'm sorry, I encountered an error processing your request."}
        
        # Create output message
        output_message = OutputMessage(
            id=uuid.uuid4(),
            channel_id=f"conversation_{message.conversation_id}",
            channel_type=ChannelType.CONVERSATION,
            content=response.get("content", ""),
            user_id=None,  # No user ID for assistant messages
            workspace_id=message.workspace_id,
            conversation_id=message.conversation_id,
            reference_message_id=message.id,
            metadata={
                "source": "mcp",
                "role": "assistant"
            }
        )
        
        # Send output message
        result = await io_manager.send_output(output_message)
        
        # Store message and response in memory
        # This is a simple implementation that could be enhanced later
        await memory_manager.store(
            workspace_id=message.workspace_id,
            item=MemoryItemCreate(
                item_type="message",
                content=message.content,
                metadata={
                    "conversation_id": str(message.conversation_id),
                    "role": "user",
                    "timestamp": message.timestamp.isoformat()
                }
            )
        )
        
        await memory_manager.store(
            workspace_id=message.workspace_id,
            item=MemoryItemCreate(
                item_type="message",
                content=response.get("content", ""),
                metadata={
                    "conversation_id": str(message.conversation_id),
                    "role": "assistant",
                    "reference_message_id": str(message.id)
                }
            )
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error handling text message: {str(e)}")
        return False


async def handle_action_message(message: RouterMessage) -> bool:
    """
    Handle an action message.
    
    This handler processes action messages which are typically commands or
    special instructions rather than natural language.
    
    Args:
        message: The router message to handle
        
    Returns:
        True if the message was handled successfully, False otherwise
    """
    try:
        logger.debug(f"Handling action message: {message.id}")
        
        # Get action type from metadata
        action_type = message.metadata.get("action_type")
        
        if not action_type:
            logger.warning(f"Action message {message.id} has no action_type metadata")
            return False
        
        # Process different action types
        if action_type == "clear_context":
            # Clear conversation context
            memory_manager = get_memory_manager()
            await memory_manager.clear_context(
                workspace_id=message.workspace_id,
                conversation_id=message.conversation_id
            )
            
            # Notify client that context was cleared
            io_manager = get_io_manager()
            output_message = OutputMessage(
                id=uuid.uuid4(),
                channel_id=f"conversation_{message.conversation_id}",
                channel_type=ChannelType.CONVERSATION,
                content="Context cleared successfully.",
                user_id=None,
                workspace_id=message.workspace_id,
                conversation_id=message.conversation_id,
                reference_message_id=message.id,
                metadata={
                    "source": "system",
                    "role": "system",
                    "action_type": "clear_context",
                    "action_status": "success"
                }
            )
            
            return await io_manager.send_output(output_message)
            
        else:
            logger.warning(f"Unknown action type: {action_type}")
            return False
        
    except Exception as e:
        logger.error(f"Error handling action message: {str(e)}")
        return False


# Map of message types to handlers
message_handlers = {
    MessageType.TEXT.value: handle_text_message,
    MessageType.ACTION.value: handle_action_message,
}


def register_handlers(router) -> None:
    """
    Register all message handlers with the router.
    
    Args:
        router: The message router
    """
    for message_type, handler in message_handlers.items():
        router.register_handler(message_type, handler)
        logger.info(f"Registered handler for message type: {message_type}")