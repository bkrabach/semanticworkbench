# Memory System

This document provides a comprehensive guide to the Memory System in Cortex Core, including its architecture, implementations, and extension points.

## Overview

The Memory System is responsible for storing and retrieving contextual information in Cortex Core. It provides a unified interface for persisting various types of data that need to be accessible across conversations and sessions.

## Current Implementation Status

The Memory System is currently implemented as a "Whiteboard" pattern, which is a simple database-backed storage system. This initial implementation provides the foundation for more advanced memory capabilities in the future.

**Currently Implemented:**
- ✅ Memory System Interface
- ✅ Whiteboard Memory Implementation (database-backed)
- ✅ Basic CRUD operations for memory items
- ✅ Simple querying with filters

**Planned for Future Development:**
- ❌ JAKE Memory Implementation (vector-based)
- ❌ Advanced context synthesis
- ❌ Semantic search capabilities
- ❌ Entity extraction and relationship tracking
- ❌ Advanced memory management with priority-based retention

This document describes both the current implementation and the planned enhancements to provide a complete picture of the Memory System architecture.

## Architecture

The Memory System follows an interface-based design pattern, allowing for different implementations with a consistent API:

```
┌─────────────────┐     ┌─────────────────────┐
│                 │     │                     │
│  API Endpoints  │     │  Context Manager    │
│                 │     │                     │
└────────┬────────┘     └──────────┬──────────┘
         │                         │
         │                         │
         │     ┌───────────────────▼────────────────────┐
         │     │                                        │
         └────►│   Memory System Interface (Abstract)   │
               │                                        │
               └───────────┬───────────────────────────┘
                           │
                           │
             ┌─────────────┴──────────────┐
             │                            │
 ┌───────────▼───────────┐    ┌───────────▼───────────┐
 │                       │    │                       │
 │  Whiteboard Memory    │    │   JAKE Memory         │
 │  (Database-backed)    │    │   (Vector database)   │
 │    [IMPLEMENTED]      │    │      [PLANNED]        │
 └───────────────────────┘    └───────────────────────┘
```

This architecture allows us to start with a simple implementation (Whiteboard Memory) while designing for more advanced capabilities in the future (JAKE Memory or other vector-based solutions).

## Memory System Interface

The Memory System Interface defines the contract that all memory implementations must follow:

```python
class MemorySystemInterface(ABC):
    """
    Interface for memory systems in Cortex Core
    """
    @abstractmethod
    async def initialize(self, config: MemoryConfig) -> None:
        """Initialize the memory system"""
        pass

    @abstractmethod
    async def store(self, workspace_id: str, item: MemoryItem) -> str:
        """Store a memory item"""
        pass

    @abstractmethod
    async def retrieve(self, workspace_id: str, query: MemoryQuery) -> List[MemoryItem]:
        """Retrieve memory items based on a query"""
        pass

    @abstractmethod
    async def update(self, workspace_id: str, item_id: str, updates: MemoryItem) -> None:
        """Update an existing memory item"""
        pass

    @abstractmethod
    async def delete(self, workspace_id: str, item_id: str) -> None:
        """Delete a memory item"""
        pass

    @abstractmethod
    async def synthesize_context(self, workspace_id: str, query: MemoryQuery) -> SynthesizedMemory:
        """Generate a synthetic/enriched context from raw memory"""
        pass
```

This interface ensures that all memory implementations provide the same capabilities, making them interchangeable from the perspective of other components.

## Data Model

The Memory System operates on the following data models:

### Memory Item

```python
class MemoryItem(BaseModel):
    """Memory item model"""
    id: Optional[str] = None
    type: str  # "message", "entity", "file", "event"
    content: Any
    metadata: Dict[str, Any] = {}
    timestamp: datetime
    expires_at: Optional[datetime] = None
```

### Memory Query

