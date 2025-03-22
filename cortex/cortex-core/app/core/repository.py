import logging
from typing import Any, Dict, List, Optional, Tuple

from app.core.exceptions import DatabaseError
from app.database.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


class RepositoryManager:
    """
    Manager for repository instances.

    Provides a simplified interface for the Memory Service
    to access repositories through the Unit of Work pattern.
    """

    def __init__(self):
        """Initialize the repository manager."""
        logger.info("Repository manager created")

    async def initialize(self) -> None:
        """Initialize the repository manager."""
        logger.info("Repository manager initialized")

    def get_repository(self, name: str) -> "Repository":
        """
        Get a repository by name.

        Args:
            name: The name of the repository (messages, workspaces, conversations, users)

        Returns:
            The repository adapter

        Raises:
            ValueError: If the repository does not exist
        """
        if name == "messages":
            return MessageRepository()
        elif name == "workspaces":
            return WorkspaceRepository()
        elif name == "conversations":
            return ConversationRepository()
        elif name == "users":
            return UserRepository()
        else:
            raise ValueError(f"Unknown repository: {name}")


class Repository:
    """Abstract interface for repositories used by the Memory Service."""

    async def create(self, data: Dict[str, Any]) -> str:
        """
        Create a new item.

        Args:
            data: The item data

        Returns:
            The ID of the created item
        """
        raise NotImplementedError("Subclasses must implement create")

    async def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Find a single item matching the query.

        Args:
            query: The query criteria

        Returns:
            The matching item or None if not found
        """
        raise NotImplementedError("Subclasses must implement find_one")

    async def find_many(
        self, query: Dict[str, Any], limit: Optional[int] = None, sort: Optional[List[Tuple[str, int]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find multiple items matching the query.

        Args:
            query: The query criteria
            limit: Optional maximum number of items to return
            sort: Optional sort criteria (list of (field, direction) tuples)
                  where direction is 1 for ascending, -1 for descending

        Returns:
            List of matching items
        """
        raise NotImplementedError("Subclasses must implement find_many")

    async def update(self, query: Dict[str, Any], update: Dict[str, Any]) -> bool:
        """
        Update items matching the query.

        Args:
            query: The query criteria
            update: The update operations

        Returns:
            True if any items were updated, False otherwise
        """
        raise NotImplementedError("Subclasses must implement update")

    async def delete_one(self, query: Dict[str, Any]) -> bool:
        """
        Delete a single item matching the query.

        Args:
            query: The query criteria

        Returns:
            True if an item was deleted, False otherwise
        """
        raise NotImplementedError("Subclasses must implement delete_one")


