"""
Memory System Interface for Cortex Core.

This module defines the interface for memory management systems in the Cortex platform.
The interface is designed to be simple and focused on core functionality while being
extensible for future enhancements.
"""

from typing import Dict, List, Any, Optional, Protocol
from uuid import UUID
from datetime import datetime

from app.models.domain.memory import MemoryItemCreate, MemoryItemInfo, MemoryQuery, MemoryContext


class MemorySystemInterface(Protocol):
    """
    Interface for memory systems that provide context management for conversations.
    
    The memory system is responsible for storing, retrieving, and managing memory items
    that provide context for conversations. This interface defines the contract that all
    memory system implementations must follow.
    """
    
    async def store(self, workspace_id: UUID, item: MemoryItemCreate) -> UUID:
        """
        Store a memory item in the specified workspace.
        
        Args:
            workspace_id: The ID of the workspace to store the item in
            item: The memory item to store
            
        Returns:
            The ID of the stored memory item
        """
        ...
    
    async def retrieve(self, workspace_id: UUID, query: MemoryQuery) -> List[MemoryItemInfo]:
        """
        Retrieve memory items based on a query.
        
        Args:
            workspace_id: The ID of the workspace to retrieve items from
            query: The query parameters
            
        Returns:
            A list of memory items matching the query
        """
        ...
    
    async def update(self, workspace_id: UUID, item_id: UUID, metadata: Dict[str, Any]) -> None:
        """
        Update the metadata of an existing memory item.
        
        Args:
            workspace_id: The ID of the workspace containing the item
            item_id: The ID of the item to update
            metadata: The metadata updates to apply
        """
        ...
    
    async def delete(self, workspace_id: UUID, item_id: UUID) -> None:
        """
        Delete a memory item.
        
        Args:
            workspace_id: The ID of the workspace containing the item
            item_id: The ID of the item to delete
        """
        ...
    
    async def get_context(self, workspace_id: UUID, conversation_id: UUID) -> MemoryContext:
        """
        Get the current memory context for a conversation.
        
        Args:
            workspace_id: The ID of the workspace
            conversation_id: The ID of the conversation
            
        Returns:
            The current memory context
        """
        ...
    
    async def clear_context(self, workspace_id: UUID, conversation_id: UUID) -> None:
        """
        Clear the memory context for a conversation.
        
        Args:
            workspace_id: The ID of the workspace
            conversation_id: The ID of the conversation
        """
        ...