```python
class MemoryQuery(BaseModel):
    """Memory query parameters"""
    types: Optional[List[str]] = None
    from_timestamp: Optional[datetime] = None
    to_timestamp: Optional[datetime] = None
    content_query: Optional[str] = None
    metadata_filters: Optional[Dict[str, Any]] = None
    limit: Optional[int] = None
    include_expired: bool = False
```

### Synthesized Memory

```python
class SynthesizedMemory(BaseModel):
    """Synthesized memory result"""
    raw_items: List[MemoryItem]
    summary: str
    entities: Dict[str, Any]
    relevance_score: float
```

## Memory Types

The Memory System supports different types of memory items:

1. **Message Memory** - Conversation messages with role, content, and metadata
2. **Entity Memory** - Named entities extracted from conversations (people, places, concepts)
3. **File Memory** - Document or file references with content and metadata
4. **Event Memory** - System or user-generated events with timestamps

## Implementations

### Whiteboard Memory (Current Implementation)

The Whiteboard Memory is the current default implementation that uses the database for storage:

- **Storage**: SQLAlchemy models in the database
- **Querying**: SQL queries for retrieval
- **Indexing**: Database indexes for efficient retrieval
- **Retention**: TTL-based expiration with background cleanup

```python
class WhiteboardMemory(MemorySystemInterface):
    """Database-backed memory implementation"""
    
    async def initialize(self, config: MemoryConfig) -> None:
        self.db = get_db()
        self.retention_days = config.retention_policy.default_ttl_days
    
    async def store(self, workspace_id: str, item: MemoryItem) -> str:
        # Create a unique ID if not provided
        if not item.id:
            item.id = str(uuid.uuid4())
            
        # Calculate expiration date based on retention policy
        if not item.expires_at and self.retention_days:
            item.expires_at = datetime.now(timezone.utc) + timedelta(days=self.retention_days)
            
        # Create database model from domain model
        db_item = MemoryItemDB(
            id=item.id,
            workspace_id=workspace_id,
            type=item.type,
            content=json.dumps(item.content),
            metadata=json.dumps(item.metadata),
            timestamp_utc=item.timestamp,
            expires_at_utc=item.expires_at
        )
        
        # Save to database
        self.db.add(db_item)
        self.db.commit()
        
        return item.id
```

Current Limitations:

- No semantic search capabilities
- Basic text-based filtering only
- Limited context synthesis
- No vector embeddings or similarity search

### JAKE Memory (Planned Implementation)

The JAKE Memory is a planned advanced implementation using vector-based storage:

- **Storage**: Vector database with embeddings
- **Querying**: Semantic and keyword-based queries
- **Indexing**: Vector indexes for similarity search
- **Retention**: TTL-based expiration with pruning

```python
class JakeMemory(MemorySystemInterface):
    """Vector database memory implementation (PLANNED)"""
    
    async def initialize(self, config: MemoryConfig) -> None:
        # Connect to vector database
        # This is a placeholder for the planned implementation
        pass
    
    async def store(self, workspace_id: str, item: MemoryItem) -> str:
        # Generate embeddings and store in vector database
        # This is a placeholder for the planned implementation
        pass
```

Planned Features:

- Semantic search using vector embeddings
- Relevance ranking of search results
- Advanced context synthesis
- Entity extraction and relationship tracking
- Cross-reference capabilities
- Improved memory prioritization

## Current Usage

The current Whiteboard Memory implementation is used primarily for:

### Storing Messages

```python
# In the repository layer
async def add_message(self, conversation_id: str, content: str, role: str, metadata: Dict[str, Any] = None) -> Message:
    # ... database operations ...
    
    # Optionally store in memory system
    if self.memory_system:
        memory_item = MemoryItem(
            type="message",
            content={
                "role": role,
                "content": content,
                "message_id": message_id
            },
            metadata={
                "conversation_id": conversation_id,
                **metadata or {}
            },
            timestamp=datetime.now(timezone.utc)
        )
        await self.memory_system.store(workspace_id, memory_item)
```

### Retrieving Conversation History

