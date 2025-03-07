/**
 * Redis cache utility for Cortex Core with in-memory fallback
 */

import Redis from 'ioredis';
import config from '../config';
import { logger } from '../utils/logger';

// Redis client instance
let redisClientInstance: Redis | null = null;

// In-memory cache fallback
const memoryCache = new Map<string, {
  value: string;
  expiry: number | null;
}>();

// Track if we're using memory fallback
let usingMemoryFallback = false;

/**
 * Connect to Redis
 */
export async function connectRedis(): Promise<void> {
  try {
    logger.info('Connecting to Redis...');

    // Create Redis client
    redisClientInstance = new Redis({
      host: config.cache.host,
      port: config.cache.port,
      password: config.cache.password,
      retryStrategy: (times) => {
        // If we've failed a few times, use memory fallback
        if (times >= 2) {
          if (!usingMemoryFallback) {
            logger.warn('Redis connection failed, using in-memory cache fallback');
            usingMemoryFallback = true;
          }
          return null; // stop retrying
        }
        const delay = Math.min(times * 50, 2000);
        return delay;
      }
    });

    // Set up event handlers
    redisClientInstance.on('connect', () => {
      usingMemoryFallback = false;
      logger.info('Redis connection established');
    });

    redisClientInstance.on('error', (error) => {
      logger.error('Redis error', error);
      // On error, switch to memory fallback
      if (!usingMemoryFallback) {
        logger.warn('Switching to in-memory cache fallback');
        usingMemoryFallback = true;
      }
    });

    redisClientInstance.on('reconnecting', () => {
      logger.warn('Reconnecting to Redis...');
    });

    try {
      // Test connection
      await redisClientInstance.ping();
      usingMemoryFallback = false;
    } catch (error) {
      logger.warn('Redis ping failed, using in-memory cache fallback');
      usingMemoryFallback = true;
      // We'll continue with the memory fallback
    }

  } catch (error) {
    logger.error('Failed to connect to Redis', error);
    logger.warn('Using in-memory cache fallback');
    usingMemoryFallback = true;
  }

  // Start memory cache cleanup interval
  startMemoryCacheCleanup();
}

/**
 * Disconnect from Redis
 */
export async function disconnectRedis(): Promise<void> {
  try {
    if (redisClientInstance && !usingMemoryFallback) {
      logger.info('Disconnecting from Redis...');
      await redisClientInstance.quit();
      redisClientInstance = null;
      logger.info('Redis connection closed');
    }
  } catch (error) {
    logger.error('Failed to disconnect from Redis', error);
  }
}

/**
 * Start periodic cleanup of expired items in memory cache
 */
function startMemoryCacheCleanup(): void {
  const CLEANUP_INTERVAL = 60 * 1000; // 1 minute

  setInterval(() => {
    const now = Date.now();
    let expiredCount = 0;

    // Clean up expired items
    for (const [key, entry] of memoryCache.entries()) {
      if (entry.expiry !== null && entry.expiry < now) {
        memoryCache.delete(key);
        expiredCount++;
      }
    }

    if (expiredCount > 0) {
      logger.debug(`Memory cache cleanup: removed ${expiredCount} expired items. Current size: ${memoryCache.size}`);
    }
  }, CLEANUP_INTERVAL);
}

/**
 * Redis client wrapper with typed methods that falls back to in-memory storage
 */
