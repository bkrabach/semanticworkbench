/**
 * Implementation of the Whiteboard Memory System for Cortex Core
 * This serves as a simplified implementation that will be replaced by JAKE in the future
 */

import { v4 as uuidv4 } from 'uuid';
import { logger } from '../utils/logger';
import { db } from '../database/connection';
import { redisClient } from '../cache/redis';
import { MemorySystemInterface } from '../interfaces/memory-system-interface';
import { stringifyJson, parseJsonString } from '../utils/json-helpers';

export interface MemoryConfig {
  storageType: "in_memory" | "persistent";
  retentionPolicy?: RetentionPolicy;
  encryptionEnabled: boolean;
}

export interface MemoryItem {
  id?: string;
  type: "message" | "entity" | "file" | "event";
  content: any;
  metadata: Record<string, any>;
  timestamp: Date;
  expiresAt?: Date;
}

export interface MemoryQuery {
  types?: string[];
  fromTimestamp?: Date;
  toTimestamp?: Date;
  contentQuery?: string;
  metadataFilters?: Record<string, any>;
  limit?: number;
  includeExpired?: boolean;
}

export interface SynthesizedMemory {
  rawItems: MemoryItem[];
  summary: string;
  entities: Record<string, any>;
  relevanceScore: number;
}

export interface RetentionPolicy {
  defaultTtlDays: number;
  typeSpecificTtl?: Record<string, number>; // type -> days
  maxItems?: number;
}

export class WhiteboardMemorySystem implements MemorySystemInterface {
  private readonly MEMORY_CACHE_PREFIX = 'memory:';
  private readonly CACHE_TTL = 3600; // 1 hour in seconds
  private config: MemoryConfig;
  private initialized = false;

  constructor() {
    // Default configuration
    this.config = {
      storageType: 'persistent',
      retentionPolicy: {
        defaultTtlDays: 90,
        typeSpecificTtl: {
          'message': 90,
          'entity': 180,
          'file': 30,
          'event': 60
        },
        maxItems: 10000
      },
      encryptionEnabled: false
    };
  }

  /**
   * Initialize the memory system
   * @param config Configuration options
   */
  async initialize(config: MemoryConfig): Promise<void> {
    try {
      logger.info('Initializing Whiteboard Memory System');

      this.config = {
        ...this.config,
        ...config
      };

      // Ensure database is set up correctly
      if (this.config.storageType === 'persistent') {
        // Check if the necessary tables exist, etc.
        // This is handled by our database migration system in real implementation
      }

      this.initialized = true;
      logger.info('Whiteboard Memory System initialized successfully');
    } catch (error) {
      logger.error('Failed to initialize Whiteboard Memory System', error);
      throw new Error(`Failed to initialize memory system: ${(error as Error).message}`);
    }
  }

  /**
   * Store a memory item
   * @param workspaceId The ID of the workspace
   * @param item The memory item to store
   * @returns The ID of the stored item
   */
  async store(workspaceId: string, item: MemoryItem): Promise<string> {
    try {
      this.ensureInitialized();

      // Generate ID if not provided
      if (!item.id) {
        item.id = uuidv4();
      }

      // Set expiration date based on retention policy if not already set
      if (!item.expiresAt && this.config.retentionPolicy) {
        const ttlDays = this.config.retentionPolicy.typeSpecificTtl?.[item.type] ||
          this.config.retentionPolicy.defaultTtlDays;

        const expiresAt = new Date();
        expiresAt.setDate(expiresAt.getDate() + ttlDays);
        item.expiresAt = expiresAt;
      }

      // Store in database if using persistent storage
      if (this.config.storageType === 'persistent') {
        await db.memoryItems.create({
          data: {
            id: item.id,
            workspaceId,
            type: item.type,
            content: stringifyJson(item.content),        // Convert to JSON string
            metadata: stringifyJson(item.metadata),      // Convert to JSON string
            timestamp: item.timestamp,
            expiresAt: item.expiresAt
          }
        });
      }

      // Update cache
      await this.updateMemoryCache(workspaceId);

      logger.debug(`Stored memory item ${item.id} in workspace ${workspaceId}`);
      return item.id;
    } catch (error) {
      logger.error(`Failed to store memory item in workspace ${workspaceId}`, error);
      throw new Error(`Failed to store memory item: ${(error as Error).message}`);
    }
  }

