"""
Memory System Interface for Cortex Core
Defines the contract for memory systems (Whiteboard, JAKE, etc.)
"""

from typing import Dict, List, Optional, Any, Protocol
from datetime import datetime
from abc import ABC, abstractmethod
from pydantic import BaseModel


class RetentionPolicy(BaseModel):
    """Retention policy for memory items"""

    default_ttl_days: int
    type_specific_ttl: Optional[Dict[str, int]] = None  # type -> days
    max_items: Optional[int] = None


class MemoryConfig(BaseModel):
    """Memory system configuration"""

    storage_type: str  # "in_memory" or "persistent"
    retention_policy: Optional[RetentionPolicy] = None
    encryption_enabled: bool = False


class MemoryItem(BaseModel):
    """Memory item model"""

    id: Optional[str] = None
    type: str  # "message", "entity", "file", "event"
    content: Any
    metadata: Dict[str, Any] = {}
    timestamp: datetime
    expires_at: Optional[datetime] = None


class MemoryQuery(BaseModel):
    """Memory query parameters"""

    types: Optional[List[str]] = None
    from_timestamp: Optional[datetime] = None
    to_timestamp: Optional[datetime] = None
    content_query: Optional[str] = None
    metadata_filters: Optional[Dict[str, Any]] = None
    limit: Optional[int] = None
    include_expired: bool = False


class SynthesizedMemory(BaseModel):
    """Synthesized memory result"""

    raw_items: List[MemoryItem]
    summary: str
    entities: Dict[str, Any]
    relevance_score: float


class MemorySystemInterface(ABC):
    """
    Interface for memory systems in Cortex Core
    This provides a consistent contract that all memory implementations
    (Whiteboard, JAKE, etc.) must adhere to
    """

    @abstractmethod
    async def initialize(self, config: MemoryConfig) -> None:
        """
        Initialize the memory system

        Args:
            config: Configuration options
        """
        pass

    @abstractmethod
    async def store(self, workspace_id: str, item: MemoryItem) -> str:
        """
        Store a memory item

        Args:
            workspace_id: The ID of the workspace
            item: The memory item to store

        Returns:
            The ID of the stored item
        """
        pass

    @abstractmethod
    async def retrieve(self, workspace_id: str, query: MemoryQuery) -> List[MemoryItem]:
        """
        Retrieve memory items based on a query

        Args:
            workspace_id: The ID of the workspace
            query: The query parameters

        Returns:
            Array of memory items
        """
        pass

    @abstractmethod
    async def update(
        self, workspace_id: str, item_id: str, updates: MemoryItem
    ) -> None:
        """
        Update an existing memory item

        Args:
            workspace_id: The ID of the workspace
            item_id: The ID of the item to update
            updates: The updates to apply
        """
        pass

    @abstractmethod
    async def delete(self, workspace_id: str, item_id: str) -> None:
        """
        Delete a memory item

        Args:
            workspace_id: The ID of the workspace
            item_id: The ID of the item to delete
        """
        pass

    @abstractmethod
    async def synthesize_context(
        self, workspace_id: str, query: MemoryQuery
    ) -> SynthesizedMemory:
        """
        Generate a synthetic/enriched context from raw memory

        Args:
            workspace_id: The ID of the workspace
            query: The query parameters

        Returns:
            Synthesized memory
        """
        pass
