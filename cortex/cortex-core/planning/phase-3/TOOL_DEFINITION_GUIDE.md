# Tool and Resource Definition Guide

## Overview

This document provides a comprehensive guide for creating and implementing MCP tools and resources in the Cortex Core Phase 3 implementation. It covers standard patterns, naming conventions, implementation best practices, error handling, testing strategies, and documentation requirements to ensure consistency across services.

In the Model Context Protocol (MCP) architecture, tools and resources form the standardized interface through which services communicate. Understanding how to properly define and implement these components is critical for maintaining clean service boundaries while enabling effective communication.

## Core Concepts

### Tools vs Resources

The MCP architecture is built on two primary interface mechanisms:

1. **Tools**: Executable functions that perform operations and can have side effects

   - Called with named arguments
   - Return structured data
   - Can modify system state
   - Used for operations like storing data, processing information, or generating content
   - Similar to RPC (Remote Procedure Call) endpoints

2. **Resources**: Data that can be accessed and read
   - Addressed using URI-style paths
   - Return structured data
   - Read-only (no side effects)
   - Used for retrieving data like history, context, or configuration
   - Similar to REST resources

### When to Use Each

| Use Case               | Tools  | Resources |
| ---------------------- | ------ | --------- |
| Reading data           | ❌     | ✅        |
| Writing/modifying data | ✅     | ❌        |
| Processing operations  | ✅     | ❌        |
| Data retrieval         | ❌     | ✅        |
| Stateful operations    | ✅     | ❌        |
| Idempotent operations  | Can be | Always    |

## Tool Definition

### Basic Structure

Tools are defined using a decorator pattern with the `@mcp.tool()` decorator:

```python
@mcp.tool()
async def tool_name(param1: type, param2: type = default_value) -> Dict[str, Any]:
    """
    Tool description.

    Args:
        param1: Description of param1
        param2: Description of param2 (default: default_value)

    Returns:
        Description of return value structure
    """
    # Implementation
    pass
```

### Example Tool Implementation

Here's an example of a complete tool implementation for storing input:

```python
@mcp.tool()
async def store_input(
    user_id: str,
    input_data: Dict[str, Any],
    timestamp: Optional[str] = None
) -> Dict[str, Any]:
    """
    Store input data for a specific user.

    Args:
        user_id: The unique user identifier
        input_data: The input data to store
        timestamp: Optional ISO-8601 timestamp (default: current time)

    Returns:
        Dictionary containing:
        - status: "stored" if successful
        - item_id: ID of the stored item
    """
    # Input validation
    if not user_id:
        raise ValueError("user_id is required")

    if not input_data:
        raise ValueError("input_data is required")

    # Set timestamp if not provided
    if not timestamp:
        timestamp = datetime.now().isoformat()

    # Generate unique ID for the item
    item_id = str(uuid.uuid4())

    # Add metadata
    storage_item = {
        "id": item_id,
        "user_id": user_id,
        "data": input_data,
        "timestamp": timestamp
    }

    try:
        # Store the item using the repository
        await self.repository.store_item(storage_item)

        # Return success response
        return {
            "status": "stored",
            "item_id": item_id
        }
    except Exception as e:
        # Log the error
        logger.error(f"Error storing input for user {user_id}: {e}")

        # Return error response
        return {
            "status": "error",
            "error": str(e)
        }
```

### Parameter Guidelines

1. **Type Annotations**

   - Always include type annotations for all parameters
   - Use standard Python types where possible
   - Use typing module for complex types (Dict, List, Optional, etc.)

2. **Required vs Optional**

   - Make parameters required unless they have a sensible default
   - Use Optional[type] for optional parameters
   - Always provide default values for optional parameters

3. **User Partitioning**

   - Almost all tools should have a `user_id` parameter as the first parameter
   - Use the `user_id` for data partitioning to maintain security boundaries

4. **Parameter Ordering**

   - Required parameters first
   - Optional parameters after required ones
   - Most important parameters should come first