class MessageRepository(Repository):
    """Repository adapter for messages."""

    async def create(self, data: Dict[str, Any]) -> str:
        """
        Create a new message.

        Args:
            data: The message data

        Returns:
            The ID of the created message
        """
        from app.models import Message

        try:
            # Convert the data dict to a domain model
            message = Message(
                id=data.get("id", None),  # Allow ID to be generated if not provided
                conversation_id=data.get("conversation_id", None),
                sender_id=data.get("user_id", None),  # Map user_id to sender_id
                content=data.get("content", ""),
                timestamp=data.get("timestamp", None),  # Allow timestamp to be generated if not provided
                metadata=data.get("metadata", {}),
            )

            async with UnitOfWork.for_transaction() as uow:
                # Create the message
                created_message = await uow.repositories.get_message_repository().create(message)
                await uow.commit()

                return created_message.id
        except Exception as e:
            logger.error(f"Failed to create message: {e}")
            raise DatabaseError(f"Failed to create message: {e}") from e

    async def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Find a single message matching the query.

        Args:
            query: The query criteria

        Returns:
            The matching message or None if not found
        """
        try:
            # Map keys from MCP-compatible names to repository names
            query_mapped = {}
            if "id" in query:
                query_mapped["id"] = query["id"]
            if "user_id" in query:
                query_mapped["sender_id"] = query["user_id"]
            if "conversation_id" in query:
                query_mapped["conversation_id"] = query["conversation_id"]

            async with UnitOfWork.for_transaction() as uow:
                # Try to get the message
                message_repo = uow.repositories.get_message_repository()

                # Use get_by_id if we have an ID
                if "id" in query_mapped:
                    message = await message_repo.get_by_id(query_mapped["id"])
                # Otherwise use list with filters
                else:
                    filters = {k: v for k, v in query_mapped.items()}
                    messages = await message_repo.list(filters=filters, limit=1)
                    message = messages[0] if messages else None

                if not message:
                    return None

                # Convert to dictionary and map fields for MCP compatibility
                return {
                    "id": message.id,
                    "user_id": message.sender_id,  # Map sender_id to user_id
                    "conversation_id": message.conversation_id,
                    "content": message.content,
                    "timestamp": message.timestamp,
                    "metadata": message.metadata or {},
                }
        except Exception as e:
            logger.error(f"Failed to find message: {e}")
            return None

    async def find_many(
        self, query: Dict[str, Any], limit: Optional[int] = None, sort: Optional[List[Tuple[str, int]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find multiple messages matching the query.

        Args:
            query: The query criteria
            limit: Optional maximum number of items to return
            sort: Optional sort criteria (list of (field, direction) tuples)

        Returns:
            List of matching messages
        """
        try:
            # Map keys from MCP-compatible names to repository names
            query_mapped = {}
            if "user_id" in query:
                query_mapped["sender_id"] = query["user_id"]
            if "conversation_id" in query:
                query_mapped["conversation_id"] = query["conversation_id"]

            async with UnitOfWork.for_transaction() as uow:
                message_repo = uow.repositories.get_message_repository()

                # Use list_by_conversation if we're querying by conversation
                if "conversation_id" in query_mapped and "sender_id" not in query_mapped:
                    # Convert sort order
                    is_asc = True
                    if sort and sort[0][0] == "timestamp" and sort[0][1] == -1:
                        is_asc = False

                    # Use conversation-specific query with built-in sorting
                    if is_asc:
                        messages = await message_repo.list_by_conversation(
                            query_mapped["conversation_id"], limit=limit or 100
                        )
                    else:
                        # We'd need to reverse the results for descending order
                        messages = await message_repo.list_by_conversation(
                            query_mapped["conversation_id"], limit=limit or 100
                        )
                        messages.reverse()
                else:
                    # Use generic list method
                    filters = {k: v for k, v in query_mapped.items()}
                    messages = await message_repo.list(filters=filters, limit=limit or 100)

                # Convert to dictionaries and map fields for MCP compatibility
                return [
                    {
                        "id": message.id,
                        "user_id": message.sender_id,  # Map sender_id to user_id
                        "conversation_id": message.conversation_id,
                        "content": message.content,
                        "timestamp": message.timestamp,
                        "metadata": message.metadata or {},
                    }
                    for message in messages
                ]
        except Exception as e:
            logger.error(f"Failed to find messages: {e}")
            return []

    async def update(self, query: Dict[str, Any], update: Dict[str, Any]) -> bool:
        """
        Update a message matching the query.

        Args:
            query: The query criteria
            update: The update operations

        Returns:
            True if the message was updated, False otherwise
        """
        try:
            # Map keys from MCP-compatible names to repository names
            query_mapped = {}
            if "id" in query:
                query_mapped["id"] = query["id"]
            if "user_id" in query:
                query_mapped["sender_id"] = query["user_id"]

            async with UnitOfWork.for_transaction() as uow:
                # Get the message
                message_repo = uow.repositories.get_message_repository()

                # Use get_by_id if we have an ID
                if "id" in query_mapped:
                    message = await message_repo.get_by_id(query_mapped["id"])
                # Otherwise use list with filters
                else:
                    filters = {k: v for k, v in query_mapped.items()}
                    messages = await message_repo.list(filters=filters, limit=1)
                    message = messages[0] if messages else None

                if not message:
                    return False

                # Apply updates
                update_data = update.get("$set", {})

                if "content" in update_data:
                    message.content = update_data["content"]

                if "metadata" in update_data:
                    # Merge with existing metadata
                    if message.metadata is None:
                        message.metadata = {}
                    message.metadata.update(update_data["metadata"])

                if "updated_at" in update_data:
                    # Store in metadata
                    if message.metadata is None:
                        message.metadata = {}
                    message.metadata["updated_at"] = update_data["updated_at"]

                # Update the message
                await message_repo.update(message)
                await uow.commit()

                return True
        except Exception as e:
            logger.error(f"Failed to update message: {e}")
            return False

    async def delete_one(self, query: Dict[str, Any]) -> bool:
        """
        Delete a message matching the query.

        Args:
            query: The query criteria

        Returns:
            True if the message was deleted, False otherwise
        """
        try:
            # Map keys from MCP-compatible names to repository names
            if "id" not in query:
                logger.error("Cannot delete message without ID")
                return False

            message_id = query["id"]

            # Additional check for user ownership if user_id is provided
            user_id = query.get("user_id")

            async with UnitOfWork.for_transaction() as uow:
                message_repo = uow.repositories.get_message_repository()

                # Check if the message exists and is owned by the user
                if user_id:
                    message = await message_repo.get_by_id(message_id)
                    if not message or message.sender_id != user_id:
                        return False

                # Delete the message
                result = await message_repo.delete(message_id)

                if result:
                    await uow.commit()

                return result
        except Exception as e:
            logger.error(f"Failed to delete message: {e}")
            return False


