"""
Whiteboard Memory Component

This module implements the memory system interface for storing and retrieving
memory items. It uses SQLAlchemy models for persistence and provides search,
filtering, and hierarchical operations.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Any, AsyncIterator, Dict, List, Optional, Set, Tuple, Union, cast

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select, func, delete, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.redis import redis_cache
from app.config import settings
from app.database.connection import get_db, transactional
from app.database.models import MemoryItem, MemoryItemType, User, Workspace
from app.interfaces.memory_system_interface import MemorySystemInterface
from app.schemas.base import MemoryItemRead, PaginatedResponse
from app.utils.logger import get_contextual_logger, log_execution_time

# Configure logger
logger = get_contextual_logger("components.whiteboard_memory")


class WhiteboardMemory(MemorySystemInterface[MemoryItemRead]):
    """
    Whiteboard Memory System

    This class implements the memory system interface for storing and retrieving
    memory items. It uses SQLAlchemy for database operations and supports
    hierarchical memory items, search, and filtering.
    """

    def __init__(self):
        """Initialize the whiteboard memory system"""
        self.initialized = False
        self._bg_tasks = set()

    async def initialize(self) -> None:
        """
        Initialize the memory system

        This method sets up the memory system and any background tasks.
        """
        if self.initialized:
            logger.warning("Whiteboard memory already initialized")
            return

        logger.info("Initializing whiteboard memory system")

        # Start background tasks like expired item cleanup
        cleanup_task = asyncio.create_task(self._cleanup_expired_items_task())
        self._bg_tasks.add(cleanup_task)
        cleanup_task.add_done_callback(self._bg_tasks.discard)

        self.initialized = True
        logger.info("Whiteboard memory system initialized")

    async def shutdown(self) -> None:
        """
        Shut down the memory system

        This method cleans up resources and stops background tasks.
        """
        if not self.initialized:
            logger.warning("Whiteboard memory not initialized, nothing to shut down")
            return

        logger.info("Shutting down whiteboard memory system")

        # Cancel all background tasks
        for task in self._bg_tasks:
            task.cancel()

        # Wait for tasks to complete cancellation
        if self._bg_tasks:
            await asyncio.gather(*self._bg_tasks, return_exceptions=True)

        self.initialized = False
        logger.info("Whiteboard memory system shut down")

    async def _cleanup_expired_items_task(self) -> None:
        """
        Background task to clean up expired memory items

        This task runs periodically to delete items past their expiration time.
        """
        while True:
            try:
                logger.info("Running expired items cleanup task")

                async with get_db() as db:
                    # Find and delete expired items
                    now = datetime.utcnow()

                    # Query for expired items
                    query = select(MemoryItem.id).where(
                        and_(
                            MemoryItem.expires_at.is_not(None),
                            MemoryItem.expires_at < now,
                        )
                    )

                    result = await db.execute(query)
                    expired_ids = [row[0] for row in result.fetchall()]

                    if expired_ids:
                        # Delete expired items
                        delete_query = delete(MemoryItem).where(
                            MemoryItem.id.in_(expired_ids)
                        )
                        await db.execute(delete_query)
                        await db.commit()

                        logger.info(
                            f"Cleaned up {len(expired_ids)} expired memory items"
                        )

                # Wait for next cleanup interval (1 hour)
                await asyncio.sleep(3600)

            except asyncio.CancelledError:
                logger.info("Expired items cleanup task cancelled")
                break

            except Exception as e:
                logger.error(
                    f"Error in expired items cleanup task: {str(e)}", exc_info=True
                )
                # Wait a shorter time before retry if there was an error
                await asyncio.sleep(300)

    def _calculate_expiry(self, ttl: Optional[int] = None) -> Optional[datetime]:
        """
        Calculate expiry datetime from TTL

        Args:
            ttl: Time-to-live in seconds

        Returns:
            Expiry datetime or None if no TTL
        """
        if ttl is None:
            ttl = settings.default_memory_ttl

        if ttl <= 0:
            return None

        return datetime.utcnow() + timedelta(seconds=ttl)

    def _to_schema(self, item: MemoryItem) -> MemoryItemRead:
        """
        Convert database model to schema

        Args:
            item: Database memory item model

        Returns:
            Pydantic schema model
        """
        return MemoryItemRead.from_orm(item)

    @transactional
    async def create_item(
        self,
        workspace_id: uuid.UUID,
        owner_id: uuid.UUID,
        item_type: Any,
        content: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        parent_id: Optional[uuid.UUID] = None,
        ttl: Optional[int] = None,
        db: Optional[AsyncSession] = None,
        **kwargs,
    ) -> MemoryItemRead:
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
            db: Optional database session

        Returns:
            The created memory item

        Raises:
            HTTPException: If workspace doesn't exist or error occurs
        """
        logger.info(f"Creating memory item in workspace {workspace_id}")

        try:
            # Validate workspace exists
            workspace_query = select(Workspace).where(
                and_(Workspace.id == workspace_id, Workspace.is_active == True)
            )
            workspace_result = await db.execute(workspace_query)
            workspace = workspace_result.scalar_one_or_none()

            if not workspace:
                logger.warning(f"Workspace not found: {workspace_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Workspace not found or inactive",
                )

            # Validate owner exists
            owner_query = select(User).where(
                and_(User.id == owner_id, User.is_active == True)
            )
            owner_result = await db.execute(owner_query)
            owner = owner_result.scalar_one_or_none()

            if not owner:
                logger.warning(f"User not found: {owner_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found or inactive",
                )

            # Validate parent exists if provided
            if parent_id:
                parent_query = select(MemoryItem).where(MemoryItem.id == parent_id)
                parent_result = await db.execute(parent_query)
                parent = parent_result.scalar_one_or_none()

                if not parent:
                    logger.warning(f"Parent item not found: {parent_id}")
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Parent memory item not found",
                    )

                # Ensure parent is in the same workspace
                if parent.workspace_id != workspace_id:
                    logger.warning(
                        f"Parent item {parent_id} not in workspace {workspace_id}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Parent memory item must be in the same workspace",
                    )

            # Calculate expiry time
            expires_at = self._calculate_expiry(ttl)

            # Create item
            item = MemoryItem(
                workspace_id=workspace_id,
                owner_id=owner_id,
                type=item_type,
                content=content,
                metadata=metadata or {},
                parent_id=parent_id,
                expires_at=expires_at,
            )

            db.add(item)
            await db.flush()

            # Cache item if Redis is available
            if settings.redis_url:
                cache_key = f"item:{item.id}"
                namespace = f"workspace:{workspace_id}"
                await redis_cache.set(
                    key=cache_key,
                    value=self._to_schema(item).dict(),
                    namespace=namespace,
                    ttl=ttl if ttl else settings.redis_default_ttl,
                )

            logger.info(f"Created memory item: {item.id}")

            return self._to_schema(item)

        except HTTPException:
            # Re-raise HTTP exceptions
            raise

        except Exception as e:
            logger.error(f"Error creating memory item: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating memory item",
            )

    @transactional
    async def get_item(
        self,
        workspace_id: uuid.UUID,
        item_id: uuid.UUID,
        db: Optional[AsyncSession] = None,
        **kwargs,
    ) -> Optional[MemoryItemRead]:
        """
        Get a memory item by ID

        Args:
            workspace_id: The workspace to look in
            item_id: The ID of the item to retrieve
            db: Optional database session

        Returns:
            The memory item or None if not found
        """
        logger.debug(f"Getting memory item {item_id} from workspace {workspace_id}")

        try:
            # Check cache if Redis is available
            if settings.redis_url:
                cache_key = f"item:{item_id}"
                namespace = f"workspace:{workspace_id}"
                cached_item = await redis_cache.get(key=cache_key, namespace=namespace)

                if cached_item:
                    logger.debug(f"Found memory item {item_id} in cache")
                    return MemoryItemRead(**cached_item)

            # Get from database
            query = select(MemoryItem).where(
                and_(MemoryItem.id == item_id, MemoryItem.workspace_id == workspace_id)
            )

            result = await db.execute(query)
            item = result.scalar_one_or_none()

            if not item:
                logger.debug(f"Memory item {item_id} not found")
                return None

            # Cache item if Redis is available
            if settings.redis_url:
                cache_key = f"item:{item_id}"
                namespace = f"workspace:{workspace_id}"
                ttl = (
                    (item.expires_at - datetime.utcnow()).total_seconds()
                    if item.expires_at
                    else settings.redis_default_ttl
                )

                await redis_cache.set(
                    key=cache_key,
                    value=self._to_schema(item).dict(),
                    namespace=namespace,
                    ttl=int(ttl) if ttl > 0 else settings.redis_default_ttl,
                )

            return self._to_schema(item)

        except Exception as e:
            logger.error(f"Error getting memory item: {str(e)}", exc_info=True)
            return None

    @transactional
    async def update_item(
        self,
        workspace_id: uuid.UUID,
        item_id: uuid.UUID,
        content: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None,
        db: Optional[AsyncSession] = None,
        **kwargs,
    ) -> Optional[MemoryItemRead]:
        """
        Update a memory item

        Args:
            workspace_id: The workspace the item belongs to
            item_id: The ID of the item to update
            content: Optional new content for the item
            metadata: Optional metadata to update or add
            ttl: Optional new time-to-live in seconds
            db: Optional database session

        Returns:
            The updated memory item or None if not found
        """
        logger.info(f"Updating memory item {item_id} in workspace {workspace_id}")

        try:
            # Get item
            query = select(MemoryItem).where(
                and_(MemoryItem.id == item_id, MemoryItem.workspace_id == workspace_id)
            )

            result = await db.execute(query)
            item = result.scalar_one_or_none()

            if not item:
                logger.warning(f"Memory item {item_id} not found")
                return None

            # Update fields
            if content is not None:
                item.content = content

            if metadata is not None:
                # Merge metadata dictionaries
                item.metadata = {**item.metadata, **metadata}

            if ttl is not None:
                item.expires_at = self._calculate_expiry(ttl)

            # Update timestamp
            item.updated_at = datetime.utcnow()

            await db.flush()

            # Update cache if Redis is available
            if settings.redis_url:
                cache_key = f"item:{item_id}"
                namespace = f"workspace:{workspace_id}"
                ttl_seconds = (
                    (item.expires_at - datetime.utcnow()).total_seconds()
                    if item.expires_at
                    else settings.redis_default_ttl
                )

                await redis_cache.set(
                    key=cache_key,
                    value=self._to_schema(item).dict(),
                    namespace=namespace,
                    ttl=int(ttl_seconds)
                    if ttl_seconds > 0
                    else settings.redis_default_ttl,
                )

            logger.info(f"Updated memory item: {item_id}")

            return self._to_schema(item)

        except Exception as e:
            logger.error(f"Error updating memory item: {str(e)}", exc_info=True)
            return None

    @transactional
    async def delete_item(
        self,
        workspace_id: uuid.UUID,
        item_id: uuid.UUID,
        recursive: bool = True,
        db: Optional[AsyncSession] = None,
        **kwargs,
    ) -> bool:
        """
        Delete a memory item

        Args:
            workspace_id: The workspace the item belongs to
            item_id: The ID of the item to delete
            recursive: Whether to delete child items recursively
            db: Optional database session

        Returns:
            True if the item was deleted, False otherwise
        """
        logger.info(f"Deleting memory item {item_id} from workspace {workspace_id}")

        try:
            # Verify the item exists in the workspace
            query = select(MemoryItem).where(
                and_(MemoryItem.id == item_id, MemoryItem.workspace_id == workspace_id)
            )

            result = await db.execute(query)
            item = result.scalar_one_or_none()

            if not item:
                logger.warning(f"Memory item {item_id} not found")
                return False

            if recursive:
                # Get all child items recursively
                all_descendants = await self._get_all_descendants(
                    workspace_id, item_id, db
                )

                # Delete descendants first
                for descendant_id in all_descendants:
                    # Delete from cache if Redis is available
                    if settings.redis_url:
                        cache_key = f"item:{descendant_id}"
                        namespace = f"workspace:{workspace_id}"
                        await redis_cache.delete(key=cache_key, namespace=namespace)

                # Delete all descendants in one query
                if all_descendants:
                    delete_query = delete(MemoryItem).where(
                        MemoryItem.id.in_(all_descendants)
                    )
                    await db.execute(delete_query)

            # Delete from cache if Redis is available
            if settings.redis_url:
                cache_key = f"item:{item_id}"
                namespace = f"workspace:{workspace_id}"
                await redis_cache.delete(key=cache_key, namespace=namespace)

            # Delete the item
            await db.delete(item)

            logger.info(f"Deleted memory item: {item_id}")

            return True

        except Exception as e:
            logger.error(f"Error deleting memory item: {str(e)}", exc_info=True)
            return False

    async def _get_all_descendants(
        self,
        workspace_id: uuid.UUID,
        parent_id: uuid.UUID,
        db: AsyncSession,
    ) -> List[uuid.UUID]:
        """
        Get all descendant item IDs recursively

        Args:
            workspace_id: The workspace ID
            parent_id: The parent item ID
            db: Database session

        Returns:
            List of descendant item IDs
        """
        # Get direct children
        query = select(MemoryItem.id).where(
            and_(
                MemoryItem.parent_id == parent_id,
                MemoryItem.workspace_id == workspace_id,
            )
        )

        result = await db.execute(query)
        child_ids = [row[0] for row in result.fetchall()]

        # If no children, return empty list
        if not child_ids:
            return []

        # Get descendants of children
        descendants = []
        for child_id in child_ids:
            child_descendants = await self._get_all_descendants(
                workspace_id, child_id, db
            )
            descendants.extend(child_descendants)

        # Return all descendant IDs including direct children
        return child_ids + descendants

    @transactional
    async def list_items(
        self,
        workspace_id: uuid.UUID,
        item_types: Optional[List[Any]] = None,
        owner_id: Optional[uuid.UUID] = None,
        parent_id: Optional[uuid.UUID] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
        db: Optional[AsyncSession] = None,
        **kwargs,
    ) -> List[MemoryItemRead]:
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
            db: Optional database session

        Returns:
            List of memory items matching the criteria
        """
        logger.debug(f"Listing memory items in workspace {workspace_id}")

        try:
            # Build query conditions
            conditions = [MemoryItem.workspace_id == workspace_id]

            if item_types:
                item_type_list = [
                    t if isinstance(t, MemoryItemType) else MemoryItemType(t)
                    for t in item_types
                ]
                conditions.append(MemoryItem.type.in_(item_type_list))

            if owner_id:
                conditions.append(MemoryItem.owner_id == owner_id)

            if parent_id:
                conditions.append(MemoryItem.parent_id == parent_id)
            else:
                # By default, only show root items (not children)
                conditions.append(MemoryItem.parent_id.is_(None))

            # Query database
            query = select(MemoryItem).where(and_(*conditions))

            # Order by most recent first
            query = query.order_by(MemoryItem.created_at.desc())

            # Apply pagination
            query = query.limit(limit).offset(offset)

            result = await db.execute(query)
            items = result.scalars().all()

            # Post-filter for metadata if needed
            # Note: This is inefficient for large datasets but allows complex filtering
            if metadata_filter:
                filtered_items = []
                for item in items:
                    match = True
                    for key, value in metadata_filter.items():
                        if key not in item.metadata or item.metadata[key] != value:
                            match = False
                            break

                    if match:
                        filtered_items.append(item)

                items = filtered_items

            # Convert to schemas
            return [self._to_schema(item) for item in items]

        except Exception as e:
            logger.error(f"Error listing memory items: {str(e)}", exc_info=True)
            return []

    @transactional
    async def count_items(
        self,
        workspace_id: uuid.UUID,
        item_types: Optional[List[Any]] = None,
        owner_id: Optional[uuid.UUID] = None,
        parent_id: Optional[uuid.UUID] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
        db: Optional[AsyncSession] = None,
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
            db: Optional database session

        Returns:
            Count of memory items matching the criteria
        """
        logger.debug(f"Counting memory items in workspace {workspace_id}")

        try:
            # Build query conditions
            conditions = [MemoryItem.workspace_id == workspace_id]

            if item_types:
                item_type_list = [
                    t if isinstance(t, MemoryItemType) else MemoryItemType(t)
                    for t in item_types
                ]
                conditions.append(MemoryItem.type.in_(item_type_list))

            if owner_id:
                conditions.append(MemoryItem.owner_id == owner_id)

            if parent_id:
                conditions.append(MemoryItem.parent_id == parent_id)

            # Query database for count
            query = (
                select(func.count()).select_from(MemoryItem).where(and_(*conditions))
            )

            result = await db.execute(query)
            count = result.scalar_one()

            # Post-filter for metadata if needed
            if metadata_filter:
                # This is inefficient - we need to get all items and filter manually
                # In a production system, consider using a different approach for metadata filtering
                items_query = select(MemoryItem).where(and_(*conditions))
                items_result = await db.execute(items_query)
                items = items_result.scalars().all()

                filtered_count = 0
                for item in items:
                    match = True
                    for key, value in metadata_filter.items():
                        if key not in item.metadata or item.metadata[key] != value:
                            match = False
                            break

                    if match:
                        filtered_count += 1

                count = filtered_count

            return count

        except Exception as e:
            logger.error(f"Error counting memory items: {str(e)}", exc_info=True)
            return 0

    @transactional
    async def search(
        self,
        workspace_id: uuid.UUID,
        query: str,
        item_types: Optional[List[Any]] = None,
        limit: int = 20,
        db: Optional[AsyncSession] = None,
        **kwargs,
    ) -> List[MemoryItemRead]:
        """
        Search for memory items

        Args:
            workspace_id: The workspace to search in
            query: The search query
            item_types: Optional list of item types to filter by
            limit: Maximum number of results to return
            db: Optional database session

        Returns:
            List of memory items matching the search query
        """
        logger.info(
            f"Searching memory items in workspace {workspace_id} with query: {query}"
        )

        try:
            if not query.strip():
                logger.warning("Empty search query")
                return []

            # Basic search implementation - in a production system, you might use
            # a more sophisticated solution like Elasticsearch or PostgreSQL full-text search

            # Convert search terms to lowercase for case-insensitive search
            search_terms = query.lower().split()

            # Build query conditions
            conditions = [MemoryItem.workspace_id == workspace_id]

            if item_types:
                item_type_list = [
                    t if isinstance(t, MemoryItemType) else MemoryItemType(t)
                    for t in item_types
                ]
                conditions.append(MemoryItem.type.in_(item_type_list))

            # Get all items from the workspace
            base_query = select(MemoryItem).where(and_(*conditions))
            result = await db.execute(base_query)
            items = result.scalars().all()

            # Filter and score items manually
            scored_items = []

            for item in items:
                score = 0

                # Search in content
                content_str = str(item.content).lower()
                for term in search_terms:
                    if term in content_str:
                        score += (
                            content_str.count(term) * 2
                        )  # Higher weight for content

                # Search in metadata
                metadata_str = str(item.metadata).lower()
                for term in search_terms:
                    if term in metadata_str:
                        score += metadata_str.count(term)

                if score > 0:
                    scored_items.append((item, score))

            # Sort by score (highest first)
            scored_items.sort(key=lambda x: x[1], reverse=True)

            # Take top results
            top_items = [item for item, _ in scored_items[:limit]]

            return [self._to_schema(item) for item in top_items]

        except Exception as e:
            logger.error(f"Error searching memory items: {str(e)}", exc_info=True)
            return []

    @transactional
    async def get_child_items(
        self,
        workspace_id: uuid.UUID,
        parent_id: uuid.UUID,
        item_types: Optional[List[Any]] = None,
        db: Optional[AsyncSession] = None,
        **kwargs,
    ) -> List[MemoryItemRead]:
        """
        Get child memory items for a parent

        Args:
            workspace_id: The workspace to look in
            parent_id: The parent item ID to find children for
            item_types: Optional list of item types to filter by
            db: Optional database session

        Returns:
            List of child memory items
        """
        logger.debug(f"Getting child items for parent {parent_id}")

        # Use list_items with parent_id filter
        return await self.list_items(
            workspace_id=workspace_id,
            item_types=item_types,
            parent_id=parent_id,
            db=db,
            **kwargs,
        )

    async def stream_updates(
        self, workspace_id: uuid.UUID, item_id: Optional[uuid.UUID] = None, **kwargs
    ) -> AsyncIterator[MemoryItemRead]:
        """
        Stream real-time updates to memory items

        Args:
            workspace_id: The workspace to stream updates from
            item_id: Optional specific item ID to watch

        Yields:
            Memory items as they are created, updated, or deleted
        """
        logger.info(f"Streaming updates for workspace {workspace_id}")

        # This implementation uses a simple polling approach
        # In a production system, consider using PostgreSQL LISTEN/NOTIFY, Redis pub/sub,
        # or a dedicated message broker like RabbitMQ or Kafka

        # Track last update timestamp
        last_update = datetime.utcnow()

        try:
            while True:
                # Get items updated since last check
                async with get_db() as db:
                    # Build query conditions
                    conditions = [
                        MemoryItem.workspace_id == workspace_id,
                        MemoryItem.updated_at > last_update,
                    ]

                    if item_id:
                        conditions.append(MemoryItem.id == item_id)

                    # Query for updated items
                    query = select(MemoryItem).where(and_(*conditions))
                    result = await db.execute(query)
                    updated_items = result.scalars().all()

                    # Update timestamp for next poll
                    last_update = datetime.utcnow()

                    # Yield updated items
                    for item in updated_items:
                        yield self._to_schema(item)

                # Wait before next poll
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info(f"Update stream for workspace {workspace_id} cancelled")
            raise


# Create global instance
whiteboard_memory = WhiteboardMemory()


# Export public symbols
__all__ = ["WhiteboardMemory", "whiteboard_memory"]
