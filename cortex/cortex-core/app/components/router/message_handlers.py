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
        mcp_client = get_mcp_client("domain_experts")
        
        # First, save the incoming message to memory
        # This ensures the message is stored even if processing fails
        await memory_manager.add_to_memory(
            workspace_id=message.workspace_id,
            conversation_id=message.conversation_id,
            content=message.content,
            metadata={
                "role": "user",
                "timestamp": message.timestamp.isoformat(),
                "message_id": str(message.id)
            }
        )
        
        # Get conversation context with message history
        context = await memory_manager.get_context(
            workspace_id=message.workspace_id,
            conversation_id=message.conversation_id
        )
        
        # Format conversation history for the LLM
        history = []
        for item in context.items:
            if item.item_type == "message":
                role = item.metadata.get("role", "unknown")
                history.append({
                    "role": role,
                    "content": item.content,
                    "id": str(item.id),
                    "timestamp": item.metadata.get("timestamp", item.created_at.isoformat())
                })
        
        # Sort history by timestamp (oldest first)
        history.sort(key=lambda x: x.get("timestamp", ""))
        
        # Prepare message for MCP client
        mcp_args = {
            "conversation_id": str(message.conversation_id),
            "message": message.content,
            "history": history,
            "context": {
                "workspace_id": str(message.workspace_id),
                "user_id": str(message.metadata.get("user_id", "unknown")),
                "conversation_name": message.metadata.get("conversation_name", "Conversation")
            }
        }
        
        # Create an initial "thinking" message to show the user something is happening
        thinking_message = OutputMessage(
            id=uuid.uuid4(),
            channel_id=f"conversation_{message.conversation_id}",
            channel_type=ChannelType.CONVERSATION,
            content="",
            user_id=None,
            workspace_id=message.workspace_id,
            conversation_id=message.conversation_id,
            reference_message_id=message.id,
            metadata={
                "source": "system",
                "role": "assistant",
                "status": "thinking"
            }
        )
        await io_manager.send_output(thinking_message)
        
        # Call MCP client
        response = {"content": "This is a placeholder response."}
        try:
            # If MCP client is connected, use it
            if mcp_client.is_connected:
                logger.debug(f"Calling MCP for conversation {message.conversation_id}")
                response = await mcp_client.call_tool("generate_response", mcp_args)
                logger.debug(f"MCP response received for conversation {message.conversation_id}")
            else:
                # Try the default MCP client as fallback
                default_mcp = get_mcp_client()
                if default_mcp.is_connected:
                    logger.debug("Domain experts MCP not connected, using default MCP client")
                    response = await default_mcp.call_tool("generate_response", mcp_args)
                else:
                    logger.warning("No MCP clients connected, using placeholder response")
                    response = {"content": "I'm sorry, I'm not currently able to process your request."}
        except Exception as e:
            logger.error(f"Error calling MCP client: {str(e)}")
            response = {"content": "I'm sorry, I encountered an error processing your request."}
        
        # Create output message for the actual response
        response_id = uuid.uuid4()
        output_message = OutputMessage(
            id=response_id,
            channel_id=f"conversation_{message.conversation_id}",
            channel_type=ChannelType.CONVERSATION,
            content=response.get("content", ""),
            user_id=None,  # No user ID for assistant messages
            workspace_id=message.workspace_id,
            conversation_id=message.conversation_id,
            reference_message_id=message.id,
            metadata={
                "source": "mcp",
                "role": "assistant",
                "status": "complete",
                "thinking_message_id": str(thinking_message.id)
            }
        )
        
        # Send output message
        result = await io_manager.send_output(output_message)
        
        # Store the assistant response in memory
        await memory_manager.add_to_memory(
            workspace_id=message.workspace_id,
            conversation_id=message.conversation_id,
            content=response.get("content", ""),
            metadata={
                "role": "assistant",
                "reference_message_id": str(message.id),
                "message_id": str(response_id)
            }
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
        
        # Get services and managers
        memory_manager = get_memory_manager()
        io_manager = get_io_manager()
        
        # Get action type from metadata
        action_type = message.metadata.get("action_type")
        
        if not action_type:
            logger.warning(f"Action message {message.id} has no action_type metadata")
            return False
        
        # Create message ID for response
        response_id = uuid.uuid4()
        
        # Process different action types
        if action_type == "clear_context":
            # Clear conversation context
            await memory_manager.clear_context(
                workspace_id=message.workspace_id,
                conversation_id=message.conversation_id
            )
            
            # Create a fresh context with a system message
            await memory_manager.add_to_memory(
                workspace_id=message.workspace_id,
                conversation_id=message.conversation_id,
                content="Conversation context has been cleared.",
                metadata={
                    "role": "system",
                    "action_type": "clear_context"
                }
            )
            
            # Notify client that context was cleared
            output_message = OutputMessage(
                id=response_id,
                channel_id=f"conversation_{message.conversation_id}",
                channel_type=ChannelType.CONVERSATION,
                content="Conversation context has been cleared. You're now starting with a fresh conversation.",
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
            
        elif action_type == "list_domains":
            # List available domain experts
            mcp_client = get_mcp_client("domain_experts")
            
            try:
                if mcp_client.is_connected:
                    # Get available domains
                    tools = await mcp_client.list_tools()
                    domains = tools.get("tools", [])
                    domain_names = [tool.get("name") for tool in domains if "name" in tool]
                    
                    # Format the response
                    if domain_names:
                        content = "Available domain experts:\n" + "\n".join([f"- {name}" for name in domain_names])
                    else:
                        content = "No domain experts are currently available."
                else:
                    content = "Unable to connect to domain experts service."
            except Exception as e:
                logger.error(f"Error listing domains: {str(e)}")
                content = "Error retrieving domain experts list."
            
            # Send response
            output_message = OutputMessage(
                id=response_id,
                channel_id=f"conversation_{message.conversation_id}",
                channel_type=ChannelType.CONVERSATION,
                content=content,
                user_id=None,
                workspace_id=message.workspace_id,
                conversation_id=message.conversation_id,
                reference_message_id=message.id,
                metadata={
                    "source": "system",
                    "role": "system",
                    "action_type": "list_domains",
                    "action_status": "success"
                }
            )
            
            return await io_manager.send_output(output_message)
            
        elif action_type == "set_domain":
            # Set the domain expert for this conversation
            domain_name = message.metadata.get("domain_name")
            
            if not domain_name:
                content = "Error: No domain expert specified."
                action_status = "error"
            else:
                # Store the domain selection in memory
                await memory_manager.add_to_memory(
                    workspace_id=message.workspace_id,
                    conversation_id=message.conversation_id,
                    content=f"Domain expert set to: {domain_name}",
                    metadata={
                        "role": "system",
                        "action_type": "set_domain",
                        "domain_name": domain_name
                    }
                )
                
                content = f"Domain expert set to: {domain_name}"
                action_status = "success"
            
            # Send response
            output_message = OutputMessage(
                id=response_id,
                channel_id=f"conversation_{message.conversation_id}",
                channel_type=ChannelType.CONVERSATION,
                content=content,
                user_id=None,
                workspace_id=message.workspace_id,
                conversation_id=message.conversation_id,
                reference_message_id=message.id,
                metadata={
                    "source": "system",
                    "role": "system",
                    "action_type": "set_domain",
                    "action_status": action_status,
                    "domain_name": domain_name if domain_name else ""
                }
            )
            
            return await io_manager.send_output(output_message)
            
        elif action_type == "ping":
            # Simple ping-pong action for testing
            output_message = OutputMessage(
                id=response_id,
                channel_id=f"conversation_{message.conversation_id}",
                channel_type=ChannelType.CONVERSATION,
                content="pong",
                user_id=None,
                workspace_id=message.workspace_id,
                conversation_id=message.conversation_id,
                reference_message_id=message.id,
                metadata={
                    "source": "system",
                    "role": "system",
                    "action_type": "ping",
                    "action_status": "success"
                }
            )
            
            return await io_manager.send_output(output_message)
        
        else:
            logger.warning(f"Unknown action type: {action_type}")
            
            # Send unknown action error response
            output_message = OutputMessage(
                id=response_id,
                channel_id=f"conversation_{message.conversation_id}",
                channel_type=ChannelType.CONVERSATION,
                content=f"Unknown action type: {action_type}",
                user_id=None,
                workspace_id=message.workspace_id,
                conversation_id=message.conversation_id,
                reference_message_id=message.id,
                metadata={
                    "source": "system",
                    "role": "system",
                    "action_type": action_type,
                    "action_status": "error"
                }
            )
            
            return await io_manager.send_output(output_message)
        
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