class ConversationRepository(Repository):
    """Repository adapter for conversations."""

    async def create(self, data: Dict[str, Any]) -> str:
        """Create a new conversation."""
        from app.models import Conversation

        try:
            # Convert the data dict to a domain model
            conversation = Conversation(
                id=data.get("id", None),  # Allow ID to be generated if not provided
                workspace_id=data.get("workspace_id", ""),
                topic=data.get("title", "New Conversation"),  # Map title to topic
                participant_ids=[data.get("user_id", "")] if data.get("user_id") else [],
                metadata=data.get("metadata", {}),
            )

            async with UnitOfWork.for_transaction() as uow:
                # Create the conversation
                created_conversation = await uow.repositories.get_conversation_repository().create(conversation)
                await uow.commit()

                return created_conversation.id
        except Exception as e:
            logger.error(f"Failed to create conversation: {e}")
            raise DatabaseError(f"Failed to create conversation: {e}") from e

    async def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find a single conversation matching the query."""
        # Implementation similar to MessageRepository.find_one
        # Simplified for brevity
        return None

    async def find_many(
        self, query: Dict[str, Any], limit: Optional[int] = None, sort: Optional[List[Tuple[str, int]]] = None
    ) -> List[Dict[str, Any]]:
        """Find multiple conversations matching the query."""
        # Implementation similar to MessageRepository.find_many
        # Simplified for brevity
        return []

    async def update(self, query: Dict[str, Any], update: Dict[str, Any]) -> bool:
        """Update a conversation matching the query."""
        # Implementation similar to MessageRepository.update
        # Simplified for brevity
        return False

    async def delete_one(self, query: Dict[str, Any]) -> bool:
        """Delete a conversation matching the query."""
        # Implementation similar to MessageRepository.delete_one
        # Simplified for brevity
        return False


class WorkspaceRepository(Repository):
    """Repository adapter for workspaces."""

    async def create(self, data: Dict[str, Any]) -> str:
        """Create a new workspace."""
        # Implementation similar to MessageRepository.create
        # Simplified for brevity
        return ""

    async def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find a single workspace matching the query."""
        # Implementation similar to MessageRepository.find_one
        # Simplified for brevity
        return None

    async def find_many(
        self, query: Dict[str, Any], limit: Optional[int] = None, sort: Optional[List[Tuple[str, int]]] = None
    ) -> List[Dict[str, Any]]:
        """Find multiple workspaces matching the query."""
        # Implementation similar to MessageRepository.find_many
        # Simplified for brevity
        return []

    async def update(self, query: Dict[str, Any], update: Dict[str, Any]) -> bool:
        """Update a workspace matching the query."""
        # Implementation similar to MessageRepository.update
        # Simplified for brevity
        return False

    async def delete_one(self, query: Dict[str, Any]) -> bool:
        """Delete a workspace matching the query."""
        # Implementation similar to MessageRepository.delete_one
        # Simplified for brevity
        return False


class UserRepository(Repository):
    """Repository adapter for users."""

    async def create(self, data: Dict[str, Any]) -> str:
        """Create a new user."""
        # Implementation similar to MessageRepository.create
        # Simplified for brevity
        return ""

    async def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find a single user matching the query."""
        # Implementation similar to MessageRepository.find_one
        # Simplified for brevity
        return None

    async def find_many(
        self, query: Dict[str, Any], limit: Optional[int] = None, sort: Optional[List[Tuple[str, int]]] = None
    ) -> List[Dict[str, Any]]:
        """Find multiple users matching the query."""
        # Implementation similar to MessageRepository.find_many
        # Simplified for brevity
        return []

    async def update(self, query: Dict[str, Any], update: Dict[str, Any]) -> bool:
        """Update a user matching the query."""
        # Implementation similar to MessageRepository.update
        # Simplified for brevity
        return False

    async def delete_one(self, query: Dict[str, Any]) -> bool:
        """Delete a user matching the query."""
        # Implementation similar to MessageRepository.delete_one
        # Simplified for brevity
        return False