5. **Parameter Naming**
   - Use clear, descriptive names following Python's snake_case convention
   - Be consistent with naming across tools and services
   - Avoid abbreviations unless they're universally understood

### Return Type Guidelines

1. **Always Return Dictionaries**

   - All tools should return Dict[str, Any]
   - This provides flexibility and forward compatibility
   - Enables easy extension with additional fields

2. **Status Indication**

   - Include a "status" field indicating success or failure
   - Use consistent status values across tools ("success", "error", etc.)

3. **Result Data**

   - For successful operations, include relevant result data
   - For errors, include error details in a consistent format

4. **Standard Return Structure**
   - Success: `{"status": "success", "data": {...}}`
   - Error: `{"status": "error", "error": "Error message", "details": {...}}`

## Resource Definition

### Basic Structure

Resources are defined using a decorator pattern with the `@mcp.resource()` decorator:

```python
@mcp.resource("resource_path/{parameter}")
async def resource_handler(parameter: type) -> Any:
    """
    Resource description.

    Args:
        parameter: Description of parameter

    Returns:
        Description of return value
    """
    # Implementation
    pass
```

### Example Resource Implementation

Here's an example of a complete resource implementation for retrieving user history:

```python
@mcp.resource("history/{user_id}")
async def get_history(user_id: str) -> List[Dict[str, Any]]:
    """
    Get full history for a specific user.

    Args:
        user_id: The unique user identifier

    Returns:
        List of history items for the user
    """
    # Validate user_id
    if not user_id:
        raise ValueError("user_id is required")

    try:
        # Retrieve items from repository
        items = await self.repository.get_items_by_user(user_id)

        # Return the items
        return items
    except Exception as e:
        # Log the error
        logger.error(f"Error retrieving history for user {user_id}: {e}")

        # Return empty list on error
        return []
```

### URI Pattern Guidelines

1. **URI Structure**

   - Use RESTful-style URI paths
   - Start with a noun describing the resource
   - Use path parameters in curly braces `{param}`
   - Keep paths simple and intuitive

2. **Common URI Patterns**

   - Collection: `resource_type`
   - Single item: `resource_type/{id}`
   - Filtered collection: `resource_type/filter/{filter_value}`
   - Nested resources: `parent_resource/{parent_id}/child_resource`

3. **Parameter Extraction**
   - Parameters in the URI are automatically extracted and passed to the handler
   - Parameter names in the URI must match the handler function parameters
   - Parameters are passed as strings and should be converted to the appropriate type

### Resource Return Guidelines

1. **Return Types**

   - Resources can return various types (not just dictionaries)
   - Common return types: List[Dict], Dict, str, bytes
   - Return type should be appropriate for the resource content

2. **Error Handling**
   - Unlike tools, resources should handle errors internally
   - Resources should never raise exceptions to the client
   - Return empty collections or default values on error

## Standard Tool Patterns

### CRUD Operations

1. **Create Tools**

```python
@mcp.tool()
async def create_item(
    user_id: str,
    item_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Create a new item."""
    # Implementation
    pass
```

2. **Read Tools**

```python
@mcp.tool()
async def get_item(
    user_id: str,
    item_id: str
) -> Dict[str, Any]:
    """Get an item by ID."""
    # Implementation
    pass
```

3. **Update Tools**

```python
@mcp.tool()
async def update_item(
    user_id: str,
    item_id: str,
    item_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Update an existing item."""
    # Implementation
    pass
```

4. **Delete Tools**

```python
@mcp.tool()
async def delete_item(
    user_id: str,
    item_id: str
) -> Dict[str, Any]:
    """Delete an item by ID."""
    # Implementation
    pass
```

### Query Operations

```python
@mcp.tool()
async def search_items(
    user_id: str,
    query: str,
    limit: Optional[int] = 10,
    offset: Optional[int] = 0
) -> Dict[str, Any]:
    """Search for items matching a query."""
    # Implementation
    pass
```

### Processing Operations

```python
@mcp.tool()
async def process_data(
    user_id: str,
    data: Dict[str, Any],
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Process data with optional configuration."""
    # Implementation
    pass
```