  /**
   * Retrieve memory items based on a query
   * @param workspaceId The ID of the workspace
   * @param query The query parameters
   * @returns Array of memory items
   */
  async retrieve(workspaceId: string, query: MemoryQuery): Promise<MemoryItem[]> {
    try {
      this.ensureInitialized();

      logger.debug(`Retrieving memory items from workspace ${workspaceId}`);

      // Build database query conditions
      const where: any = { workspaceId };

      // Filter by type
      if (query.types && query.types.length > 0) {
        where.type = { in: query.types };
      }

      // Filter by timestamp range
      if (query.fromTimestamp || query.toTimestamp) {
        where.timestamp = {};

        if (query.fromTimestamp) {
          where.timestamp.gte = query.fromTimestamp;
        }

        if (query.toTimestamp) {
          where.timestamp.lte = query.toTimestamp;
        }
      }

      // Filter by expiration
      if (!query.includeExpired) {
        where.expiresAt = {
          gt: new Date()
        };
      }

      // Execute database query
      const items = await db.memoryItems.findMany({
        where,
        orderBy: { timestamp: 'desc' },
        take: query.limit || 100
      });

      // Parse JSON strings and convert to MemoryItem objects
      const memoryItems: MemoryItem[] = items.map((item: any) => ({
        id: item.id,
        type: item.type as "message" | "entity" | "file" | "event",
        content: parseJsonString(item.content, {}),
        metadata: parseJsonString(item.metadata, {}),
        timestamp: item.timestamp,
        expiresAt: item.expiresAt
      }));

      // Apply content query filter if specified
      // This is a simplified implementation - in a real system this would use
      // more sophisticated text search
      let filteredItems = memoryItems;

      if (query.contentQuery && query.contentQuery.trim().length > 0) {
        const searchTerms = query.contentQuery.toLowerCase().split(/\s+/);

        filteredItems = filteredItems.filter(item => {
          const contentStr = JSON.stringify(item.content).toLowerCase();
          return searchTerms.every(term => contentStr.includes(term));
        });
      }

      // Apply metadata filters if specified
      if (query.metadataFilters && Object.keys(query.metadataFilters).length > 0) {
        filteredItems = filteredItems.filter(item => {
          return Object.entries(query.metadataFilters || {}).every(([key, value]) => {
            return item.metadata[key] === value;
          });
        });
      }

      return filteredItems;
    } catch (error) {
      logger.error(`Failed to retrieve memory items from workspace ${workspaceId}`, error);
      return []; // Return empty array on error
    }
  }

  /**
   * Update an existing memory item
   * @param workspaceId The ID of the workspace
   * @param itemId The ID of the item to update
   * @param updates The updates to apply
   */
  async update(workspaceId: string, itemId: string, updates: Partial<MemoryItem>): Promise<void> {
    try {
      this.ensureInitialized();

      logger.debug(`Updating memory item ${itemId} in workspace ${workspaceId}`);

      // Prepare data updates with JSON serialization for content and metadata
      const updateData: any = { ...updates };

      // Remove fields that shouldn't be updated
      delete updateData.id;
      delete updateData.type;
      delete updateData.workspaceId;

      // Serialize JSON fields if they exist in the updates
      if (updates.content !== undefined) {
        updateData.content = stringifyJson(updates.content);
      }

      if (updates.metadata !== undefined) {
        updateData.metadata = stringifyJson(updates.metadata);
      }

      // Update in database
      await db.memoryItems.update({
        where: {
          id: itemId,
          workspaceId
        },
        data: updateData
      });

      // Update cache
      await this.updateMemoryCache(workspaceId);
    } catch (error) {
      logger.error(`Failed to update memory item ${itemId} in workspace ${workspaceId}`, error);
      throw new Error(`Failed to update memory item: ${(error as Error).message}`);
    }
  }

