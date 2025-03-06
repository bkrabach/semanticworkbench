import logging
from typing import Dict, List, Any, Optional, Union, Set, Callable, Awaitable
import asyncio
import json
from datetime import datetime
import uuid
from functools import lru_cache
import re
import weakref
import traceback
from pydantic import ValidationError

from cortex_core.core.config import get_settings
from cortex_core.core.router import message_router
from cortex_core.models.schemas import MemoryEntry

# Setup logging
logger = logging.getLogger(__name__)
settings = get_settings()

class MemoryAdapter:
    """
    Adapter for interfacing with the Memory System.
    
    This class is responsible for:
    - Storing and retrieving conversation context
    - Managing memory partitioning by user
    - Providing abstractions to simplify memory operations
    - Interfacing with an external memory system via MCP or using local fallback
    """
    
    def __init__(self):
        """Initialize the Memory Adapter."""
        # Connect to memory system
        self.use_external_memory = settings.use_external_memory if hasattr(settings, 'use_external_memory') else False
        self.external_memory_url = settings.external_memory_url if hasattr(settings, 'external_memory_url') else None
        
        # In-memory storage for fallback
        # Key: memory_id, Value: MemoryEntry
        self.memory_entries: Dict[str, MemoryEntry] = {}
        
        # User memories
        # Key: user_id, Value: Set of memory_ids
        self.user_memories: Dict[str, Set[str]] = {}
        
        # Conversation memories
        # Key: conversation_id, Value: Set of memory_ids
        self.conversation_memories: Dict[str, Set[str]] = {}
        
        # Connect status
        self.connected = False
        
        # Register with router for events
        message_router.register_component("memory_adapter", self)
        
        logger.info("MemoryAdapter initialized")
    
    async def initialize(self) -> None:
        """Initialize connection to memory system."""
        try:
            if self.use_external_memory and self.external_memory_url:
                # Try to connect to external memory system
                logger.info(f"Connecting to external memory system at {self.external_memory_url}")
                
                # In a real implementation, we would use an MCP client to connect
                # For the PoC, we'll simulate a connection
                await asyncio.sleep(0.5)
                
                # Set connected status
                self.connected = True
                
                logger.info("Connected to external memory system")
            else:
                logger.info("Using in-memory storage for memory system")
                
            # Subscribe to cleanup conversation event
            await message_router.subscribe_to_event(
                "memory_adapter",
                "conversation_deleted",
                self._handle_conversation_deleted
            )
            
        except Exception as e:
            logger.error(f"Error initializing memory system: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Use in-memory fallback
            logger.info("Falling back to in-memory storage")
            self.use_external_memory = False
    
    async def _handle_conversation_deleted(
        self,
        data: Dict[str, Any]
    ) -> None:
        """
        Handle conversation deleted event.
        
        Args:
            data: Event data
        """
        # Extract data
        conversation_id = data.get("conversation_id")
        
        if not conversation_id:
            logger.warning("Invalid conversation_deleted event data")
            return
        
        # Delete conversation memories
        await self.delete_conversation_memories(conversation_id)
    
    async def store_memory(
        self,
        user_id: str,
        conversation_id: str,
        content: str,
        memory_type: str = "conversation",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store a memory entry.
        
        Args:
            user_id: User ID
            conversation_id: Conversation ID
            content: Memory content
            memory_type: Type of memory entry
            metadata: Optional metadata
            
        Returns:
            Memory ID
        """
        # Create memory ID
        memory_id = str(uuid.uuid4())
        
        # Create memory entry
        memory = MemoryEntry(
            id=memory_id,
            user_id=user_id,
            conversation_id=conversation_id,
            content=content,
            type=memory_type,
            metadata=metadata or {}
        )
        
        try:
            if self.use_external_memory and self.connected:
                # Use external memory system
                logger.debug(f"Storing memory {memory_id} in external memory system")
                
                # In a real implementation, we would use an MCP client to store
                # For the PoC, we'll simulate storage
                await asyncio.sleep(0.1)
                
                # Store in local cache as well
                self.memory_entries[memory_id] = memory
                
            else:
                # Use in-memory storage
                logger.debug(f"Storing memory {memory_id} in in-memory storage")
                
                # Store in memory
                self.memory_entries[memory_id] = memory
            
            # Add to user memories
            if user_id not in self.user_memories:
                self.user_memories[user_id] = set()
            
            self.user_memories[user_id].add(memory_id)
            
            # Add to conversation memories
            if conversation_id not in self.conversation_memories:
                self.conversation_memories[conversation_id] = set()
            
            self.conversation_memories[conversation_id].add(memory_id)
            
            logger.debug(f"Stored memory {memory_id} for user {user_id}, conversation {conversation_id}")
            
            return memory_id
            
        except Exception as e:
            logger.error(f"Error storing memory: {str(e)}")
            logger.error(traceback.format_exc())
            raise RuntimeError(f"Failed to store memory: {str(e)}")
    
    async def retrieve_memory(
        self,
        memory_id: str
    ) -> Optional[MemoryEntry]:
        """
        Retrieve a memory entry.
        
        Args:
            memory_id: Memory ID
            
        Returns:
            Memory entry if found
        """
        try:
            if self.use_external_memory and self.connected:
                # Use external memory system
                logger.debug(f"Retrieving memory {memory_id} from external memory system")
                
                # In a real implementation, we would use an MCP client to retrieve
                # For the PoC, we'll use the local cache
                memory = self.memory_entries.get(memory_id)
                
            else:
                # Use in-memory storage
                logger.debug(f"Retrieving memory {memory_id} from in-memory storage")
                
                # Get from memory
                memory = self.memory_entries.get(memory_id)
            
            if memory:
                logger.debug(f"Retrieved memory {memory_id}")
            else:
                logger.debug(f"Memory {memory_id} not found")
            
            return memory
            
        except Exception as e:
            logger.error(f"Error retrieving memory: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    
    async def search_memories(
        self,
        user_id: str,
        query: str,
        memory_type: Optional[str] = None,
        conversation_id: Optional[str] = None,
        limit: int = 10
    ) -> List[MemoryEntry]:
        """
        Search memory entries.
        
        Args:
            user_id: User ID
            query: Search query
            memory_type: Optional type filter
            conversation_id: Optional conversation filter
            limit: Maximum number of results
            
        Returns:
            Matching memory entries
        """
        try:
            # For the PoC, we'll do a simple in-memory search
            # In a real implementation, we would use semantic search via the MCP client
            
            if self.use_external_memory and self.connected:
                # Use external memory system
                logger.debug(f"Searching memories for user {user_id} in external memory system")
                
                # In a real implementation, we would use an MCP client to search
                # For the PoC, we'll simulate search using the local cache
                await asyncio.sleep(0.2)
                
                # Filter memories
                memories = []
                
                # Get user memories
                user_memory_ids = self.user_memories.get(user_id, set())
                
                # Further filter by conversation if specified
                if conversation_id:
                    conversation_memory_ids = self.conversation_memories.get(conversation_id, set())
                    memory_ids = user_memory_ids.intersection(conversation_memory_ids)
                else:
                    memory_ids = user_memory_ids
                
                # Get memory entries
                for memory_id in memory_ids:
                    memory = self.memory_entries.get(memory_id)
                    
                    if not memory:
                        continue
                    
                    # Apply type filter
                    if memory_type and memory.type != memory_type:
                        continue
                    
                    # Apply query filter (simple substring match for the PoC)
                    if query.lower() in memory.content.lower():
                        memories.append(memory)
                    
                    # Check limit
                    if len(memories) >= limit:
                        break
                
            else:
                # Use in-memory storage
                logger.debug(f"Searching memories for user {user_id} in in-memory storage")
                
                # Filter memories
                memories = []
                
                # Get user memories
                user_memory_ids = self.user_memories.get(user_id, set())
                
                # Further filter by conversation if specified
                if conversation_id:
                    conversation_memory_ids = self.conversation_memories.get(conversation_id, set())
                    memory_ids = user_memory_ids.intersection(conversation_memory_ids)
                else:
                    memory_ids = user_memory_ids
                
                # Get memory entries
                for memory_id in memory_ids:
                    memory = self.memory_entries.get(memory_id)
                    
                    if not memory:
                        continue
                    
                    # Apply type filter
                    if memory_type and memory.type != memory_type:
                        continue
                    
                    # Apply query filter (simple substring match for the PoC)
                    if query.lower() in memory.content.lower():
                        memories.append(memory)
                    
                    # Check limit
                    if len(memories) >= limit:
                        break
            
            logger.debug(f"Found {len(memories)} memories for user {user_id}")
            
            return memories
            
        except Exception as e:
            logger.error(f"Error searching memories: {str(e)}")
            logger.error(traceback.format_exc())
            return []
    
    async def get_conversation_context(
        self,
        user_id: str,
        conversation_id: str,
        limit: int = 100
    ) -> List[MemoryEntry]:
        """
        Get conversation context for LLM.
        
        Args:
            user_id: User ID
            conversation_id: Conversation ID
            limit: Maximum number of entries
            
        Returns:
            Conversation memory entries
        """
        try:
            # Get conversation memories
            if not conversation_id in self.conversation_memories:
                logger.debug(f"No memories for conversation {conversation_id}")
                return []
            
            conversation_memory_ids = self.conversation_memories[conversation_id]
            user_memory_ids = self.user_memories.get(user_id, set())
            
            # Filter to user's memories for this conversation
            memory_ids = conversation_memory_ids.intersection(user_memory_ids)
            
            # Get memory entries
            memories = []
            
            for memory_id in memory_ids:
                memory = await self.retrieve_memory(memory_id)
                
                if memory:
                    memories.append(memory)
                
                # Check limit
                if len(memories) >= limit:
                    break
            
            # Sort by creation time
            memories.sort(key=lambda m: m.created_at)
            
            logger.debug(f"Retrieved {len(memories)} memories for conversation {conversation_id}")
            
            return memories
            
        except Exception as e:
            logger.error(f"Error getting conversation context: {str(e)}")
            logger.error(traceback.format_exc())
            return []
    
    async def delete_memory(
        self,
        memory_id: str
    ) -> bool:
        """
        Delete a memory entry.
        
        Args:
            memory_id: Memory ID
            
        Returns:
            True if deleted successfully
        """
        try:
            # Check if memory exists
            if memory_id not in self.memory_entries:
                logger.warning(f"Memory {memory_id} not found")
                return False
            
            # Get memory
            memory = self.memory_entries[memory_id]
            user_id = memory.user_id
            conversation_id = memory.conversation_id
            
            if self.use_external_memory and self.connected:
                # Use external memory system
                logger.debug(f"Deleting memory {memory_id} from external memory system")
                
                # In a real implementation, we would use an MCP client to delete
                # For the PoC, we'll simulate deletion
                await asyncio.sleep(0.1)
                
            # Remove from memory entries
            del self.memory_entries[memory_id]
            
            # Remove from user memories
            if user_id in self.user_memories:
                self.user_memories[user_id].discard(memory_id)
                
                # Remove user entry if empty
                if not self.user_memories[user_id]:
                    del self.user_memories[user_id]
            
            # Remove from conversation memories
            if conversation_id in self.conversation_memories:
                self.conversation_memories[conversation_id].discard(memory_id)
                
                # Remove conversation entry if empty
                if not self.conversation_memories[conversation_id]:
                    del self.conversation_memories[conversation_id]
            
            logger.debug(f"Deleted memory {memory_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting memory: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    async def delete_user_memories(
        self,
        user_id: str
    ) -> int:
        """
        Delete all memories for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Number of memories deleted
        """
        try:
            # Check if user has memories
            if user_id not in self.user_memories:
                logger.debug(f"No memories for user {user_id}")
                return 0
            
            # Get user memories
            user_memory_ids = list(self.user_memories[user_id])
            
            # Delete each memory
            deleted_count = 0
            
            for memory_id in user_memory_ids:
                deleted = await self.delete_memory(memory_id)
                
                if deleted:
                    deleted_count += 1
            
            logger.debug(f"Deleted {deleted_count} memories for user {user_id}")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error deleting user memories: {str(e)}")
            logger.error(traceback.format_exc())
            return 0
    
    async def delete_conversation_memories(
        self,
        conversation_id: str
    ) -> int:
        """
        Delete all memories for a conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Number of memories deleted
        """
        try:
            # Check if conversation has memories
            if conversation_id not in self.conversation_memories:
                logger.debug(f"No memories for conversation {conversation_id}")
                return 0
            
            # Get conversation memories
            conversation_memory_ids = list(self.conversation_memories[conversation_id])
            
            # Delete each memory
            deleted_count = 0
            
            for memory_id in conversation_memory_ids:
                deleted = await self.delete_memory(memory_id)
                
                if deleted:
                    deleted_count += 1
            
            logger.debug(f"Deleted {deleted_count} memories for conversation {conversation_id}")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error deleting conversation memories: {str(e)}")
            logger.error(traceback.format_exc())
            return 0
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            # Close connection to external memory system
            if self.use_external_memory and self.connected:
                logger.info("Disconnecting from external memory system")
                
                # In a real implementation, we would close the MCP client
                # For the PoC, we'll just simulate disconnection
                await asyncio.sleep(0.2)
                
                self.connected = False
            
            # Clear data
            self.memory_entries.clear()
            self.user_memories.clear()
            self.conversation_memories.clear()
            
            logger.info("MemoryAdapter cleaned up")
            
        except Exception as e:
            logger.error(f"Error in cleanup: {str(e)}")

# Create a global instance for use throughout the application
memory_adapter = MemoryAdapter()