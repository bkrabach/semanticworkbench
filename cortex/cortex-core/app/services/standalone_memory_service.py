"""
Standalone Memory Service.

This module implements a standalone Memory Service that serves
MCP tools and resources over HTTP and SSE.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from app.core.repository import RepositoryManager
from app.database.unit_of_work import UnitOfWork
from app.models import Message

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Memory Service",
    description="MCP Memory Service for storing and retrieving data",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOW_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global repository manager
repository_manager = RepositoryManager()


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize the service on startup."""
    logger.info("Initializing database connection...")
    from app.database.connection import init_db

    await init_db()

    logger.info("Initializing repository manager...")
    await repository_manager.initialize()

    logger.info("Memory Service started successfully")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Clean up resources on shutdown."""
    logger.info("Shutting down Memory Service...")
    # Any cleanup code here


@app.get("/health")
async def health_check() -> Dict[str, str] | JSONResponse:
    """Health check endpoint for service discovery."""
    # Check database connectivity
    try:
        async with UnitOfWork.for_transaction() as uow:
            # Simple query to verify database connection
            message_repo = uow.repositories.get_message_repository()
            await message_repo.count({})
            await uow.commit()
            return {"status": "healthy"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(status_code=500, content={"status": "unhealthy", "error": str(e)})


@app.post("/tool/{tool_name}")
async def call_tool(tool_name: str, request: Request):
    """
    Endpoint for calling a tool on the Memory Service.

    Args:
        tool_name: The name of the tool to call
        request: The HTTP request containing tool arguments

    Returns:
        The tool result
    """
    # Parse request body
    try:
        body = await request.json()
        arguments = body.get("arguments", {})
    except Exception as e:
        logger.error(f"Invalid request body: {e}")
        raise HTTPException(
            status_code=400, detail={"error": {"code": "invalid_request", "message": "Invalid request body"}}
        )

    # Call the appropriate tool based on the tool name
    try:
        if tool_name == "store_input":
            result = await store_input(**arguments)
        elif tool_name == "update_message":
            result = await update_message(**arguments)
        elif tool_name == "delete_message":
            result = await delete_message(**arguments)
        elif tool_name == "get_message":
            result = await get_message(**arguments)
        else:
            raise HTTPException(
                status_code=404,
                detail={"error": {"code": "tool_not_found", "message": f"Tool '{tool_name}' not found"}},
            )

        return {"result": result}
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "tool_execution_error",
                    "message": f"Error executing tool: {str(e)}",
                    "details": {"tool_name": tool_name},
                }
            },
        )


@app.get("/resource/{resource_path:path}")
async def get_resource(resource_path: str, request: Request):
    """
    Endpoint for accessing a resource stream.

    Args:
        resource_path: The resource path
        request: The HTTP request

    Returns:
        SSE stream of resource data
    """
    # Parse the resource path to determine which resource to access
    parts = resource_path.split("/")
    resource_type = parts[0] if parts else ""

    try:
        if resource_type == "history":
            # Format: history/{user_id}
            if len(parts) < 2:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": {
                            "code": "invalid_resource_path",
                            "message": "Invalid resource path for history. Format: history/{user_id}",
                        }
                    },
                )

            user_id = parts[1]

            # Check for limit parameter
            limit = None
            if len(parts) >= 4 and parts[2] == "limit":
                try:
                    limit = int(parts[3])
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail={"error": {"code": "invalid_parameter", "message": "Invalid limit parameter"}},
                    )

            # Create SSE stream for history data
            return StreamingResponse(get_history_stream(user_id, limit), media_type="text/event-stream")

        elif resource_type == "conversation":
            # Format: conversation/{conversation_id}
            if len(parts) < 2:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": {
                            "code": "invalid_resource_path",
                            "message": "Invalid resource path for conversation. Format: conversation/{conversation_id}",
                        }
                    },
                )

            conversation_id = parts[1]

            # Check if this is a user-specific request
            user_id = None
            if len(parts) >= 4 and parts[2] == "user":
                user_id = parts[3]

            # Create SSE stream for conversation data
            return StreamingResponse(get_conversation_stream(conversation_id, user_id), media_type="text/event-stream")

        else:
            raise HTTPException(
                status_code=404,
                detail={"error": {"code": "resource_not_found", "message": f"Resource '{resource_path}' not found"}},
            )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error accessing resource {resource_path}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "resource_access_error",
                    "message": f"Error accessing resource: {str(e)}",
                    "details": {"resource_path": resource_path},
                }
            },
        )


# Tool implementations


async def store_input(user_id: str, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """
    Store input data for a specific user.

    Args:
        user_id: The unique user identifier
        input_data: The input data to store
        **kwargs: Additional arguments

    Returns:
        Status object with operation result
    """
    try:
        # Validate user_id
        if not user_id:
            return {"status": "error", "user_id": "", "error": "User ID is required"}

        # Validate input_data
        if not input_data:
            return {"status": "error", "user_id": user_id, "error": "Input data is required"}

        async with UnitOfWork.for_transaction() as uow:
            # Get the appropriate repository
            message_repo = uow.repositories.get_message_repository()

            # Create the message data
            message_data = {
                "user_id": user_id,
                "content": input_data.get("content", ""),
                "conversation_id": input_data.get("conversation_id"),
                "timestamp": input_data.get("timestamp", datetime.now().isoformat()),
                "metadata": input_data.get("metadata", {}),
            }

            # Create a Message entity
            message_entity = Message(**message_data)

            # Store the input
            message = await message_repo.create(message_entity)
            message_id = message.id

            await uow.commit()

            logger.info(f"Stored input for user {user_id}: {message_id}")

            # Return success status
            return {"status": "stored", "user_id": user_id, "item_id": message_id}
    except Exception as e:
        logger.error(f"Error storing input for user {user_id}: {e}")

        # Return error status
        return {"status": "error", "user_id": user_id, "error": str(e)}


async def update_message(user_id: str, message_id: str, updates: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """
    Update an existing message.

    Args:
        user_id: The unique user identifier
        message_id: The ID of the message to update
        updates: The fields to update
        **kwargs: Additional arguments

    Returns:
        Status object with operation result
    """
    try:
        # Validate parameters
        if not user_id or not message_id or not updates:
            return {
                "status": "error",
                "user_id": user_id,
                "message_id": message_id,
                "error": "User ID, message ID, and updates are required",
            }

        async with UnitOfWork.for_transaction() as uow:
            # Get the messages repository
            message_repo = uow.repositories.get_message_repository()

            # Find the message
            message = await message_repo.get_by_id(message_id)

            if not message or message.sender_id != user_id:
                return {
                    "status": "error",
                    "user_id": user_id,
                    "message_id": message_id,
                    "error": "Message not found or access denied",
                }

            # Create update object with only allowed fields
            update_data = {}

            if "content" in updates:
                update_data["content"] = updates["content"]

            if "metadata" in updates:
                # Merge existing metadata with updates
                metadata = {**(message.metadata or {}), **updates["metadata"]}
                update_data["metadata"] = metadata

            # Add update timestamp
            if "updated_at" not in update_data.get("metadata", {}):
                if "metadata" not in update_data:
                    update_data["metadata"] = {}
                update_data["metadata"]["updated_at"] = datetime.now().isoformat()

            # Get the message and update its properties
            message.content = update_data.get("content", message.content)
            message.metadata = update_data.get("metadata", message.metadata)

            # Update the message
            updated_message = await message_repo.update(message)
            await uow.commit()

            if updated_message:
                logger.info(f"Updated message {message_id} for user {user_id}")
                return {"status": "updated", "user_id": user_id, "message_id": message_id}
            else:
                return {
                    "status": "error",
                    "user_id": user_id,
                    "message_id": message_id,
                    "error": "Failed to update message",
                }
    except Exception as e:
        logger.error(f"Error updating message {message_id} for user {user_id}: {e}")

        return {"status": "error", "user_id": user_id, "message_id": message_id, "error": str(e)}


async def delete_message(user_id: str, message_id: str, **kwargs) -> Dict[str, Any]:
    """
    Delete a message.

    Args:
        user_id: The unique user identifier
        message_id: The ID of the message to delete
        **kwargs: Additional arguments

    Returns:
        Status object with operation result
    """
    try:
        # Validate parameters
        if not user_id or not message_id:
            return {
                "status": "error",
                "user_id": user_id,
                "message_id": message_id,
                "error": "User ID and message ID are required",
            }

        async with UnitOfWork.for_transaction() as uow:
            # Get the messages repository
            message_repo = uow.repositories.get_message_repository()

            # Get the message first to check ownership
            message = await message_repo.get_by_id(message_id)

            if not message or message.sender_id != user_id:
                return {
                    "status": "error",
                    "user_id": user_id,
                    "message_id": message_id,
                    "error": "Message not found or access denied",
                }

            # Delete the message
            deleted = await message_repo.delete(message_id)
            await uow.commit()

            if deleted:
                logger.info(f"Deleted message {message_id} for user {user_id}")
                return {"status": "deleted", "user_id": user_id, "message_id": message_id}
            else:
                return {
                    "status": "error",
                    "user_id": user_id,
                    "message_id": message_id,
                    "error": "Failed to delete message",
                }
    except Exception as e:
        logger.error(f"Error deleting message {message_id} for user {user_id}: {e}")

        return {"status": "error", "user_id": user_id, "message_id": message_id, "error": str(e)}


async def get_message(message_id: str, **kwargs) -> Optional[Dict[str, Any]]:
    """
    Get a specific message by ID.

    Args:
        message_id: The unique message identifier
        **kwargs: Additional arguments

    Returns:
        The message or None if not found
    """
    try:
        # Validate message_id
        if not message_id:
            logger.error("Empty message ID provided to get_message")
            return None

        async with UnitOfWork.for_transaction() as uow:
            # Get the messages repository
            message_repo = uow.repositories.get_message_repository()

            # Find the message
            message = await message_repo.get_by_id(message_id)

            if message:
                logger.info(f"Retrieved message {message_id}")
                # Convert domain model to dict
                return message.dict()
            else:
                logger.info(f"Message {message_id} not found")
                return None
    except Exception as e:
        logger.error(f"Error retrieving message {message_id}: {e}")
        return None


# Resource stream implementations


async def get_history_stream(user_id: str, limit: Optional[int] = None):
    """
    Generate SSE stream for user history.

    Args:
        user_id: The user ID
        limit: Optional maximum number of items

    Yields:
        SSE-formatted history items
    """
    try:
        if not user_id:
            yield f"data: {json.dumps({'error': 'User ID is required'})}\n\n"
            return

        async with UnitOfWork.for_transaction() as uow:
            message_repo = uow.repositories.get_message_repository()

            # Get messages for the user (using sender_id)
            if limit:
                messages = await message_repo.list_by_sender(user_id, limit=limit)
            else:
                messages = await message_repo.list_by_sender(user_id)

            # Convert domain models to dicts
            for message in messages:
                # Send each message as an SSE event
                yield f"data: {json.dumps(message.dict())}\n\n"

            # End of stream
            yield f"data: {json.dumps({'end': True})}\n\n"
    except Exception as e:
        logger.error(f"Error streaming history for user {user_id}: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


async def get_conversation_stream(conversation_id: str, user_id: Optional[str] = None):
    """
    Generate SSE stream for conversation messages.

    Args:
        conversation_id: The conversation ID
        user_id: Optional user ID to filter messages

    Yields:
        SSE-formatted conversation messages
    """
    try:
        if not conversation_id:
            yield f"data: {json.dumps({'error': 'Conversation ID is required'})}\n\n"
            return

        async with UnitOfWork.for_transaction() as uow:
            # First, check if the conversation exists
            conversation_repo = uow.repositories.get_conversation_repository()
            conversation = await conversation_repo.get_by_id(conversation_id)
            
            if not conversation:
                logger.warning(f"Conversation {conversation_id} does not exist in Memory Service")
                # Instead of returning error, return an empty set with end marker
                # This aligns with the principle that no messages is a valid state
                yield f"data: {json.dumps({'end': True})}\n\n"
                return
                
            message_repo = uow.repositories.get_message_repository()

            # Get messages for the conversation
            # We'll get all messages for the conversation first
            messages = await message_repo.list_by_conversation(conversation_id)

            # If user_id is provided, filter the messages client-side
            if user_id:
                # Keep only messages sent by the user
                messages = [m for m in messages if m.sender_id == user_id]

            # Convert domain models to dicts
            for message in messages:
                # Send each message as an SSE event
                yield f"data: {json.dumps(message.dict())}\n\n"

            # End of stream
            yield f"data: {json.dumps({'end': True})}\n\n"
    except Exception as e:
        logger.error(f"Error streaming conversation {conversation_id}: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)

    # Get port from environment or use default
    port = int(os.getenv("MEMORY_SERVICE_PORT", 9000))

    # Start server
    uvicorn.run("app.services.standalone_memory_service:app", host="0.0.0.0", port=port, log_level="info")
