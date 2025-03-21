# Performance Optimization Guide

## Overview

This document provides a comprehensive guide for implementing performance optimizations in Phase 5 of the Cortex Core. It covers database query optimization, connection pooling, caching strategies, network communication efficiency, memory optimization, load testing, and benchmarking techniques that will ensure the system meets production performance requirements.

Performance optimization is a critical aspect of production hardening, directly impacting:

1. **User Experience**: Response times and system responsiveness
2. **Resource Utilization**: Efficient use of CPU, memory, and storage
3. **Scalability**: System capacity to handle increased load
4. **Cost Efficiency**: Minimizing infrastructure costs
5. **System Stability**: Preventing performance-related outages

This guide builds upon the system architecture established in Phase 4, focusing on targeted optimizations rather than premature optimizations. The goal is to achieve reliable, predictable performance that meets service level objectives (SLOs) in production environments.

## System Architecture

The performance optimization components integrate with the Cortex Core architecture as follows:

```mermaid
graph TD
    Client[Client Applications] --> API[FastAPI Application]

    API --> DBOptimization[Database Optimization]
    API --> CachingLayer[Caching Layer]
    API --> ConnectionPooling[Connection Pooling]
    API --> AsyncProcessing[Asynchronous Processing]

    DBOptimization --> PostgresDB[(PostgreSQL Database)]

    API --> NetworkMcpClient[Network MCP Client]
    NetworkMcpClient --> ServiceDiscovery[Service Discovery]

    ServiceDiscovery --> MemoryService[Memory Service]
    ServiceDiscovery --> CognitionService[Cognition Service]

    MemoryService --> ServiceCache[Service Cache]
    CognitionService --> ServiceCache

    MemoryService --> MemoryDB[(Memory Service Database)]

    subgraph "Performance Optimization Components"
        DBOptimization
        CachingLayer
        ConnectionPooling
        AsyncProcessing
        ServiceCache
    end

    subgraph "Monitoring & Feedback"
        API --> PerformanceMetrics[Performance Metrics]
        MemoryService --> PerformanceMetrics
        CognitionService --> PerformanceMetrics
        PerformanceMetrics --> LoadTesting[Load Testing]
        LoadTesting --> PerformanceBaselines[Performance Baselines]
    end
```

## Database Optimization

### Query Optimization Principles

1. **Analyze Before Optimizing**: Use explain plans to understand query performance
2. **Index Strategically**: Create indexes based on query patterns and data access
3. **Use Appropriate Data Types**: Choose the right data types for columns
4. **Optimize Joins**: Minimize joins and ensure they use indexed columns
5. **Minimize Data Transfer**: Select only the columns you need
6. **Use Database Features**: Leverage PostgreSQL-specific optimizations

### Setting Up EXPLAIN ANALYZE

Use `EXPLAIN ANALYZE` to understand and optimize query performance:

```python
import asyncpg
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

async def analyze_query(db_session: AsyncSession, query: str, params: dict = None):
    """
    Analyze a SQL query and return the execution plan.

    Args:
        db_session: SQLAlchemy async session
        query: SQL query to analyze
        params: Query parameters

    Returns:
        Execution plan as a string
    """
    # Convert the query to use $1, $2, etc. for parameters
    if params:
        # This is a simplified approach; you might need more robust parameter conversion
        for i, (key, value) in enumerate(params.items(), 1):
            query = query.replace(f":{key}", f"${i}")

    # Wrap the query with EXPLAIN ANALYZE
    explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"

    # Execute the explain query
    result = await db_session.execute(text(explain_query))
    explain_result = result.scalar()

    return explain_result

# Example usage
async def optimize_query(db_session: AsyncSession):
    query = """
    SELECT u.name, w.name as workspace_name, count(c.id) as conversation_count
    FROM users u
    JOIN workspaces w ON w.owner_id = u.user_id
    LEFT JOIN conversations c ON c.workspace_id = w.id
    WHERE u.user_id = :user_id
    GROUP BY u.name, w.name
    """

    params = {"user_id": "test-user-123"}

    plan = await analyze_query(db_session, query, params)

    # Print the plan for analysis
    import json
    print(json.dumps(plan, indent=2))

    # Analyze the plan and suggest optimizations
    # This could be extended to automatically analyze common issues
    return analyze_plan(plan)

def analyze_plan(plan):
    """
    Analyze a query execution plan and provide optimization suggestions.

    Args:
        plan: JSON execution plan from EXPLAIN ANALYZE

    Returns:
        Dictionary of optimization suggestions
    """
    suggestions = []

    # Extract the root node
    root_node = plan[0]["Plan"]

    # Check for sequential scans on large tables
    if root_node.get("Node Type") == "Seq Scan" or any_node_has(root_node, "Node Type", "Seq Scan"):
        suggestions.append({
            "issue": "Sequential Scan detected",
            "suggestion": "Consider adding an index to avoid sequential scans on large tables",
            "details": "Look for tables with sequential scans in the execution plan"
        })

    # Check for high-cost operations
    if root_node.get("Total Cost", 0) > 1000:
        suggestions.append({
            "issue": "High cost query",
            "suggestion": "Optimize the most expensive operations in the query",
            "details": f"Total cost is {root_node.get('Total Cost')}, which is high"
        })

    # Check for hash joins on large tables
    if any_node_has(root_node, "Node Type", "Hash Join") and root_node.get("Plan Rows", 0) > 10000:
        suggestions.append({
            "issue": "Hash Join on large result set",
            "suggestion": "Ensure join columns are indexed or consider denormalizing data",
            "details": "Hash joins can be expensive for large datasets"
        })

    return suggestions

def any_node_has(node, key, value):
    """Check if any node in the plan has the specified key-value pair"""
    if node.get(key) == value:
        return True

    # Check child plans
    for child_key in ["Plans", "Plan"]:
        if child_key in node and isinstance(node[child_key], list):
            for child in node[child_key]:
                if any_node_has(child, key, value):
                    return True
        elif child_key in node and isinstance(node[child_key], dict):
            if any_node_has(node[child_key], key, value):
                return True

    return False
```

### Index Optimization

Optimize database indexes based on query patterns:

```python
from sqlalchemy import Column, String, Index, create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import Table

Base = declarative_base()

# Example of optimized indexes for the Workspace model
class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(String, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String, nullable=False)
    owner_id = Column(String, nullable=False)

    # Create an index on owner_id for fast lookups by owner
    __table_args__ = (
        Index('idx_workspace_owner', 'owner_id'),
    )

# Example of optimized indexes for the Message model
class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True)
    conversation_id = Column(String, nullable=False)
    sender_id = Column(String, nullable=False)
    content = Column(String, nullable=False)
    timestamp = Column(String, nullable=False)

    # Create composite indexes for common query patterns
    __table_args__ = (
        # Index for finding messages in a conversation, ordered by timestamp
        Index('idx_message_convo_time', 'conversation_id', 'timestamp'),

        # Index for finding messages by sender
        Index('idx_message_sender', 'sender_id'),
    )

# Create partial indexes for specific query patterns using raw SQL
def create_optimized_indexes(engine):
    """Create optimized indexes that can't be easily defined in SQLAlchemy models"""
    with engine.connect() as conn:
        # Partial index for active workspaces only
        conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_active_workspaces
        ON workspaces (owner_id)
        WHERE metadata->>'status' = 'active'
        """)

        # Expression index for lower case name searches
        conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_workspace_name_lower
        ON workspaces (lower(name))
        """)

        # Index on JSONB metadata for specific fields
        conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_workspace_metadata_type
        ON workspaces ((metadata->>'type'))
        """)
```

### Query Optimization Techniques

Optimize common query patterns:

```python
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Workspace, Conversation, Message, User

# 1. Use specific columns instead of SELECT *
async def get_workspace_summaries(db: AsyncSession, owner_id: str):
    """Optimized query that selects only needed columns"""
    query = select(
        Workspace.id,
        Workspace.name,
        Workspace.description,
        func.count(Conversation.id).label('conversation_count')
    ).join(
        Conversation, Conversation.workspace_id == Workspace.id, isouter=True
    ).where(
        Workspace.owner_id == owner_id
    ).group_by(
        Workspace.id, Workspace.name, Workspace.description
    )

    result = await db.execute(query)
    return result.mappings().all()

# 2. Use EXISTS for checking existence (more efficient than COUNT)
async def has_conversations(db: AsyncSession, workspace_id: str):
    """Optimized query that uses EXISTS instead of COUNT"""
    query = select(
        func.exists().where(Conversation.workspace_id == workspace_id)
    )

    result = await db.execute(query)
    return result.scalar()

# 3. Use LIMIT for pagination
async def get_paginated_messages(db: AsyncSession, conversation_id: str, page: int, page_size: int):
    """Optimized query with pagination"""
    offset = (page - 1) * page_size

    query = select(Message).where(
        Message.conversation_id == conversation_id
    ).order_by(
        Message.timestamp.desc()
    ).limit(page_size).offset(offset)

    result = await db.execute(query)
    return result.scalars().all()

# 4. Use window functions for complex aggregations
async def get_conversation_stats(db: AsyncSession, workspace_id: str):
    """Optimized query using window functions"""
    query = text("""
    SELECT
        c.id,
        c.topic,
        COUNT(m.id) as message_count,
        MAX(m.timestamp) as last_activity,
        FIRST_VALUE(m.content) OVER (
            PARTITION BY c.id
            ORDER BY m.timestamp DESC
        ) as last_message
    FROM conversations c
    LEFT JOIN messages m ON c.id = m.conversation_id
    WHERE c.workspace_id = :workspace_id
    GROUP BY c.id, c.topic
    ORDER BY last_activity DESC
    """)

    result = await db.execute(query, {"workspace_id": workspace_id})
    return result.mappings().all()

# 5. Use materialized views for complex reports
async def refresh_user_activity_view(db: AsyncSession):
    """Refresh a materialized view for reporting"""
    await db.execute(text("""
    REFRESH MATERIALIZED VIEW user_activity_summary
    """))

# Define the materialized view in a migration
"""
CREATE MATERIALIZED VIEW user_activity_summary AS
SELECT
    u.user_id,
    u.name,
    COUNT(DISTINCT w.id) as workspace_count,
    COUNT(DISTINCT c.id) as conversation_count,
    COUNT(DISTINCT m.id) as message_count,
    MAX(m.timestamp) as last_activity
FROM users u
LEFT JOIN workspaces w ON w.owner_id = u.user_id
LEFT JOIN conversations c ON c.workspace_id = w.id
LEFT JOIN messages m ON m.conversation_id = c.id
GROUP BY u.user_id, u.name;

CREATE UNIQUE INDEX ON user_activity_summary (user_id);
"""
```

### PostgreSQL-Specific Optimizations

Leverage PostgreSQL features for better performance:

```python
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

async def apply_postgres_optimizations(db: AsyncSession):
    """Apply PostgreSQL-specific optimizations"""

    # 1. Configure appropriate work_mem for complex operations
    await db.execute(text("SET work_mem = '16MB'"))

    # 2. Use unlogged tables for temporary or cache data
    await db.execute(text("""
    CREATE UNLOGGED TABLE IF NOT EXISTS temp_session_data (
        session_id TEXT PRIMARY KEY,
        data JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """))

    # 3. Use appropriate JSONB operators for metadata queries
    async def find_workspaces_by_metadata(db: AsyncSession, key: str, value: str):
        query = text("""
        SELECT * FROM workspaces
        WHERE metadata @> :metadata
        """)

        # Build a JSON string that matches the key-value pair
        json_filter = f'{{"{ key }": "{ value }"}}'

        result = await db.execute(query, {"metadata": json_filter})
        return result.mappings().all()

    # 4. Use appropriate JSONB indexing for metadata
    await db.execute(text("""
    CREATE INDEX IF NOT EXISTS idx_workspaces_metadata_gin
    ON workspaces USING GIN (metadata)
    """))

    # 5. Use table partitioning for large tables
    # This would be done in a migration
    """
    -- Example partitioning for messages table by month
    CREATE TABLE messages_partitioned (
        id TEXT NOT NULL,
        conversation_id TEXT NOT NULL,
        sender_id TEXT NOT NULL,
        content TEXT NOT NULL,
        timestamp TIMESTAMP NOT NULL,
        metadata JSONB DEFAULT '{}'
    ) PARTITION BY RANGE (timestamp);

    -- Create monthly partitions
    CREATE TABLE messages_y2025m01 PARTITION OF messages_partitioned
        FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

    CREATE TABLE messages_y2025m02 PARTITION OF messages_partitioned
        FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

    -- Add indexes to the partitioned table
    CREATE INDEX ON messages_partitioned (conversation_id, timestamp);
    """
```

## Connection Pooling Optimization

### AsyncPG Connection Pool Configuration

Configure optimal connection pooling for PostgreSQL with AsyncPG:

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os

def configure_optimized_engine():
    """Configure SQLAlchemy engine with optimized connection pooling"""

    # Get configuration from environment with reasonable defaults
    database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost/cortex")
    pool_size = int(os.getenv("DB_POOL_SIZE", "10"))
    max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "1800"))  # 30 minutes
    echo = os.getenv("DB_ECHO", "false").lower() == "true"

    # Create engine with optimized pool settings
    engine = create_async_engine(
        database_url,
        pool_size=pool_size,  # Base pool size
        max_overflow=max_overflow,  # Allow up to this many connections beyond pool_size
        pool_timeout=pool_timeout,  # Seconds to wait for a connection from the pool
        pool_recycle=pool_recycle,  # Recycle connections older than this many seconds
        pool_pre_ping=True,  # Test connections with a ping before using them
        echo=echo  # SQL logging for debugging (disable in production)
    )

    # Create session factory
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False  # Don't expire objects after commit for better performance
    )

    return engine, async_session

# Example usage of the session factory
async def get_db_session():
    """Dependency for FastAPI that provides a database session"""
    async_session = configure_optimized_engine()[1]
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
```

### Connection Pool Monitoring and Management

Monitor and manage connection pools to ensure optimal performance:

```python
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import logging

logger = logging.getLogger(__name__)

# Global tracker for active connections
_active_db_connections = 0
_connection_limit = int(os.getenv("DB_CONNECTION_LIMIT", "50"))
_connection_semaphore = asyncio.Semaphore(_connection_limit)

async def get_db_with_limits():
    """
    Database session dependency with connection limiting.
    Prevents too many simultaneous database connections.
    """
    global _active_db_connections

    # Try to acquire a semaphore slot
    try:
        # Wait for at most 5 seconds to get a database connection slot
        acquire_timeout = 5
        connection_available = await asyncio.wait_for(
            _connection_semaphore.acquire(),
            timeout=acquire_timeout
        )

        if not connection_available:
            logger.warning("Failed to acquire database connection slot")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection limit reached. Please try again later."
            )

        # Increment active connection count
        _active_db_connections += 1

        # Log connection stats periodically (every 10 connections)
        if _active_db_connections % 10 == 0:
            logger.info(f"Active DB connections: {_active_db_connections}")

        # Get a session from the regular dependency
        async_session = configure_optimized_engine()[1]
        async with async_session() as session:
            try:
                yield session
            finally:
                await session.close()
    except asyncio.TimeoutError:
        logger.error("Timeout waiting for database connection slot")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection timeout. Please try again later."
        )
    finally:
        # Always decrement the counter and release the semaphore when done
        if _active_db_connections > 0:
            _active_db_connections -= 1

        try:
            _connection_semaphore.release()
        except ValueError:
            # Semaphore was likely already released
            pass
```

### Optimizing Database Connections Initialization

Optimize database connection initialization:

```python
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import AsyncAdaptedQueuePool
import asyncpg
import os

async def init_connection(conn):
    """Initialize database connection with optimized settings"""
    # Set session parameters for better performance
    await conn.execute("SET timezone TO 'UTC'")

    # Set statement timeout to prevent long-running queries
    timeout_seconds = int(os.getenv("DB_STATEMENT_TIMEOUT", "30"))
    await conn.execute(f"SET statement_timeout = {timeout_seconds * 1000}")

    # Set appropriate work_mem for complex operations
    work_mem = os.getenv("DB_WORK_MEM", "8MB")
    await conn.execute(f"SET work_mem = '{work_mem}'")

    # Set appropriate maintenance_work_mem for maintenance operations
    maintenance_work_mem = os.getenv("DB_MAINTENANCE_WORK_MEM", "64MB")
    await conn.execute(f"SET maintenance_work_mem = '{maintenance_work_mem}'")

    # Disable synchronous commit for performance if data loss is acceptable
    # (Use with caution, as it can lead to data loss in case of a crash)
    if os.getenv("DB_ASYNC_COMMIT", "false").lower() == "true":
        await conn.execute("SET synchronous_commit TO OFF")