```python
# Create a query for recent messages in the conversation
query = MemoryQuery(
    types=["message"],
    metadata_filters={"conversation_id": conversation_id},
    limit=50
)

# Retrieve messages
messages = await memory_system.retrieve(workspace_id, query)
```

### Basic Synthesize_Context Implementation

The current implementation of `synthesize_context` is basic and will be enhanced in future versions:

```python
async def synthesize_context(self, workspace_id: str, query: MemoryQuery) -> SynthesizedMemory:
    """Generate a synthetic context from raw memory (basic implementation)"""
    # Retrieve raw items matching the query
    items = await self.retrieve(workspace_id, query)
    
    # For now, just return the raw items with a placeholder summary
    # In future implementations, this will use LLMs for summarization
    return SynthesizedMemory(
        raw_items=items,
        summary=f"Collection of {len(items)} memory items related to the query",
        entities={},  # No entity extraction in current implementation
        relevance_score=1.0 if items else 0.0
    )
```

## Configuration

The Memory System is configured using the `MemoryConfig` model:

```python
class RetentionPolicy(BaseModel):
    """Retention policy for memory items"""
    default_ttl_days: int
    type_specific_ttl: Optional[Dict[str, int]] = None  # type -> days
    max_items: Optional[int] = None

class MemoryConfig(BaseModel):
    """Memory system configuration"""
    storage_type: str  # "whiteboard" or "jake" (future)
    retention_policy: Optional[RetentionPolicy] = None
    encryption_enabled: bool = False
```

Example configuration for the current implementation:

```python
# Configure retention policy
retention_policy = RetentionPolicy(
    default_ttl_days=90,
    type_specific_ttl={
        "message": 30,
        "entity": 180,
        "file": 365
    },
    max_items=10000
)

# Configure memory system
memory_config = MemoryConfig(
    storage_type="whiteboard",  # Current implementation
    retention_policy=retention_policy,
    encryption_enabled=False  # Not yet implemented
)

# Initialize memory system
await memory_system.initialize(memory_config)
```

## Future Enhancements

The Memory System will be enhanced with these planned features:

1. **Vector Database Integration**: Implement JAKE Memory with vector embeddings
2. **Advanced Context Synthesis**: Use LLMs to generate rich context summaries
3. **Entity Extraction**: Automatically extract and track entities from conversations
4. **Relationship Tracking**: Track relationships between entities
5. **Improved Retention**: More sophisticated retention policies based on importance
6. **Encrypted Storage**: Implement encrypted storage for sensitive memory items
7. **Memory Compression**: Compress and summarize old memories to save space
8. **Cross-Reference**: Link related memories across conversations and workspaces

## Creating Custom Implementations

To create a custom memory implementation:

1. **Implement the Interface**: Create a class that implements all methods of `MemorySystemInterface`
2. **Register the Implementation**: Add the implementation to the service provider

Example custom implementation:

```python
class CustomMemory(MemorySystemInterface):
    """Custom memory implementation"""
    
    async def initialize(self, config: MemoryConfig) -> None:
        # Custom initialization logic
        pass
    
    # Implement all other required methods...
```

## Best Practices

1. **Workspace Isolation**: Always scope memory operations to a specific workspace ID
2. **Type-Based Querying**: Use the `types` parameter for more efficient queries
3. **Metadata Filtering**: Use metadata filters for efficient filtering without full-text search
4. **Caching Strategy**: Implement caching for frequently accessed memory items
5. **Appropriate TTL**: Set reasonable TTL values based on the type of memory item
6. **Batch Operations**: Use batch operations for bulk processing when available
7. **Error Handling**: Implement robust error handling for storage and retrieval operations

## Related Documentation

- [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md): Overall implementation status
- [ARCHITECTURE.md](ARCHITECTURE.md): System architecture overview
- [Technical_Architecture.md](/cortex-platform/ai-context/cortex/Cortex_Platform-Technical_Architecture.md): Vision document that describes the memory system concept