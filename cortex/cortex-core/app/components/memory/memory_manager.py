"""
Memory Manager implementation for Cortex platform.

This module provides a simplified implementation of the Memory System interface,
providing context management capabilities for conversations.
"""

import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
from uuid import UUID

from app.interfaces.memory_system import MemorySystemInterface
from app.models.domain.memory import (
    MemoryItemCreate,
    MemoryItemInfo,
    MemoryQuery,
    MemoryContext
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MemoryManager(MemorySystemInterface):
    """
    Implementation of the Memory System interface.
    
    Provides simplified memory storage and retrieval capabilities for
    conversation context management. This implementation uses in-memory
    storage for simplicity, but could be extended to use a database or
    vector store in the future.
    """
    
    def __init__(self):
        """Initialize the memory manager."""
        # In-memory storage for memory items
        # Structure: {workspace_id: {item_id: MemoryItemInfo}}
        self._memory_store: Dict[UUID, Dict[UUID, MemoryItemInfo]] = {}
        
        # Context cache for quick access to conversation contexts
        # Structure: {workspace_id: {conversation_id: MemoryContext}}
        self._context_cache: Dict[UUID, Dict[UUID, MemoryContext]] = {}
        
        logger.info("Memory Manager initialized")
    
    async def store(self, workspace_id: UUID, item: MemoryItemCreate) -> UUID:
        """
        Store a memory item in the specified workspace.
        
        Args:
            workspace_id: The ID of the workspace to store the item in
            item: The memory item to store
            
        Returns:
            The ID of the stored memory item
        """
        # Initialize workspace storage if needed
        if workspace_id not in self._memory_store:
            self._memory_store[workspace_id] = {}
        
        # Create a unique ID for the item
        item_id = uuid.uuid4()
        
        # Create a MemoryItemInfo from the MemoryItemCreate
        memory_item = MemoryItemInfo(
            id=item_id,
            workspace_id=workspace_id,
            item_type=item.item_type,
            content=item.content,
            content_type=item.content_type,
            expires_at=item.expires_at,
            metadata=item.metadata,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Store the item
        self._memory_store[workspace_id][item_id] = memory_item
        
        # Clear context cache for this workspace
        if workspace_id in self._context_cache:
            self._context_cache[workspace_id] = {}
        
        logger.debug(f"Stored memory item {item_id} in workspace {workspace_id}")
        return item_id
    
    async def retrieve(self, workspace_id: UUID, query: MemoryQuery) -> List[MemoryItemInfo]:
        """
        Retrieve memory items based on a query.
        
        Args:
            workspace_id: The ID of the workspace to retrieve items from
            query: The query parameters
            
        Returns:
            A list of memory items matching the query
        """
        if workspace_id not in self._memory_store:
            return []
        
        # Get all items for the workspace
        all_items = list(self._memory_store[workspace_id].values())
        
        # Apply filters
        filtered_items = []
        for item in all_items:
            # Filter by item type
            if query.item_type and item.item_type != query.item_type:
                continue
                
            # Filter by content type
            if query.content_type and item.content_type != query.content_type:
                continue
                
            # Filter by creation time
            if query.created_after and item.created_at < query.created_after:
                continue
                
            if query.created_before and item.created_at > query.created_before:
                continue
                
            # Filter by metadata
            if query.metadata_filter:
                match = True
                for key, value in query.metadata_filter.items():
                    if key not in item.metadata or item.metadata[key] != value:
                        match = False
                        break
                        
                if not match:
                    continue
            
            # All filters passed, add to results
            filtered_items.append(item)
        
        # Apply pagination
        start = query.offset
        end = start + query.limit
        paginated_items = filtered_items[start:end]
        
        return paginated_items
    
    async def update(self, workspace_id: UUID, item_id: UUID, metadata: Dict[str, Any]) -> None:
        """
        Update the metadata of an existing memory item.
        
        Args:
            workspace_id: The ID of the workspace containing the item
            item_id: The ID of the item to update
            metadata: The metadata updates to apply
        """
        if workspace_id not in self._memory_store or item_id not in self._memory_store[workspace_id]:
            logger.warning(f"Item {item_id} not found in workspace {workspace_id}")
            return
        
        # Update the metadata
        item = self._memory_store[workspace_id][item_id]
        item.metadata.update(metadata)
        item.updated_at = datetime.now()
        
        # Clear context cache for this workspace
        if workspace_id in self._context_cache:
            self._context_cache[workspace_id] = {}
        
        logger.debug(f"Updated memory item {item_id} in workspace {workspace_id}")
    
    async def delete(self, workspace_id: UUID, item_id: UUID) -> None:
        """
        Delete a memory item.
        
        Args:
            workspace_id: The ID of the workspace containing the item
            item_id: The ID of the item to delete
        """
        if workspace_id not in self._memory_store or item_id not in self._memory_store[workspace_id]:
            logger.warning(f"Item {item_id} not found in workspace {workspace_id}")
            return
        
        # Delete the item
        del self._memory_store[workspace_id][item_id]
        
        # Clear context cache for this workspace
        if workspace_id in self._context_cache:
            self._context_cache[workspace_id] = {}
        
        logger.debug(f"Deleted memory item {item_id} from workspace {workspace_id}")
    
    async def get_context(self, workspace_id: UUID, conversation_id: UUID) -> MemoryContext:
        """
        Get the current memory context for a conversation.
        
        Args:
            workspace_id: The ID of the workspace
            conversation_id: The ID of the conversation
            
        Returns:
            The current memory context
        """
        # Check cache first
        if (workspace_id in self._context_cache and 
            conversation_id in self._context_cache[workspace_id]):
            return self._context_cache[workspace_id][conversation_id]
        
        # Initialize context
        context = MemoryContext(
            items=[],
            metadata={"conversation_id": str(conversation_id)}
        )
        
        # Get relevant memory items
        query = MemoryQuery(
            metadata_filter={"conversation_id": str(conversation_id)},
            limit=100  # Get a reasonable number of items
        )
        
        items = await self.retrieve(workspace_id, query)
        context.items = items
        
        # Cache the context
        if workspace_id not in self._context_cache:
            self._context_cache[workspace_id] = {}
            
        self._context_cache[workspace_id][conversation_id] = context
        
        return context
    
    async def clear_context(self, workspace_id: UUID, conversation_id: UUID) -> None:
        """
        Clear the memory context for a conversation.
        
        Args:
            workspace_id: The ID of the workspace
            conversation_id: The ID of the conversation
        """
        if workspace_id not in self._memory_store:
            return
        
        # Get items for this conversation
        query = MemoryQuery(
            metadata_filter={"conversation_id": str(conversation_id)},
            limit=1000  # Get all items for this conversation
        )
        
        items = await self.retrieve(workspace_id, query)
        
        # Delete all items
        for item in items:
            await self.delete(workspace_id, item.id)
        
        # Clear cache
        if (workspace_id in self._context_cache and 
            conversation_id in self._context_cache[workspace_id]):
            del self._context_cache[workspace_id][conversation_id]
        
        logger.debug(f"Cleared memory context for conversation {conversation_id} in workspace {workspace_id}")


# Singleton instance
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """
    Get the singleton memory manager instance.
    
    Returns:
        The memory manager instance
    """
    global _memory_manager
    
    if _memory_manager is None:
        _memory_manager = MemoryManager()
        
    return _memory_manager