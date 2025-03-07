/**
 * Implementation of the Context Manager component for Cortex Core
 */

import { v4 as uuidv4 } from 'uuid';
import { logger } from '../utils/logger';
import { MemorySystemInterface } from '../interfaces/memory-system-interface';
import { redisClient } from '../cache/redis';

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
  metadata?: Record<string, any>;
}

export interface Entity {
  id: string;
  type: string;
  name: string;
  properties: Record<string, any>;
}

export interface Context {
  messages: Message[];
  entities: Entity[];
  metadata: Record<string, any>;
  lastUpdated: Date;
}

export interface ContextUpdate {
  addMessages?: Message[];
  removeMessageIds?: string[];
  addEntities?: Entity[];
  removeEntityIds?: string[];
  updateMetadata?: Record<string, any>;
}

export class ContextManager {
  private readonly memorySystem: MemorySystemInterface;
  private readonly CONTEXT_CACHE_PREFIX = 'context:';
  private readonly CONTEXT_CACHE_TTL = 3600; // 1 hour in seconds

  constructor(memorySystem: MemorySystemInterface) {
    this.memorySystem = memorySystem;
  }

  /**
   * Get context relevant to a specific query or task
   * @param sessionId The ID of the session
   * @param workspaceId The ID of the workspace
   * @param query Optional query to filter relevant context
   * @returns The context object
   */
  async getContext(sessionId: string, workspaceId: string, query?: string): Promise<Context> {
    try {
      logger.info(`Getting context for session ${sessionId}, workspace ${workspaceId}`);

      // Try to get from cache first
      const cacheKey = this.getCacheKey(sessionId, workspaceId);
      const cachedContext = await redisClient.get(cacheKey);

      if (cachedContext) {
        const parsedContext = JSON.parse(cachedContext) as Context;
        logger.debug(`Retrieved context from cache for session ${sessionId}, workspace ${workspaceId}`);

        // If no query, return cached context
        if (!query) {
          return parsedContext;
        }

        // With a query, still need to get synthesized context from memory system
      }

      // Prepare memory query
      const memoryQuery = {
        contentQuery: query,
        includeExpired: false,
        limit: 50 // Reasonable default
      };

      // Get synthesized memory from memory system
      const synthesizedMemory = await this.memorySystem.synthesizeContext(workspaceId, memoryQuery);

      // Convert memory items to context format
      const messages: Message[] = [];
      const entities: Entity[] = [];

      for (const item of synthesizedMemory.rawItems) {
        if (item.type === 'message') {
          messages.push(item.content as Message);
        } else if (item.type === 'entity') {
          entities.push(item.content as Entity);
        }
      }

      const context: Context = {
        messages,
        entities,
        metadata: synthesizedMemory.entities || {},
        lastUpdated: new Date()
      };

      // Cache the context
      await this.cacheContext(sessionId, workspaceId, context);

      return context;
    } catch (error) {
      logger.error(`Failed to get context for session ${sessionId}, workspace ${workspaceId}`, error);

      // Return empty context on error
      return {
        messages: [],
        entities: [],
        metadata: {},
        lastUpdated: new Date()
      };
    }
  }