# Use the init_connection function with asyncpg
def create_db_engine_with_init():
    """Create database engine with connection initialization"""
    database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost/cortex")

    # Extract connection parameters to use with asyncpg directly
    connect_args = {
        "server_settings": {
            "application_name": "cortex-core"  # Helps identify connections in pg_stat_activity
        },
        "command_timeout": 10,  # Timeout for connection commands in seconds
        "statement_cache_size": 100,  # Size of prepared statement cache
        "max_cached_statement_lifetime": 300,  # Max seconds to keep statements cached
    }

    # Create engine with custom connection callable
    engine = create_async_engine(
        database_url,
        poolclass=AsyncAdaptedQueuePool,
        pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
        pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
        connect_args=connect_args,
        pool_pre_ping=True
    )

    # Set up connection initialization
    @engine.on_connect()
    async def on_connect(dbapi_connection):
        await init_connection(dbapi_connection)

    return engine
```

## Caching Implementation

### Redis Cache Configuration

Configure Redis for caching:

```python
import redis.asyncio as redis
import json
import os
import asyncio
from typing import Any, Optional, Union, Dict, List
import hashlib
import logging

logger = logging.getLogger(__name__)

class RedisCache:
    """Redis cache implementation for the Cortex Core"""

    def __init__(self, redis_url: str = None, namespace: str = "cortex:", default_ttl: int = 300):
        """
        Initialize Redis cache

        Args:
            redis_url: Redis connection URL
            namespace: Prefix for cache keys
            default_ttl: Default time-to-live in seconds
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.namespace = namespace
        self.default_ttl = default_ttl
        self._redis = None

    async def get_redis(self) -> redis.Redis:
        """Get Redis connection, initializing if needed"""
        if self._redis is None:
            self._redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            # Test connection
            try:
                await self._redis.ping()
            except redis.ConnectionError as e:
                logger.warning(f"Redis connection failed: {e}")
                self._redis = None
                raise

        return self._redis

    def _make_key(self, key: str) -> str:
        """Create a namespaced key"""
        return f"{self.namespace}{key}"

    async def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from the cache

        Args:
            key: Cache key
            default: Default value if key not found

        Returns:
            Cached value or default
        """
        try:
            r = await self.get_redis()
            value = await r.get(self._make_key(key))

            if value is None:
                return default

            # Deserialize JSON
            return json.loads(value)
        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.warning(f"Cache get error for key {key}: {e}")
            return default

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set a value in the cache

        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time-to-live in seconds (None for default)

        Returns:
            True if set succeeded, False otherwise
        """
        ttl = ttl if ttl is not None else self.default_ttl

        try:
            r = await self.get_redis()
            serialized = json.dumps(value)
            result = await r.set(self._make_key(key), serialized, ex=ttl)
            return result
        except (redis.RedisError, TypeError) as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete a value from the cache

        Args:
            key: Cache key

        Returns:
            True if deleted, False otherwise
        """
        try:
            r = await self.get_redis()
            result = await r.delete(self._make_key(key))
            return result > 0
        except redis.RedisError as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache

        Args:
            key: Cache key

        Returns:
            True if exists, False otherwise
        """
        try:
            r = await self.get_redis()
            result = await r.exists(self._make_key(key))
            return result > 0
        except redis.RedisError as e:
            logger.warning(f"Cache exists error for key {key}: {e}")
            return False

    async def clear_namespace(self) -> int:
        """
        Clear all keys in the current namespace

        Returns:
            Number of keys deleted
        """
        try:
            r = await self.get_redis()
            keys = await r.keys(f"{self.namespace}*")

            if not keys:
                return 0

            return await r.delete(*keys)
        except redis.RedisError as e:
            logger.warning(f"Cache clear error: {e}")
            return 0

    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Increment a numeric value in the cache

        Args:
            key: Cache key
            amount: Amount to increment

        Returns:
            New value after increment, or None on error
        """
        try:
            r = await self.get_redis()
            return await r.incrby(self._make_key(key), amount)
        except redis.RedisError as e:
            logger.warning(f"Cache increment error for key {key}: {e}")
            return None

    async def close(self) -> None:
        """Close Redis connection"""
        if self._redis is not None:
            await self._redis.close()
            self._redis = None

# Global cache instance
cache = RedisCache()

# Helper function to create cache keys from functions and arguments
def make_cache_key(func_name: str, *args, **kwargs) -> str:
    """
    Create a deterministic cache key from function name and arguments

    Args:
        func_name: Name of the function being cached
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Cache key as a string
    """
    # Convert args and kwargs to a consistent string representation
    key_parts = [func_name]

    # Add positional args
    for arg in args:
        key_parts.append(str(arg))

    # Add keyword args (sorted for consistency)
    for k in sorted(kwargs.keys()):
        key_parts.append(f"{k}={kwargs[k]}")

    # Join and hash if the key would be too long
    key = ":".join(key_parts)
    if len(key) > 100:
        # Hash long keys to avoid Redis key length limits
        key = hashlib.md5(key.encode()).hexdigest()

    return key
```

### Caching Decorators

Create decorators for easy caching of function results:

```python
import functools
from typing import Callable, Optional, Any, TypeVar, Union, cast

T = TypeVar('T')

def cached(ttl: Optional[int] = None, key_prefix: Optional[str] = None):
    """
    Decorator for caching async function results

    Args:
        ttl: Time-to-live in seconds (None for default)
        key_prefix: Optional prefix for the cache key

    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            # Generate cache key
            prefix = key_prefix or func.__module__ + "." + func.__name__
            cache_key = make_cache_key(prefix, *args, **kwargs)

            # Try to get from cache
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cast(T, cached_result)

            # Cache miss, call the original function
            logger.debug(f"Cache miss for {cache_key}")
            result = await func(*args, **kwargs)

            # Only cache non-None results
            if result is not None:
                await cache.set(cache_key, result, ttl=ttl)

            return result

        return wrapper

    return decorator

def cached_property(ttl: Optional[int] = None):
    """
    Decorator for caching async property results

    Args:
        ttl: Time-to-live in seconds (None for default)

    Returns:
        Decorated property
    """
    def decorator(func):
        @property
        @functools.wraps(func)
        def wrapper(self):
            # Create a unique key based on the object and function
            key = f"{func.__module__}.{func.__qualname__}:{id(self)}"

            # Create an async function that gets/sets the cache
            async def get_value():
                # Try to get from cache
                cached_result = await cache.get(key)
                if cached_result is not None:
                    logger.debug(f"Cache hit for property {key}")
                    return cached_result

                # Cache miss, call the original function
                logger.debug(f"Cache miss for property {key}")
                result = await func(self)

                # Cache the result
                if result is not None:
                    await cache.set(key, result, ttl=ttl)

                return result

            # Return a future for the result
            return asyncio.create_task(get_value())

        return wrapper

    return decorator

# Clear cache for specific function
async def clear_cache_for_function(func: Callable, *args, **kwargs) -> bool:
    """
    Clear cache for a specific function call

    Args:
        func: The function whose cache to clear
        *args: Function arguments
        **kwargs: Function keyword arguments

    Returns:
        True if cache was cleared, False otherwise
    """
    key_prefix = func.__module__ + "." + func.__name__
    cache_key = make_cache_key(key_prefix, *args, **kwargs)
    return await cache.delete(cache_key)
```

### Caching Strategies

Implement different caching strategies for specific scenarios:

```python
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional

# 1. Single item caching
@cached(ttl=300)  # Cache for 5 minutes
async def get_workspace(db: AsyncSession, workspace_id: str) -> Optional[Dict[str, Any]]:
    """Get a workspace by ID with caching"""
    result = await db.execute(
        select(Workspace).where(Workspace.id == workspace_id)
    )

    workspace = result.scalars().first()
    if workspace:
        # Convert to dict for JSON serialization
        return {
            "id": workspace.id,
            "name": workspace.name,
            "description": workspace.description,
            "owner_id": workspace.owner_id,
            "metadata": workspace.metadata
        }

    return None

# 2. List caching with user partitioning
@cached(ttl=60)  # Cache for 1 minute
async def get_user_workspaces(db: AsyncSession, user_id: str) -> List[Dict[str, Any]]:
    """Get workspaces for a user with caching"""
    result = await db.execute(
        select(Workspace).where(Workspace.owner_id == user_id)
    )

    workspaces = result.scalars().all()
    return [
        {
            "id": ws.id,
            "name": ws.name,
            "description": ws.description,
            "owner_id": ws.owner_id,
            "metadata": ws.metadata
        }
        for ws in workspaces
    ]

# 3. Cache invalidation on update
async def update_workspace(db: AsyncSession, workspace_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update a workspace and invalidate cache"""
    # Update in database
    result = await db.execute(
        select(Workspace).where(Workspace.id == workspace_id)
    )

    workspace = result.scalars().first()
    if not workspace:
        raise ValueError(f"Workspace not found: {workspace_id}")

    # Update fields
    for key, value in data.items():
        if hasattr(workspace, key):
            setattr(workspace, key, value)

    await db.commit()

    # Clear cache for both single item and list
    await clear_cache_for_function(get_workspace, db, workspace_id)
    await clear_cache_for_function(get_user_workspaces, db, workspace.owner_id)

    # Return updated workspace
    return {
        "id": workspace.id,
        "name": workspace.name,
        "description": workspace.description,
        "owner_id": workspace.owner_id,
        "metadata": workspace.metadata
    }

# 4. Cached configuration settings
@cached(ttl=3600)  # Cache for 1 hour
async def get_system_config(db: AsyncSession, config_name: str) -> Dict[str, Any]:
    """Get system configuration with caching"""
    # This would fetch from a configuration table
    result = await db.execute(
        text("SELECT config_value FROM system_config WHERE config_name = :name"),
        {"name": config_name}
    )

    config_row = result.first()
    if config_row:
        return json.loads(config_row[0])

    # Return default config if not found
    return {}

# 5. Cache with manual bypass option
async def get_workspace_with_bypass(
    db: AsyncSession,
    workspace_id: str,
    bypass_cache: bool = False
) -> Optional[Dict[str, Any]]:
    """Get workspace with option to bypass cache"""
    if not bypass_cache:
        # Try to get from cache
        cache_key = make_cache_key("get_workspace", db, workspace_id)
        cached_result = await cache.get(cache_key)
        if cached_result is not None:
            return cached_result

    # Cache miss or bypass requested, call the database
    result = await db.execute(
        select(Workspace).where(Workspace.id == workspace_id)
    )

    workspace = result.scalars().first()
    if workspace:
        data = {
            "id": workspace.id,
            "name": workspace.name,
            "description": workspace.description,
            "owner_id": workspace.owner_id,
            "metadata": workspace.metadata
        }

        # Cache if not bypassing
        if not bypass_cache:
            cache_key = make_cache_key("get_workspace", db, workspace_id)
            await cache.set(cache_key, data, ttl=300)

        return data

    return None
```

### Cache Warming and Preloading

Implement cache warming for frequently accessed data:

```python
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import logging

logger = logging.getLogger(__name__)

class CacheWarmer:
    """Cache warming implementation for preloading frequent data"""

    def __init__(self, db_session_factory):
        """
        Initialize cache warmer

        Args:
            db_session_factory: Factory for creating database sessions
        """
        self.db_session_factory = db_session_factory

    async def warm_user_caches(self, user_ids: List[str]) -> None:
        """
        Preload caches for given users

        Args:
            user_ids: List of user IDs to warm caches for
        """
        logger.info(f"Warming caches for {len(user_ids)} users")

        async with self.db_session_factory() as db:
            # Preload workspaces for all users
            tasks = [self._preload_user_workspaces(db, user_id) for user_id in user_ids]
            await asyncio.gather(*tasks)

    async def _preload_user_workspaces(self, db: AsyncSession, user_id: str) -> None:
        """Preload workspaces for a user"""
        try:
            # This will populate the cache due to the @cached decorator
            await get_user_workspaces(db, user_id)
            logger.debug(f"Preloaded workspaces for user {user_id}")

            # Get workspace IDs to preload conversations
            workspaces = await get_user_workspaces(db, user_id)
            workspace_ids = [ws["id"] for ws in workspaces]

            # Preload conversations for each workspace
            for workspace_id in workspace_ids:
                await self._preload_workspace_conversations(db, workspace_id)
        except Exception as e:
            logger.error(f"Error preloading data for user {user_id}: {e}")

    async def _preload_workspace_conversations(self, db: AsyncSession, workspace_id: str) -> None:
        """Preload conversations for a workspace"""
        try:
            # Get conversations for workspace (this would have its own @cached decorator)
            result = await db.execute(
                select(Conversation).where(Conversation.workspace_id == workspace_id)
            )

            conversations = result.scalars().all()

            # Convert to dict and cache manually
            conversations_data = [
                {
                    "id": conv.id,
                    "workspace_id": conv.workspace_id,
                    "topic": conv.topic,
                    "participant_ids": conv.participant_ids,
                    "metadata": conv.metadata
                }
                for conv in conversations
            ]

            # Cache the conversations list
            cache_key = make_cache_key("get_workspace_conversations", db, workspace_id)
            await cache.set(cache_key, conversations_data, ttl=300)

            logger.debug(f"Preloaded {len(conversations_data)} conversations for workspace {workspace_id}")
        except Exception as e:
            logger.error(f"Error preloading conversations for workspace {workspace_id}: {e}")

    async def schedule_periodic_warming(self, interval_seconds: int = 3600) -> None:
        """
        Schedule periodic cache warming

        Args:
            interval_seconds: Interval between warming runs
        """
        while True:
            try:
                # Get active users to warm
                async with self.db_session_factory() as db:
                    # Get users active in the last 24 hours
                    result = await db.execute(text("""
                    SELECT DISTINCT sender_id FROM messages
                    WHERE timestamp > NOW() - INTERVAL '24 hours'
                    LIMIT 100
                    """))

                    active_users = [row[0] for row in result.fetchall()]

                # Warm caches for active users
                if active_users:
                    await self.warm_user_caches(active_users)
            except Exception as e:
                logger.error(f"Error in cache warming: {e}")

            # Wait for next interval
            await asyncio.sleep(interval_seconds)

# Usage in application startup
async def start_cache_warming():
    warmer = CacheWarmer(async_session)

    # Start a background task for periodic warming
    asyncio.create_task(warmer.schedule_periodic_warming())

    # Warm caches for specific users immediately
    admin_users = ["admin-user-1", "admin-user-2"]
    await warmer.warm_user_caches(admin_users)
```

## Asynchronous Processing Optimization

### Task Queue Implementation

Implement an optimized task queue for background processing:

```python
import asyncio
import logging
from typing import Callable, Dict, Any, List, Optional, Coroutine
import time
import uuid
import traceback

logger = logging.getLogger(__name__)

class TaskQueue:
    """Asynchronous task queue for background processing"""

    def __init__(self, max_workers: int = 10, max_queue_size: int = 1000):
        """
        Initialize task queue

        Args:
            max_workers: Maximum number of concurrent tasks
            max_queue_size: Maximum size of task queue
        """
        self.max_workers = max_workers
        self.queue = asyncio.Queue(max_queue_size)
        self.workers: List[asyncio.Task] = []
        self.running = False
        self.tasks_processed = 0
        self.tasks_failed = 0

        # Task storage for status tracking
        self.task_status: Dict[str, Dict[str, Any]] = {}

    async def start(self) -> None:
        """Start the task queue workers"""
        if self.running:
            return

        self.running = True

        # Start worker tasks
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker_loop(i))
            self.workers.append(worker)

        logger.info(f"Started {self.max_workers} task queue workers")

    async def stop(self) -> None:
        """Stop the task queue workers"""
        if not self.running:
            return

        self.running = False

        # Cancel all workers
        for worker in self.workers:
            worker.cancel()

        # Wait for workers to complete
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)

        self.workers = []
        logger.info("Stopped all task queue workers")

    async def _worker_loop(self, worker_id: int) -> None:
        """Worker loop for processing tasks"""
        logger.debug(f"Worker {worker_id} started")

        while self.running:
            try:
                # Get task from queue with timeout
                try:
                    task_id, coroutine, args, kwargs = await asyncio.wait_for(
                        self.queue.get(),
                        timeout=1.0  # Check self.running every second
                    )
                except asyncio.TimeoutError:
                    continue

                # Update task status
                self.task_status[task_id]["status"] = "running"
                self.task_status[task_id]["started_at"] = time.time()

                # Execute the task
                try:
                    result = await coroutine(*args, **kwargs)

                    # Update task status
                    self.task_status[task_id]["status"] = "completed"
                    self.task_status[task_id]["completed_at"] = time.time()
                    self.task_status[task_id]["result"] = result
                    self.tasks_processed += 1

                    logger.debug(f"Task {task_id} completed successfully")
                except Exception as e:
                    # Update task status with error
                    self.task_status[task_id]["status"] = "failed"
                    self.task_status[task_id]["error"] = str(e)
                    self.task_status[task_id]["error_traceback"] = traceback.format_exc()
                    self.task_status[task_id]["completed_at"] = time.time()
                    self.tasks_failed += 1

                    logger.error(f"Task {task_id} failed: {e}")

                # Mark task as done
                self.queue.task_done()
            except asyncio.CancelledError:
                logger.debug(f"Worker {worker_id} cancelled")
                break
            except Exception as e:
                logger.error(f"Error in worker {worker_id}: {e}")

    async def enqueue(
        self,
        coroutine: Callable[..., Coroutine],
        *args,
        **kwargs
    ) -> str:
        """
        Enqueue a task for background processing

        Args:
            coroutine: Coroutine function to execute
            *args: Arguments for the coroutine
            **kwargs: Keyword arguments for the coroutine

        Returns:
            Task ID for status tracking
        """
        # Generate task ID
        task_id = str(uuid.uuid4())

        # Store task status
        self.task_status[task_id] = {
            "id": task_id,
            "status": "queued",
            "queued_at": time.time(),
            "function": coroutine.__name__
        }

        # Put task in queue
        await self.queue.put((task_id, coroutine, args, kwargs))

        logger.debug(f"Enqueued task {task_id} ({coroutine.__name__})")
        return task_id

    def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a task

        Args:
            task_id: Task ID

        Returns:
            Task status or None if not found
        """
        return self.task_status.get(task_id)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get task queue statistics

        Returns:
            Statistics dict
        """
        return {
            "queue_size": self.queue.qsize(),
            "active_workers": len(self.workers),
            "tasks_processed": self.tasks_processed,
            "tasks_failed": self.tasks_failed,
            "running": self.running
        }

    def clear_completed_tasks(self, max_age_seconds: int = 3600) -> int:
        """
        Clear completed tasks from status tracking

        Args:
            max_age_seconds: Maximum age of completed tasks to keep

        Returns:
            Number of tasks cleared
        """
        now = time.time()
        to_remove = []

        for task_id, status in self.task_status.items():
            if status["status"] in ("completed", "failed"):
                completed_at = status.get("completed_at", 0)
                if now - completed_at > max_age_seconds:
                    to_remove.append(task_id)

        for task_id in to_remove:
            del self.task_status[task_id]

        return len(to_remove)

