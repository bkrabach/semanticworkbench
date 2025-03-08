"""
Test suite for the memory system interface
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import uuid

from app.interfaces.memory_system import (
    MemorySystemInterface,
    MemoryConfig,
    MemoryItem,
    MemoryQuery,
    RetentionPolicy,
    SynthesizedMemory
)


class MockMemorySystem(MemorySystemInterface):
    """Mock implementation of MemorySystemInterface for testing"""
    
    def __init__(self):
        self.storage: Dict[str, Dict[str, MemoryItem]] = {}
        self.initialized = False
        self.config = None
    
    async def initialize(self, config: MemoryConfig) -> None:
        """Initialize the memory system"""
        self.initialized = True
        self.config = config
    
    async def store(self, workspace_id: str, item: MemoryItem) -> str:
        """Store a memory item"""
        if workspace_id not in self.storage:
            self.storage[workspace_id] = {}
        
        # Generate ID if not provided
        if not item.id:
            item.id = str(uuid.uuid4())
        
        # Set expiration based on retention policy if configured
        if self.config and self.config.retention_policy and not item.expires_at:
            ttl_days = self.config.retention_policy.default_ttl_days
            if (self.config.retention_policy.type_specific_ttl and 
                item.type in self.config.retention_policy.type_specific_ttl):
                ttl_days = self.config.retention_policy.type_specific_ttl[item.type]
            
            item.expires_at = item.timestamp + timedelta(days=ttl_days)
        
        self.storage[workspace_id][item.id] = item
        return item.id
    
    async def retrieve(self, workspace_id: str, query: MemoryQuery) -> List[MemoryItem]:
        """Retrieve memory items based on a query"""
        if workspace_id not in self.storage:
            return []
        
        results = []
        for item in self.storage[workspace_id].values():
            # Skip expired items unless explicitly included
            if not query.include_expired and item.expires_at and item.expires_at < datetime.now():
                continue
            
            # Filter by type
            if query.types and item.type not in query.types:
                continue
            
            # Filter by timestamp range
            if query.from_timestamp and item.timestamp < query.from_timestamp:
                continue
            if query.to_timestamp and item.timestamp > query.to_timestamp:
                continue
            
            # Filter by content query (simple string matching for the mock)
            if query.content_query and isinstance(item.content, str):
                if query.content_query not in item.content:
                    continue
            
            # Filter by metadata
            if query.metadata_filters:
                match = True
                for key, value in query.metadata_filters.items():
                    if key not in item.metadata or item.metadata[key] != value:
                        match = False
                        break
                if not match:
                    continue
            
            results.append(item)
        
        # Apply limit if specified
        if query.limit and len(results) > query.limit:
            results = results[:query.limit]
        
        return results
    
    async def update(self, workspace_id: str, item_id: str, updates: MemoryItem) -> None:
        """Update an existing memory item"""
        if (workspace_id not in self.storage or 
            item_id not in self.storage[workspace_id]):
            raise KeyError(f"Item {item_id} not found in workspace {workspace_id}")
        
        original_item = self.storage[workspace_id][item_id]
        
        # Update fields while preserving the ID
        if updates.type:
            original_item.type = updates.type
        if updates.content:
            original_item.content = updates.content
        if updates.metadata:
            original_item.metadata.update(updates.metadata)
        if updates.timestamp:
            original_item.timestamp = updates.timestamp
        if updates.expires_at:
            original_item.expires_at = updates.expires_at
    
    async def delete(self, workspace_id: str, item_id: str) -> None:
        """Delete a memory item"""
        if (workspace_id not in self.storage or 
            item_id not in self.storage[workspace_id]):
            raise KeyError(f"Item {item_id} not found in workspace {workspace_id}")
        
        del self.storage[workspace_id][item_id]
    
    async def synthesize_context(
        self, workspace_id: str, query: MemoryQuery
    ) -> SynthesizedMemory:
        """Generate a synthetic/enriched context from raw memory"""
        items = await self.retrieve(workspace_id, query)
        
        # This is a mock implementation - for a real system this would likely 
        # involve LLM-based processing or other complex logic
        summary = f"Summary of {len(items)} items"
        entities = {"detected_entities": len(items)}
        
        return SynthesizedMemory(
            raw_items=items,
            summary=summary,
            entities=entities,
            relevance_score=0.95 if items else 0.0
        )


@pytest.fixture
def memory_system():
    """Create a fresh memory system for each test"""
    return MockMemorySystem()


@pytest.mark.asyncio
async def test_memory_initialization(memory_system):
    """Test memory system initialization"""
    # Setup retention policy and config
    retention_policy = RetentionPolicy(
        default_ttl_days=30,
        type_specific_ttl={"message": 90, "file": 365},
        max_items=1000
    )
    
    config = MemoryConfig(
        storage_type="persistent",
        retention_policy=retention_policy,
        encryption_enabled=True
    )
    
    # Initialize the memory system
    await memory_system.initialize(config)
    
    # Verify initialization
    assert memory_system.initialized is True
    assert memory_system.config == config
    assert memory_system.config.retention_policy.default_ttl_days == 30
    assert memory_system.config.retention_policy.type_specific_ttl["message"] == 90
    assert memory_system.config.storage_type == "persistent"
    assert memory_system.config.encryption_enabled is True


@pytest.mark.asyncio
async def test_store_and_retrieve(memory_system):
    """Test storing and retrieving memory items"""
    # Initialize with config
    await memory_system.initialize(MemoryConfig(storage_type="in_memory"))
    
    # Setup
    workspace_id = "test-workspace"
    now = datetime.now()
    
    # Store some items
    item1 = MemoryItem(
        type="message",
        content="Hello world",
        metadata={"source": "user", "important": True},
        timestamp=now
    )
    
    item2 = MemoryItem(
        type="file",
        content={"filename": "document.pdf", "size": 1024},
        metadata={"category": "document"},
        timestamp=now - timedelta(hours=1)
    )
    
    item3 = MemoryItem(
        type="event",
        content="System started",
        metadata={"level": "info"},
        timestamp=now - timedelta(days=1)
    )
    
    # Store the items
    item1_id = await memory_system.store(workspace_id, item1)
    item2_id = await memory_system.store(workspace_id, item2)
    item3_id = await memory_system.store(workspace_id, item3)
    
    # Verify IDs were assigned
    assert item1_id is not None
    assert item2_id is not None
    assert item3_id is not None
    
    # Retrieve all items
    all_items = await memory_system.retrieve(workspace_id, MemoryQuery())
    assert len(all_items) == 3
    
    # Retrieve by type
    messages = await memory_system.retrieve(
        workspace_id, MemoryQuery(types=["message"])
    )
    assert len(messages) == 1
    assert messages[0].type == "message"
    assert messages[0].content == "Hello world"
    
    # Retrieve by time range
    recent_items = await memory_system.retrieve(
        workspace_id, 
        MemoryQuery(from_timestamp=now - timedelta(hours=2))
    )
    assert len(recent_items) == 2  # should include item1 and item2
    
    # Retrieve with limit
    limited_items = await memory_system.retrieve(
        workspace_id, MemoryQuery(limit=1)
    )
    assert len(limited_items) == 1
    
    # Retrieve with metadata filter
    important_items = await memory_system.retrieve(
        workspace_id, 
        MemoryQuery(metadata_filters={"important": True})
    )
    assert len(important_items) == 1
    assert important_items[0].id == item1_id


@pytest.mark.asyncio
async def test_update_item(memory_system):
    """Test updating a memory item"""
    # Initialize
    await memory_system.initialize(MemoryConfig(storage_type="in_memory"))
    
    # Setup
    workspace_id = "test-workspace"
    now = datetime.now()
    
    # Store an item
    item = MemoryItem(
        type="message",
        content="Original content",
        metadata={"source": "user"},
        timestamp=now
    )
    
    item_id = await memory_system.store(workspace_id, item)
    
    # Update the item
    updates = MemoryItem(
        type="message",  # Required field
        content="Updated content",
        metadata={"updated": True},
        timestamp=datetime.now()  # Required field
    )
    
    await memory_system.update(workspace_id, item_id, updates)
    
    # Retrieve and verify
    updated_items = await memory_system.retrieve(workspace_id, MemoryQuery())
    assert len(updated_items) == 1
    updated_item = updated_items[0]
    
    assert updated_item.id == item_id
    assert updated_item.content == "Updated content"  # Updated
    assert updated_item.metadata["source"] == "user"  # Original preserved
    assert updated_item.metadata["updated"] is True   # New metadata added
    
    # Test updating non-existent item
    with pytest.raises(KeyError):
        await memory_system.update(workspace_id, "non-existent-id", updates)


@pytest.mark.asyncio
async def test_delete_item(memory_system):
    """Test deleting a memory item"""
    # Initialize
    await memory_system.initialize(MemoryConfig(storage_type="in_memory"))
    
    # Setup
    workspace_id = "test-workspace"
    
    # Store an item
    item = MemoryItem(
        type="message",
        content="Test content",
        metadata={},
        timestamp=datetime.now()
    )
    
    item_id = await memory_system.store(workspace_id, item)
    
    # Verify it exists
    items = await memory_system.retrieve(workspace_id, MemoryQuery())
    assert len(items) == 1
    
    # Delete the item
    await memory_system.delete(workspace_id, item_id)
    
    # Verify it's gone
    items_after = await memory_system.retrieve(workspace_id, MemoryQuery())
    assert len(items_after) == 0
    
    # Test deleting non-existent item
    with pytest.raises(KeyError):
        await memory_system.delete(workspace_id, "non-existent-id")


@pytest.mark.asyncio
async def test_retention_policy(memory_system):
    """Test that retention policy is applied to stored items"""
    # Initialize with retention policy
    retention_policy = RetentionPolicy(
        default_ttl_days=30,
        type_specific_ttl={"message": 7, "file": 90}
    )
    
    config = MemoryConfig(
        storage_type="in_memory",
        retention_policy=retention_policy
    )
    
    await memory_system.initialize(config)
    
    # Setup
    workspace_id = "test-workspace"
    now = datetime.now()
    
    # Store items with different types
    message_item = MemoryItem(
        type="message",
        content="Test message",
        metadata={},
        timestamp=now
    )
    
    file_item = MemoryItem(
        type="file",
        content={"filename": "test.txt"},
        metadata={},
        timestamp=now
    )
    
    event_item = MemoryItem(
        type="event",
        content="Test event",
        metadata={},
        timestamp=now
    )
    
    # Store the items
    await memory_system.store(workspace_id, message_item)
    await memory_system.store(workspace_id, file_item)
    await memory_system.store(workspace_id, event_item)
    
    # Retrieve the items and check expiration times
    items = await memory_system.retrieve(workspace_id, MemoryQuery())
    
    # Verify each item has the correct expiration based on type
    for item in items:
        if item.type == "message":
            assert item.expires_at == now + timedelta(days=7)
        elif item.type == "file":
            assert item.expires_at == now + timedelta(days=90)
        else:  # Default TTL
            assert item.expires_at == now + timedelta(days=30)


@pytest.mark.asyncio
async def test_synthesize_context(memory_system):
    """Test context synthesis from memory items"""
    # Initialize
    await memory_system.initialize(MemoryConfig(storage_type="in_memory"))
    
    # Setup
    workspace_id = "test-workspace"
    now = datetime.now()
    
    # Store some items
    for i in range(5):
        item = MemoryItem(
            type="message",
            content=f"Message {i}",
            metadata={"index": i},
            timestamp=now - timedelta(minutes=i)
        )
        await memory_system.store(workspace_id, item)
    
    # Synthesize context
    synthesized = await memory_system.synthesize_context(
        workspace_id, 
        MemoryQuery(types=["message"])
    )
    
    # Verify
    assert isinstance(synthesized, SynthesizedMemory)
    assert len(synthesized.raw_items) == 5
    assert "Summary of 5 items" in synthesized.summary
    assert synthesized.entities["detected_entities"] == 5
    assert synthesized.relevance_score > 0.9
    
    # Test with empty result
    empty_synthesized = await memory_system.synthesize_context(
        workspace_id,
        MemoryQuery(types=["non_existent_type"])
    )
    
    assert len(empty_synthesized.raw_items) == 0
    assert empty_synthesized.relevance_score == 0.0


@pytest.mark.asyncio
async def test_query_content(memory_system):
    """Test querying by content"""
    # Initialize
    await memory_system.initialize(MemoryConfig(storage_type="in_memory"))
    
    # Setup
    workspace_id = "test-workspace"
    now = datetime.now()
    
    # Store items with different content
    await memory_system.store(workspace_id, MemoryItem(
        type="message",
        content="This is about Python programming",
        metadata={},
        timestamp=now
    ))
    
    await memory_system.store(workspace_id, MemoryItem(
        type="message",
        content="This is about JavaScript development",
        metadata={},
        timestamp=now
    ))
    
    await memory_system.store(workspace_id, MemoryItem(
        type="message",
        content="This is about machine learning",
        metadata={},
        timestamp=now
    ))
    
    # Query by content
    python_items = await memory_system.retrieve(
        workspace_id,
        MemoryQuery(content_query="Python")
    )
    
    js_items = await memory_system.retrieve(
        workspace_id,
        MemoryQuery(content_query="JavaScript")
    )
    
    ml_items = await memory_system.retrieve(
        workspace_id,
        MemoryQuery(content_query="machine learning")
    )
    
    # Verify
    assert len(python_items) == 1
    assert "Python" in python_items[0].content
    
    assert len(js_items) == 1
    assert "JavaScript" in js_items[0].content
    
    assert len(ml_items) == 1
    assert "machine learning" in ml_items[0].content
    
    # Test non-matching query
    no_results = await memory_system.retrieve(
        workspace_id,
        MemoryQuery(content_query="Rust programming")
    )
    assert len(no_results) == 0


@pytest.mark.asyncio
async def test_multiple_workspaces(memory_system):
    """Test managing memory across multiple workspaces"""
    # Initialize
    await memory_system.initialize(MemoryConfig(storage_type="in_memory"))
    
    # Setup
    workspace1 = "workspace-1"
    workspace2 = "workspace-2"
    now = datetime.now()
    
    # Store items in different workspaces
    await memory_system.store(workspace1, MemoryItem(
        type="message",
        content="Workspace 1 content",
        metadata={},
        timestamp=now
    ))
    
    await memory_system.store(workspace2, MemoryItem(
        type="message",
        content="Workspace 2 content",
        metadata={},
        timestamp=now
    ))
    
    # Retrieve from each workspace
    items1 = await memory_system.retrieve(workspace1, MemoryQuery())
    items2 = await memory_system.retrieve(workspace2, MemoryQuery())
    
    # Verify
    assert len(items1) == 1
    assert "Workspace 1" in items1[0].content
    
    assert len(items2) == 1
    assert "Workspace 2" in items2[0].content
    
    # Verify no cross-contamination
    assert "Workspace 2" not in items1[0].content
    assert "Workspace 1" not in items2[0].content