### Analysis Operations

```python
@mcp.tool()
async def analyze_content(
    user_id: str,
    content: str,
    analysis_type: Optional[str] = "general"
) -> Dict[str, Any]:
    """Analyze content with specified analysis type."""
    # Implementation
    pass
```

## Standard Resource Patterns

### Collection Resources

```python
@mcp.resource("items/{user_id}")
async def get_items(user_id: str) -> List[Dict[str, Any]]:
    """Get all items for a user."""
    # Implementation
    pass
```

### Single Item Resources

```python
@mcp.resource("item/{user_id}/{item_id}")
async def get_item(user_id: str, item_id: str) -> Dict[str, Any]:
    """Get a specific item for a user."""
    # Implementation
    pass
```

### Filtered Collection Resources

```python
@mcp.resource("items/{user_id}/category/{category}")
async def get_items_by_category(user_id: str, category: str) -> List[Dict[str, Any]]:
    """Get items for a user filtered by category."""
    # Implementation
    pass
```

### Limited Collection Resources

```python
@mcp.resource("items/{user_id}/limit/{limit}")
async def get_limited_items(user_id: str, limit: str) -> List[Dict[str, Any]]:
    """Get a limited number of items for a user."""
    # Convert string parameter to integer
    limit_int = int(limit)
    # Implementation
    pass
```

## Naming Conventions

### Tool Naming

1. **Verb-Noun Pattern**

   - Start with a verb describing the action
   - Follow with a noun describing the entity
   - Examples: `store_input`, `get_context`, `analyze_conversation`

2. **Common Verb Prefixes**
   - `get_` - Retrieve data
   - `store_` - Store data
   - `create_` - Create new entities
   - `update_` - Update existing entities
   - `delete_` - Remove entities
   - `process_` - Process data
   - `analyze_` - Analyze data

### Resource Naming

1. **Noun Pattern**

   - Use nouns to describe the resource
   - Use plural for collections, singular for individual items
   - Examples: `history/{user_id}`, `item/{item_id}`, `settings/{user_id}`

2. **URI Parameter Naming**
   - Use clear, descriptive names
   - Match parameter names with handler function parameters
   - Examples: `{user_id}`, `{item_id}`, `{category}`

### Consistency Guidelines

1. **Cross-Service Consistency**

   - Use the same naming pattern for similar operations across services
   - Use the same parameter names for the same concepts
   - Use the same return structures for similar operations

2. **Internal Consistency**
   - Be consistent within a service
   - Follow the same patterns for all tools and resources
   - Use the same error handling patterns throughout

## Implementation Best Practices

### Input Validation

Always validate input parameters:

```python
# Validate required parameters
if not user_id:
    raise ValueError("user_id is required")

# Validate parameter types
if not isinstance(limit, int) or limit <= 0:
    raise ValueError("limit must be a positive integer")

# Validate parameter values
if category not in VALID_CATEGORIES:
    raise ValueError(f"Invalid category: {category}")
```

### Error Handling

1. **Tool Error Handling**

```python
try:
    # Perform operation
    result = await perform_operation(user_id, data)

    # Return success response
    return {
        "status": "success",
        "data": result
    }
except ValueError as e:
    # Handle validation errors
    logger.warning(f"Validation error in tool_name: {e}")
    return {
        "status": "error",
        "error": str(e),
        "error_type": "validation_error"
    }
except Exception as e:
    # Handle unexpected errors
    logger.error(f"Error in tool_name: {e}")
    return {
        "status": "error",
        "error": "An unexpected error occurred",
        "error_type": "internal_error"
    }
```

2. **Resource Error Handling**

```python
try:
    # Retrieve data
    items = await retrieve_data(user_id)

    # Return the data
    return items
except Exception as e:
    # Log the error
    logger.error(f"Error retrieving resource: {e}")

    # Return empty result on error
    return [] if is_collection else {}
```

### Async Implementation

All tool and resource handlers should be async:

```python
@mcp.tool()
async def async_tool(user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Async tool implementation."""
    # Async operations
    result = await async_operation(user_id, data)
    return {"status": "success", "data": result}
```