  /**
   * Delete a memory item
   * @param workspaceId The ID of the workspace
   * @param itemId The ID of the item to delete
   */
  async delete(workspaceId: string, itemId: string): Promise<void> {
    try {
      this.ensureInitialized();

      logger.debug(`Deleting memory item ${itemId} from workspace ${workspaceId}`);

      // Delete from database
      await db.memoryItems.delete({
        where: {
          id: itemId,
          workspaceId
        }
      });

      // Update cache
      await this.updateMemoryCache(workspaceId);
    } catch (error) {
      logger.error(`Failed to delete memory item ${itemId} from workspace ${workspaceId}`, error);
      throw new Error(`Failed to delete memory item: ${(error as Error).message}`);
    }
  }

  /**
   * Generate a synthetic/enriched context from raw memory
   * This is a simplified implementation compared to what JAKE would do
   * @param workspaceId The ID of the workspace
   * @param query The query parameters
   * @returns Synthesized memory
   */
  async synthesizeContext(workspaceId: string, query: MemoryQuery): Promise<SynthesizedMemory> {
    try {
      this.ensureInitialized();

      logger.debug(`Synthesizing context for workspace ${workspaceId}`);

      // Retrieve raw memory items
      const rawItems = await this.retrieve(workspaceId, query);

      // For the whiteboard implementation, we do minimal synthesis
      // Just extract entities and generate a basic summary

      // Extract entities (simplified)
      const entities: Record<string, any> = {};

      for (const item of rawItems) {
        if (item.type === 'entity') {
          const entity = item.content;
          if (entity && entity.id && entity.type) {
            entities[entity.id] = entity;
          }
        }
      }

      // Generate a very basic summary
      // In a real implementation, this would use an LLM to generate a summary
      const messageCount = rawItems.filter(item => item.type === 'message').length;
      const entityCount = Object.keys(entities).length;
      const fileCount = rawItems.filter(item => item.type === 'file').length;
      const eventCount = rawItems.filter(item => item.type === 'event').length;

      const summary = `Context contains ${messageCount} messages, ${entityCount} entities, ${fileCount} files, and ${eventCount} events.`;

      // Calculate a simple relevance score based on recency and content match
      let relevanceScore = Math.min(rawItems.length / 10, 1.0); // 0.0 to 1.0 based on number of items

      if (query.contentQuery && rawItems.length > 0) {
        // Adjust score based on how many items matched the content query
        // A perfect match would have all items matching the content query
        relevanceScore *= rawItems.length / (await this.countItems(workspaceId));
      }

      return {
        rawItems,
        summary,
        entities,
        relevanceScore
      };
    } catch (error) {
      logger.error(`Failed to synthesize context for workspace ${workspaceId}`, error);

      // Return empty results on error
      return {
        rawItems: [],
        summary: "Error retrieving context.",
        entities: {},
        relevanceScore: 0
      };
    }
  }

  /**
   * Count items in a workspace
   * @param workspaceId The workspace ID
   * @private
   */
  private async countItems(workspaceId: string): Promise<number> {
    const count = await db.memoryItems.count({
      where: { workspaceId }
    });

    return count;
  }

  /**
   * Update the memory cache for a workspace
   * @param workspaceId The workspace ID
   * @private
   */
  private async updateMemoryCache(workspaceId: string): Promise<void> {
    try {
      // Get recent memory items
      const recentItems = await db.memoryItems.findMany({
        where: {
          workspaceId,
          expiresAt: {
            gt: new Date()
          }
        },
        orderBy: { timestamp: 'desc' },
        take: 100
      });

      // Parse JSON strings into objects for proper caching
      const memoryItems: MemoryItem[] = recentItems.map((item: any) => ({
        id: item.id,
        type: item.type as "message" | "entity" | "file" | "event",
        content: parseJsonString(item.content, {}),
        metadata: parseJsonString(item.metadata, {}),
        timestamp: item.timestamp,
        expiresAt: item.expiresAt
      }));

      // Cache the recent items
      const cacheKey = `${this.MEMORY_CACHE_PREFIX}${workspaceId}`;
      await redisClient.set(
        cacheKey,
        JSON.stringify(memoryItems),
        'EX',
        this.CACHE_TTL
      );
    } catch (error) {
      logger.error(`Failed to update memory cache for workspace ${workspaceId}`, error);
    }
  }

  /**
   * Ensure the memory system is initialized
   * @private
   */
  private ensureInitialized(): void {
    if (!this.initialized) {
      throw new Error('Memory system not initialized. Call initialize() first.');
    }
  }
}
