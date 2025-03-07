"""
Redis cache utility for Cortex Core with in-memory fallback
"""

import redis.asyncio as redis
from app.config import settings
from app.utils.logger import logger
import asyncio
import time
from typing import Dict, Any, Optional, Union
import threading

# Redis client instance
redis_client = None
using_memory_fallback = False

# In-memory cache
memory_cache: Dict[str, Dict[str, Any]] = {}


async def connect_redis():
    """Connect to Redis"""
    global redis_client, using_memory_fallback

    try:
        logger.info("Connecting to Redis...")

        # Create Redis client
        redis_client = redis.Redis(
            host=settings.cache.host,
            port=settings.cache.port,
            password=settings.cache.password,
            decode_responses=True,
            retry_on_timeout=True,
        )

        # Test connection
        await redis_client.ping()
        using_memory_fallback = False
        logger.info("Redis connection established")

    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        logger.warning("Using in-memory cache fallback")
        using_memory_fallback = True

    # Start memory cache cleanup in a background thread if using fallback
    if using_memory_fallback:
        start_memory_cache_cleanup()


async def disconnect_redis():
    """Disconnect from Redis"""
    global redis_client

    try:
        if redis_client and not using_memory_fallback:
            logger.info("Disconnecting from Redis...")
            await redis_client.close()
            redis_client = None
            logger.info("Redis connection closed")
    except Exception as e:
        logger.error(f"Failed to disconnect from Redis: {e}")


def start_memory_cache_cleanup():
    """Start memory cache cleanup in a background thread"""

    def cleanup_task():
        while True:
            try:
                # Run cleanup every minute
                time.sleep(60)
                cleanup_count = cleanup_memory_cache()
                if cleanup_count > 0:
                    logger.debug(
                        f"Memory cache cleanup: removed {cleanup_count} expired items"
                    )
            except Exception as e:
                logger.error(f"Error in memory cache cleanup: {e}")

    # Start cleanup thread
    cleanup_thread = threading.Thread(target=cleanup_task, daemon=True)
    cleanup_thread.start()


def cleanup_memory_cache() -> int:
    """Clean up expired items in memory cache"""
    now = time.time()
    expired_keys = []

    # Find expired keys
    for key, entry in memory_cache.items():
        if entry.get("expiry") and entry["expiry"] < now:
            expired_keys.append(key)

    # Remove expired keys
    for key in expired_keys:
        memory_cache.pop(key, None)

    return len(expired_keys)


class RedisClient:
    """Redis client wrapper with fallback to in-memory storage"""

    @staticmethod
    async def set(
        key: str, value: str, ex: Optional[int] = None, px: Optional[int] = None
    ) -> str:
        """Set a key-value pair"""
        if using_memory_fallback:
            # Store in memory with expiry
            expiry = None
            if ex:  # Seconds
                expiry = time.time() + ex
            elif px:  # Milliseconds
                expiry = time.time() + (px / 1000)

            memory_cache[key] = {"value": value, "expiry": expiry}
            return "OK"
        else:
            # Use Redis
            return await redis_client.set(key, value, ex=ex, px=px)

    @staticmethod
    async def get(key: str) -> Optional[str]:
        """Get a value from a key"""
        if using_memory_fallback:
            entry = memory_cache.get(key)

            # Return None if key doesn't exist or is expired
            if not entry:
                return None

            if entry.get("expiry") and entry["expiry"] < time.time():
                # Clean up expired entry
                memory_cache.pop(key, None)
                return None

            return entry["value"]
        else:
            return await redis_client.get(key)

    @staticmethod
    async def delete(key: str) -> int:
        """Delete a key"""
        if using_memory_fallback:
            if key in memory_cache:
                del memory_cache[key]
                return 1
            return 0
        else:
            return await redis_client.delete(key)

    @staticmethod
    async def exists(key: str) -> int:
        """Check if a key exists"""
        if using_memory_fallback:
            entry = memory_cache.get(key)

            # Check if key exists and is not expired
            if entry and (not entry.get("expiry") or entry["expiry"] >= time.time()):
                return 1

            # Clean up expired entry if needed
            if entry and entry.get("expiry") and entry["expiry"] < time.time():
                memory_cache.pop(key, None)

            return 0
        else:
            return await redis_client.exists(key)

    @staticmethod
    async def expire(key: str, seconds: int) -> int:
        """Set expiry time on a key"""
        if using_memory_fallback:
            entry = memory_cache.get(key)

            # Return 0 if key doesn't exist or is already expired
            if not entry:
                return 0

            if entry.get("expiry") and entry["expiry"] < time.time():
                memory_cache.pop(key, None)
                return 0

            # Set new expiry
            entry["expiry"] = time.time() + seconds
            memory_cache[key] = entry
            return 1
        else:
            return await redis_client.expire(key, seconds)

    @staticmethod
    async def ttl(key: str) -> int:
        """Get TTL for a key"""
        if using_memory_fallback:
            entry = memory_cache.get(key)

            # Return -2 if key doesn't exist
            if not entry:
                return -2

            # Return -1 if key has no expiry
            if not entry.get("expiry"):
                return -1

            # Check if already expired
            now = time.time()
            if entry["expiry"] < now:
                # Clean up expired entry
                memory_cache.pop(key, None)
                return -2

            # Return TTL in seconds
            return int(entry["expiry"] - now)
        else:
            return await redis_client.ttl(key)

    @staticmethod
    async def incr(key: str) -> int:
        """Increment a number stored at key"""
        if using_memory_fallback:
            entry = memory_cache.get(key)

            # If key doesn't exist, set to 1
            if not entry:
                memory_cache[key] = {"value": "1", "expiry": None}
                return 1

            # Parse current value
            try:
                current_value = int(entry["value"])
            except (ValueError, TypeError):
                current_value = 0

            new_value = current_value + 1

            # Update value
            entry["value"] = str(new_value)
            memory_cache[key] = entry

            return new_value
        else:
            return await redis_client.incr(key)

    @staticmethod
    async def incrby(key: str, amount: int) -> int:
        """Increment a number by the given amount"""
        if using_memory_fallback:
            entry = memory_cache.get(key)

            # If key doesn't exist, set to amount
            if not entry:
                memory_cache[key] = {"value": str(amount), "expiry": None}
                return amount

            # Parse current value
            try:
                current_value = int(entry["value"])
            except (ValueError, TypeError):
                current_value = 0

            new_value = current_value + amount

            # Update value
            entry["value"] = str(new_value)
            memory_cache[key] = entry

            return new_value
        else:
            return await redis_client.incrby(key, amount)

    @staticmethod
    async def setnx(key: str, value: str) -> int:
        """Set key to hold string value if key does not exist"""
        if using_memory_fallback:
            # Check if key exists and is not expired
            entry = memory_cache.get(key)
            if entry and (not entry.get("expiry") or entry["expiry"] >= time.time()):
                return 0  # Key exists, not set

            # Set the value (key doesn't exist or is expired)
            memory_cache[key] = {"value": value, "expiry": None}
            return 1
        else:
            return await redis_client.setnx(key, value)

    @staticmethod
    async def flushall() -> str:
        """Flush all data - useful for testing"""
        if using_memory_fallback:
            memory_cache.clear()
            return "OK"
        else:
            return await redis_client.flushall()

    @staticmethod
    def is_using_memory_fallback() -> bool:
        """Check if using memory fallback"""
        return using_memory_fallback


# Create and export client instance
redis_client_instance = RedisClient()