# Global task queue instance
task_queue = TaskQueue()

# Start task queue in application startup
async def start_task_queue():
    await task_queue.start()

# Stop task queue in application shutdown
async def stop_task_queue():
    await task_queue.stop()

# Decorator for easily enqueueing async functions
def enqueue_task(func):
    """Decorator to enqueue a function as a background task"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        return await task_queue.enqueue(func, *args, **kwargs)

    return wrapper
```

### Background Task Management

Optimize background task execution and management:

```python
from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException
import asyncio
import logging
import time
import uuid
from typing import Dict, Any, List, Set, Optional
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class OptimizedBackgroundTasks:
    """Optimized background tasks manager with tracking and limits"""

    def __init__(self, max_concurrent: int = 50):
        """
        Initialize background tasks manager

        Args:
            max_concurrent: Maximum number of concurrent tasks
        """
        self.tasks: Dict[str, asyncio.Task] = {}
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.task_metadata: Dict[str, Dict[str, Any]] = {}

    async def add_task(
        self,
        func,
        *args,
        task_name: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Add a task to be run in the background

        Args:
            func: Coroutine function to execute
            *args: Arguments for the function
            task_name: Optional task name for identification
            **kwargs: Keyword arguments for the function

        Returns:
            Task ID for tracking
        """
        # Generate task ID
        task_id = str(uuid.uuid4())

        # Generate task name if not provided
        if task_name is None:
            task_name = func.__name__

        # Create metadata
        self.task_metadata[task_id] = {
            "id": task_id,
            "name": task_name,
            "created_at": time.time(),
            "status": "pending"
        }

        # Create task wrapper that uses the semaphore
        wrapper_task = asyncio.create_task(
            self._run_task_with_semaphore(task_id, func, *args, **kwargs)
        )

        # Store task
        self.tasks[task_id] = wrapper_task

        # Setup callback to remove task when done
        wrapper_task.add_done_callback(
            lambda t: self._task_done_callback(task_id, t)
        )

        return task_id

    async def _run_task_with_semaphore(self, task_id: str, func, *args, **kwargs):
        """Run a task with semaphore for concurrency control"""
        self.task_metadata[task_id]["status"] = "waiting"

        # Limit concurrent executions
        async with self.semaphore:
            self.task_metadata[task_id]["status"] = "running"
            self.task_metadata[task_id]["started_at"] = time.time()

            try:
                # Run the actual task
                result = await func(*args, **kwargs)

                # Update metadata
                self.task_metadata[task_id]["status"] = "completed"
                self.task_metadata[task_id]["completed_at"] = time.time()
                self.task_metadata[task_id]["result"] = result

                return result
            except Exception as e:
                # Update metadata with error information
                self.task_metadata[task_id]["status"] = "failed"
                self.task_metadata[task_id]["error"] = str(e)
                self.task_metadata[task_id]["completed_at"] = time.time()

                # Log the error
                logger.error(f"Background task {task_id} failed: {e}")

                # Re-raise the exception
                raise

    def _task_done_callback(self, task_id: str, task: asyncio.Task):
        """Callback when a task is done (called in the event loop)"""
        # Remove task from tasks dict
        if task_id in self.tasks:
            del self.tasks[task_id]

        # Keep metadata for a while for status reporting
        # These will be cleaned up periodically by clean_old_tasks

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a task

        Args:
            task_id: Task ID to check

        Returns:
            Task metadata dict or None if not found
        """
        return self.task_metadata.get(task_id)

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """
        Get all task metadata

        Returns:
            List of task metadata dicts
        """
        return list(self.task_metadata.values())

    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """
        Get active task metadata

        Returns:
            List of active task metadata dicts
        """
        return [
            metadata for metadata in self.task_metadata.values()
            if metadata["status"] in ("pending", "waiting", "running")
        ]

    def clean_old_tasks(self, max_age_seconds: int = 3600) -> int:
        """
        Clean up metadata for old completed/failed tasks

        Args:
            max_age_seconds: Maximum age in seconds for completed tasks

        Returns:
            Number of tasks cleaned up
        """
        now = time.time()
        to_remove = []

        for task_id, metadata in self.task_metadata.items():
            if metadata["status"] in ("completed", "failed"):
                completed_at = metadata.get("completed_at", 0)
                if now - completed_at > max_age_seconds:
                    to_remove.append(task_id)

        for task_id in to_remove:
            del self.task_metadata[task_id]

        return len(to_remove)

    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task

        Args:
            task_id: Task ID to cancel

        Returns:
            True if task was cancelled, False if not found or already done
        """
        if task_id in self.tasks:
            task = self.tasks[task_id]
            if not task.done():
                task.cancel()
                self.task_metadata[task_id]["status"] = "cancelled"
                return True

        return False

    async def cancel_all_tasks(self) -> int:
        """
        Cancel all running tasks

        Returns:
            Number of tasks cancelled
        """
        count = 0

        for task_id in list(self.tasks.keys()):
            if self.cancel_task(task_id):
                count += 1

        return count

# Global background tasks manager
optimized_bg_tasks = OptimizedBackgroundTasks()

# FastAPI dependency
def get_background_tasks() -> OptimizedBackgroundTasks:
    """Dependency for FastAPI that provides the background tasks manager"""
    return optimized_bg_tasks

# Task monitoring endpoint
@app.get("/admin/tasks")
async def get_all_tasks(
    background_tasks: OptimizedBackgroundTasks = Depends(get_background_tasks)
):
    """Get all tasks and their status"""
    return {
        "active_tasks": background_tasks.get_active_tasks(),
        "all_tasks": background_tasks.get_all_tasks()
    }

# Task cancellation endpoint
@app.delete("/admin/tasks/{task_id}")
async def cancel_task(
    task_id: str,
    background_tasks: OptimizedBackgroundTasks = Depends(get_background_tasks)
):
    """Cancel a specific task"""
    success = background_tasks.cancel_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found or already completed")

    return {"status": "cancelled", "task_id": task_id}

# Task cleanup in application lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Clean up old tasks periodically
    cleanup_task = None

    async def clean_tasks_periodically():
        while True:
            try:
                count = optimized_bg_tasks.clean_old_tasks()
                if count > 0:
                    logger.info(f"Cleaned up {count} old tasks")
            except Exception as e:
                logger.error(f"Error cleaning up tasks: {e}")

            await asyncio.sleep(300)  # Run every 5 minutes

    # Start background cleaning
    cleanup_task = asyncio.create_task(clean_tasks_periodically())

    yield

    # Cancel cleanup task
    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass

    # Cancel all background tasks on shutdown
    await optimized_bg_tasks.cancel_all_tasks()
```

### Prioritized Task Execution

Implement prioritized task execution for important operations:

```python
import asyncio
from typing import Dict, Any, Optional, Callable, Coroutine
import logging
import time
import uuid
import functools

logger = logging.getLogger(__name__)

class PriorityTaskQueue:
    """Task queue with priority levels"""

    def __init__(self, max_workers: Dict[str, int] = None):
        """
        Initialize priority task queue

        Args:
            max_workers: Dict mapping priority levels to max workers
        """
        # Default priority levels: high, normal, low
        self.max_workers = max_workers or {
            "high": 5,  # 5 workers for high priority tasks
            "normal": 3,  # 3 workers for normal priority tasks
            "low": 2  # 2 workers for low priority tasks
        }

        # Create a queue for each priority level
        self.queues = {
            priority: asyncio.Queue()
            for priority in self.max_workers.keys()
        }

        # Workers for each priority level
        self.workers = {
            priority: []
            for priority in self.max_workers.keys()
        }

        # Task status tracking
        self.task_status = {}

        # Running flag
        self.running = False

    async def start(self) -> None:
        """Start workers for all priority levels"""
        if self.running:
            return

        self.running = True

        # Start workers for each priority level
        for priority, max_count in self.max_workers.items():
            for i in range(max_count):
                worker = asyncio.create_task(
                    self._worker_loop(priority, i)
                )
                self.workers[priority].append(worker)

            logger.info(f"Started {max_count} workers for {priority} priority tasks")

    async def stop(self) -> None:
        """Stop all workers"""
        if not self.running:
            return

        self.running = False

        # Cancel all workers
        for priority, workers in self.workers.items():
            for worker in workers:
                worker.cancel()

            if workers:
                await asyncio.gather(*workers, return_exceptions=True)

            self.workers[priority] = []

        logger.info("Stopped all task queue workers")

    async def _worker_loop(self, priority: str, worker_id: int) -> None:
        """Worker loop for a specific priority level"""
        logger.debug(f"{priority} priority worker {worker_id} started")

        queue = self.queues[priority]

        while self.running:
            try:
                # Get task from queue with timeout
                try:
                    task_id, coroutine, args, kwargs = await asyncio.wait_for(
                        queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                # Update task status
                self.task_status[task_id]["status"] = "running"
                self.task_status[task_id]["started_at"] = time.time()

                # Execute task
                try:
                    result = await coroutine(*args, **kwargs)

                    # Update task status
                    self.task_status[task_id]["status"] = "completed"
                    self.task_status[task_id]["completed_at"] = time.time()
                    self.task_status[task_id]["result"] = result

                    logger.debug(f"{priority} priority task {task_id} completed successfully")
                except Exception as e:
                    # Update task status with error
                    self.task_status[task_id]["status"] = "failed"
                    self.task_status[task_id]["error"] = str(e)
                    self.task_status[task_id]["completed_at"] = time.time()

                    logger.error(f"{priority} priority task {task_id} failed: {e}")

                # Mark task as done
                queue.task_done()
            except asyncio.CancelledError:
                logger.debug(f"{priority} priority worker {worker_id} cancelled")
                break
            except Exception as e:
                logger.error(f"Error in {priority} priority worker {worker_id}: {e}")

    async def enqueue(
        self,
        coroutine: Callable[..., Coroutine],
        *args,
        priority: str = "normal",
        **kwargs
    ) -> str:
        """
        Enqueue a task with specified priority

        Args:
            coroutine: Coroutine function to execute
            *args: Arguments for the coroutine
            priority: Priority level ("high", "normal", "low")
            **kwargs: Keyword arguments for the coroutine

        Returns:
            Task ID for status tracking
        """
        # Validate priority
        if priority not in self.queues:
            raise ValueError(f"Invalid priority: {priority}. Valid values: {list(self.queues.keys())}")

        # Generate task ID
        task_id = str(uuid.uuid4())

        # Store task status
        self.task_status[task_id] = {
            "id": task_id,
            "status": "queued",
            "queued_at": time.time(),
            "function": coroutine.__name__,
            "priority": priority
        }

        # Put task in appropriate queue
        await self.queues[priority].put((task_id, coroutine, args, kwargs))

        logger.debug(f"Enqueued {priority} priority task {task_id} ({coroutine.__name__})")
        return task_id

    def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task"""
        return self.task_status.get(task_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics for all priority levels"""
        stats = {
            "running": self.running,
            "priorities": {}
        }

        for priority, queue in self.queues.items():
            stats["priorities"][priority] = {
                "queue_size": queue.qsize(),
                "active_workers": len(self.workers[priority])
            }

        return stats

# Global priority task queue
priority_task_queue = PriorityTaskQueue()

# Start task queue in application startup
async def start_priority_tasks():
    await priority_task_queue.start()

# Stop task queue in application shutdown
async def stop_priority_tasks():
    await priority_task_queue.stop()

# Decorator for easily enqueueing prioritized tasks
def priority_task(priority: str = "normal"):
    """Decorator to enqueue a function as a prioritized background task"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await priority_task_queue.enqueue(func, *args, priority=priority, **kwargs)

        return wrapper

    return decorator

# Example usage
@priority_task(priority="high")
async def process_important_data(data_id: str) -> Dict[str, Any]:
    """Process important data with high priority"""
    # ... implementation ...
    return {"status": "processed", "data_id": data_id}

@priority_task(priority="low")
async def cleanup_old_data() -> None:
    """Clean up old data with low priority"""
    # ... implementation ...
```

## Network Communication Optimization

### MCP Client Optimization

Optimize the MCP client for efficient network communication:

```python
import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Set
import mcp  # Assuming the MCP client library
import json

logger = logging.getLogger(__name__)

class OptimizedMcpClient:
    """Optimized MCP client with connection pooling and caching"""

    def __init__(
        self,
        endpoint: str,
        service_name: str,
        pool_size: int = 5,
        connect_timeout: float = 10.0,
        request_timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize optimized MCP client

        Args:
            endpoint: MCP server endpoint URL
            service_name: Name of the service
            pool_size: Size of the connection pool
            connect_timeout: Connection timeout in seconds
            request_timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
            retry_delay: Delay between retries in seconds
        """
        self.endpoint = endpoint
        self.service_name = service_name
        self.pool_size = pool_size
        self.connect_timeout = connect_timeout
        self.request_timeout = request_timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Connection pool
        self.pool: List[mcp.ClientSession] = []
        self.pool_semaphore = asyncio.Semaphore(pool_size)
        self.pool_lock = asyncio.Lock()

        # Connection status tracking
        self.connection_errors = 0
        self.last_connection_error = None
        self.healthy = True

        # Statistics
        self.requests_total = 0
        self.requests_success = 0
        self.requests_error = 0
        self.retry_count = 0

        # Request caching
        self.request_cache = {}
        self.cache_hits = 0
        self.cache_misses = 0

    async def initialize(self) -> None:
        """Initialize the connection pool"""
        async with self.pool_lock:
            # Create initial connections
            for _ in range(self.pool_size):
                try:
                    session = await self._create_session()
                    self.pool.append(session)
                except Exception as e:
                    logger.error(f"Failed to create initial connection to {self.service_name}: {e}")
                    self.connection_errors += 1
                    self.last_connection_error = str(e)

            # Log connection status
            if self.pool:
                logger.info(f"Initialized connection pool with {len(self.pool)} connections to {self.service_name}")
                self.healthy = True
            else:
                logger.error(f"Failed to initialize any connections to {self.service_name}")
                self.healthy = False

    async def _create_session(self) -> mcp.ClientSession:
        """Create a new MCP client session"""
        try:
            # Create reader and writer with timeout
            connect_task = mcp.sse_client(self.endpoint)
            reader, writer = await asyncio.wait_for(connect_task, timeout=self.connect_timeout)

            # Create session
            session = mcp.ClientSession(reader, writer)

            # Initialize session
            await asyncio.wait_for(session.initialize(), timeout=self.connect_timeout)

            return session
        except Exception as e:
            logger.error(f"Error creating MCP session to {self.service_name}: {e}")
            raise

    async def _get_session(self) -> mcp.ClientSession:
        """Get a session from the pool with semaphore control"""
        await self.pool_semaphore.acquire()

        try:
            async with self.pool_lock:
                # Check if pool has available connections
                if not self.pool:
                    # Try to create a new connection
                    session = await self._create_session()
                    return session

                # Get a connection from the pool
                return self.pool.pop()
        except Exception as e:
            # Release semaphore on error
            self.pool_semaphore.release()
            raise

    async def _release_session(self, session: mcp.ClientSession, error: bool = False) -> None:
        """
        Release a session back to the pool

        Args:
            session: The session to release
            error: Whether an error occurred with this session
        """
        try:
            if error or not session.connected:
                # Close bad connection
                await session.close()

                # Create new connection if pool is not at capacity
                async with self.pool_lock:
                    if len(self.pool) < self.pool_size:
                        try:
                            new_session = await self._create_session()
                            self.pool.append(new_session)
                        except Exception as e:
                            logger.error(f"Failed to replace bad connection: {e}")
            else:
                # Return good connection to pool
                async with self.pool_lock:
                    self.pool.append(session)
        finally:
            # Always release the semaphore
            self.pool_semaphore.release()

    async def call_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
        cacheable: bool = False,
        cache_ttl: int = 300
    ) -> Dict[str, Any]:
        """
        Call a tool on the MCP server

        Args:
            name: Tool name
            arguments: Tool arguments
            cacheable: Whether the result can be cached
            cache_ttl: Cache TTL in seconds

        Returns:
            Tool result
        """
        start_time = time.time()
        self.requests_total += 1

        # Check cache for cacheable requests
        if cacheable:
            cache_key = f"{name}:{json.dumps(arguments, sort_keys=True)}"
            cached_result = self.request_cache.get(cache_key)

            if cached_result and cached_result["expires"] > time.time():
                self.cache_hits += 1
                return cached_result["result"]

            self.cache_misses += 1

        # Track retries
        retry_count = 0
        last_error = None

        # Retry loop
        while retry_count <= self.max_retries:
            session = None

            try:
                # Get session from pool
                session = await self._get_session()

                # Set timeout for the request
                result = await asyncio.wait_for(
                    session.call_tool(name=name, arguments=arguments),
                    timeout=self.request_timeout
                )

                # Update statistics
                self.requests_success += 1

                # Release session
                await self._release_session(session)

                # Cache result if cacheable
                if cacheable:
                    self.request_cache[cache_key] = {
                        "result": result,
                        "expires": time.time() + cache_ttl
                    }

                # Clean cache periodically (simple approach)
                if self.requests_total % 100 == 0:
                    self._clean_cache()

                # Log timing for slow requests
                request_time = time.time() - start_time
                if request_time > 1.0:
                    logger.warning(f"Slow MCP tool call: {name} took {request_time:.2f}s")

                return result
            except Exception as e:
                # Update statistics
                self.requests_error += 1
                last_error = e

                # Release session with error flag
                if session:
                    await self._release_session(session, error=True)

                # Determine if we should retry
                retry_count += 1
                self.retry_count += 1

                if retry_count <= self.max_retries:
                    retry_delay = self.retry_delay * (2 ** (retry_count - 1))  # Exponential backoff
                    logger.warning(f"Retrying MCP tool call {name} after error: {e} (retry {retry_count}/{self.max_retries})")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"MCP tool call {name} failed after {retry_count-1} retries: {e}")
                    raise

        # If we get here, all retries failed
        raise last_error or RuntimeError(f"Failed to call MCP tool {name} after {self.max_retries} retries")

    async def read_resource(
        self,
        uri: str,
        cacheable: bool = True,
        cache_ttl: int = 300
    ) -> Any:
        """
        Read a resource from the MCP server

        Args:
            uri: Resource URI
            cacheable: Whether the result can be cached
            cache_ttl: Cache TTL in seconds

        Returns:
            Resource content
        """
        start_time = time.time()
        self.requests_total += 1

        # Check cache for cacheable requests
        if cacheable:
            cache_key = f"resource:{uri}"
            cached_result = self.request_cache.get(cache_key)

            if cached_result and cached_result["expires"] > time.time():
                self.cache_hits += 1
                return cached_result["result"]

            self.cache_misses += 1

        # Track retries
        retry_count = 0
        last_error = None

        # Retry loop
        while retry_count <= self.max_retries:
            session = None

            try:
                # Get session from pool
                session = await self._get_session()

                # Set timeout for the request
                content, mime_type = await asyncio.wait_for(
                    session.read_resource(uri),
                    timeout=self.request_timeout
                )

                # Update statistics
                self.requests_success += 1

                # Release session
                await self._release_session(session)

                # Cache result if cacheable
                if cacheable:
                    self.request_cache[cache_key] = {
                        "result": (content, mime_type),
                        "expires": time.time() + cache_ttl
                    }

                # Log timing for slow requests
                request_time = time.time() - start_time
                if request_time > 1.0:
                    logger.warning(f"Slow MCP resource read: {uri} took {request_time:.2f}s")

                return content, mime_type
            except Exception as e:
                # Update statistics
                self.requests_error += 1
                last_error = e

                # Release session with error flag
                if session:
                    await self._release_session(session, error=True)

                # Determine if we should retry
                retry_count += 1
                self.retry_count += 1

                if retry_count <= self.max_retries:
                    retry_delay = self.retry_delay * (2 ** (retry_count - 1))  # Exponential backoff
                    logger.warning(f"Retrying MCP resource read {uri} after error: {e} (retry {retry_count}/{self.max_retries})")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"MCP resource read {uri} failed after {retry_count-1} retries: {e}")
                    raise

        # If we get here, all retries failed
        raise last_error or RuntimeError(f"Failed to read MCP resource {uri} after {self.max_retries} retries")

    def _clean_cache(self) -> int:
        """
        Clean expired entries from the cache

        Returns:
            Number of entries removed
        """
        now = time.time()
        to_remove = [
            key for key, value in self.request_cache.items()
            if value["expires"] < now
        ]

        for key in to_remove:
            del self.request_cache[key]

        return len(to_remove)

    async def close(self) -> None:
        """Close all connections in the pool"""
        async with self.pool_lock:
            for session in self.pool:
                await session.close()

            self.pool = []

    def get_stats(self) -> Dict[str, Any]:
        """
        Get client statistics

        Returns:
            Statistics dict
        """
        return {
            "service_name": self.service_name,
            "endpoint": self.endpoint,
            "healthy": self.healthy,
            "active_connections": len(self.pool),
            "max_connections": self.pool_size,
            "requests_total": self.requests_total,
            "requests_success": self.requests_success,
            "requests_error": self.requests_error,
            "retry_count": self.retry_count,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_size": len(self.request_cache)
        }