export const redisClient = {
  /**
   * Set a key-value pair in Redis or memory
   * @param key The key
   * @param value The value
   * @param expiryMode Optional expiry mode ('EX' for seconds, 'PX' for milliseconds)
   * @param time Optional time value for expiry
   */
  async set(key: string, value: string, expiryMode?: string, time?: number): Promise<string> {
    if (usingMemoryFallback) {
      // Store in memory with expiry
      let expiry: number | null = null;

      if (expiryMode && time) {
        const multiplier = expiryMode === 'EX' ? 1000 : 1; // Convert seconds to ms if needed
        expiry = Date.now() + (time * multiplier);
      }

      memoryCache.set(key, { value, expiry });
      return 'OK';
    } else {
      // Use Redis
      const client = getClient();
      if (expiryMode && time) {
        // Use specific overloads based on the expiry mode
        if (expiryMode === 'EX') {
          return client.set(key, value, 'EX', time);
        } else if (expiryMode === 'PX') {
          return client.set(key, value, 'PX', time);
        } else {
          // Fall back to generic set
          return client.set(key, value);
        }
      } else {
        return client.set(key, value);
      }
    }
  },

  /**
   * Get a value from Redis or memory
   * @param key The key
   * @returns The value or null if key doesn't exist
   */
  async get(key: string): Promise<string | null> {
    if (usingMemoryFallback) {
      const entry = memoryCache.get(key);

      // Return null if key doesn't exist or is expired
      if (!entry || (entry.expiry !== null && entry.expiry < Date.now())) {
        if (entry) {
          // Clean up expired entry
          memoryCache.delete(key);
        }
        return null;
      }

      return entry.value;
    } else {
      const client = getClient();
      return client.get(key);
    }
  },

  /**
   * Delete a key from Redis or memory
   * @param key The key
   * @returns Number of keys removed
   */
  async del(key: string): Promise<number> {
    if (usingMemoryFallback) {
      const existed = memoryCache.delete(key);
      return existed ? 1 : 0;
    } else {
      const client = getClient();
      return client.del(key);
    }
  },

  /**
   * Check if a key exists
   * @param key The key
   * @returns 1 if key exists, 0 otherwise
   */
  async exists(key: string): Promise<number> {
    if (usingMemoryFallback) {
      const entry = memoryCache.get(key);

      // Check if key exists and is not expired
      if (entry && (entry.expiry === null || entry.expiry >= Date.now())) {
        return 1;
      }

      // Clean up expired entry if needed
      if (entry && entry.expiry !== null && entry.expiry < Date.now()) {
        memoryCache.delete(key);
      }

      return 0;
    } else {
      const client = getClient();
      return client.exists(key);
    }
  },

  /**
   * Set expiry time on a key
   * @param key The key
   * @param seconds Expiry time in seconds
   * @returns 1 if timeout was set, 0 if key doesn't exist
   */
  async expire(key: string, seconds: number): Promise<number> {
    if (usingMemoryFallback) {
      const entry = memoryCache.get(key);

      // Return 0 if key doesn't exist or is already expired
      if (!entry || (entry.expiry !== null && entry.expiry < Date.now())) {
        if (entry) {
          // Clean up expired entry
          memoryCache.delete(key);
        }
        return 0;
      }

      // Set new expiry
      entry.expiry = Date.now() + (seconds * 1000);
      memoryCache.set(key, entry);

      return 1;
    } else {
      const client = getClient();
      return client.expire(key, seconds);
    }
  },

  /**
   * Get TTL for a key
   * @param key The key
   * @returns TTL in seconds, -1 if key has no TTL, -2 if key doesn't exist
   */
  async ttl(key: string): Promise<number> {
    if (usingMemoryFallback) {
      const entry = memoryCache.get(key);

      // Return -2 if key doesn't exist
      if (!entry) {
        return -2;
      }

      // Return -1 if key has no expiry
      if (entry.expiry === null) {
        return -1;
      }

      // Check if already expired
      const now = Date.now();
      if (entry.expiry < now) {
        // Clean up expired entry
        memoryCache.delete(key);
        return -2;
      }

      // Return TTL in seconds
      return Math.ceil((entry.expiry - now) / 1000);
    } else {
      const client = getClient();
      return client.ttl(key);
    }
  },

  /**
   * Increment a number stored at key
   * @param key The key
   * @returns The value after incrementing
   */
  async incr(key: string): Promise<number> {
    if (usingMemoryFallback) {
      const entry = memoryCache.get(key);

      // If key doesn't exist, set to 1
      if (!entry) {
        memoryCache.set(key, { value: '1', expiry: null });
        return 1;
      }

      // Parse current value
      const currentValue = parseInt(entry.value, 10) || 0;
      const newValue = currentValue + 1;

      // Update value
      entry.value = newValue.toString();
      memoryCache.set(key, entry);

      return newValue;
    } else {
      const client = getClient();
      return client.incr(key);
    }
  },

  /**
   * Increment a number stored at key by a specified amount
   * @param key The key
   * @param increment The increment amount
   * @returns The value after incrementing
   */
  async incrBy(key: string, increment: number): Promise<number> {
    if (usingMemoryFallback) {
      const entry = memoryCache.get(key);

      // If key doesn't exist, set to increment value
      if (!entry) {
        memoryCache.set(key, { value: increment.toString(), expiry: null });
        return increment;
      }

      // Parse current value
      const currentValue = parseInt(entry.value, 10) || 0;
      const newValue = currentValue + increment;

      // Update value
      entry.value = newValue.toString();
      memoryCache.set(key, entry);

      return newValue;
    } else {
      const client = getClient();
      return client.incrby(key, increment);
    }
  },

  /**
   * Set a key's time to live in milliseconds
   * @param key The key
   * @param milliseconds Expiry time in milliseconds
   * @returns 1 if timeout was set, 0 if key doesn't exist
   */
  async pExpire(key: string, milliseconds: number): Promise<number> {
    if (usingMemoryFallback) {
      const entry = memoryCache.get(key);

      // Return 0 if key doesn't exist or is already expired
      if (!entry || (entry.expiry !== null && entry.expiry < Date.now())) {
        if (entry) {
          // Clean up expired entry
          memoryCache.delete(key);
        }
        return 0;
      }

      // Set new expiry
      entry.expiry = Date.now() + milliseconds;
      memoryCache.set(key, entry);

      return 1;
    } else {
      const client = getClient();
      return client.pexpire(key, milliseconds);
    }
  },

  /**
   * Set key to hold string value if key does not exist
   * @param key The key
   * @param value The value
   * @returns 1 if set, 0 if not set
   */
  async setNX(key: string, value: string): Promise<number> {
    if (usingMemoryFallback) {
      // Check if key exists and is not expired
      const entry = memoryCache.get(key);
      if (entry && (entry.expiry === null || entry.expiry >= Date.now())) {
        return 0; // Key exists, not set
      }

      // Set the value (key doesn't exist or is expired)
      memoryCache.set(key, { value, expiry: null });
      return 1;
    } else {
      const client = getClient();
      return client.setnx(key, value);
    }
  },

  /**
   * Execute a raw Redis command - limited support in memory fallback mode
   * @param command Command name
   * @param args Command arguments
   * @returns Command result
   */
  async exec(command: string, ...args: any[]): Promise<any> {
    if (usingMemoryFallback) {
      // Only support a few basic commands in memory mode
      const lowerCommand = command.toLowerCase();

      switch (lowerCommand) {
        case 'get':
          return this.get(args[0]);
        case 'set':
          return this.set(args[0], args[1]);
        case 'del':
          return this.del(args[0]);
        case 'exists':
          return this.exists(args[0]);
        case 'expire':
          return this.expire(args[0], args[1]);
        case 'ttl':
          return this.ttl(args[0]);
        case 'incr':
          return this.incr(args[0]);
        case 'incrby':
          return this.incrBy(args[0], args[1]);
        default:
          throw new Error(`Command '${command}' not supported in memory fallback mode`);
      }
    } else {
      const client = getClient();
      return client.call(command, ...args);
    }
  },

  /**
   * Flush all data - useful for testing
   */
  async flushAll(): Promise<string> {
    if (usingMemoryFallback) {
      memoryCache.clear();
      return 'OK';
    } else {
      const client = getClient();
      return client.flushall();
    }
  },

  /**
   * Returns true if we're currently using the memory fallback
   */
  isUsingMemoryFallback(): boolean {
    return usingMemoryFallback;
  }
};

/**
 * Get Redis client instance
 * @throws Error if Redis client is not initialized and we're not using memory fallback
 */
function getClient(): Redis {
  if (!redisClientInstance && !usingMemoryFallback) {
    throw new Error('Redis client not initialized');
  }
  return redisClientInstance as Redis;
}

// Export for use in other modules
export default redisClient;
