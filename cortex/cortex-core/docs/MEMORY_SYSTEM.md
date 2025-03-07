# Memory System

This document provides a comprehensive guide to the Memory System in Cortex Core, including its architecture, implementations, and extension points.

## Overview

The Memory System is responsible for storing and retrieving contextual information in Cortex Core. It provides a unified interface for persisting various types of data that need to be accessible across conversations and sessions.

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
 │                       │    │                       │
 └───────────────────────┘    └───────────────────────┘
```

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

### Whiteboard Memory

The default implementation that uses the database for storage:

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
        # Implementation details for storing in database
        pass
    
    # Other interface methods...
```

### JAKE Memory

A more advanced implementation using vector-based storage:

- **Storage**: Vector database with embeddings
- **Querying**: Semantic and keyword-based queries
- **Indexing**: Vector indexes for similarity search
- **Retention**: TTL-based expiration with pruning

```python
class JakeMemory(MemorySystemInterface):
    """Vector database memory implementation"""
    
    async def initialize(self, config: MemoryConfig) -> None:
        # Connect to vector database
        pass
    
    async def store(self, workspace_id: str, item: MemoryItem) -> str:
        # Generate embeddings and store in vector database
        pass
    
    # Other interface methods...
```

## Usage

### Storing Memory Items

```python
# Create a memory item
memory_item = MemoryItem(
    type="message",
    content={
        "role": "user",
        "content": "How can I configure the system?",
        "message_id": "msg-123"
    },
    metadata={
        "conversation_id": "conv-456",
        "importance": "medium"
    },
    timestamp=datetime.utcnow()
)

# Store the item
item_id = await memory_system.store(workspace_id="ws-789", item=memory_item)
```

### Retrieving Memory Items

```python
# Create a query
query = MemoryQuery(
    types=["message"],
    from_timestamp=datetime.utcnow() - timedelta(days=7),
    content_query="configuration",
    limit=10
)

# Retrieve items
items = await memory_system.retrieve(workspace_id="ws-789", query=query)

# Process items
for item in items:
    print(f"Item {item.id}: {item.content}")
```

### Synthesizing Context

```python
# Create a query for synthesis
query = MemoryQuery(
    content_query="system configuration",
    limit=20
)

# Get synthesized context
context = await memory_system.synthesize_context(workspace_id="ws-789", query=query)

# Use the synthesized context
summary = context.summary
relevant_items = context.raw_items
related_entities = context.entities
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
    storage_type: str  # "in_memory" or "persistent"
    retention_policy: Optional[RetentionPolicy] = None
    encryption_enabled: bool = False
```

Example configuration:

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
    storage_type="persistent",
    retention_policy=retention_policy,
    encryption_enabled=True
)

# Initialize memory system
await memory_system.initialize(memory_config)
```

## Creating Custom Implementations

To create a custom memory implementation:

1. **Implement the Interface**: Create a class that implements all methods of `MemorySystemInterface`
2. **Register the Implementation**: Add the implementation to the service provider

Example implementation:

```python
class CustomMemory(MemorySystemInterface):
    """Custom memory implementation"""
    
    async def initialize(self, config: MemoryConfig) -> None:
        # Custom initialization logic
        pass
    
    async def store(self, workspace_id: str, item: MemoryItem) -> str:
        # Custom storage logic
        pass
    
    async def retrieve(self, workspace_id: str, query: MemoryQuery) -> List[MemoryItem]:
        # Custom retrieval logic
        pass
    
    async def update(self, workspace_id: str, item_id: str, updates: MemoryItem) -> None:
        # Custom update logic
        pass
    
    async def delete(self, workspace_id: str, item_id: str) -> None:
        # Custom deletion logic
        pass
    
    async def synthesize_context(self, workspace_id: str, query: MemoryQuery) -> SynthesizedMemory:
        # Custom context synthesis logic
        pass
```

## Best Practices

1. **Workspace Isolation**: Always scope memory operations to a specific workspace ID
2. **Type-Based Querying**: Use the `types` parameter for more efficient queries
3. **Metadata Filtering**: Use metadata filters for efficient filtering without full-text search
4. **Caching Strategy**: Implement caching for frequently accessed memory items
5. **Appropriate TTL**: Set reasonable TTL values based on the type of memory item
6. **Batch Operations**: Use batch operations for bulk processing when available
7. **Error Handling**: Implement robust error handling for storage and retrieval operations

## Common Patterns

### Context Retrieval for Conversations

```python
async def get_conversation_context(conversation_id: str, workspace_id: str) -> SynthesizedMemory:
    # Create a query for recent messages in the conversation
    query = MemoryQuery(
        types=["message"],
        metadata_filters={"conversation_id": conversation_id},
        limit=50
    )
    
    # Get relevant entities for the conversation
    entity_query = MemoryQuery(
        types=["entity"],
        metadata_filters={"conversation_id": conversation_id},
        limit=20
    )
    
    # Retrieve and combine results
    messages = await memory_system.retrieve(workspace_id, query)
    entities = await memory_system.retrieve(workspace_id, entity_query)
    
    # Return as synthesized memory
    return SynthesizedMemory(
        raw_items=messages + entities,
        summary=generate_summary(messages),
        entities={e.content["name"]: e.content for e in entities},
        relevance_score=1.0
    )
```

### Entity Extraction and Storage

```python
async def extract_and_store_entities(text: str, conversation_id: str, workspace_id: str) -> List[str]:
    # Extract entities from text
    entities = entity_extractor.extract(text)
    
    # Store each entity as a memory item
    entity_ids = []
    for entity in entities:
        item = MemoryItem(
            type="entity",
            content={
                "name": entity.name,
                "type": entity.type,
                "value": entity.value
            },
            metadata={
                "conversation_id": conversation_id,
                "confidence": entity.confidence
            },
            timestamp=datetime.utcnow()
        )
        
        entity_id = await memory_system.store(workspace_id, item)
        entity_ids.append(entity_id)
    
    return entity_ids
```

## Troubleshooting

### Common Issues

1. **Performance Problems**
   - Check query patterns and indexing
   - Implement caching for frequent queries
   - Use more specific query parameters

2. **Memory Leaks**
   - Ensure TTL values are set correctly
   - Verify that cleanup processes are running
   - Monitor memory usage with metrics

3. **Data Consistency**
   - Implement transactional operations when needed
   - Handle concurrent writes appropriately
   - Add validation for memory item content

### Logging and Monitoring

- Enable debug logging for memory operations
- Track memory system metrics (items stored, retrieved, synthesized)
- Monitor performance and resource usage

## Related Topics

- [OVERVIEW.md](OVERVIEW.md): System architecture overview
- [COMPONENTS.md](COMPONENTS.md): Details on all system components
- [DEVELOPMENT.md](DEVELOPMENT.md): Guidelines for development

