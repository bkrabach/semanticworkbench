"""
Redis Cache Module

This module provides Redis-based caching functionality with support for
namespaces, serialization, and TTL (time-to-live) for cached items.
"""

import json
import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional, Set, TypeVar, Union, cast

import redis.asyncio as redis
from redis.asyncio.client import Redis
from redis.exceptions import RedisError

from app.config import settings
from app.utils.logger import get_contextual_logger

# Configure logger
logger = get_contextual_logger("cache.redis")

# Type variable for generic cache values
T = TypeVar("T")


class RedisCache:
    """
    Redis Cache

    Provides asynchronous Redis caching with namespacing,
    serialization, and TTL management. Designed to work with
    both standalone Redis and Redis clusters.
    """

    def __init__(self, url: Optional[str] = None, prefix: str = ""):
        """
        Initialize Redis cache

        Args:
            url: Redis connection URL (redis://host:port/db)
            prefix: Global key prefix for all cache keys
        """
        self.url = url or settings.redis_url
        self.prefix = prefix or settings.redis_prefix
        self.default_ttl = settings.redis_default_ttl
        self._redis: Optional[Redis] = None
        self._initialized = False

    async def initialize(self) -> bool:
        """
        Initialize Redis connection

        Returns:
            True if connection successful, False otherwise
        """
        if self._initialized and self._redis:
            logger.debug("Redis already initialized")
            return True

        if not self.url:
            logger.warning("Redis URL not configured, Redis cache disabled")
            return False

        try:
            logger.info(f"Initializing Redis connection to {self.url}")
            self._redis = redis.from_url(
                self.url,
                encoding="utf-8",
                decode_responses=True,
                health_check_interval=30,
            )

            # Test connection
            await self._redis.ping()

            self._initialized = True
            logger.info("Redis connection established")
            return True

        except (RedisError, ConnectionError, ValueError) as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            self._redis = None
            self._initialized = False
            return False

    async def close(self) -> None:
        """Close Redis connection"""
        if self._redis:
            logger.info("Closing Redis connection")
            await self._redis.close()
            self._redis = None
            self._initialized = False

    def _format_key(self, key: str, namespace: Optional[str] = None) -> str:
        """
        Format cache key with prefix and namespace

        Args:
            key: The cache key
            namespace: Optional namespace

        Returns:
            Formatted key string
        """
        if namespace:
            return f"{self.prefix}{namespace}:{key}"
        else:
            return f"{self.prefix}{key}"

    async def _ensure_connection(self) -> bool:
        """
        Ensure Redis connection is active

        Returns:
            True if connection active, False otherwise
        """
        if not self._initialized or not self._redis:
            return await self.initialize()

        return True

    async def get(
        self, key: str, namespace: Optional[str] = None, default: Any = None
    ) -> Any:
        """
        Get value from cache

        Args:
            key: Cache key
            namespace: Optional namespace
            default: Default value if not found

        Returns:
            Cached value or default if not found
        """
        if not await self._ensure_connection() or not self._redis:
            return default

        try:
            formatted_key = self._format_key(key, namespace)
            value = await self._redis.get(formatted_key)

            if value is None:
                return default

            # Try to deserialize JSON
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                # Return as is if not JSON
                return value

        except RedisError as e:
            logger.error(f"Redis error getting key {key}: {str(e)}")
            return default

    async def set(
        self,
        key: str,
        value: Any,
        namespace: Optional[str] = None,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache
            namespace: Optional namespace
            ttl: Time-to-live in seconds

        Returns:
            True if successful, False otherwise
        """
        if not await self._ensure_connection() or not self._redis:
            return False

        try:
            formatted_key = self._format_key(key, namespace)

            # Serialize value if necessary
            if isinstance(value, (dict, list, tuple, set)):
                value = json.dumps(value)

            # Set with TTL
            if ttl is None:
                ttl = self.default_ttl

            await self._redis.set(formatted_key, value, ex=ttl)
            return True

        except RedisError as e:
            logger.error(f"Redis error setting key {key}: {str(e)}")
            return False

    async def delete(self, key: str, namespace: Optional[str] = None) -> bool:
        """
        Delete value from cache

        Args:
            key: Cache key
            namespace: Optional namespace

        Returns:
            True if successful, False otherwise
        """
        if not await self._ensure_connection() or not self._redis:
            return False

        try:
            formatted_key = self._format_key(key, namespace)
            await self._redis.delete(formatted_key)
            return True

        except RedisError as e:
            logger.error(f"Redis error deleting key {key}: {str(e)}")
            return False

    async def exists(self, key: str, namespace: Optional[str] = None) -> bool:
        """
        Check if key exists in cache

        Args:
            key: Cache key
            namespace: Optional namespace

        Returns:
            True if key exists, False otherwise
        """
        if not await self._ensure_connection() or not self._redis:
            return False

        try:
            formatted_key = self._format_key(key, namespace)
            return bool(await self._redis.exists(formatted_key))

        except RedisError as e:
            logger.error(f"Redis error checking key {key}: {str(e)}")
            return False

    async def clear_namespace(self, namespace: str) -> int:
        """
        Clear all keys in a namespace

        Args:
            namespace: Namespace to clear

        Returns:
            Number of keys deleted
        """
        if not await self._ensure_connection() or not self._redis:
            return 0

        try:
            pattern = self._format_key("*", namespace)
            keys = await self._redis.keys(pattern)

            if not keys:
                return 0

            # Delete all keys in namespace
            deleted = await self._redis.delete(*keys)
            logger.info(f"Cleared {deleted} keys from namespace {namespace}")
            return deleted

        except RedisError as e:
            logger.error(f"Redis error clearing namespace {namespace}: {str(e)}")
            return 0

    async def increment(
        self,
        key: str,
        value: int = 1,
        namespace: Optional[str] = None,
        ttl: Optional[int] = None,
    ) -> Optional[int]:
        """
        Increment a counter

        Args:
            key: Cache key
            value: Value to increment by
            namespace: Optional namespace
            ttl: Optional new TTL after increment

        Returns:
            New counter value or None if failed
        """
        if not await self._ensure_connection() or not self._redis:
            return None

        try:
            formatted_key = self._format_key(key, namespace)
            pipe = self._redis.pipeline()

            # Increment and get new value
            new_value = await self._redis.incrby(formatted_key, value)

            # Set TTL if provided
            if ttl is not None:
                await self._redis.expire(formatted_key, ttl)

            return new_value

        except RedisError as e:
            logger.error(f"Redis error incrementing key {key}: {str(e)}")
            return None

    async def get_ttl(self, key: str, namespace: Optional[str] = None) -> Optional[int]:
        """
        Get TTL for key

        Args:
            key: Cache key
            namespace: Optional namespace

        Returns:
            TTL in seconds or None if key doesn't exist
        """
        if not await self._ensure_connection() or not self._redis:
            return None

        try:
            formatted_key = self._format_key(key, namespace)
            ttl = await self._redis.ttl(formatted_key)

            # Redis returns -2 if key doesn't exist, -1 if no TTL
            if ttl == -2:
                return None
            if ttl == -1:
                return 0  # No expiration

            return ttl

        except RedisError as e:
            logger.error(f"Redis error getting TTL for key {key}: {str(e)}")
            return None

    async def set_ttl(
        self, key: str, ttl: int, namespace: Optional[str] = None
    ) -> bool:
        """
        Set TTL for key

        Args:
            key: Cache key
            ttl: TTL in seconds
            namespace: Optional namespace

        Returns:
            True if successful, False otherwise
        """
        if not await self._ensure_connection() or not self._redis:
            return False

        try:
            formatted_key = self._format_key(key, namespace)
            return bool(await self._redis.expire(formatted_key, ttl))

        except RedisError as e:
            logger.error(f"Redis error setting TTL for key {key}: {str(e)}")
            return False

    async def get_many(
        self, keys: List[str], namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get multiple values from cache

        Args:
            keys: List of cache keys
            namespace: Optional namespace

        Returns:
            Dict of key/value pairs for found keys
        """
        if not await self._ensure_connection() or not self._redis:
            return {}

        if not keys:
            return {}

        try:
            # Format all keys
            formatted_keys = [self._format_key(key, namespace) for key in keys]

            # Get all values
            values = await self._redis.mget(formatted_keys)

            # Build result dict
            result = {}
            for i, value in enumerate(values):
                if value is not None:
                    key = keys[i]

                    # Try to deserialize JSON
                    try:
                        result[key] = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        # Return as is if not JSON
                        result[key] = value

            return result

        except RedisError as e:
            logger.error(f"Redis error getting multiple keys: {str(e)}")
            return {}

    async def healthcheck(self) -> bool:
        """
        Perform Redis healthcheck

        Returns:
            True if Redis is healthy, False otherwise
        """
        if not self.url:
            # Redis not configured, so it's "healthy" by being disabled
            return True

        try:
            if not await self._ensure_connection() or not self._redis:
                return False

            # Ping Redis
            await self._redis.ping()
            return True

        except RedisError as e:
            logger.error(f"Redis healthcheck failed: {str(e)}")
            return False


# Create global instance
redis_cache = RedisCache()


# Export public symbols
__all__ = ["RedisCache", "redis_cache"]