```

### Domain Expert Client Factory

Create a factory for efficiently managing MCP client connections:

```python
import logging
import os
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class McpClientFactory:
    """Factory for creating and managing MCP clients"""

    def __init__(self):
        """Initialize the MCP client factory"""
        self.clients = {}

    async def get_client(
        self,
        service_name: str,
        endpoint: Optional[str] = None,
        pool_size: Optional[int] = None,
        connect_timeout: Optional[float] = None,
        request_timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        retry_delay: Optional[float] = None
    ) -> OptimizedMcpClient:
        """
        Get or create an MCP client for a service

        Args:
            service_name: Name of the service
            endpoint: Optional endpoint URL (defaults to environment variable)
            pool_size: Optional connection pool size
            connect_timeout: Optional connection timeout
            request_timeout: Optional request timeout
            max_retries: Optional maximum retries
            retry_delay: Optional retry delay

        Returns:
            Optimized MCP client instance
        """
        # Check if client already exists
        if service_name in self.clients:
            return self.clients[service_name]

        # Determine endpoint from environment variable if not provided
        if endpoint is None:
            env_var = f"{service_name.upper().replace('-', '_')}_SERVICE_URL"
            endpoint = os.getenv(env_var)

            if not endpoint:
                raise ValueError(f"No endpoint provided and {env_var} environment variable not set")

        # Create client with provided or default options
        client = OptimizedMcpClient(
            endpoint=endpoint,
            service_name=service_name,
            pool_size=pool_size or int(os.getenv("MCP_POOL_SIZE", "5")),
            connect_timeout=connect_timeout or float(os.getenv("MCP_CONNECT_TIMEOUT", "10.0")),
            request_timeout=request_timeout or float(os.getenv("MCP_REQUEST_TIMEOUT", "30.0")),
            max_retries=max_retries or int(os.getenv("MCP_MAX_RETRIES", "3")),
            retry_delay=retry_delay or float(os.getenv("MCP_RETRY_DELAY", "1.0"))
        )

        # Initialize the client
        await client.initialize()

        # Store the client
        self.clients[service_name] = client

        logger.info(f"Created and initialized MCP client for {service_name}")
        return client

    async def close_all(self) -> None:
        """Close all MCP clients"""
        for service_name, client in self.clients.items():
            try:
                await client.close()
                logger.info(f"Closed MCP client for {service_name}")
            except Exception as e:
                logger.error(f"Error closing MCP client for {service_name}: {e}")

        self.clients = {}

# Global client factory
mcp_client_factory = McpClientFactory()

# Initialize clients in application startup
async def initialize_mcp_clients():
    # Initialize essential services
    await mcp_client_factory.get_client("memory-service")
    await mcp_client_factory.get_client("cognition-service")

# Close clients in application shutdown
async def close_mcp_clients():
    await mcp_client_factory.close_all()
```

### Request Batching

Implement request batching for efficient network communication:

```python
from typing import List, Dict, Any, TypeVar, Generic
import asyncio
import logging
import time
from collections import defaultdict

logger = logging.getLogger(__name__)

T = TypeVar('T')

class BatchProcessor(Generic[T]):
    """
    Generic batch processor for combining multiple requests into batches

    Type T is the result type of each individual request.
    """

    def __init__(
        self,
        batch_size: int = 50,
        max_wait_time: float = 0.1,
        processor_func = None
    ):
        """
        Initialize batch processor

        Args:
            batch_size: Maximum batch size
            max_wait_time: Maximum wait time in seconds before processing a partial batch
            processor_func: Function to process a batch of requests
        """
        self.batch_size = batch_size
        self.max_wait_time = max_wait_time
        self.processor_func = processor_func

        # Request queues by batch type
        self.request_queues = defaultdict(list)

        # Event to trigger processing
        self.processing_events = defaultdict(asyncio.Event)

        # Tasks
        self.processor_tasks = {}

        # Statistics
        self.total_requests = 0
        self.total_batches = 0
        self.batch_sizes = []

    async def submit(self, batch_type: str, request: Any) -> T:
        """
        Submit a request to be processed in a batch

        Args:
            batch_type: Type of batch for grouping similar requests
            request: Request to process

        Returns:
            Result of the request
        """
        # Create a future to hold the result
        future = asyncio.get_running_loop().create_future()

        # Add to the appropriate queue
        async with self._get_queue_lock(batch_type):
            self.request_queues[batch_type].append((request, future))

            # Update statistics
            self.total_requests += 1

            # Start processor task if not already running
            if batch_type not in self.processor_tasks or self.processor_tasks[batch_type].done():
                self.processor_tasks[batch_type] = asyncio.create_task(
                    self._process_batch_loop(batch_type)
                )

            # Set event to trigger processing if batch is full
            if len(self.request_queues[batch_type]) >= self.batch_size:
                self.processing_events[batch_type].set()

        # Wait for the result
        return await future

    def _get_queue_lock(self, batch_type: str):
        """Get or create a lock for a batch type"""
        if not hasattr(self, 'queue_locks'):
            self.queue_locks = defaultdict(asyncio.Lock)

        return self.queue_locks[batch_type]

    async def _process_batch_loop(self, batch_type: str) -> None:
        """Process batches for a specific batch type"""
        while True:
            try:
                # Wait for either batch size threshold or timeout
                try:
                    # Check if we already have a full batch
                    async with self._get_queue_lock(batch_type):
                        has_full_batch = len(self.request_queues[batch_type]) >= self.batch_size

                    if not has_full_batch:
                        # Wait for event with timeout
                        try:
                            await asyncio.wait_for(
                                self.processing_events[batch_type].wait(),
                                timeout=self.max_wait_time
                            )
                        except asyncio.TimeoutError:
                            # Timeout reached, process what we have
                            pass

                    # Clear event
                    self.processing_events[batch_type].clear()
                except asyncio.CancelledError:
                    # Task cancelled, exit loop
                    break

                # Get batch to process
                batch = []
                futures = []

                async with self._get_queue_lock(batch_type):
                    # Extract requests up to batch size
                    batch_count = min(len(self.request_queues[batch_type]), self.batch_size)

                    if batch_count == 0:
                        # No requests to process, wait for more
                        continue

                    # Extract batch
                    for _ in range(batch_count):
                        request, future = self.request_queues[batch_type].pop(0)
                        batch.append(request)
                        futures.append(future)

                    # Update statistics
                    self.total_batches += 1
                    self.batch_sizes.append(batch_count)

                # Process batch
                try:
                    start_time = time.time()

                    # Call processor function
                    if self.processor_func:
                        results = await self.processor_func(batch_type, batch)
                    else:
                        # If no processor function, call the _process_batch method
                        results = await self._process_batch(batch_type, batch)

                    duration = time.time() - start_time

                    # Validate results
                    if len(results) != len(futures):
                        raise ValueError(f"Expected {len(futures)} results, got {len(results)}")

                    # Set results to futures
                    for future, result in zip(futures, results):
                        if not future.done():
                            future.set_result(result)

                    # Log timing for slow batches
                    if duration > 1.0:
                        logger.warning(f"Slow batch processing: {batch_type} batch of {len(batch)} took {duration:.2f}s")
                except Exception as e:
                    logger.error(f"Error processing {batch_type} batch: {e}")

                    # Set exception to all futures
                    for future in futures:
                        if not future.done():
                            future.set_exception(e)
            except asyncio.CancelledError:
                # Task cancelled, exit loop
                break
            except Exception as e:
                logger.error(f"Unexpected error in batch processor for {batch_type}: {e}")

                # Continue processing other batches
                await asyncio.sleep(1.0)

    async def _process_batch(self, batch_type: str, batch: List[Any]) -> List[T]:
        """
        Default batch processor implementation

        This should be overridden by subclasses or provided as processor_func.

        Args:
            batch_type: Type of batch
            batch: List of requests to process

        Returns:
            List of results, one for each request
        """
        raise NotImplementedError("Batch processor function not implemented")

    async def close(self) -> None:
        """Close the batch processor and cancel all tasks"""
        for batch_type, task in self.processor_tasks.items():
            if not task.done():
                task.cancel()

        # Wait for tasks to complete
        for batch_type, task in self.processor_tasks.items():
            try:
                await task
            except asyncio.CancelledError:
                pass

        self.processor_tasks = {}

    def get_stats(self) -> Dict[str, Any]:
        """
        Get batch processor statistics

        Returns:
            Statistics dict
        """
        avg_batch_size = sum(self.batch_sizes) / max(len(self.batch_sizes), 1)

        return {
            "total_requests": self.total_requests,
            "total_batches": self.total_batches,
            "average_batch_size": avg_batch_size,
            "batch_efficiency": avg_batch_size / self.batch_size if self.batch_size > 0 else 0,
            "active_batch_types": list(self.request_queues.keys())
        }

# Example implementation for batching user lookups
class UserLookupBatchProcessor(BatchProcessor[Dict[str, Any]]):
    """Batch processor for user lookups"""

    def __init__(self, user_service_client, batch_size: int = 50, max_wait_time: float = 0.1):
        """
        Initialize user lookup batch processor

        Args:
            user_service_client: Client for user service
            batch_size: Maximum batch size
            max_wait_time: Maximum wait time in seconds
        """
        super().__init__(batch_size, max_wait_time)
        self.user_service_client = user_service_client

    async def _process_batch(self, batch_type: str, batch: List[str]) -> List[Dict[str, Any]]:
        """
        Process a batch of user ID lookups

        Args:
            batch_type: Type of batch (ignored in this implementation)
            batch: List of user IDs to look up

        Returns:
            List of user objects
        """
        # Call batch lookup endpoint
        return await self.user_service_client.get_users_batch(batch)

# Example usage
async def get_user_with_batching(user_id: str) -> Dict[str, Any]:
    """Get user with batching for efficiency"""
    # Get global batch processor instance
    processor = get_user_lookup_processor()

    # Submit request to batch
    return await processor.submit("user_lookup", user_id)

# Singleton instance
_user_lookup_processor = None

def get_user_lookup_processor() -> UserLookupBatchProcessor:
    """Get or create the user lookup batch processor"""
    global _user_lookup_processor

    if _user_lookup_processor is None:
        # Create processor with user service client
        _user_lookup_processor = UserLookupBatchProcessor(
            user_service_client=get_user_service_client(),
            batch_size=int(os.getenv("USER_LOOKUP_BATCH_SIZE", "50")),
            max_wait_time=float(os.getenv("USER_LOOKUP_BATCH_WAIT", "0.1"))
        )

    return _user_lookup_processor
```

## Memory Usage Optimization

### Memory Profiling

Implement memory profiling to identify and resolve memory issues:

```python
import gc
import tracemalloc
import linecache
import os
import logging
from typing import Dict, Any, List, Optional
import time
import asyncio
import functools

logger = logging.getLogger(__name__)

