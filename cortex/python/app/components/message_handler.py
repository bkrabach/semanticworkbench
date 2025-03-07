"""
Message Handler Component

This module implements a message handler that processes incoming messages,
applies security policies, and manages the flow of messages through the system.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field

from app.components.context_manager import (
    Context,
    ContextUpdate,
    Message,
    initialize_context_manager,
)
from app.components.dispatcher import dispatcher
from app.components.security_manager import security_manager
from app.config import settings
from app.utils.logger import get_contextual_logger

# Configure logger
logger = get_contextual_logger("components.message_handler")


class MessageResponse(BaseModel):
    """Response to a processed message"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    role: str = "assistant"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


async def process_message(
    content: str,
    role: str = "user",
    session_id: uuid.UUID = None,
    workspace_id: uuid.UUID = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> MessageResponse:
    """
    Process an incoming message

    Args:
        content: Message content
        role: Message role (user, system, assistant)
        session_id: Session ID
        workspace_id: Workspace ID
        metadata: Optional message metadata

    Returns:
        Message response
    """
    try:
        logger.info(
            f"Processing message from {role}, session: {session_id}, workspace: {workspace_id}"
        )

        # Create new session and workspace if not provided
        if session_id is None:
            from app.components.session_manager import session_manager

            session = await session_manager.create_session(
                metadata={"source": "message_handler"}
            )
            session_id = session.id
            logger.info(f"Created new session: {session_id}")

        if workspace_id is None:
            # In a real implementation, this would interact with a workspace manager
            # For now, we'll just create a UUID
            workspace_id = uuid.uuid4()
            logger.info(f"Created new workspace: {workspace_id}")

        # Initialize message metadata
        if metadata is None:
            metadata = {}

        metadata.update(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "session_id": str(session_id),
                "workspace_id": str(workspace_id),
            }
        )

        # Create message object
        message = Message(
            role=role,
            content=content,
            metadata=metadata,
        )

        # Update context with the new message
        context_manager = initialize_context_manager(
            None
        )  # This gets the global instance

        await context_manager.update_context(
            session_id=session_id,
            workspace_id=workspace_id,
            context_update=ContextUpdate(add_messages=[message]),
        )

        # Get current context
        context = await context_manager.get_context(
            session_id=session_id,
            workspace_id=workspace_id,
        )

        # Apply security checks
        if security_manager is not None:
            # Check if message content is allowed
            security_result = await security_manager.check_message_content(
                message=message,
                context=context,
            )

            if not security_result.allowed:
                logger.warning(
                    f"Message blocked by security policy: {security_result.reason}"
                )
                return MessageResponse(
                    content=f"I'm unable to process that request: {security_result.reason}",
                    metadata={
                        "blocked": True,
                        "reason": security_result.reason,
                        "session_id": str(session_id),
                        "workspace_id": str(workspace_id),
                    },
                )

        # Prepare message for dispatcher
        dispatch_message = {
            "content": content,
            "role": role,
            "id": message.id,
            "timestamp": message.timestamp.isoformat(),
            "metadata": metadata,
        }

        # Prepare context for dispatcher
        dispatch_context = {
            "session_id": session_id,
            "workspace_id": workspace_id,
            "message_count": len(context.messages),
            "entity_count": len(context.entities),
        }

        # Dispatch message to handlers
        if dispatcher:
            results = await dispatcher.dispatch(
                message_type="message",
                message=dispatch_message,
                context=dispatch_context,
                session_id=session_id,
                workspace_id=workspace_id,
            )
        else:
            # Fallback if dispatcher is not available
            logger.warning("Dispatcher not available, using fallback response")
            results = [
                {
                    "content": "I've received your message, but the system is still initializing. Please try again later.",
                    "metadata": {"fallback": True},
                }
            ]

        # Process results
        if results and len(results) > 0:
            # Use the first result as the response
            result = results[0]
            response_content = result.get("content", "I've processed your message.")
            response_metadata = result.get("metadata", {})

            # Add session and workspace IDs to response metadata
            response_metadata.update(
                {
                    "session_id": str(session_id),
                    "workspace_id": str(workspace_id),
                }
            )

            # Create response
            response = MessageResponse(
                content=response_content,
                metadata=response_metadata,
            )

            # Add response to context
            response_message = Message(
                role="assistant",
                content=response_content,
                metadata=response_metadata,
            )

            await context_manager.update_context(
                session_id=session_id,
                workspace_id=workspace_id,
                context_update=ContextUpdate(add_messages=[response_message]),
            )

            logger.info(f"Message processed, response ID: {response.id}")
            return response

        else:
            # No results, return a default response
            default_response = MessageResponse(
                content="I've received your message, but I'm not sure how to respond.",
                metadata={
                    "default": True,
                    "session_id": str(session_id),
                    "workspace_id": str(workspace_id),
                },
            )

            logger.warning("No handler results, returning default response")
            return default_response

    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)

        # Return error response
        return MessageResponse(
            content="I encountered an error while processing your message. Please try again later.",
            metadata={
                "error": True,
                "message": str(e),
                "session_id": str(session_id) if session_id else None,
                "workspace_id": str(workspace_id) if workspace_id else None,
            },
        )


async def mock_message_handler(
    message: Dict[str, Any], context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Mock message handler for testing

    This is a simple handler that echoes back the message content with
    some additional information. In a real system, this would implement
    actual message processing logic or call an AI model.

    Args:
        message: Message content
        context: Message context

    Returns:
        Handler response
    """
    logger.info("Mock message handler called")

    message_content = message.get("content", "")

    # Simple echo response
    response = {
        "content": f'I received your message: "{message_content}"',
        "metadata": {
            "handler": "mock_message_handler",
            "timestamp": datetime.utcnow().isoformat(),
        },
    }

    return response


# Use the mock handler as the message handler for now
# In a real system, this would be replaced with a more sophisticated handler
message_handler = mock_message_handler


# Export public symbols
__all__ = [
    "MessageResponse",
    "process_message",
    "message_handler",
]