  /**
   * Update the context with new information
   * @param sessionId The ID of the session
   * @param workspaceId The ID of the workspace
   * @param contextUpdate The updates to apply to the context
   */
  async updateContext(sessionId: string, workspaceId: string, contextUpdate: ContextUpdate): Promise<void> {
    try {
      logger.info(`Updating context for session ${sessionId}, workspace ${workspaceId}`);

      // Get current context
      let currentContext = await this.getContext(sessionId, workspaceId);

      // Apply updates
      if (contextUpdate.addMessages) {
        // Add new messages
        for (const message of contextUpdate.addMessages) {
          // Ensure message has an ID
          if (!message.id) {
            message.id = uuidv4();
          }

          // Store in memory system
          await this.memorySystem.store(workspaceId, {
            type: 'message',
            content: message,
            metadata: message.metadata || {},
            timestamp: message.timestamp
          });

          // Add to current context
          currentContext.messages.push(message);
        }
      }

      if (contextUpdate.removeMessageIds) {
        // Remove messages by ID
        for (const messageId of contextUpdate.removeMessageIds) {
          // Remove from memory system
          await this.memorySystem.delete(workspaceId, messageId);

          // Remove from current context
          currentContext.messages = currentContext.messages.filter(m => m.id !== messageId);
        }
      }

      if (contextUpdate.addEntities) {
        // Add new entities
        for (const entity of contextUpdate.addEntities) {
          // Ensure entity has an ID
          if (!entity.id) {
            entity.id = uuidv4();
          }

          // Store in memory system
          await this.memorySystem.store(workspaceId, {
            type: 'entity',
            content: entity,
            metadata: {
              type: entity.type,
              name: entity.name
            },
            timestamp: new Date()
          });

          // Add to current context
          currentContext.entities.push(entity);
        }
      }

      if (contextUpdate.removeEntityIds) {
        // Remove entities by ID
        for (const entityId of contextUpdate.removeEntityIds) {
          // Remove from memory system
          await this.memorySystem.delete(workspaceId, entityId);

          // Remove from current context
          currentContext.entities = currentContext.entities.filter(e => e.id !== entityId);
        }
      }

      if (contextUpdate.updateMetadata) {
        // Update metadata
        currentContext.metadata = {
          ...currentContext.metadata,
          ...contextUpdate.updateMetadata
        };
      }

      // Update last updated timestamp
      currentContext.lastUpdated = new Date();

      // Cache updated context
      await this.cacheContext(sessionId, workspaceId, currentContext);

    } catch (error) {
      logger.error(`Failed to update context for session ${sessionId}, workspace ${workspaceId}`, error);
      throw new Error(`Failed to update context: ${(error as Error).message}`);
    }
  }

  /**
   * Clear outdated or irrelevant context
   * @param sessionId The ID of the session
   * @param workspaceId The ID of the workspace
   * @param olderThan Optional date to remove context older than
   */
  async pruneContext(sessionId: string, workspaceId: string, olderThan?: Date): Promise<void> {
    try {
      logger.info(`Pruning context for session ${sessionId}, workspace ${workspaceId}`);

      // Get current context
      const currentContext = await this.getContext(sessionId, workspaceId);

      if (olderThan) {
        // Remove messages older than the specified date
        const olderThanTime = olderThan.getTime();

        // Filter messages to keep
        const messagesToKeep = currentContext.messages.filter(message =>
          new Date(message.timestamp).getTime() >= olderThanTime
        );

        // Identify messages to remove
        const messagesToRemove = currentContext.messages.filter(message =>
          new Date(message.timestamp).getTime() < olderThanTime
        ).map(message => message.id);

        // Remove messages from memory system
        for (const messageId of messagesToRemove) {
          await this.memorySystem.delete(workspaceId, messageId);
        }

        // Update current context
        currentContext.messages = messagesToKeep;
        currentContext.lastUpdated = new Date();

        // Update cache
        await this.cacheContext(sessionId, workspaceId, currentContext);
      } else {
        // Clear all context for this workspace
        // This is more efficiently done by clearing the cache and letting
        // memory system handle persistence pruning
        await redisClient.del(this.getCacheKey(sessionId, workspaceId));
      }

    } catch (error) {
      logger.error(`Failed to prune context for session ${sessionId}, workspace ${workspaceId}`, error);
      throw new Error(`Failed to prune context: ${(error as Error).message}`);
    }
  }

  /**
   * Get the cache key for a session's context in a workspace
   * @param sessionId The session ID
   * @param workspaceId The workspace ID
   * @returns The cache key
   * @private
   */
  private getCacheKey(sessionId: string, workspaceId: string): string {
    return `${this.CONTEXT_CACHE_PREFIX}${sessionId}:${workspaceId}`;
  }

  /**
   * Cache a context for fast access
   * @param sessionId The session ID
   * @param workspaceId The workspace ID
   * @param context The context to cache
   * @private
   */
  private async cacheContext(sessionId: string, workspaceId: string, context: Context): Promise<void> {
    const cacheKey = this.getCacheKey(sessionId, workspaceId);

    await redisClient.set(
      cacheKey,
      JSON.stringify(context),
      'EX',
      this.CONTEXT_CACHE_TTL
    );
  }
}