class MemoryProfiler:
    """Memory profiler for tracking and optimizing memory usage"""

    def __init__(self):
        """Initialize memory profiler"""
        self.enabled = os.getenv("ENABLE_MEMORY_PROFILING", "false").lower() == "true"
        self.snapshot_interval = int(os.getenv("MEMORY_SNAPSHOT_INTERVAL", "300"))  # 5 minutes
        self.snapshot_count = int(os.getenv("MEMORY_SNAPSHOT_COUNT", "10"))
        self.high_memory_threshold_mb = int(os.getenv("MEMORY_HIGH_THRESHOLD_MB", "1024"))

        self.snapshots = []
        self.snapshot_task = None

        # Performance statistics
        self.object_counts = {}
        self.last_gc_count = None
        self.memory_growth = []

    def start(self) -> None:
        """Start memory profiling"""
        if not self.enabled:
            logger.info("Memory profiling disabled")
            return

        # Start tracemalloc for memory profiling
        tracemalloc.start()

        # Store initial GC counts
        self.last_gc_count = gc.get_count()

        # Take initial snapshot
        self._take_snapshot()

        logger.info("Memory profiling started")

        # Start background task for periodic snapshots
        self.snapshot_task = asyncio.create_task(self._snapshot_loop())

    async def stop(self) -> None:
        """Stop memory profiling"""
        if not self.enabled or self.snapshot_task is None:
            return

        # Cancel snapshot task
        self.snapshot_task.cancel()
        try:
            await self.snapshot_task
        except asyncio.CancelledError:
            pass

        # Take final snapshot
        self._take_snapshot()

        # Stop tracemalloc
        tracemalloc.stop()

        logger.info("Memory profiling stopped")

    def _take_snapshot(self) -> None:
        """Take a memory snapshot"""
        snapshot = tracemalloc.take_snapshot()

        # Store only a limited number of snapshots
        self.snapshots.append(snapshot)
        if len(self.snapshots) > self.snapshot_count:
            self.snapshots.pop(0)

        # Save memory statistics
        memory_info = self._get_memory_info()
        self.memory_growth.append({
            "timestamp": time.time(),
            "memory_mb": memory_info["process_memory_mb"]
        })

        # Check for high memory usage
        if memory_info["process_memory_mb"] > self.high_memory_threshold_mb:
            logger.warning(f"High memory usage detected: {memory_info['process_memory_mb']} MB")
            self._log_top_memory_stats(snapshot)

        # Get object counts
        self.object_counts = self._get_object_counts()

        # Check for garbage collection
        gc_count = gc.get_count()
        if gc_count != self.last_gc_count:
            logger.info(f"Garbage collection ran: {self.last_gc_count} -> {gc_count}")
            self.last_gc_count = gc_count

    async def _snapshot_loop(self) -> None:
        """Background task for taking periodic snapshots"""
        while True:
            try:
                await asyncio.sleep(self.snapshot_interval)
                self._take_snapshot()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in memory snapshot loop: {e}")

    def _get_memory_info(self) -> Dict[str, Any]:
        """Get current memory information"""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()

        return {
            "process_memory_mb": memory_info.rss / (1024 * 1024),
            "virtual_memory_mb": memory_info.vms / (1024 * 1024),
            "percent_memory": process.memory_percent(),
            "page_faults": memory_info.pfaults if hasattr(memory_info, "pfaults") else 0
        }

    def _get_object_counts(self) -> Dict[str, int]:
        """Get counts of Python objects by type"""
        counts = {}
        for obj in gc.get_objects():
            obj_type = type(obj).__name__
            counts[obj_type] = counts.get(obj_type, 0) + 1

        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True)[:20])

    def _log_top_memory_stats(self, snapshot) -> None:
        """Log top memory statistics"""
        top_stats = snapshot.statistics('lineno')

        logger.warning("Top 10 memory consumers:")
        for index, stat in enumerate(top_stats[:10], 1):
            frame = stat.traceback[0]
            filename = os.path.basename(frame.filename)
            line = linecache.getline(frame.filename, frame.lineno).strip()
            logger.warning(
                f"#{index}: {filename}:{frame.lineno}: {stat.size / 1024:.1f} KB\n"
                f"    {line}"
            )

    def compare_snapshots(self) -> None:
        """Compare current snapshot with previous to find memory leaks"""
        if len(self.snapshots) < 2:
            logger.warning("Not enough snapshots for comparison")
            return

        # Compare the latest two snapshots
        current = self.snapshots[-1]
        previous = self.snapshots[-2]

        # Find differences
        top_stats = current.compare_to(previous, 'lineno')

        logger.info("Top memory changes since last snapshot:")
        for index, stat in enumerate(top_stats[:10], 1):
            frame = stat.traceback[0]
            filename = os.path.basename(frame.filename)
            line = linecache.getline(frame.filename, frame.lineno).strip()
            logger.info(
                f"#{index}: {filename}:{frame.lineno}: {stat.size_diff / 1024:.1f} KB\n"
                f"    {line}"
            )

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get current memory statistics for monitoring"""
        memory_info = self._get_memory_info()

        return {
            "memory_mb": memory_info["process_memory_mb"],
            "virtual_memory_mb": memory_info["virtual_memory_mb"],
            "object_counts": dict(sorted(self.object_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
            "gc_stats": {
                "counts": gc.get_count(),
                "thresholds": gc.get_threshold(),
                "objects": len(gc.get_objects())
            },
            "memory_growth": self.memory_growth[-10:] if self.memory_growth else []
        }

# Global profiler instance
memory_profiler = MemoryProfiler()

# Start memory profiling in application startup
def start_memory_profiling():
    memory_profiler.start()

# Stop memory profiling in application shutdown
async def stop_memory_profiling():
    await memory_profiler.stop()

# Memory profiling endpoint
def add_memory_profiling_endpoints(app):
    @app.get("/admin/memory", tags=["admin"])
    async def get_memory_stats():
        """Get current memory statistics"""
        if not memory_profiler.enabled:
            return {"status": "disabled"}

        return memory_profiler.get_memory_stats()

    @app.post("/admin/memory/snapshot", tags=["admin"])
    async def take_memory_snapshot():
        """Force taking a memory snapshot"""
        if not memory_profiler.enabled:
            return {"status": "disabled"}

        memory_profiler._take_snapshot()
        return {"status": "snapshot taken"}

    @app.get("/admin/memory/compare", tags=["admin"])
    async def compare_memory_snapshots():
        """Compare memory snapshots to find leaks"""
        if not memory_profiler.enabled:
            return {"status": "disabled"}

        memory_profiler.compare_snapshots()
        return {"status": "comparison logged"}

# Memory profile decorator
def memory_profile(func):
    """Decorator to profile memory usage of a function"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if not memory_profiler.enabled:
            return await func(*args, **kwargs)

        # Take snapshot before
        snapshot_before = tracemalloc.take_snapshot()

        # Run function
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
        finally:
            # Take snapshot after
            execution_time = time.time() - start_time
            snapshot_after = tracemalloc.take_snapshot()

            # Compare snapshots
            top_stats = snapshot_after.compare_to(snapshot_before, 'lineno')

            # Log results
            logger.info(f"Memory profile for {func.__name__}:")
            logger.info(f"Execution time: {execution_time:.2f} seconds")

            for index, stat in enumerate(top_stats[:5], 1):
                frame = stat.traceback[0]
                filename = os.path.basename(frame.filename)
                line = linecache.getline(frame.filename, frame.lineno).strip()
                logger.info(
                    f"#{index}: {filename}:{frame.lineno}: {stat.size_diff / 1024:.1f} KB\n"
                    f"    {line}"
                )

        return result

    return wrapper
```

### Memory-Efficient Data Structures

Implement memory-efficient data structures for improved performance:

```python
from typing import List, Dict, Any, Optional, TypeVar, Generic, Iterator
import sys
import weakref
import logging
import json

logger = logging.getLogger(__name__)

T = TypeVar('T')

class WeakCache(Generic[T]):
    """
    Cache implementation using weak references to prevent memory leaks

    Items are automatically removed when no other references exist.
    """

    def __init__(self):
        """Initialize weak cache"""
        self.data = weakref.WeakValueDictionary()

    def get(self, key: str) -> Optional[T]:
        """Get an item from the cache"""
        return self.data.get(key)

    def set(self, key: str, value: T) -> None:
        """Set an item in the cache"""
        self.data[key] = value

    def delete(self, key: str) -> None:
        """Delete an item from the cache"""
        if key in self.data:
            del self.data[key]

    def clear(self) -> None:
        """Clear the cache"""
        self.data.clear()

    def __len__(self) -> int:
        """Get the number of items in the cache"""
        return len(self.data)

class LRUCache(Generic[T]):
    """
    Memory-efficient LRU (Least Recently Used) cache

    Maintains a maximum size and evicts least recently used items.
    """

    def __init__(self, max_size: int = 1000):
        """
        Initialize LRU cache

        Args:
            max_size: Maximum number of items to store
        """
        self.max_size = max_size
        self.data: Dict[str, T] = {}
        self.usage_order: List[str] = []

    def get(self, key: str) -> Optional[T]:
        """
        Get an item from the cache

        Updates usage order to mark item as recently used.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if key in self.data:
            # Move key to end of usage order (most recently used)
            self.usage_order.remove(key)
            self.usage_order.append(key)
            return self.data[key]

        return None

    def set(self, key: str, value: T) -> None:
        """
        Set an item in the cache

        Evicts least recently used item if cache is full.

        Args:
            key: Cache key
            value: Value to cache
        """
        # Check if key already exists
        if key in self.data:
            # Update existing item
            self.data[key] = value
            # Move to end of usage order
            self.usage_order.remove(key)
            self.usage_order.append(key)
            return

        # Check if cache is full
        if len(self.data) >= self.max_size:
            # Evict least recently used item (first in usage order)
            lru_key = self.usage_order.pop(0)
            del self.data[lru_key]

        # Add new item
        self.data[key] = value
        self.usage_order.append(key)

    def delete(self, key: str) -> None:
        """Delete an item from the cache"""
        if key in self.data:
            del self.data[key]
            self.usage_order.remove(key)

    def clear(self) -> None:
        """Clear the cache"""
        self.data.clear()
        self.usage_order.clear()

    def __len__(self) -> int:
        """Get the number of items in the cache"""
        return len(self.data)

class LazyLoader(Generic[T]):
    """
    Lazy loader for expensive objects

    Only loads the object when needed, reducing memory usage.
    """

    def __init__(self, loader_func):
        """
        Initialize lazy loader

        Args:
            loader_func: Function to load the object
        """
        self.loader_func = loader_func
        self.object = None
        self.loaded = False

    def get(self) -> T:
        """
        Get the object, loading it if necessary

        Returns:
            The loaded object
        """
        if not self.loaded:
            self.object = self.loader_func()
            self.loaded = True

        return self.object

    def reset(self) -> None:
        """Reset the loader, forcing reload on next get"""
        self.object = None
        self.loaded = False

class MemoryEfficientList(Generic[T]):
    """
    Memory-efficient list implementation with chunking

    Reduces memory overhead for large lists by using chunks.
    """

    CHUNK_SIZE = 1000

    def __init__(self, items: Optional[List[T]] = None):
        """
        Initialize memory-efficient list

        Args:
            items: Optional initial items
        """
        self.chunks: List[List[T]] = []
        self.length = 0

        if items:
            self.extend(items)

    def append(self, item: T) -> None:
        """Append an item to the list"""
        # Get current chunk or create new one
        if self.length % self.CHUNK_SIZE == 0:
            self.chunks.append([])

        current_chunk = self.chunks[-1]
        current_chunk.append(item)
        self.length += 1

    def extend(self, items: List[T]) -> None:
        """Extend the list with items"""
        for item in items:
            self.append(item)

    def __getitem__(self, index) -> T:
        """Get item at index"""
        if isinstance(index, slice):
            # Handle slicing
            start, stop, step = index.indices(self.length)
            return [self[i] for i in range(start, stop, step)]

        if index < 0:
            # Convert negative index
            index += self.length

        if index < 0 or index >= self.length:
            raise IndexError("Index out of range")

        # Calculate chunk and index within chunk
        chunk_index = index // self.CHUNK_SIZE
        item_index = index % self.CHUNK_SIZE

        return self.chunks[chunk_index][item_index]

    def __setitem__(self, index, value: T) -> None:
        """Set item at index"""
        if index < 0:
            # Convert negative index
            index += self.length

        if index < 0 or index >= self.length:
            raise IndexError("Index out of range")

        # Calculate chunk and index within chunk
        chunk_index = index // self.CHUNK_SIZE
        item_index = index % self.CHUNK_SIZE

        self.chunks[chunk_index][item_index] = value

    def __len__(self) -> int:
        """Get length of the list"""
        return self.length

    def __iter__(self) -> Iterator[T]:
        """Iterate over items"""
        for chunk in self.chunks:
            for item in chunk:
                yield item

class CompressedJsonCache:
    """
    Cache that stores JSON data in compressed format

    Reduces memory usage for large JSON structures.
    """

    def __init__(self, compression_threshold: int = 1024):
        """
        Initialize compressed JSON cache

        Args:
            compression_threshold: Minimum size in bytes for compression
        """
        self.data = {}
        self.compression_threshold = compression_threshold
        self.compression_savings = 0
        self.total_size = 0
        self.compressed_count = 0
        self.uncompressed_count = 0

    def _should_compress(self, value_str: str) -> bool:
        """Determine if a value should be compressed"""
        return len(value_str) >= self.compression_threshold

    def _compress(self, value_str: str) -> bytes:
        """Compress a string value"""
        import zlib
        return zlib.compress(value_str.encode('utf-8'))

    def _decompress(self, compressed_value: bytes) -> str:
        """Decompress a compressed value"""
        import zlib
        return zlib.decompress(compressed_value).decode('utf-8')

    def set(self, key: str, value: Any) -> None:
        """
        Set a value in the cache

        Compresses the value if it exceeds the threshold.

        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
        """
        # Convert to JSON string
        value_str = json.dumps(value)
        original_size = len(value_str)
        self.total_size += original_size

        # Check if compression is beneficial
        if self._should_compress(value_str):
            compressed_value = self._compress(value_str)
            compressed_size = len(compressed_value)

            # Only use compression if it saves space
            if compressed_size < original_size:
                self.data[key] = ('compressed', compressed_value)
                self.compression_savings += (original_size - compressed_size)
                self.compressed_count += 1
                return

        # Store uncompressed
        self.data[key] = ('raw', value_str)
        self.uncompressed_count += 1

    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache

        Decompresses the value if it was compressed.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if key not in self.data:
            return None

        value_type, value = self.data[key]

        # Handle compressed values
        if value_type == 'compressed':
            value_str = self._decompress(value)
        else:
            value_str = value

        # Convert from JSON string back to object
        return json.loads(value_str)

    def delete(self, key: str) -> None:
        """Delete a value from the cache"""
        if key in self.data:
            del self.data[key]

    def clear(self) -> None:
        """Clear the cache"""
        self.data.clear()
        self.compression_savings = 0
        self.total_size = 0
        self.compressed_count = 0
        self.uncompressed_count = 0

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Statistics dict
        """
        return {
            "items": len(self.data),
            "compressed_items": self.compressed_count,
            "uncompressed_items": self.uncompressed_count,
            "total_size_bytes": self.total_size,
            "compression_savings_bytes": self.compression_savings,
            "compression_ratio": (self.total_size / (self.total_size - self.compression_savings)) if self.compression_savings > 0 else 1.0
        }
```

### Object Pooling

Implement object pooling to reduce memory churn:

```python
from typing import TypeVar, Generic, Callable, List, Any, Optional
import logging
import threading
import asyncio
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

T = TypeVar('T')

class ObjectPool(Generic[T]):
    """
    Generic object pool to reduce allocation overhead

    Reuses expensive objects instead of creating new ones.
    """

    def __init__(
        self,
        factory: Callable[[], T],
        max_size: int = 10,
        reset_func: Optional[Callable[[T], None]] = None
    ):
        """
        Initialize object pool

        Args:
            factory: Function to create new objects
            max_size: Maximum pool size
            reset_func: Optional function to reset objects before reuse
        """
        self.factory = factory
        self.max_size = max_size
        self.reset_func = reset_func

        self.pool: List[T] = []
        self.lock = threading.Lock()

        # Statistics
        self.created_count = 0
        self.reused_count = 0
        self.max_used = 0

    def get(self) -> T:
        """
        Get an object from the pool

        Returns a new object if pool is empty.

        Returns:
            Pooled object
        """
        with self.lock:
            if self.pool:
                # Get object from pool
                obj = self.pool.pop()
                self.reused_count += 1
            else:
                # Create new object
                obj = self.factory()
                self.created_count += 1

            # Track statistics
            currently_used = self.created_count - len(self.pool)
            if currently_used > self.max_used:
                self.max_used = currently_used

        # Reset object if needed
        if self.reset_func and obj:
            self.reset_func(obj)

        return obj

    def put(self, obj: T) -> None:
        """
        Return an object to the pool

        Discards the object if pool is full.

        Args:
            obj: Object to return to pool
        """
        with self.lock:
            if len(self.pool) < self.max_size:
                self.pool.append(obj)

    def clear(self) -> None:
        """Clear the pool"""
        with self.lock:
            self.pool.clear()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get pool statistics

        Returns:
            Statistics dict
        """
        with self.lock:
            return {
                "pool_size": len(self.pool),
                "max_size": self.max_size,
                "created_count": self.created_count,
                "reused_count": self.reused_count,
                "max_used": self.max_used,
                "current_usage": self.created_count - len(self.pool)
            }

class AsyncObjectPool(Generic[T]):
    """
    Asynchronous object pool for async resources

    Reuses expensive async objects instead of creating new ones.
    """

    def __init__(
        self,
        factory: Callable[[], Any],
        max_size: int = 10,
        reset_func: Optional[Callable[[T], Any]] = None
    ):
        """
        Initialize async object pool

        Args:
            factory: Async function to create new objects
            max_size: Maximum pool size
            reset_func: Optional async function to reset objects before reuse
        """
        self.factory = factory
        self.max_size = max_size
        self.reset_func = reset_func

        self.pool: List[T] = []
        self.semaphore = asyncio.Semaphore(max_size)
        self.lock = asyncio.Lock()

        # Statistics
        self.created_count = 0
        self.reused_count = 0
        self.max_used = 0

    async def get(self) -> T:
        """
        Get an object from the pool

        Returns a new object if pool is empty.

        Returns:
            Pooled object
        """
        async with self.lock:
            if self.pool:
                # Get object from pool
                obj = self.pool.pop()
                self.reused_count += 1
            else:
                # Create new object
                obj = await self.factory()
                self.created_count += 1

            # Track statistics
            currently_used = self.created_count - len(self.pool)
            if currently_used > self.max_used:
                self.max_used = currently_used

        # Reset object if needed
        if self.reset_func and obj:
            await self.reset_func(obj)

        return obj

    async def put(self, obj: T) -> None:
        """
        Return an object to the pool

        Discards the object if pool is full.

        Args:
            obj: Object to return to pool
        """
        async with self.lock:
            if len(self.pool) < self.max_size:
                self.pool.append(obj)

    @asynccontextmanager
    async def acquire(self):
        """
        Context manager for acquiring and releasing objects

        Usage:
            async with pool.acquire() as obj:
                # Use obj
                ...
        """
        obj = await self.get()
        try:
            yield obj
        finally:
            await self.put(obj)

    async def clear(self) -> None:
        """Clear the pool"""
        async with self.lock:
            self.pool.clear()

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get pool statistics

        Returns:
            Statistics dict
        """
        async with self.lock:
            return {
                "pool_size": len(self.pool),
                "max_size": self.max_size,
                "created_count": self.created_count,
                "reused_count": self.reused_count,
                "max_used": self.max_used,
                "current_usage": self.created_count - len(self.pool)
            }