### User Partitioning

Always use user_id for data partitioning:

```python
@mcp.tool()
async def create_item(user_id: str, item_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create an item for a specific user."""
    # Create item with user_id association
    item = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,  # Associate with user
        "data": item_data,
        "created_at": datetime.now().isoformat()
    }

    # Store with user partitioning
    await self.repository.create_item(item)

    return {"status": "success", "item_id": item["id"]}
```

### Performance Optimization

1. **Limit Result Sets**

```python
@mcp.resource("items/{user_id}/limit/{limit}")
async def get_limited_items(user_id: str, limit: str) -> List[Dict[str, Any]]:
    """Get a limited number of items."""
    # Convert and validate limit
    try:
        limit_int = int(limit)
        if limit_int <= 0:
            limit_int = 10  # Default limit
    except ValueError:
        limit_int = 10  # Default on conversion error

    # Get items with limit
    items = await self.repository.get_items_by_user(user_id, limit=limit_int)

    return items
```

2. **Early Filtering**

```python
@mcp.tool()
async def search_items(user_id: str, query: str) -> Dict[str, Any]:
    """Search for items matching a query."""
    # Get items with filtering at the repository level
    items = await self.repository.search_items(user_id, query)

    return {
        "status": "success",
        "items": items,
        "count": len(items)
    }
```

## Documentation Standards

### Tool Documentation

Tools should be documented with detailed docstrings:

```python
@mcp.tool()
async def analyze_content(
    user_id: str,
    content: str,
    analysis_type: Optional[str] = "general"
) -> Dict[str, Any]:
    """
    Analyze content using the specified analysis type.

    This tool performs textual analysis on the provided content,
    generating insights based on the specified analysis type.

    Args:
        user_id: The unique user identifier
        content: The text content to analyze
        analysis_type: Type of analysis to perform (default: "general")
            Supported types: "general", "sentiment", "entities", "topics"

    Returns:
        Dictionary containing:
        - status: "success" or "error"
        - analysis: Analysis results (on success)
            - type: The analysis type performed
            - results: Analysis-specific results
            - meta: Additional metadata
        - error: Error message (on error)
        - error_type: Type of error (on error)

    Examples:
        Sentiment analysis:
        >>> await analyze_content("user123", "I love this product!", "sentiment")
        {
            "status": "success",
            "analysis": {
                "type": "sentiment",
                "results": {"sentiment": "positive", "score": 0.92},
                "meta": {"version": "1.0"}
            }
        }
    """
    # Implementation
    pass
```

### Resource Documentation

Resources should be documented with detailed docstrings:

```python
@mcp.resource("history/{user_id}/limit/{limit}")
async def get_limited_history(user_id: str, limit: str) -> List[Dict[str, Any]]:
    """
    Get a limited number of history items for a user.

    This resource retrieves the most recent history items for the specified user,
    limited to the number specified by the limit parameter.

    Args:
        user_id: The unique user identifier
        limit: Maximum number of items to return (string, will be converted to int)

    Returns:
        List of history items, each containing:
        - id: Unique item identifier
        - user_id: The user the item belongs to
        - data: The item data
        - timestamp: When the item was created or last modified

    Examples:
        >>> await get_limited_history("user123", "5")
        [
            {
                "id": "item1",
                "user_id": "user123",
                "data": {"content": "Example content"},
                "timestamp": "2023-01-01T12:00:00Z"
            },
            ...
        ]
    """
    # Implementation
    pass
```

### Documentation Catalog

Maintain a catalog of all tools and resources in a service:

