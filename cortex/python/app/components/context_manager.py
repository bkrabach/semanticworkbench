"""
Context Manager Component

This module implements a context manager that maintains and organizes
conversation context, entities, and metadata. It provides functions
for retrieving, updating, and pruning context information.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

from fastapi import HTTPException, status
from pydantic import BaseModel, Field

from app.cache.redis import redis_cache
from app.config import settings
from app.interfaces.memory_system_interface import MemorySystemInterface
from app.utils.logger import get_contextual_logger

# Configure logger
logger = get_contextual_logger("components.context_manager")


class Message(BaseModel):
    """Message model representing a conversation message"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: str = Field(
        ..., description="Role of the message sender (user, assistant, system)"
    )
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "role": "user",
                "content": "How can I use the context manager?",
                "timestamp": "2025-03-06T15:30:45.123456",
                "metadata": {"source": "web_client", "session_id": "abc123"},
            }
        }


class Entity(BaseModel):
    """Entity model representing a named entity in the context"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    name: str
    properties: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440001",
                "type": "person",
                "name": "Jane Doe",
                "properties": {"email": "jane@example.com", "role": "admin"},
            }
        }


class Context(BaseModel):
    """Context model representing the current conversation context"""

    messages: List[Message] = Field(default_factory=list)
    entities: List[Entity] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class ContextUpdate(BaseModel):
    """Model for context updates"""

    add_messages: Optional[List[Message]] = None
    remove_message_ids: Optional[List[str]] = None
    add_entities: Optional[List[Entity]] = None
    remove_entity_ids: Optional[List[str]] = None
    update_metadata: Optional[Dict[str, Any]] = None


class ContextManager:
    """
    Context Manager for maintaining conversation context

    This class manages context for conversations, including messages,
    entities, and metadata. It provides methods for retrieving,
    updating, and pruning context information.
    """

    CONTEXT_CACHE_PREFIX = "context:"
    CONTEXT_CACHE_TTL = 3600  # 1 hour in seconds

    def __init__(self, memory_system: MemorySystemInterface):
        """
        Initialize the context manager

        Args:
            memory_system: Implementation of the memory system interface
        """
        self.memory_system = memory_system
        logger.info("Context manager initialized")

    async def get_context(
        self,
        session_id: uuid.UUID,
        workspace_id: uuid.UUID,
        query: Optional[str] = None,
    ) -> Context:
        """
        Get context relevant to a specific query or task

        Args:
            session_id: The session ID
            workspace_id: The workspace ID
            query: Optional query to filter relevant context

        Returns:
            The context object
        """
        try:
            logger.info(
                f"Getting context for session {session_id}, workspace {workspace_id}"
            )

            # Try to get from cache first
            cache_key = self._get_cache_key(session_id, workspace_id)
            cached_context = await redis_cache.get(key=cache_key)

            if cached_context:
                logger.debug(f"Retrieved context from cache for session {session_id}")
                context = Context(**cached_context)

                # If no query, return cached context
                if not query:
                    return context

                # With query, we still need to get synthesized context from memory system

            # Prepare memory query with workspace UUID
            memory_query = {
                "contentQuery": query,
                "includeExpired": False,
                "limit": 50,  # Reasonable default
            }

            # Get synthesized memory from memory system
            synthesized_memory = await self.memory_system.search(
                workspace_id=workspace_id, query=query or "", limit=50
            )

            # Convert memory items to context format
            messages = []
            entities = []

            for item in synthesized_memory:
                if item.type == "conversation":
                    # If item content has the expected fields, convert to Message
                    if "role" in item.content and "content" in item.content:
                        message = Message(
                            id=str(item.id),
                            role=item.content["role"],
                            content=item.content["content"],
                            timestamp=item.created_at,
                            metadata=item.metadata,
                        )
                        messages.append(message)
                elif item.type in ["person", "organization", "location", "custom"]:
                    # If this is an entity type, convert to Entity
                    entity = Entity(
                        id=str(item.id),
                        type=item.type,
                        name=item.content.get("name", "Unnamed"),
                        properties=item.content,
                    )
                    entities.append(entity)

            # Create context
            context = Context(
                messages=messages,
                entities=entities,
                metadata={},  # Initialize empty, will be populated from memory items
                last_updated=datetime.utcnow(),
            )

            # Cache the context
            await self._cache_context(session_id, workspace_id, context)

            return context

        except Exception as e:
            logger.error(f"Failed to get context: {str(e)}", exc_info=True)

            # Return empty context on error
            return Context(
                messages=[], entities=[], metadata={}, last_updated=datetime.utcnow()
            )

    async def update_context(
        self,
        session_id: uuid.UUID,
        workspace_id: uuid.UUID,
        context_update: ContextUpdate,
    ) -> None:
        """
        Update the context with new information

        Args:
            session_id: The session ID
            workspace_id: The workspace ID
            context_update: The updates to apply to the context

        Raises:
            HTTPException: If an error occurs during update
        """
        try:
            logger.info(
                f"Updating context for session {session_id}, workspace {workspace_id}"
            )

            # Get current context
            current_context = await self.get_context(session_id, workspace_id)

            # Process message additions
            if context_update.add_messages:
                for message in context_update.add_messages:
                    # Ensure message has an ID
                    if not message.id:
                        message.id = str(uuid.uuid4())

                    # Store in memory system
                    await self.memory_system.create_item(
                        workspace_id=workspace_id,
                        owner_id=uuid.UUID(
                            session_id.hex
                        ),  # Using session ID as owner ID
                        item_type="conversation",
                        content={"role": message.role, "content": message.content},
                        metadata=message.metadata or {},
                        ttl=settings.default_memory_ttl,
                    )

                    # Add to current context
                    current_context.messages.append(message)

            # Process message removals
            if context_update.remove_message_ids:
                for message_id in context_update.remove_message_ids:
                    # Remove from memory system
                    await self.memory_system.delete_item(
                        workspace_id=workspace_id, item_id=uuid.UUID(message_id)
                    )

                    # Remove from current context
                    current_context.messages = [
                        m for m in current_context.messages if m.id != message_id
                    ]

            # Process entity additions
            if context_update.add_entities:
                for entity in context_update.add_entities:
                    # Ensure entity has an ID
                    if not entity.id:
                        entity.id = str(uuid.uuid4())

                    # Store in memory system
                    await self.memory_system.create_item(
                        workspace_id=workspace_id,
                        owner_id=uuid.UUID(
                            session_id.hex
                        ),  # Using session ID as owner ID
                        item_type=entity.type,
                        content={"name": entity.name, **entity.properties},
                        metadata={
                            "entity_type": entity.type,
                            "entity_name": entity.name,
                        },
                        ttl=settings.default_memory_ttl,
                    )

                    # Add to current context
                    current_context.entities.append(entity)

            # Process entity removals
            if context_update.remove_entity_ids:
                for entity_id in context_update.remove_entity_ids:
                    # Remove from memory system
                    await self.memory_system.delete_item(
                        workspace_id=workspace_id, item_id=uuid.UUID(entity_id)
                    )

                    # Remove from current context
                    current_context.entities = [
                        e for e in current_context.entities if e.id != entity_id
                    ]

            # Update metadata
            if context_update.update_metadata:
                # Update metadata by merging dictionaries
                current_context.metadata = {
                    **current_context.metadata,
                    **context_update.update_metadata,
                }

            # Update last updated timestamp
            current_context.last_updated = datetime.utcnow()

            # Cache updated context
            await self._cache_context(session_id, workspace_id, current_context)

        except Exception as e:
            logger.error(f"Failed to update context: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update context: {str(e)}",
            )

    async def prune_context(
        self,
        session_id: uuid.UUID,
        workspace_id: uuid.UUID,
        older_than: Optional[datetime] = None,
    ) -> None:
        """
        Clear outdated or irrelevant context

        Args:
            session_id: The session ID
            workspace_id: The workspace ID
            older_than: Optional date to remove context older than

        Raises:
            HTTPException: If an error occurs during pruning
        """
        try:
            logger.info(
                f"Pruning context for session {session_id}, workspace {workspace_id}"
            )

            # Get current context
            current_context = await self.get_context(session_id, workspace_id)

            if older_than:
                # Remove messages older than the specified date

                # Identify messages to keep and remove
                messages_to_keep = []
                messages_to_remove = []

                for message in current_context.messages:
                    if message.timestamp >= older_than:
                        messages_to_keep.append(message)
                    else:
                        messages_to_remove.append(message)

                # Remove messages from memory system
                for message in messages_to_remove:
                    await self.memory_system.delete_item(
                        workspace_id=workspace_id, item_id=uuid.UUID(message.id)
                    )

                # Update current context
                current_context.messages = messages_to_keep
                current_context.last_updated = datetime.utcnow()

                # Update cache
                await self._cache_context(session_id, workspace_id, current_context)
            else:
                # Clear all context for this workspace
                # This is more efficiently done by clearing the cache and letting
                # memory system handle persistence pruning
                await redis_cache.delete(
                    key=self._get_cache_key(session_id, workspace_id)
                )

        except Exception as e:
            logger.error(f"Failed to prune context: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to prune context: {str(e)}",
            )

    def _get_cache_key(self, session_id: uuid.UUID, workspace_id: uuid.UUID) -> str:
        """
        Get the cache key for a session's context in a workspace

        Args:
            session_id: The session ID
            workspace_id: The workspace ID

        Returns:
            The cache key
        """
        return f"{self.CONTEXT_CACHE_PREFIX}{session_id}:{workspace_id}"

    async def _cache_context(
        self, session_id: uuid.UUID, workspace_id: uuid.UUID, context: Context
    ) -> None:
        """
        Cache a context for fast access

        Args:
            session_id: The session ID
            workspace_id: The workspace ID
            context: The context to cache
        """
        cache_key = self._get_cache_key(session_id, workspace_id)

        await redis_cache.set(
            key=cache_key, value=context.dict(), ttl=self.CONTEXT_CACHE_TTL
        )


# Create global instance (will be initialized with the memory system later)
context_manager = None


def initialize_context_manager(memory_system: MemorySystemInterface) -> ContextManager:
    """
    Initialize the global context manager instance

    Args:
        memory_system: The memory system to use

    Returns:
        The initialized context manager
    """
    global context_manager
    if context_manager is None:
        context_manager = ContextManager(memory_system)
    return context_manager


# Export public symbols
__all__ = [
    "Message",
    "Entity",
    "Context",
    "ContextUpdate",
    "ContextManager",
    "context_manager",
    "initialize_context_manager",
]
