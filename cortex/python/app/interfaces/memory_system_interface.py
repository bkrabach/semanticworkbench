"""
Memory System Interface

This module defines the abstract interface for memory system components.
It specifies the required methods and types for any memory system implementation.
"""

import abc
import uuid
from datetime import datetime
from typing import Any, AsyncIterator, Dict, Generic, List, Optional, TypeVar, Union

# Define a generic type parameter for different types of memory items
T = TypeVar("T")


class MemorySystemInterface(Generic[T], abc.ABC):
    """
    Abstract interface for memory system implementations

    This interface defines the contract that any memory system implementation
    must fulfill, including methods for storing, retrieving, and
    manipulating memory items.

    Args:
        T: The type of memory items this system handles
    """

    @abc.abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the memory system

        This method should set up any necessary resources or connections
        required by the memory system implementation.
        """
        pass

    @abc.abstractmethod
    async def shutdown(self) -> None:
        """
        Shut down the memory system

        This method should clean up any resources or connections
        used by the memory system implementation.
        """
        pass

    @abc.abstractmethod
    async def create_item(
        self,
        workspace_id: uuid.UUID,
        owner_id: uuid.UUID,
        item_type: Any,
        content: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        parent_id: Optional[uuid.UUID] = None,
        ttl: Optional[int] = None,
        **kwargs,
    ) -> T:
        """
        Create a new memory item

        Args:
            workspace_id: The workspace this item belongs to
            owner_id: The user ID of the item's owner
            item_type: The type of memory item
            content: The content of the memory item
            metadata: Optional metadata associated with the item
            parent_id: Optional parent item ID for hierarchical relationships
            ttl: Optional time-to-live in seconds

        Returns:
            The created memory item
        """
        pass

    @abc.abstractmethod
    async def get_item(
        self, workspace_id: uuid.UUID, item_id: uuid.UUID, **kwargs
    ) -> Optional[T]:
        """
        Get a memory item by ID

        Args:
            workspace_id: The workspace to look in
            item_id: The ID of the item to retrieve

        Returns:
            The memory item or None if not found
        """
        pass

    @abc.abstractmethod
    async def update_item(
        self,
        workspace_id: uuid.UUID,
        item_id: uuid.UUID,
        content: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None,
        **kwargs,
    ) -> Optional[T]:
        """
        Update a memory item

        Args:
            workspace_id: The workspace the item belongs to
            item_id: The ID of the item to update
            content: Optional new content for the item
            metadata: Optional metadata to update or add
            ttl: Optional new time-to-live in seconds

        Returns:
            The updated memory item or None if not found
        """
        pass

    @abc.abstractmethod
    async def delete_item(
        self,
        workspace_id: uuid.UUID,
        item_id: uuid.UUID,
        recursive: bool = True,
        **kwargs,
    ) -> bool:
        """
        Delete a memory item

        Args:
            workspace_id: The workspace the item belongs to
            item_id: The ID of the item to delete
            recursive: Whether to delete child items recursively

        Returns:
            True if the item was deleted, False otherwise
        """
        pass

    @abc.abstractmethod
    async def list_items(
        self,
        workspace_id: uuid.UUID,
        item_types: Optional[List[Any]] = None,
        owner_id: Optional[uuid.UUID] = None,
        parent_id: Optional[uuid.UUID] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
        **kwargs,
    ) -> List[T]:
        """
        List memory items with filtering

        Args:
            workspace_id: The workspace to list items from
            item_types: Optional list of item types to filter by
            owner_id: Optional owner ID to filter by
            parent_id: Optional parent ID to filter by
            metadata_filter: Optional metadata key/value pairs to filter by
            limit: Maximum number of items to return
            offset: Number of items to skip

        Returns:
            List of memory items matching the criteria
        """
        pass

    @abc.abstractmethod
    async def count_items(
        self,
        workspace_id: uuid.UUID,
        item_types: Optional[List[Any]] = None,
        owner_id: Optional[uuid.UUID] = None,
        parent_id: Optional[uuid.UUID] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> int:
        """
        Count memory items matching criteria

        Args:
            workspace_id: The workspace to count items from
            item_types: Optional list of item types to filter by
            owner_id: Optional owner ID to filter by
            parent_id: Optional parent ID to filter by
            metadata_filter: Optional metadata key/value pairs to filter by

        Returns:
            Count of memory items matching the criteria
        """
        pass

    @abc.abstractmethod
    async def search(
        self,
        workspace_id: uuid.UUID,
        query: str,
        item_types: Optional[List[Any]] = None,
        limit: int = 20,
        **kwargs,
    ) -> List[T]:
        """
        Search for memory items

        Args:
            workspace_id: The workspace to search in
            query: The search query
            item_types: Optional list of item types to filter by
            limit: Maximum number of results to return

        Returns:
            List of memory items matching the search query
        """
        pass

    @abc.abstractmethod
    async def get_child_items(
        self,
        workspace_id: uuid.UUID,
        parent_id: uuid.UUID,
        item_types: Optional[List[Any]] = None,
        **kwargs,
    ) -> List[T]:
        """
        Get child memory items for a parent

        Args:
            workspace_id: The workspace to look in
            parent_id: The parent item ID to find children for
            item_types: Optional list of item types to filter by

        Returns:
            List of child memory items
        """
        pass

    @abc.abstractmethod
    async def stream_updates(
        self, workspace_id: uuid.UUID, item_id: Optional[uuid.UUID] = None, **kwargs
    ) -> AsyncIterator[T]:
        """
        Stream real-time updates to memory items

        Args:
            workspace_id: The workspace to stream updates from
            item_id: Optional specific item ID to watch

        Yields:
            Memory items as they are created, updated, or deleted
        """
        pass