# Example usage for a connection pool
async def create_db_connection():
    """Create a database connection"""
    return await asyncpg.connect(os.getenv("DATABASE_URL"))

async def reset_db_connection(conn):
    """Reset a database connection"""
    await conn.execute("ROLLBACK")

# Create connection pool
db_pool = AsyncObjectPool(create_db_connection, max_size=20, reset_func=reset_db_connection)

# Usage with context manager
async def execute_query(query, *args):
    """Execute a query using a pooled connection"""
    async with db_pool.acquire() as conn:
        return await conn.fetch(query, *args)
```

## Load Testing and Benchmarking

### Load Testing Framework

Implement a comprehensive load testing framework:

```python
import asyncio
import aiohttp
import time
import statistics
import logging
import json
import csv
import os
import uuid
from typing import Dict, Any, List, Optional, Callable, Coroutine
import concurrent.futures
import argparse
import sys
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class RequestResult:
    """Results of a single request"""
    request_id: str
    endpoint: str
    status_code: int
    duration_ms: float
    success: bool
    error: Optional[str] = None
    response_size: Optional[int] = None
    timestamp: float = field(default_factory=time.time)

@dataclass
class LoadTestResult:
    """Results of a load test"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    min_duration_ms: float
    max_duration_ms: float
    avg_duration_ms: float
    median_duration_ms: float
    p95_duration_ms: float
    p99_duration_ms: float
    total_duration_seconds: float
    requests_per_second: float
    start_time: float
    end_time: float
    results: List[RequestResult]

class LoadTester:
    """Load testing framework for API performance testing"""

    def __init__(
        self,
        base_url: str,
        auth_token: Optional[str] = None,
        num_users: int = 10,
        requests_per_user: int = 100,
        ramp_up_seconds: int = 5,
        timeout: int = 30,
        results_file: Optional[str] = None
    ):
        """
        Initialize load tester

        Args:
            base_url: Base URL of the API
            auth_token: Optional authentication token
            num_users: Number of simulated users
            requests_per_user: Number of requests per user
            ramp_up_seconds: Seconds to ramp up to full load
            timeout: Request timeout in seconds
            results_file: Optional file to save results
        """
        self.base_url = base_url
        self.auth_token = auth_token
        self.num_users = num_users
        self.requests_per_user = requests_per_user
        self.ramp_up_seconds = ramp_up_seconds
        self.timeout = timeout
        self.results_file = results_file

        # Results
        self.results: List[RequestResult] = []

        # Test scenarios
        self.scenarios: Dict[str, Dict[str, Any]] = {}

    def add_scenario(
        self,
        name: str,
        endpoint: str,
        method: str = "GET",
        payload: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        weight: int = 1
    ) -> None:
        """
        Add a test scenario

        Args:
            name: Scenario name
            endpoint: API endpoint to test
            method: HTTP method
            payload: Optional request payload
            headers: Optional additional headers
            weight: Relative weight of this scenario
        """
        self.scenarios[name] = {
            "endpoint": endpoint,
            "method": method,
            "payload": payload or {},
            "headers": headers or {},
            "weight": weight
        }

    async def _make_request(
        self,
        session: aiohttp.ClientSession,
        scenario: Dict[str, Any]
    ) -> RequestResult:
        """
        Make a single request

        Args:
            session: HTTP session
            scenario: Test scenario

        Returns:
            Request result
        """
        request_id = str(uuid.uuid4())
        endpoint = scenario["endpoint"]
        method = scenario["method"]
        payload = scenario["payload"]
        headers = {**scenario["headers"]}

        # Add authorization if token is provided
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        start_time = time.time()

        try:
            async with session.request(
                method=method,
                url=url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            ) as response:
                # Read response to measure complete request time
                response_data = await response.read()

                end_time = time.time()
                duration_ms = (end_time - start_time) * 1000

                return RequestResult(
                    request_id=request_id,
                    endpoint=endpoint,
                    status_code=response.status,
                    duration_ms=duration_ms,
                    success=response.status < 400,
                    response_size=len(response_data),
                    timestamp=start_time
                )
        except Exception as e:
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000

            return RequestResult(
                request_id=request_id,
                endpoint=endpoint,
                status_code=0,
                duration_ms=duration_ms,
                success=False,
                error=str(e),
                timestamp=start_time
            )

    async def _user_task(self, user_id: int) -> List[RequestResult]:
        """
        Task for a single simulated user

        Args:
            user_id: User ID

        Returns:
            List of request results
        """
        # Calculate delay based on ramp-up period
        if self.ramp_up_seconds > 0 and self.num_users > 1:
            delay = (user_id / (self.num_users - 1)) * self.ramp_up_seconds
            await asyncio.sleep(delay)

        # Create HTTP session
        async with aiohttp.ClientSession() as session:
            results = []

            # Make requests
            for i in range(self.requests_per_user):
                # Select scenario based on weights
                scenarios = list(self.scenarios.values())
                weights = [s["weight"] for s in scenarios]
                total_weight = sum(weights)

                # Normalize weights
                weights = [w / total_weight for w in weights]

                # Random selection
                import random
                r = random.random()
                cumulative_weight = 0
                selected_scenario = scenarios[0]

                for scenario, weight in zip(scenarios, weights):
                    cumulative_weight += weight
                    if r <= cumulative_weight:
                        selected_scenario = scenario
                        break

                # Make request
                result = await self._make_request(session, selected_scenario)
                results.append(result)

                # Small delay between requests
                await asyncio.sleep(0.1)

            return results

    async def run(self) -> LoadTestResult:
        """
        Run the load test

        Returns:
            Load test results
        """
        if not self.scenarios:
            raise ValueError("No scenarios defined. Add at least one scenario with add_scenario().")

        logger.info(f"Starting load test with {self.num_users} users, {self.requests_per_user} requests per user")

        # Record start time
        start_time = time.time()

        # Create tasks for each user
        tasks = []
        for user_id in range(self.num_users):
            task = asyncio.create_task(self._user_task(user_id))
            tasks.append(task)

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks)

        # Flatten results
        self.results = [result for user_results in results for result in user_results]

        # Record end time
        end_time = time.time()

        # Calculate statistics
        durations = [r.duration_ms for r in self.results]
        successful_requests = sum(1 for r in self.results if r.success)
        failed_requests = len(self.results) - successful_requests

        # Handle empty results
        if not durations:
            return LoadTestResult(
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                min_duration_ms=0,
                max_duration_ms=0,
                avg_duration_ms=0,
                median_duration_ms=0,
                p95_duration_ms=0,
                p99_duration_ms=0,
                total_duration_seconds=end_time - start_time,
                requests_per_second=0,
                start_time=start_time,
                end_time=end_time,
                results=[]
            )

        # Calculate percentiles
        durations.sort()
        p95_index = int(len(durations) * 0.95)
        p99_index = int(len(durations) * 0.99)

        # Create result
        test_result = LoadTestResult(
            total_requests=len(self.results),
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            min_duration_ms=min(durations),
            max_duration_ms=max(durations),
            avg_duration_ms=statistics.mean(durations),
            median_duration_ms=statistics.median(durations),
            p95_duration_ms=durations[p95_index],
            p99_duration_ms=durations[p99_index],
            total_duration_seconds=end_time - start_time,
            requests_per_second=len(self.results) / (end_time - start_time),
            start_time=start_time,
            end_time=end_time,
            results=self.results
        )

        # Save results if filename is provided
        if self.results_file:
            self._save_results(test_result)

        return test_result

    def _save_results(self, result: LoadTestResult) -> None:
        """
        Save test results to a file

        Args:
            result: Load test results
        """
        # Create results directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(self.results_file)), exist_ok=True)

        # Determine file format
        file_extension = os.path.splitext(self.results_file)[1].lower()

        if file_extension == '.json':
            # Save as JSON
            with open(self.results_file, 'w') as f:
                json.dump({
                    "summary": {
                        "total_requests": result.total_requests,
                        "successful_requests": result.successful_requests,
                        "failed_requests": result.failed_requests,
                        "min_duration_ms": result.min_duration_ms,
                        "max_duration_ms": result.max_duration_ms,
                        "avg_duration_ms": result.avg_duration_ms,
                        "median_duration_ms": result.median_duration_ms,
                        "p95_duration_ms": result.p95_duration_ms,
                        "p99_duration_ms": result.p99_duration_ms,
                        "total_duration_seconds": result.total_duration_seconds,
                        "requests_per_second": result.requests_per_second,
                        "start_time": result.start_time,
                        "end_time": result.end_time
                    },
                    "results": [
                        {
                            "request_id": r.request_id,
                            "endpoint": r.endpoint,
                            "status_code": r.status_code,
                            "duration_ms": r.duration_ms,
                            "success": r.success,
                            "error": r.error,
                            "response_size": r.response_size,
                            "timestamp": r.timestamp
                        }
                        for r in result.results
                    ]
                }, f, indent=2)
        elif file_extension == '.csv':
            # Save as CSV
            with open(self.results_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "request_id", "endpoint", "status_code", "duration_ms",
                    "success", "error", "response_size", "timestamp"
                ])

                for r in result.results:
                    writer.writerow([
                        r.request_id, r.endpoint, r.status_code, r.duration_ms,
                        r.success, r.error or "", r.response_size or 0, r.timestamp
                    ])
        else:
            # Default to text summary
            with open(self.results_file, 'w') as f:
                f.write(f"Load Test Results\n")
                f.write(f"================\n\n")
                f.write(f"Total Requests: {result.total_requests}\n")
                f.write(f"Successful Requests: {result.successful_requests}\n")
                f.write(f"Failed Requests: {result.failed_requests}\n")
                f.write(f"Min Duration: {result.min_duration_ms:.2f} ms\n")
                f.write(f"Max Duration: {result.max_duration_ms:.2f} ms\n")
                f.write(f"Average Duration: {result.avg_duration_ms:.2f} ms\n")
                f.write(f"Median Duration: {result.median_duration_ms:.2f} ms\n")
                f.write(f"95th Percentile: {result.p95_duration_ms:.2f} ms\n")
                f.write(f"99th Percentile: {result.p99_duration_ms:.2f} ms\n")
                f.write(f"Total Duration: {result.total_duration_seconds:.2f} seconds\n")
                f.write(f"Requests Per Second: {result.requests_per_second:.2f}\n")

        logger.info(f"Results saved to {self.results_file}")

    def print_results(self, result: LoadTestResult) -> None:
        """
        Print test results to console

        Args:
            result: Load test results
        """
        print("\nLoad Test Results")
        print("================\n")
        print(f"Total Requests: {result.total_requests}")
        print(f"Successful Requests: {result.successful_requests}")
        print(f"Failed Requests: {result.failed_requests}")
        print(f"Success Rate: {(result.successful_requests / result.total_requests * 100):.2f}%")
        print(f"\nLatency (ms):")
        print(f"  Min: {result.min_duration_ms:.2f}")
        print(f"  Max: {result.max_duration_ms:.2f}")
        print(f"  Avg: {result.avg_duration_ms:.2f}")
        print(f"  Median: {result.median_duration_ms:.2f}")
        print(f"  95th Percentile: {result.p95_duration_ms:.2f}")
        print(f"  99th Percentile: {result.p99_duration_ms:.2f}")
        print(f"\nThroughput:")
        print(f"  Total Duration: {result.total_duration_seconds:.2f} seconds")
        print(f"  Requests Per Second: {result.requests_per_second:.2f}")

        if result.failed_requests > 0:
            print("\nError Summary:")
            error_counts = {}
            for r in result.results:
                if not r.success:
                    key = f"{r.endpoint} - {r.status_code or 'Network Error'}"
                    error_counts[key] = error_counts.get(key, 0) + 1

            for error, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"  {error}: {count} requests")
```

### Benchmark Utilities

Create utilities for benchmarking specific components:

```python
import time
import logging
import asyncio
import functools
import statistics
from typing import Dict, Any, List, Callable, Coroutine, TypeVar, Optional
from dataclasses import dataclass
import textwrap

logger = logging.getLogger(__name__)

T = TypeVar('T')

@dataclass
class BenchmarkResult:
    """Results of a benchmark run"""
    name: str
    iteration_count: int
    total_time_seconds: float
    min_time_seconds: float
    max_time_seconds: float
    avg_time_seconds: float
    median_time_seconds: float
    per_second: float
    execution_times: List[float]

async def benchmark(
    func: Callable[..., Coroutine[Any, Any, T]],
    *args,
    name: Optional[str] = None,
    iterations: int = 100,
    warmup_iterations: int = 5,
    **kwargs
) -> BenchmarkResult:
    """
    Benchmark an async function

    Args:
        func: Async function to benchmark
        *args: Function arguments
        name: Optional benchmark name
        iterations: Number of iterations
        warmup_iterations: Number of warmup iterations
        **kwargs: Function keyword arguments

    Returns:
        Benchmark results
    """
    # Use function name if name not provided
    if name is None:
        name = func.__name__

    logger.info(f"Starting benchmark: {name}")

    # Warmup
    logger.debug(f"Performing {warmup_iterations} warmup iterations")
    for _ in range(warmup_iterations):
        await func(*args, **kwargs)

    # Run benchmark
    times = []
    total_start = time.time()

    for i in range(iterations):
        start = time.time()
        await func(*args, **kwargs)
        end = time.time()
        times.append(end - start)

    total_end = time.time()
    total_time = total_end - total_start

    # Calculate statistics
    results = BenchmarkResult(
        name=name,
        iteration_count=iterations,
        total_time_seconds=total_time,
        min_time_seconds=min(times),
        max_time_seconds=max(times),
        avg_time_seconds=statistics.mean(times),
        median_time_seconds=statistics.median(times),
        per_second=iterations / total_time,
        execution_times=times
    )

    return results

def print_benchmark_results(result: BenchmarkResult) -> None:
    """
    Print benchmark results to console

    Args:
        result: Benchmark results
    """
    print(f"\nBenchmark Results: {result.name}")
    print("=" * (18 + len(result.name)))
    print(f"Iterations: {result.iteration_count}")
    print(f"Total Time: {result.total_time_seconds:.4f} seconds")
    print(f"\nLatency (seconds):")
    print(f"  Min: {result.min_time_seconds:.6f}")
    print(f"  Max: {result.max_time_seconds:.6f}")
    print(f"  Avg: {result.avg_time_seconds:.6f}")
    print(f"  Median: {result.median_time_seconds:.6f}")
    print(f"\nThroughput:")
    print(f"  Operations Per Second: {result.per_second:.2f}")

async def compare_benchmarks(
    funcs: List[Dict[str, Any]],
    iterations: int = 100,
    warmup_iterations: int = 5
) -> None:
    """
    Compare multiple benchmarks

    Args:
        funcs: List of function configs with keys:
            - 'func': The function to benchmark
            - 'name': Optional name for the benchmark
            - 'args': Optional args for the function
            - 'kwargs': Optional kwargs for the function
        iterations: Number of iterations
        warmup_iterations: Number of warmup iterations
    """
    results = []

    for func_config in funcs:
        func = func_config["func"]
        name = func_config.get("name", func.__name__)
        args = func_config.get("args", [])
        kwargs = func_config.get("kwargs", {})

        result = await benchmark(
            func,
            *args,
            name=name,
            iterations=iterations,
            warmup_iterations=warmup_iterations,
            **kwargs
        )

        results.append(result)
        print_benchmark_results(result)

    # Compare results
    print("\nBenchmark Comparison")
    print("===================")

    # Find the fastest result
    fastest = min(results, key=lambda r: r.median_time_seconds)

    # Create a table
    print(f"{'Name':<30} {'Median (s)':<12} {'Ops/Sec':<12} {'Relative':<12}")
    print(f"{'-'*30} {'-'*12} {'-'*12} {'-'*12}")

    for result in sorted(results, key=lambda r: r.median_time_seconds):
        relative = result.median_time_seconds / fastest.median_time_seconds
        print(f"{textwrap.shorten(result.name, width=30):<30} {result.median_time_seconds:<12.6f} {result.per_second:<12.2f} {relative:<12.2f}x")

# Decorator for benchmarking a function
def benchmark_decorator(iterations=100, warmup_iterations=5):
    """
    Decorator for benchmarking a function

    Usage:
        @benchmark_decorator(iterations=100)
        async def my_function():
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            result = await benchmark(
                func,
                *args,
                iterations=iterations,
                warmup_iterations=warmup_iterations,
                **kwargs
            )
            print_benchmark_results(result)
            return await func(*args, **kwargs)

        return wrapper

    return decorator