```python
class MemoryService:
    """
    Memory Service for storing and retrieving user data.

    Tools:
        store_input: Store input data for a user
        update_item: Update an existing item
        delete_item: Delete an item

    Resources:
        history/{user_id}: Get full history for a user
        history/{user_id}/limit/{limit}: Get limited history for a user
        item/{user_id}/{item_id}: Get a specific item
    """

    def __init__(self, repository):
        """Initialize the Memory Service."""
        self.repository = repository
        self.mcp = FastMCP("MemoryService")
        self._register_tools_and_resources()

    def _register_tools_and_resources(self):
        """Register all tools and resources with the MCP server."""
        # Register tools
        self.mcp.tool()(self.store_input)
        self.mcp.tool()(self.update_item)
        self.mcp.tool()(self.delete_item)

        # Register resources
        self.mcp.resource("history/{user_id}")(self.get_history)
        self.mcp.resource("history/{user_id}/limit/{limit}")(self.get_limited_history)
        self.mcp.resource("item/{user_id}/{item_id}")(self.get_item)
```

## Testing Tools and Resources

### Unit Testing Tools

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_store_input():
    """Test the store_input tool."""
    # Create mock repository
    mock_repository = MagicMock()
    mock_repository.store_item = AsyncMock(return_value=None)

    # Create service with mock repository
    service = MemoryService(mock_repository)

    # Test data
    user_id = "test_user"
    input_data = {"content": "Test content"}

    # Call the tool
    result = await service.store_input(user_id, input_data)

    # Verify result
    assert result["status"] == "stored"
    assert "item_id" in result

    # Verify repository call
    mock_repository.store_item.assert_called_once()
    call_args = mock_repository.store_item.call_args[0][0]
    assert call_args["user_id"] == user_id
    assert call_args["data"] == input_data
```

### Unit Testing Resources

```python
@pytest.mark.asyncio
async def test_get_history():
    """Test the get_history resource."""
    # Mock data
    mock_items = [
        {"id": "item1", "user_id": "test_user", "data": {"content": "Test 1"}},
        {"id": "item2", "user_id": "test_user", "data": {"content": "Test 2"}}
    ]

    # Create mock repository
    mock_repository = MagicMock()
    mock_repository.get_items_by_user = AsyncMock(return_value=mock_items)

    # Create service with mock repository
    service = MemoryService(mock_repository)

    # Test the resource
    result = await service.get_history("test_user")

    # Verify result
    assert len(result) == 2
    assert result[0]["id"] == "item1"
    assert result[1]["id"] == "item2"

    # Verify repository call
    mock_repository.get_items_by_user.assert_called_once_with("test_user")
```

### Testing Error Handling

```python
@pytest.mark.asyncio
async def test_store_input_error():
    """Test error handling in the store_input tool."""
    # Create mock repository that raises an exception
    mock_repository = MagicMock()
    mock_repository.store_item = AsyncMock(side_effect=Exception("Test error"))

    # Create service with mock repository
    service = MemoryService(mock_repository)

    # Call the tool
    result = await service.store_input("test_user", {"content": "Test"})

    # Verify error response
    assert result["status"] == "error"
    assert "error" in result
```

### Integration Testing

```python
@pytest.mark.asyncio
async def test_tool_integration():
    """Test tool integration with actual repository."""
    # Create repository with test database
    repository = Repository(test_database_url)

    # Create service
    service = MemoryService(repository)

    # Test data
    user_id = "test_user"
    input_data = {"content": "Integration test"}

    # Store input
    store_result = await service.store_input(user_id, input_data)
    assert store_result["status"] == "stored"
    item_id = store_result["item_id"]

    # Retrieve history
    history = await service.get_history(user_id)

    # Verify item was stored
    assert any(item["id"] == item_id for item in history)

    # Clean up
    await repository.delete_item(item_id)
```

## Common Pitfalls and Solutions

### Pitfall 1: Violating Service Boundaries

**Problem**: Accessing another service's data directly, bypassing the MCP interface.

```python
# BAD: Directly accessing repository from another service
@mcp.tool()
async def get_context(self, user_id: str, query: str) -> Dict[str, Any]:
    """Get context for a query."""
    # Directly accessing Memory Service's repository
    items = await memory_service.repository.get_items_by_user(user_id)
    # Process items...
