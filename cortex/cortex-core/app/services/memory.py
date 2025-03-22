import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

from app.core.mcp import tool, resource
from app.core.repository import RepositoryManager

logger = logging.getLogger(__name__)


class MemoryService:
    """
    MCP service for memory operations.

    This service provides tools and resources for storing and retrieving data.
    """

    def __init__(self, repository_manager: RepositoryManager):
        """
        Initialize the Memory Service.

        Args:
            repository_manager: The repository manager for data access
        """
        self.repository_manager = repository_manager
        self.initialized = False
        logger.info("Memory service created")

    async def initialize(self) -> None:
        """
        Initialize the Memory Service.

        This is called when the service is first connected to.
        """
        if self.initialized:
            return

        logger.info("Initializing Memory Service...")

        # Verify repository access
        try:
            # Test access to required repositories
            # Just verify we can access all required repositories
            self.repository_manager.get_repository("messages")
            self.repository_manager.get_repository("workspaces")
            self.repository_manager.get_repository("conversations")

            logger.info("Repository access verified")
        except Exception as e:
            logger.error(f"Failed to access repositories: {e}")
            raise

        # Set initialized flag
        self.initialized = True
        logger.info("Memory Service initialized")

    async def shutdown(self) -> None:
        """
        Shutdown the Memory Service.

        This is called when the application is shutting down.
        """
        if not self.initialized:
            return

        logger.info("Shutting down Memory Service...")

        # Perform any cleanup operations here
        # (In the in-process implementation, this may be minimal)

        # Clear initialized flag
        self.initialized = False
        logger.info("Memory Service shut down")

    # Note: The @tool decorator doesn't work properly with instance methods, 
    # so we can't use it here. In a real implementation, we'd use a proper FastMCP decorator.
    async def store_input(self, user_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store input data for a specific user.

        Args:
            user_id: The unique user identifier
            input_data: The input data to store

        Returns:
            Status object with operation result
        """
        try:
            # Validate user_id
            if not user_id:
                return {
                    "status": "error",
                    "user_id": "",
                    "error": "User ID is required"
                }

            # Validate input_data
            if not input_data:
                return {
                    "status": "error",
                    "user_id": user_id,
                    "error": "Input data is required"
                }

            # Add ID if not present
            if "id" not in input_data:
                input_data["id"] = str(uuid.uuid4())

            # Add timestamp if not present
            if "timestamp" not in input_data:
                input_data["timestamp"] = datetime.now().isoformat()

            # Get the appropriate repository
            message_repo = self.repository_manager.get_repository("messages")

            # Create the message data
            message_data = {
                "user_id": user_id,
                "content": input_data.get("content", ""),
                "conversation_id": input_data.get("conversation_id"),
                "timestamp": input_data["timestamp"],
                "metadata": input_data.get("metadata", {})
            }

            # Store the input
            message_id = await message_repo.create(message_data)

            logger.info(f"Stored input for user {user_id}: {message_id}")

            # Return success status
            return {
                "status": "stored",
                "user_id": user_id,
                "item_id": message_id
            }
        except Exception as e:
            logger.error(f"Error storing input for user {user_id}: {e}")

            # Return error status
            return {
                "status": "error",
                "user_id": user_id,
                "error": str(e)
            }

    async def update_message(
        self,
        user_id: str,
        message_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an existing message.

        Args:
            user_id: The unique user identifier
            message_id: The ID of the message to update
            updates: The fields to update

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
                    "error": "User ID, message ID, and updates are required"
                }

            # Get the messages repository
            message_repo = self.repository_manager.get_repository("messages")

            # Find the message
            message = await message_repo.find_one({
                "id": message_id,
                "user_id": user_id
            })

            if not message:
                return {
                    "status": "error",
                    "user_id": user_id,
                    "message_id": message_id,
                    "error": "Message not found or access denied"
                }

            # Create update object with only allowed fields
            update_data = {}

            if "content" in updates:
                update_data["content"] = updates["content"]

            if "metadata" in updates:
                # Merge existing metadata with updates
                metadata = {
                    **(message.get("metadata") or {}),
                    **updates["metadata"]
                }
                update_data["metadata"] = metadata

            # Add update timestamp
            update_data["updated_at"] = datetime.now().isoformat()

            # Update the message
            updated = await message_repo.update(
                {"id": message_id, "user_id": user_id},
                {"$set": update_data}
            )

            if updated:
                logger.info(f"Updated message {message_id} for user {user_id}")
                return {
                    "status": "updated",
                    "user_id": user_id,
                    "message_id": message_id
                }
            else:
                return {
                    "status": "error",
                    "user_id": user_id,
                    "message_id": message_id,
                    "error": "Failed to update message"
                }
        except Exception as e:
            logger.error(f"Error updating message {message_id} for user {user_id}: {e}")

            return {
                "status": "error",
                "user_id": user_id,
                "message_id": message_id,
                "error": str(e)
            }

    async def delete_message(self, user_id: str, message_id: str) -> Dict[str, Any]:
        """
        Delete a message.

        Args:
            user_id: The unique user identifier
            message_id: The ID of the message to delete

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
                    "error": "User ID and message ID are required"
                }

            # Get the messages repository
            message_repo = self.repository_manager.get_repository("messages")

            # Delete the message
            deleted = await message_repo.delete_one({
                "id": message_id,
                "user_id": user_id
            })

            if deleted:
                logger.info(f"Deleted message {message_id} for user {user_id}")
                return {
                    "status": "deleted",
                    "user_id": user_id,
                    "message_id": message_id
                }
            else:
                return {
                    "status": "error",
                    "user_id": user_id,
                    "message_id": message_id,
                    "error": "Message not found or access denied"
                }
        except Exception as e:
            logger.error(f"Error deleting message {message_id} for user {user_id}: {e}")

            return {
                "status": "error",
                "user_id": user_id,
                "message_id": message_id,
                "error": str(e)
            }

    async def get_history(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get history for a specific user.

        Args:
            user_id: The unique user identifier

        Returns:
            List containing the user's history
        """
        try:
            # Validate user_id
            if not user_id:
                logger.error("Empty user ID provided to get_history")
                return []

            # Get the messages repository
            message_repo = self.repository_manager.get_repository("messages")

            # Find all messages for the user
            messages = await message_repo.find_many(
                {"user_id": user_id},
                sort=[("timestamp", 1)]  # Sort by timestamp ascending
            )

            logger.info(f"Retrieved history for user {user_id}: {len(messages)} messages")
            return messages
        except Exception as e:
            logger.error(f"Error retrieving history for user {user_id}: {e}")
            return []

    async def get_limited_history(self, user_id: str, limit: str) -> List[Dict[str, Any]]:
        """
        Get limited history for a specific user.

        Args:
            user_id: The unique user identifier
            limit: Maximum number of items to return (as string)

        Returns:
            List containing the user's limited history
        """
        try:
            # Validate user_id
            if not user_id:
                logger.error("Empty user ID provided to get_limited_history")
                return []

            # Convert limit to integer
            try:
                limit_int = int(limit)
                if limit_int <= 0:
                    raise ValueError("Limit must be positive")
            except ValueError as e:
                logger.error(f"Invalid limit parameter: {e}")
                limit_int = 10  # Default limit

            # Get the messages repository
            message_repo = self.repository_manager.get_repository("messages")

            # Find messages for the user with limit
            messages = await message_repo.find_many(
                {"user_id": user_id},
                limit=limit_int,
                sort=[("timestamp", -1)]  # Sort by timestamp descending
            )

            logger.info(f"Retrieved limited history for user {user_id}: {len(messages)} messages (limit {limit})")
            return messages
        except Exception as e:
            logger.error(f"Error retrieving limited history for user {user_id}: {e}")
            return []

    async def get_conversation(self, conversation_id: str) -> List[Dict[str, Any]]:
        """
        Get messages for a specific conversation.

        Args:
            conversation_id: The unique conversation identifier

        Returns:
            List containing the conversation messages
        """
        try:
            # Validate conversation_id
            if not conversation_id:
                logger.error("Empty conversation ID provided to get_conversation")
                return []

            # Get the messages repository
            message_repo = self.repository_manager.get_repository("messages")

            # Find all messages for the conversation
            messages = await message_repo.find_many(
                {"conversation_id": conversation_id},
                sort=[("timestamp", 1)]  # Sort by timestamp ascending
            )

            logger.info(f"Retrieved conversation {conversation_id}: {len(messages)} messages")
            return messages
        except Exception as e:
            logger.error(f"Error retrieving conversation {conversation_id}: {e}")
            return []

    async def get_conversation_for_user(self, conversation_id: str, user_id: str) -> List[Dict[str, Any]]:
        """
        Get messages for a specific conversation and user.

        Args:
            conversation_id: The unique conversation identifier
            user_id: The unique user identifier

        Returns:
            List containing the conversation messages for the user
        """
        try:
            # Validate parameters
            if not conversation_id or not user_id:
                logger.error("Empty conversation ID or user ID provided to get_conversation_for_user")
                return []

            # Get the messages repository
            message_repo = self.repository_manager.get_repository("messages")

            # Find messages for the conversation and user
            messages = await message_repo.find_many(
                {
                    "conversation_id": conversation_id,
                    "user_id": user_id
                },
                sort=[("timestamp", 1)]  # Sort by timestamp ascending
            )

            logger.info(f"Retrieved conversation {conversation_id} for user {user_id}: {len(messages)} messages")
            return messages
        except Exception as e:
            logger.error(f"Error retrieving conversation {conversation_id} for user {user_id}: {e}")
            return []

    async def get_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific message by ID.

        Args:
            message_id: The unique message identifier

        Returns:
            The message or None if not found
        """
        try:
            # Validate message_id
            if not message_id:
                logger.error("Empty message ID provided to get_message")
                return None

            # Get the messages repository
            message_repo = self.repository_manager.get_repository("messages")

            # Find the message
            message = await message_repo.find_one({"id": message_id})

            if message:
                logger.info(f"Retrieved message {message_id}")
            else:
                logger.info(f"Message {message_id} not found")

            return message
        except Exception as e:
            logger.error(f"Error retrieving message {message_id}: {e}")
            return None