```

### Performance Baselines

Establish performance baselines for key operations:

```python
import asyncio
import logging
import json
import os
from typing import Dict, Any, List, Optional
import datetime

logger = logging.getLogger(__name__)

class PerformanceBaseline:
    """Performance baseline tracking for key operations"""

    def __init__(self, baseline_file: Optional[str] = None):
        """
        Initialize performance baseline

        Args:
            baseline_file: Optional file to load/save baselines
        """
        self.baseline_file = baseline_file or os.getenv(
            "PERFORMANCE_BASELINE_FILE",
            "performance_baselines.json"
        )
        self.baselines: Dict[str, Dict[str, Any]] = {}
        self.load_baselines()

    def load_baselines(self) -> None:
        """Load baselines from file"""
        if os.path.exists(self.baseline_file):
            try:
                with open(self.baseline_file, 'r') as f:
                    self.baselines = json.load(f)
                    logger.info(f"Loaded {len(self.baselines)} performance baselines")
            except Exception as e:
                logger.error(f"Error loading performance baselines: {e}")
                self.baselines = {}

    def save_baselines(self) -> None:
        """Save baselines to file"""
        try:
            with open(self.baseline_file, 'w') as f:
                json.dump(self.baselines, f, indent=2)
                logger.info(f"Saved {len(self.baselines)} performance baselines")
        except Exception as e:
            logger.error(f"Error saving performance baselines: {e}")

    def get_baseline(self, operation: str) -> Optional[Dict[str, Any]]:
        """
        Get baseline for an operation

        Args:
            operation: Operation name

        Returns:
            Baseline dict or None if not found
        """
        return self.baselines.get(operation)

    def set_baseline(
        self,
        operation: str,
        median_time_seconds: float,
        p95_time_seconds: float,
        operations_per_second: float
    ) -> None:
        """
        Set baseline for an operation

        Args:
            operation: Operation name
            median_time_seconds: Median execution time
            p95_time_seconds: 95th percentile execution time
            operations_per_second: Operations per second
        """
        self.baselines[operation] = {
            "median_time_seconds": median_time_seconds,
            "p95_time_seconds": p95_time_seconds,
            "operations_per_second": operations_per_second,
            "last_updated": datetime.datetime.now().isoformat()
        }
        self.save_baselines()

    def check_performance(
        self,
        operation: str,
        current_median_seconds: float,
        current_p95_seconds: float,
        current_ops_per_second: float
    ) -> Dict[str, Any]:
        """
        Check current performance against baseline

        Args:
            operation: Operation name
            current_median_seconds: Current median execution time
            current_p95_seconds: Current 95th percentile execution time
            current_ops_per_second: Current operations per second

        Returns:
            Comparison dict
        """
        baseline = self.get_baseline(operation)

        if not baseline:
            return {
                "has_baseline": False,
                "message": f"No baseline exists for operation: {operation}"
            }

        # Calculate deltas
        median_delta_pct = (current_median_seconds - baseline["median_time_seconds"]) / baseline["median_time_seconds"] * 100
        p95_delta_pct = (current_p95_seconds - baseline["p95_time_seconds"]) / baseline["p95_time_seconds"] * 100
        ops_delta_pct = (current_ops_per_second - baseline["operations_per_second"]) / baseline["operations_per_second"] * 100

        # Define thresholds for warning
        median_threshold = 10  # 10% worse
        p95_threshold = 15     # 15% worse
        ops_threshold = -10    # 10% fewer ops/sec

        # Check for regressions
        has_regression = (
            median_delta_pct > median_threshold or
            p95_delta_pct > p95_threshold or
            ops_delta_pct < ops_threshold
        )

        return {
            "has_baseline": True,
            "has_regression": has_regression,
            "baseline": baseline,
            "current": {
                "median_time_seconds": current_median_seconds,
                "p95_time_seconds": current_p95_seconds,
                "operations_per_second": current_ops_per_second
            },
            "deltas": {
                "median_percent": median_delta_pct,
                "p95_percent": p95_delta_pct,
                "operations_per_second_percent": ops_delta_pct
            },
            "message": (
                f"Performance regression detected for {operation}. "
                f"Median: {median_delta_pct:.1f}% slower, "
                f"P95: {p95_delta_pct:.1f}% slower, "
                f"Throughput: {abs(ops_delta_pct):.1f}% {'lower' if ops_delta_pct < 0 else 'higher'}."
            ) if has_regression else None
        }

# Usage example
async def run_baseline_comparison():
    # Initialize baseline
    baseline = PerformanceBaseline()

    # Example operation to benchmark
    async def get_user_data(user_id: str):
        # Actual implementation would query database or service
        await asyncio.sleep(0.05)  # Simulate work
        return {"user_id": user_id, "name": "Test User"}

    # Run benchmark
    result = await benchmark(
        get_user_data,
        "user123",
        name="get_user_data",
        iterations=100
    )

    # Calculate P95
    execution_times = sorted(result.execution_times)
    p95_index = int(len(execution_times) * 0.95)
    p95_time = execution_times[p95_index]

    # Check against baseline
    comparison = baseline.check_performance(
        "get_user_data",
        result.median_time_seconds,
        p95_time,
        result.per_second
    )

    if not comparison["has_baseline"]:
        # No baseline exists, set one
        baseline.set_baseline(
            "get_user_data",
            result.median_time_seconds,
            p95_time,
            result.per_second
        )
        print(f"Established new baseline for get_user_data")
    elif comparison["has_regression"]:
        # Performance regression detected
        print(comparison["message"])
        print("Baseline:", comparison["baseline"])
        print("Current:", comparison["current"])
    else:
        print(f"Performance is within acceptable range compared to baseline")
```

## Performance Monitoring

### Performance Metrics Collection

Implement metrics collection for monitoring performance:

```python
import time
import threading
import logging
import asyncio
import json
import os
from typing import Dict, Any, List, Optional, Callable
import functools
import datetime

logger = logging.getLogger(__name__)