```

**Solution**: Always use the MCP interface to communicate with other services.

```python
# GOOD: Using MCP client to access Memory Service
@mcp.tool()
async def get_context(self, user_id: str, query: str) -> Dict[str, Any]:
    """Get context for a query."""
    # Get Memory Service client
    memory_client = self.mcp_client_manager.get_client("memory")

    # Get history through the proper interface
    history, _ = await memory_client.get_resource(f"history/{user_id}")

    # Process history...
```

### Pitfall 2: Too Much Logic in Tools/Resources

**Problem**: Implementing complex business logic directly in tool/resource handlers.

```python
# BAD: Too much logic in the tool handler
@mcp.tool()
async def analyze_conversation(self, user_id: str, conversation_id: str) -> Dict[str, Any]:
    """Analyze a conversation."""
    # Get conversation messages
    messages = await self.repository.get_messages(conversation_id)

    # Complex analysis logic embedded in the tool handler
    topic_counts = {}
    sentiment_scores = []
    entities = set()

    for message in messages:
        # Extract topics
        text = message["content"]
        topics = extract_topics(text)
        for topic in topics:
            topic_counts[topic] = topic_counts.get(topic, 0) + 1

        # Calculate sentiment
        sentiment = calculate_sentiment(text)
        sentiment_scores.append(sentiment)

        # Extract entities
        message_entities = extract_entities(text)
        entities.update(message_entities)

    # More complex processing...