class PerformanceMetrics:
    """Performance metrics collection and reporting"""

    def __init__(self, enable_metrics: bool = True):
        """
        Initialize performance metrics

        Args:
            enable_metrics: Whether to enable metrics collection
        """
        self.enable_metrics = enable_metrics
        self.metrics = {}
        self.metrics_lock = threading.Lock()

        # Track metrics by operation
        self.operation_metrics = {}

        # Track metrics by endpoint
        self.endpoint_metrics = {}

        # Track metrics by category
        self.category_metrics = {}

        # Recent samples for percentile calculation
        self.recent_samples = {}
        self.max_samples = 1000

        # Reset interval in seconds
        self.reset_interval = int(os.getenv("METRICS_RESET_INTERVAL", "3600"))  # 1 hour
        self.last_reset = time.time()

    def track_operation(
        self,
        operation: str,
        duration_seconds: float,
        success: bool = True,
        category: Optional[str] = None
    ) -> None:
        """
        Track a single operation

        Args:
            operation: Operation name
            duration_seconds: Execution time in seconds
            success: Whether the operation succeeded
            category: Optional category for grouping
        """
        if not self.enable_metrics:
            return

        # Check if metrics should be reset
        now = time.time()
        if now - self.last_reset > self.reset_interval:
            self.reset_metrics()
            self.last_reset = now

        with self.metrics_lock:
            # Initialize operation metrics if not exists
            if operation not in self.operation_metrics:
                self.operation_metrics[operation] = {
                    "count": 0,
                    "total_time": 0,
                    "min_time": float('inf'),
                    "max_time": 0,
                    "success_count": 0,
                    "error_count": 0,
                    "last_execution_time": None,
                    "last_status": None
                }

            # Update operation metrics
            metrics = self.operation_metrics[operation]
            metrics["count"] += 1
            metrics["total_time"] += duration_seconds
            metrics["min_time"] = min(metrics["min_time"], duration_seconds)
            metrics["max_time"] = max(metrics["max_time"], duration_seconds)

            if success:
                metrics["success_count"] += 1
            else:
                metrics["error_count"] += 1

            metrics["last_execution_time"] = duration_seconds
            metrics["last_status"] = "success" if success else "error"

            # Store recent samples for percentile calculation
            if operation not in self.recent_samples:
                self.recent_samples[operation] = []

            self.recent_samples[operation].append(duration_seconds)

            # Limit recent samples
            if len(self.recent_samples[operation]) > self.max_samples:
                self.recent_samples[operation].pop(0)

            # Update category metrics if provided
            if category:
                if category not in self.category_metrics:
                    self.category_metrics[category] = {
                        "count": 0,
                        "total_time": 0,
                        "success_count": 0,
                        "error_count": 0
                    }

                category_metrics = self.category_metrics[category]
                category_metrics["count"] += 1
                category_metrics["total_time"] += duration_seconds

                if success:
                    category_metrics["success_count"] += 1
                else:
                    category_metrics["error_count"] += 1

    def track_endpoint(
        self,
        endpoint: str,
        duration_seconds: float,
        status_code: int
    ) -> None:
        """
        Track a single endpoint request

        Args:
            endpoint: API endpoint
            duration_seconds: Execution time in seconds
            status_code: HTTP status code
        """
        if not self.enable_metrics:
            return

        with self.metrics_lock:
            # Initialize endpoint metrics if not exists
            if endpoint not in self.endpoint_metrics:
                self.endpoint_metrics[endpoint] = {
                    "count": 0,
                    "total_time": 0,
                    "min_time": float('inf'),
                    "max_time": 0,
                    "status_counts": {}
                }

            # Update endpoint metrics
            metrics = self.endpoint_metrics[endpoint]
            metrics["count"] += 1
            metrics["total_time"] += duration_seconds
            metrics["min_time"] = min(metrics["min_time"], duration_seconds)
            metrics["max_time"] = max(metrics["max_time"], duration_seconds)

            # Track status code
            status_str = str(status_code)
            if status_str not in metrics["status_counts"]:
                metrics["status_counts"][status_str] = 0

            metrics["status_counts"][status_str] += 1

    def get_operation_metrics(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """
        Get metrics for an operation or all operations

        Args:
            operation: Optional operation name

        Returns:
            Metrics dict
        """
        with self.metrics_lock:
            if operation:
                if operation not in self.operation_metrics:
                    return {}

                metrics = self.operation_metrics[operation].copy()

                # Calculate average time
                if metrics["count"] > 0:
                    metrics["avg_time"] = metrics["total_time"] / metrics["count"]
                else:
                    metrics["avg_time"] = 0

                # Calculate success rate
                if metrics["count"] > 0:
                    metrics["success_rate"] = metrics["success_count"] / metrics["count"]
                else:
                    metrics["success_rate"] = 0

                # Calculate percentiles if samples exist
                if operation in self.recent_samples and self.recent_samples[operation]:
                    samples = sorted(self.recent_samples[operation])
                    n = len(samples)

                    metrics["median_time"] = samples[n // 2]
                    metrics["p90_time"] = samples[int(n * 0.9)]
                    metrics["p95_time"] = samples[int(n * 0.95)]
                    metrics["p99_time"] = samples[int(n * 0.99)]

                return metrics
            else:
                # Return all operation metrics
                result = {}

                for op, metrics in self.operation_metrics.items():
                    op_metrics = metrics.copy()

                    # Calculate average time
                    if op_metrics["count"] > 0:
                        op_metrics["avg_time"] = op_metrics["total_time"] / op_metrics["count"]
                    else:
                        op_metrics["avg_time"] = 0

                    # Calculate success rate
                    if op_metrics["count"] > 0:
                        op_metrics["success_rate"] = op_metrics["success_count"] / op_metrics["count"]
                    else:
                        op_metrics["success_rate"] = 0

                    # Calculate percentiles if samples exist
                    if op in self.recent_samples and self.recent_samples[op]:
                        samples = sorted(self.recent_samples[op])
                        n = len(samples)

                        op_metrics["median_time"] = samples[n // 2]
                        op_metrics["p90_time"] = samples[int(n * 0.9)]
                        op_metrics["p95_time"] = samples[int(n * 0.95)]
                        op_metrics["p99_time"] = samples[int(n * 0.99)]

                    result[op] = op_metrics

                return result

    def get_endpoint_metrics(self, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """
        Get metrics for an endpoint or all endpoints

        Args:
            endpoint: Optional endpoint name

        Returns:
            Metrics dict
        """
        with self.metrics_lock:
            if endpoint:
                if endpoint not in self.endpoint_metrics:
                    return {}

                metrics = self.endpoint_metrics[endpoint].copy()

                # Calculate average time
                if metrics["count"] > 0:
                    metrics["avg_time"] = metrics["total_time"] / metrics["count"]
                else:
                    metrics["avg_time"] = 0

                return metrics
            else:
                # Return all endpoint metrics
                result = {}

                for ep, metrics in self.endpoint_metrics.items():
                    ep_metrics = metrics.copy()

                    # Calculate average time
                    if ep_metrics["count"] > 0:
                        ep_metrics["avg_time"] = ep_metrics["total_time"] / ep_metrics["count"]
                    else:
                        ep_metrics["avg_time"] = 0

                    result[ep] = ep_metrics

                return result

    def get_category_metrics(self, category: Optional[str] = None) -> Dict[str, Any]:
        """
        Get metrics for a category or all categories

        Args:
            category: Optional category name

        Returns:
            Metrics dict
        """
        with self.metrics_lock:
            if category:
                if category not in self.category_metrics:
                    return {}

                metrics = self.category_metrics[category].copy()

                # Calculate average time
                if metrics["count"] > 0:
                    metrics["avg_time"] = metrics["total_time"] / metrics["count"]
                else:
                    metrics["avg_time"] = 0

                # Calculate success rate
                if metrics["count"] > 0:
                    metrics["success_rate"] = metrics["success_count"] / metrics["count"]
                else:
                    metrics["success_rate"] = 0

                return metrics
            else:
                # Return all category metrics
                result = {}

                for cat, metrics in self.category_metrics.items():
                    cat_metrics = metrics.copy()

                    # Calculate average time
                    if cat_metrics["count"] > 0:
                        cat_metrics["avg_time"] = cat_metrics["total_time"] / cat_metrics["count"]
                    else:
                        cat_metrics["avg_time"] = 0

                    # Calculate success rate
                    if cat_metrics["count"] > 0:
                        cat_metrics["success_rate"] = cat_metrics["success_count"] / cat_metrics["count"]
                    else:
                        cat_metrics["success_rate"] = 0

                    result[cat] = cat_metrics

                return result

    def reset_metrics(self) -> None:
        """Reset all metrics"""
        with self.metrics_lock:
            self.operation_metrics = {}
            self.endpoint_metrics = {}
            self.category_metrics = {}
            self.recent_samples = {}

    def get_all_metrics(self) -> Dict[str, Any]:
        """
        Get all metrics

        Returns:
            All metrics dict
        """
        return {
            "timestamp": datetime.datetime.now().isoformat(),
            "operations": self.get_operation_metrics(),
            "endpoints": self.get_endpoint_metrics(),
            "categories": self.get_category_metrics()
        }

    def export_metrics(self, filename: str) -> None:
        """
        Export metrics to a file

        Args:
            filename: File to export to
        """
        try:
            with open(filename, 'w') as f:
                json.dump(self.get_all_metrics(), f, indent=2)
                logger.info(f"Exported metrics to {filename}")
        except Exception as e:
            logger.error(f"Error exporting metrics: {e}")

# Global metrics instance
performance_metrics = PerformanceMetrics()

# Decorator for tracking operation performance
def track_performance(operation: str = None, category: str = None):
    """
    Decorator to track function performance

    Args:
        operation: Operation name (defaults to function name)
        category: Optional category for grouping
    """
    def decorator(func):
        nonlocal operation

        if operation is None:
            operation = func.__name__

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception:
                success = False
                raise
            finally:
                duration = time.time() - start_time
                performance_metrics.track_operation(operation, duration, success, category)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True

            try:
                result = func(*args, **kwargs)
                return result
            except Exception:
                success = False
                raise
            finally:
                duration = time.time() - start_time
                performance_metrics.track_operation(operation, duration, success, category)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator

# FastAPI middleware for tracking endpoint performance
class PerformanceMiddleware:
    """Middleware for tracking endpoint performance"""

    def __init__(self, app):
        """
        Initialize performance middleware

        Args:
            app: FastAPI application
        """
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        start_time = time.time()
        status_code = None

        # Extract endpoint path
        path = scope["path"]

        # Route regex is not available at this level, so we'll use the path directly
        endpoint = path

        # Capture original send function
        original_send = send

        # Define replacement send function to capture status code
        async def send_wrapper(message):
            nonlocal status_code

            if message["type"] == "http.response.start":
                status_code = message["status"]

            return await original_send(message)

        try:
            # Process request
            await self.app(scope, receive, send_wrapper)
        finally:
            # Calculate duration
            duration = time.time() - start_time

            # Track endpoint metrics if status code was captured
            if status_code is not None:
                performance_metrics.track_endpoint(endpoint, duration, status_code)

# Initialize FastAPI with performance middleware
def init_app_with_performance_monitoring(app):
    """
    Initialize FastAPI app with performance monitoring

    Args:
        app: FastAPI application
    """
    from fastapi import FastAPI

    # Add performance middleware
    from starlette.middleware.base import BaseHTTPMiddleware

    app.add_middleware(
        BaseHTTPMiddleware,
        dispatch=PerformanceMiddleware(app)
    )

    # Add metrics endpoint
    @app.get("/metrics/performance", tags=["monitoring"])
    async def get_performance_metrics():
        """Get performance metrics"""
        return performance_metrics.get_all_metrics()

    @app.post("/metrics/performance/reset", tags=["monitoring"])
    async def reset_performance_metrics():
        """Reset performance metrics"""
        performance_metrics.reset_metrics()
        return {"status": "Metrics reset"}
```

## Tuning Recommendations

### System Configuration

Optimize system settings for better performance:

```python
import os
import subprocess
import sys
import logging
import platform
import multiprocessing
import json
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

def check_system_settings() -> Dict[str, Any]:
    """
    Check system settings for optimal performance

    Returns:
        Dict of settings and recommendations
    """
    settings = {}
    recommendations = []

    # Check operating system
    settings["os"] = platform.system()
    settings["os_version"] = platform.version()

    # Check Python version
    settings["python_version"] = sys.version

    # Check CPU cores
    cpu_count = multiprocessing.cpu_count()
    settings["cpu_cores"] = cpu_count

    # Check available memory
    try:
        import psutil

        memory_info = psutil.virtual_memory()
        settings["total_memory_gb"] = memory_info.total / (1024 ** 3)
        settings["available_memory_gb"] = memory_info.available / (1024 ** 3)

        # Check if system has enough memory
        if settings["total_memory_gb"] < 4:
            recommendations.append({
                "setting": "system_memory",
                "current": f"{settings['total_memory_gb']:.1f} GB",
                "recommended": "At least 4 GB",
                "description": "System memory is below recommended minimum for production use"
            })

        # Check memory pressure
        if memory_info.percent > 80:
            recommendations.append({
                "setting": "memory_usage",
                "current": f"{memory_info.percent}%",
                "recommended": "Below 80%",
                "description": "High memory usage may impact application performance"
            })
    except ImportError:
        settings["memory_info"] = "psutil not available"

    # Check ulimit on Unix-like systems
    if settings["os"] in ("Linux", "Darwin"):
        try:
            # Get open file limit
            proc = subprocess.run(["ulimit", "-n"], capture_output=True, text=True, shell=True)
            if proc.returncode == 0:
                file_limit = proc.stdout.strip()
                settings["open_file_limit"] = file_limit

                # Check if limit is sufficient
                try:
                    limit = int(file_limit)
                    if limit < 1024:
                        recommendations.append({
                            "setting": "open_file_limit",
                            "current": str(limit),
                            "recommended": "At least 1024",
                            "description": "Low open file limit may cause 'Too many open files' errors",
                            "fix": "Add the following to /etc/security/limits.conf:\n"
                                  "*               soft    nofile          65536\n"
                                  "*               hard    nofile          65536"
                        })
                except ValueError:
                    pass
        except Exception:
            settings["open_file_limit"] = "Could not determine"

    # Check environment variables
    env_vars = {
        "DATABASE_URL": "Database connection string",
        "DATABASE_POOL_SIZE": "Database connection pool size",
        "REDIS_URL": "Redis connection string for caching",
        "MEMORY_SERVICE_URL": "Memory Service URL",
        "COGNITION_SERVICE_URL": "Cognition Service URL",
        "LOG_LEVEL": "Logging level"
    }

    settings["environment_variables"] = {}

    for var, description in env_vars.items():
        value = os.getenv(var)
        settings["environment_variables"][var] = {
            "value": "***" if value and ("PASSWORD" in var or "URL" in var) else value,
            "set": value is not None,
            "description": description
        }

        # Check required variables
        if var in ("DATABASE_URL", "MEMORY_SERVICE_URL", "COGNITION_SERVICE_URL") and not value:
            recommendations.append({
                "setting": f"env_var_{var}",
                "current": "Not set",
                "recommended": "Set appropriate value",
                "description": f"Required environment variable {var} is not set"
            })

    # Check database pool size
    db_pool_size = os.getenv("DATABASE_POOL_SIZE")
    if db_pool_size:
        try:
            pool_size = int(db_pool_size)
            max_connections = cpu_count * 5  # Rough estimate

            if pool_size > max_connections:
                recommendations.append({
                    "setting": "database_pool_size",
                    "current": str(pool_size),
                    "recommended": str(max_connections),
                    "description": "Database pool size may be too large for available CPU cores"
                })
            elif pool_size < cpu_count:
                recommendations.append({
                    "setting": "database_pool_size",
                    "current": str(pool_size),
                    "recommended": str(cpu_count),
                    "description": "Database pool size may be too small for optimal performance"
                })
        except ValueError:
            pass

    return {
        "settings": settings,
        "recommendations": recommendations
    }

def apply_performance_settings():
    """Apply optimal performance settings"""
    # Set default connection pool size
    if not os.getenv("DATABASE_POOL_SIZE"):
        cpu_count = multiprocessing.cpu_count()
        os.environ["DATABASE_POOL_SIZE"] = str(cpu_count * 2)

    # Set default MAX_OVERFLOW
    if not os.getenv("DATABASE_MAX_OVERFLOW"):
        cpu_count = multiprocessing.cpu_count()
        os.environ["DATABASE_MAX_OVERFLOW"] = str(cpu_count * 3)

    # Set statement timeout
    if not os.getenv("DATABASE_STATEMENT_TIMEOUT"):
        os.environ["DATABASE_STATEMENT_TIMEOUT"] = "30"  # 30 seconds

    # Set worker threads
    if not os.getenv("WORKER_THREADS"):
        cpu_count = multiprocessing.cpu_count()
        os.environ["WORKER_THREADS"] = str(cpu_count * 2)

    # Set default HTTP keep-alive
    if not os.getenv("HTTP_KEEP_ALIVE"):
        os.environ["HTTP_KEEP_ALIVE"] = "true"

    # Set Redis connection pool size
    if not os.getenv("REDIS_POOL_SIZE"):
        cpu_count = multiprocessing.cpu_count()
        os.environ["REDIS_POOL_SIZE"] = str(cpu_count * 2)

    logger.info("Applied optimal performance settings")

def get_performance_recommendations() -> List[Dict[str, Any]]:
    """
    Get performance tuning recommendations

    Returns:
        List of recommendation dicts
    """
    # Check system settings
    system_check = check_system_settings()
    recommendations = system_check["recommendations"]

    # Add general recommendations
    recommendations.extend([
        {
            "setting": "uvicorn_workers",
            "current": os.getenv("WEB_CONCURRENCY", "1"),
            "recommended": str(multiprocessing.cpu_count() + 1),
            "description": "Number of Uvicorn workers should match CPU cores + 1 for optimal performance"
        },
        {
            "setting": "database_connection_timeout",
            "current": os.getenv("DATABASE_POOL_TIMEOUT", "30"),
            "recommended": "10-30",
            "description": "Database connection timeout should be tuned based on actual connection time"
        },
        {
            "setting": "database_statement_timeout",
            "current": os.getenv("DATABASE_STATEMENT_TIMEOUT", "None"),
            "recommended": "30",
            "description": "Set a statement timeout to prevent long-running queries from blocking the system"
        },
        {
            "setting": "caching_strategy",
            "current": "Unknown",
            "recommended": "Implement Redis caching",
            "description": "Use Redis caching for frequently accessed data to reduce database load"
        },
        {
            "setting": "connection_pooling",
            "current": "Unknown",
            "recommended": "Implement pooling for all external services",
            "description": "Use connection pooling for all external services to reduce connection overhead"
        }
    ])

    return recommendations

def export_performance_recommendations(filename: str = "performance_recommendations.json"):
    """
    Export performance recommendations to a file

    Args:
        filename: File to export to
    """
    recommendations = get_performance_recommendations()

    try:
        with open(filename, 'w') as f:
            json.dump(recommendations, f, indent=2)
            logger.info(f"Exported performance recommendations to {filename}")
    except Exception as e:
        logger.error(f"Error exporting performance recommendations: {e}")
```

### Database Tuning

Database parameter tuning recommendations:

```python
from typing import Dict, Any, List
import logging
import os

logger = logging.getLogger(__name__)

def get_postgres_tuning_recommendations() -> Dict[str, Any]:
    """
    Get PostgreSQL tuning recommendations

    Returns:
        Dict of recommendations
    """
    # Get environment information
    total_memory_mb = 0
    try:
        import psutil
        total_memory_mb = psutil.virtual_memory().total / (1024 * 1024)
    except ImportError:
        total_memory_mb = 4096  # Default to 4GB

    # Calculate recommended PostgreSQL settings
    shared_buffers = int(total_memory_mb * 0.25)  # 25% of RAM
    effective_cache_size = int(total_memory_mb * 0.75)  # 75% of RAM
    maintenance_work_mem = min(1024, int(total_memory_mb * 0.05))  # 5% of RAM, max 1GB
    work_mem = max(4, int((total_memory_mb - shared_buffers) /
                        (int(os.getenv("DATABASE_POOL_SIZE", "10")) * 4)))  # Depend on connections
    random_page_cost = 1.1  # Assume SSD storage

    return {
        "shared_buffers": f"{shared_buffers}MB",
        "effective_cache_size": f"{effective_cache_size}MB",
        "maintenance_work_mem": f"{maintenance_work_mem}MB",
        "work_mem": f"{work_mem}MB",
        "random_page_cost": random_page_cost,
        "effective_io_concurrency": 200,  # Good default for SSD
        "max_worker_processes": os.cpu_count(),
        "max_parallel_workers": os.cpu_count(),
        "max_parallel_workers_per_gather": max(2, os.cpu_count() // 2),
        "wal_buffers": "16MB",
        "checkpoint_completion_target": 0.9,
        "default_statistics_target": 100,
        "explanation": {
            "shared_buffers": "Amount of memory PostgreSQL uses for caching data",
            "effective_cache_size": "Estimate of memory available for disk caching",
            "maintenance_work_mem": "Memory for maintenance operations like VACUUM",
            "work_mem": "Memory for query operations like sorting",
            "random_page_cost": "Cost of a non-sequentially-fetched disk page",
            "effective_io_concurrency": "Number of concurrent disk I/O operations",
            "max_worker_processes": "Maximum number of background worker processes",
            "max_parallel_workers": "Maximum number of parallel workers",
            "max_parallel_workers_per_gather": "Maximum parallel workers per query",
            "wal_buffers": "Memory used for write-ahead logging",
            "checkpoint_completion_target": "Time spent completing checkpoint as fraction of interval",
            "default_statistics_target": "Default target for table statistics"
        }
    }

def generate_postgres_conf() -> str:
    """
    Generate PostgreSQL configuration file

    Returns:
        PostgreSQL configuration as a string
    """
    recommendations = get_postgres_tuning_recommendations()

    # Build configuration
    config = [
        "# PostgreSQL configuration tuned for Cortex Core",
        "# Generated automatically by performance tuning utility",
        "",
        "# Connection Settings",
        f"max_connections = {int(os.getenv('DATABASE_POOL_SIZE', '10')) * 3}",
        "",
        "# Memory Settings",
        f"shared_buffers = {recommendations['shared_buffers']}",
        f"effective_cache_size = {recommendations['effective_cache_size']}",
        f"maintenance_work_mem = {recommendations['maintenance_work_mem']}",
        f"work_mem = {recommendations['work_mem']}",
        f"wal_buffers = {recommendations['wal_buffers']}",
        "",
        "# Planner Settings",
        f"random_page_cost = {recommendations['random_page_cost']}",
        f"effective_io_concurrency = {recommendations['effective_io_concurrency']}",
        f"default_statistics_target = {recommendations['default_statistics_target']}",
        "",
        "# Parallel Query Settings",
        f"max_worker_processes = {recommendations['max_worker_processes']}",
        f"max_parallel_workers = {recommendations['max_parallel_workers']}",
        f"max_parallel_workers_per_gather = {recommendations['max_parallel_workers_per_gather']}",
        f"max_parallel_maintenance_workers = {max(2, recommendations['max_parallel_workers'] // 2)}",
        "",
        "# Checkpoint Settings",
        f"checkpoint_completion_target = {recommendations['checkpoint_completion_target']}",
        "",
        "# Logging Settings",
        "log_min_duration_statement = 1000  # Log queries taking more than 1 second",
        "log_checkpoints = on",
        "log_connections = on",
        "log_disconnections = on",
        "log_lock_waits = on",
        "log_temp_files = 0",
        "",
        "# Autovacuum Settings",
        "autovacuum = on",
        "track_counts = on",
        "",
        "# Statement Timeout",
        f"statement_timeout = {int(os.getenv('DATABASE_STATEMENT_TIMEOUT', '30')) * 1000}  # milliseconds"
    ]

    return "\n".join(config)

def generate_postgres_tuning_sql() -> str:
    """
    Generate SQL for PostgreSQL tuning

    Returns:
        SQL statements for PostgreSQL tuning
    """
    sql = [
        "-- PostgreSQL tuning SQL",
        "-- Run these statements to optimize your database",
        "",
        "-- Set statements to optimize for interactive application",
        "ALTER SYSTEM SET synchronous_commit = 'off';  -- Improves transaction speed",
        "",
        "-- Update statistics for all tables",
        "ANALYZE;",
        "",
        "-- Create necessary indexes (customize based on your schema)",
        "-- Example: CREATE INDEX IF NOT EXISTS idx_conversations_workspace_id ON conversations(workspace_id);",
        "",
        "-- Optimize tables",
        "VACUUM ANALYZE;",
        "",
        "-- Reset statistics to ensure optimal query planning",
        "ALTER SYSTEM RESET all;",
        "SELECT pg_reload_conf();",
        "",
        "-- Check for orphaned temporary tables",
        "SELECT relname, relpages FROM pg_class WHERE relkind = 'r' AND relname LIKE 'pg_temp%';",
        "",
        "-- Check for bloated tables",
        "SELECT schemaname, relname, n_live_tup, n_dead_tup, last_vacuum, last_autovacuum",
        "FROM pg_stat_user_tables",
        "WHERE n_dead_tup > 1000",
        "ORDER BY n_dead_tup DESC;",
        "",
        "-- Check for unused indexes",
        "SELECT s.schemaname, s.relname, s.indexrelname, s.idx_scan, pg_size_pretty(pg_relation_size('"
        "' || s.schemaname || '"".""' || s.indexrelname || '""')) as index_size",
        "FROM pg_stat_user_indexes s",
        "JOIN pg_index i ON s.indexrelid = i.indexrelid",
        "WHERE s.idx_scan = 0 AND NOT i.indisprimary",
        "ORDER BY pg_relation_size(s.indexrelid) DESC;"
    ]

    return "\n".join(sql)
```

## Conclusion

Implementing the performance optimizations outlined in this document will significantly improve the responsiveness, scalability, and reliability of the Cortex Core system. By focusing on targeted optimizations in key areas rather than premature optimization, you can achieve substantial performance gains while maintaining code clarity and maintainability.

The key principles to remember are:

1. **Measure before optimizing**: Use the profiling and benchmarking tools to identify actual bottlenecks rather than guessing.
2. **Focus on high-impact areas**: Database queries, connection management, and caching typically provide the most significant performance improvements.
3. **Optimize for common cases**: Design your system to handle the common case efficiently, even if it means slightly worse performance for edge cases.
4. **Monitor continuously**: Implement comprehensive performance monitoring to catch regressions early.
5. **Test under realistic loads**: Use load testing to verify performance under conditions similar to production.

By following these guidelines and implementing the techniques described in this document, you will create a high-performance, scalable system that meets the production requirements for Phase 5 of the Cortex Core project.