```

**Solution**: Move complex logic to separate service methods, keeping tool handlers focused on the interface.

```python
# GOOD: Tool handler delegates to service methods
@mcp.tool()
async def analyze_conversation(self, user_id: str, conversation_id: str) -> Dict[str, Any]:
    """Analyze a conversation."""
    try:
        # Get conversation messages
        messages = await self.repository.get_messages(conversation_id)

        # Delegate to specialized service methods
        topics = await self._analyze_topics(messages)
        sentiment = await self._analyze_sentiment(messages)
        entities = await self._extract_entities(messages)

        # Return results
        return {
            "status": "success",
            "analysis": {
                "topics": topics,
                "sentiment": sentiment,
                "entities": entities
            }
        }
    except Exception as e:
        logger.error(f"Error analyzing conversation {conversation_id}: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

# Helper methods for complex logic
async def _analyze_topics(self, messages: List[Dict[str, Any]]) -> Dict[str, int]:
    """Analyze topics in messages."""
    # Implementation...

async def _analyze_sentiment(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze sentiment in messages."""
    # Implementation...

async def _extract_entities(self, messages: List[Dict[str, Any]]) -> List[str]:
    """Extract entities from messages."""
    # Implementation...
```

### Pitfall 3: Poor Error Handling

**Problem**: Letting exceptions propagate to the client or returning inconsistent error formats.

```python
# BAD: Poor error handling
@mcp.tool()
async def create_item(self, user_id: str, item_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new item."""
    # No validation

    # No try/except block
    item = await self.repository.create_item(user_id, item_data)

    # Inconsistent return format
    return {"id": item["id"]}
```

**Solution**: Implement consistent error handling and return formats.

```python
# GOOD: Proper error handling
@mcp.tool()
async def create_item(self, user_id: str, item_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new item."""
    # Validate input
    if not user_id:
        return {
            "status": "error",
            "error": "user_id is required"
        }

    if not item_data:
        return {
            "status": "error",
            "error": "item_data is required"
        }

    try:
        # Create the item
        item = await self.repository.create_item(user_id, item_data)

        # Return success response
        return {
            "status": "success",
            "item_id": item["id"]
        }
    except Exception as e:
        # Log the error
        logger.error(f"Error creating item for user {user_id}: {e}")

        # Return error response
        return {
            "status": "error",
            "error": str(e)
        }
```

### Pitfall 4: Inefficient Resource Access

**Problem**: Retrieving more data than needed and filtering in memory.

```python
# BAD: Inefficient resource access
@mcp.resource("items/{user_id}/category/{category}")
async def get_items_by_category(self, user_id: str, category: str) -> List[Dict[str, Any]]:
    """Get items by category."""
    # Get all items
    all_items = await self.repository.get_items_by_user(user_id)

    # Filter in memory
    category_items = [item for item in all_items if item.get("category") == category]

    return category_items
```

**Solution**: Use efficient querying at the repository level.

```python
# GOOD: Efficient resource access
@mcp.resource("items/{user_id}/category/{category}")
async def get_items_by_category(self, user_id: str, category: str) -> List[Dict[str, Any]]:
    """Get items by category."""
    # Get items with filtering at the repository level
    items = await self.repository.get_items_by_user_and_category(user_id, category)

    return items
```

### Pitfall 5: Overly Complex Parameter Handling

**Problem**: Complex, nested parameter structures that are hard to validate and use.

```python
# BAD: Overly complex parameters
@mcp.tool()
async def search_items(
    self,
    user_id: str,
    search_params: Dict[str, Any]
) -> Dict[str, Any]:
    """Search for items."""
    # Extract parameters from complex structure
    query = search_params.get("query", "")
    filters = search_params.get("filters", {})
    sort_by = search_params.get("sort", {}).get("field", "timestamp")
    sort_dir = search_params.get("sort", {}).get("direction", "desc")
    page = search_params.get("pagination", {}).get("page", 1)
    page_size = search_params.get("pagination", {}).get("size", 10)

    # Complex parameter validation
    # ...
```

**Solution**: Use flat parameter structures with explicit defaults.

```python
# GOOD: Simple, flat parameters
@mcp.tool()
async def search_items(
    self,
    user_id: str,
    query: str,
    filter_category: Optional[str] = None,
    filter_tags: Optional[List[str]] = None,
    sort_by: Optional[str] = "timestamp",
    sort_direction: Optional[str] = "desc",
    page: Optional[int] = 1,
    page_size: Optional[int] = 10
) -> Dict[str, Any]:
    """Search for items."""
    # Simple parameter validation
    if page < 1:
        page = 1

    if page_size < 1 or page_size > 100:
        page_size = 10

    # Use parameters directly
    # ...
```

## Example Catalog

### Memory Service

```python
class MemoryService:
    """
    Memory Service for storing and retrieving user data.

    Tools:
        store_input(user_id, input_data, timestamp=None) -> Dict
            Store input data for a user

        create_item(user_id, item_data) -> Dict
            Create a new item

        update_item(user_id, item_id, item_data) -> Dict
            Update an existing item

        delete_item(user_id, item_id) -> Dict
            Delete an item

    Resources:
        history/{user_id} -> List[Dict]
            Get full history for a user

        history/{user_id}/limit/{limit} -> List[Dict]
            Get limited history for a user

        item/{user_id}/{item_id} -> Dict
            Get a specific item

        items/{user_id}/category/{category} -> List[Dict]
            Get items by category
    """
```

### Cognition Service

```python
class CognitionService:
    """
    Cognition Service for processing and analyzing user data.

    Tools:
        get_context(user_id, query=None, limit=10) -> Dict
            Get relevant context for a user

        analyze_conversation(user_id, conversation_id, analysis_type="summary") -> Dict
            Analyze a conversation

        search_history(user_id, query, limit=10) -> Dict
            Search user history

        process_input(user_id, input_data) -> Dict
            Process input data

    Resources:
        context/{user_id} -> Dict
            Get default context for a user

        context/{user_id}/{query} -> Dict
            Get context for a specific query
    """
```

## Conclusion

Tools and resources form the foundation of the MCP architecture in Phase 3 of the Cortex Core project. By following the patterns, naming conventions, and best practices outlined in this guide, you can create a consistent, maintainable, and robust interface for service communication.

Key takeaways:

1. **Tools vs Resources**: Use tools for operations with side effects, resources for data retrieval
2. **Standard Patterns**: Follow consistent patterns for naming and implementation
3. **Input Validation**: Always validate input parameters
4. **Error Handling**: Implement robust error handling with consistent formats
5. **Documentation**: Provide detailed documentation for all tools and resources
6. **Testing**: Test all tools and resources thoroughly

By implementing tools and resources according to these guidelines, you'll establish clear service boundaries that will facilitate the transition to distributed services in Phase 4.
