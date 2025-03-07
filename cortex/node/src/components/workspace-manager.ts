/**
 * Implementation of the Workspace Manager component for Cortex Core
 */

import { v4 as uuidv4 } from 'uuid';
import { logger } from '../utils/logger';
import { db } from '../database/connection';
import { redisClient } from '../cache/redis';
import { stringifyJson, parseJsonString } from '../utils/json-helpers';

export interface Workspace {
  id: string;
  userId: string;
  name: string;
  createdAt: Date;
  lastActiveAt: Date;
  config: WorkspaceConfig;
  metadata: Record<string, any>;
}

export interface WorkspaceConfig {
  defaultModality?: string;
  sharingEnabled: boolean;
  retentionDays: number;
}

export interface Conversation {
  id: string;
  workspaceId: string;
  modality: string;
  title: string;
  createdAt: Date;
  lastActiveAt: Date;
  entries: ConversationEntry[];
  metadata: Record<string, any>;
}

export interface ConversationEntry {
  id: string;
  type: "user" | "assistant" | "system";
  content: any;
  timestamp: Date;
  metadata?: Record<string, any>;
}

export interface ConversationFilter {
  modality?: string;
  fromDate?: Date;
  toDate?: Date;
  searchText?: string;
}

// Define database record types for proper typing
interface WorkspaceRecord {
  id: string;
  userId: string;
  name: string;
  createdAt: Date;
  lastActiveAt: Date;
  config: string; // JSON string
  metadata: string; // JSON string
}

interface ConversationRecord {
  id: string;
  workspaceId: string;
  modality: string;
  title: string;
  createdAt: Date;
  lastActiveAt: Date;
  entries: string; // JSON string
  metadata: string; // JSON string
}

export class WorkspaceManager {
  private readonly WORKSPACE_CACHE_PREFIX = 'workspace:';
  private readonly CONVERSATION_CACHE_PREFIX = 'conversation:';
  private readonly CACHE_TTL = 3600; // 1 hour in seconds

  /**
   * Create a new workspace
   * @param userId The ID of the user
   * @param name The name of the workspace
   * @param config Optional workspace configuration
   * @returns The newly created workspace
   */
  async createWorkspace(userId: string, name: string, config?: Partial<WorkspaceConfig>): Promise<Workspace> {
    try {
      logger.info(`Creating workspace "${name}" for user ${userId}`);

      const defaultConfig: WorkspaceConfig = {
        defaultModality: config?.defaultModality || 'chat',
        sharingEnabled: config?.sharingEnabled ?? false,
        retentionDays: config?.retentionDays || 90
      };

      const now = new Date();
      const workspaceId = uuidv4();

      // Create workspace in database with JSON serialization
      const workspace = await db.workspaces.create({
        data: {
          id: workspaceId,
          userId,
          name,
          createdAt: now,
          lastActiveAt: now,
          config: stringifyJson(defaultConfig),  // Convert to JSON string
          metadata: stringifyJson({})            // Convert to JSON string
        }
      });

      // Parse the JSON strings to create the properly typed workspace object
      const typedWorkspace: Workspace = {
        id: workspace.id,
        userId: workspace.userId,
        name: workspace.name,
        createdAt: workspace.createdAt,
        lastActiveAt: workspace.lastActiveAt,
        config: parseJsonString(workspace.config, defaultConfig),
        metadata: parseJsonString(workspace.metadata, {})
      };

      // Cache workspace for faster access
      await this.cacheWorkspace(typedWorkspace);

      logger.info(`Created workspace ${workspaceId} for user ${userId}`);
      return typedWorkspace;
    } catch (error) {
      logger.error(`Failed to create workspace for user ${userId}`, error);
      throw new Error(`Failed to create workspace: ${(error as Error).message}`);
    }
  }

  /**
   * Get workspace by ID
   * @param workspaceId The ID of the workspace
   * @returns The workspace or null if not found
   */
  async getWorkspace(workspaceId: string): Promise<Workspace | null> {
    try {
      logger.debug(`Getting workspace ${workspaceId}`);

      // Try to get from cache first
      const cachedWorkspace = await redisClient.get(`${this.WORKSPACE_CACHE_PREFIX}${workspaceId}`);
      if (cachedWorkspace) {
        return JSON.parse(cachedWorkspace) as Workspace;
      }

      // If not in cache, get from database
      const workspace = await db.workspaces.findUnique({
        where: { id: workspaceId }
      });

      if (!workspace) {
        return null;
      }

      // Parse JSON strings into objects
      const typedWorkspace: Workspace = {
        id: workspace.id,
        userId: workspace.userId,
        name: workspace.name,
        createdAt: workspace.createdAt,
        lastActiveAt: workspace.lastActiveAt,
        config: parseJsonString(workspace.config, {
          defaultModality: 'chat',
          sharingEnabled: false,
          retentionDays: 90
        }),
        metadata: parseJsonString(workspace.metadata, {})
      };

      // Cache for future access
      await this.cacheWorkspace(typedWorkspace);

      return typedWorkspace;
    } catch (error) {
      logger.error(`Failed to get workspace ${workspaceId}`, error);
      return null;
    }
  }

  /**
   * List workspaces for a user
   * @param userId The ID of the user
   * @returns Array of workspaces
   */
  async listWorkspaces(userId: string): Promise<Workspace[]> {
    try {
      logger.debug(`Listing workspaces for user ${userId}`);

      // Get workspaces from database
      const workspaces = await db.workspaces.findMany({
        where: { userId }
      });

      // Parse JSON strings and cache workspaces
      const typedWorkspaces: Workspace[] = workspaces.map((workspace: WorkspaceRecord) => {
        const typedWorkspace: Workspace = {
          id: workspace.id,
          userId: workspace.userId,
          name: workspace.name,
          createdAt: workspace.createdAt,
          lastActiveAt: workspace.lastActiveAt,
          config: parseJsonString(workspace.config, {
            defaultModality: 'chat',
            sharingEnabled: false,
            retentionDays: 90
          }),
          metadata: parseJsonString(workspace.metadata, {})
        };

        // Cache each workspace
        this.cacheWorkspace(typedWorkspace).catch(err => {
          logger.error(`Failed to cache workspace ${workspace.id}`, err);
        });

        return typedWorkspace;
      });

      return typedWorkspaces;
    } catch (error) {
      logger.error(`Failed to list workspaces for user ${userId}`, error);
      return [];
    }
  }

  /**
   * Create a conversation in a workspace
   * @param workspaceId The ID of the workspace
   * @param modality The modality of the conversation
   * @param title Optional title for the conversation
   * @returns The newly created conversation
   */
  async createConversation(workspaceId: string, modality: string, title?: string): Promise<Conversation> {
    try {
      logger.info(`Creating ${modality} conversation in workspace ${workspaceId}`);

      const workspace = await this.getWorkspace(workspaceId);
      if (!workspace) {
        throw new Error(`Workspace not found: ${workspaceId}`);
      }

      const now = new Date();
      const conversationId = uuidv4();

      // Generate a title if none provided
      const conversationTitle = title || `${modality.charAt(0).toUpperCase() + modality.slice(1)} conversation ${now.toLocaleDateString()}`;

      // Create conversation in database with JSON serialization
      const conversation = await db.conversations.create({
        data: {
          id: conversationId,
          workspaceId,
          modality,
          title: conversationTitle,
          createdAt: now,
          lastActiveAt: now,
          entries: stringifyJson([]),     // Empty array as JSON string
          metadata: stringifyJson({})     // Empty object as JSON string
        }
      });

      // Parse JSON strings into objects
      const typedConversation: Conversation = {
        id: conversation.id,
        workspaceId: conversation.workspaceId,
        modality: conversation.modality,
        title: conversation.title,
        createdAt: conversation.createdAt,
        lastActiveAt: conversation.lastActiveAt,
        entries: parseJsonString(conversation.entries, []),
        metadata: parseJsonString(conversation.metadata, {})
      };

      // Cache conversation for faster access
      await this.cacheConversation(typedConversation);

      // Update workspace last active time
      await this.updateWorkspaceLastActive(workspaceId);

      logger.info(`Created conversation ${conversationId} in workspace ${workspaceId}`);
      return typedConversation;
    } catch (error) {
      logger.error(`Failed to create conversation in workspace ${workspaceId}`, error);
      throw new Error(`Failed to create conversation: ${(error as Error).message}`);
    }
  }

  /**
   * Get a conversation by ID
   * @param conversationId The ID of the conversation
   * @returns The conversation or null if not found
   */
  async getConversation(conversationId: string): Promise<Conversation | null> {
    try {
      logger.debug(`Getting conversation ${conversationId}`);

      // Try to get from cache first
      const cachedConversation = await redisClient.get(`${this.CONVERSATION_CACHE_PREFIX}${conversationId}`);
      if (cachedConversation) {
        return JSON.parse(cachedConversation) as Conversation;
      }

      // If not in cache, get from database
      const conversation = await db.conversations.findUnique({
        where: { id: conversationId }
      });

      if (!conversation) {
        return null;
      }

      // Parse JSON strings into objects
      const typedConversation: Conversation = {
        id: conversation.id,
        workspaceId: conversation.workspaceId,
        modality: conversation.modality,
        title: conversation.title,
        createdAt: conversation.createdAt,
        lastActiveAt: conversation.lastActiveAt,
        entries: parseJsonString(conversation.entries, []),
        metadata: parseJsonString(conversation.metadata, {})
      };

      // Cache for future access
      await this.cacheConversation(typedConversation);

      return typedConversation;
    } catch (error) {
      logger.error(`Failed to get conversation ${conversationId}`, error);
      return null;
    }
  }

  /**
   * List conversations in a workspace
   * @param workspaceId The ID of the workspace
   * @param filter Optional filter for conversations
   * @returns Array of conversations
   */
  async listConversations(workspaceId: string, filter?: ConversationFilter): Promise<Conversation[]> {
    try {
      logger.debug(`Listing conversations for workspace ${workspaceId}`);

      // Build filter conditions for database query
      const where: any = { workspaceId };

      if (filter?.modality) {
        where.modality = filter.modality;
      }

      if (filter?.fromDate) {
        where.createdAt = { gte: filter.fromDate };
      }

      if (filter?.toDate) {
        where.createdAt = {
          ...where.createdAt,
          lte: filter.toDate
        };
      }

      // Get conversations from database
      let conversationsDb = await db.conversations.findMany({ where });

      // Parse JSON strings into objects
      const typedConversations: Conversation[] = conversationsDb.map((conversation: ConversationRecord) => {
        const typedConversation: Conversation = {
          id: conversation.id,
          workspaceId: conversation.workspaceId,
          modality: conversation.modality,
          title: conversation.title,
          createdAt: conversation.createdAt,
          lastActiveAt: conversation.lastActiveAt,
          entries: parseJsonString(conversation.entries, []),
          metadata: parseJsonString(conversation.metadata, {})
        };

        return typedConversation;
      });

      // Apply text search filter if specified
      let filteredConversations = typedConversations;
      if (filter?.searchText && filter.searchText.trim().length > 0) {
        const searchLower = filter.searchText.toLowerCase();
        filteredConversations = typedConversations.filter(conv =>
          conv.title.toLowerCase().includes(searchLower) ||
          JSON.stringify(conv.metadata).toLowerCase().includes(searchLower)
        );
      }

      // Cache all conversations for faster access later
      for (const conversation of filteredConversations) {
        await this.cacheConversation(conversation);
      }

      return filteredConversations;
    } catch (error) {
      logger.error(`Failed to list conversations for workspace ${workspaceId}`, error);
      return [];
    }
  }

  /**
   * Add an entry to a conversation
   * @param conversationId The ID of the conversation
   * @param entry The entry to add
   */
  async addConversationEntry(conversationId: string, entry: Omit<ConversationEntry, 'id'>): Promise<ConversationEntry> {
    try {
      logger.info(`Adding entry to conversation ${conversationId}`);

      const conversation = await this.getConversation(conversationId);
      if (!conversation) {
        throw new Error(`Conversation not found: ${conversationId}`);
      }

      // Generate ID for entry if not provided
      const entryWithId: ConversationEntry = {
        id: uuidv4(),
        ...entry
      };

      // Add entry to conversation
      conversation.entries.push(entryWithId);
      conversation.lastActiveAt = new Date();

      // Update conversation in database
      await db.conversations.update({
        where: { id: conversationId },
        data: {
          entries: stringifyJson(conversation.entries),    // Convert array to JSON string
          lastActiveAt: conversation.lastActiveAt
        }
      });

      // Update cache
      await this.cacheConversation(conversation);

      // Update workspace last active time
      await this.updateWorkspaceLastActive(conversation.workspaceId);

      return entryWithId;
    } catch (error) {
      logger.error(`Failed to add entry to conversation ${conversationId}`, error);
      throw new Error(`Failed to add conversation entry: ${(error as Error).message}`);
    }
  }

  /**
   * Update workspace last active time
   * @param workspaceId The ID of the workspace
   * @private
   */
  private async updateWorkspaceLastActive(workspaceId: string): Promise<void> {
    try {
      const now = new Date();

      // Update in database
      await db.workspaces.update({
        where: { id: workspaceId },
        data: { lastActiveAt: now }
      });

      // Update in cache if exists
      const cachedWorkspace = await redisClient.get(`${this.WORKSPACE_CACHE_PREFIX}${workspaceId}`);
      if (cachedWorkspace) {
        const workspace = JSON.parse(cachedWorkspace) as Workspace;
        workspace.lastActiveAt = now;
        await this.cacheWorkspace(workspace);
      }
    } catch (error) {
      logger.error(`Failed to update workspace last active time: ${workspaceId}`, error);
    }
  }

  /**
   * Cache a workspace for fast access
   * @param workspace The workspace to cache
   * @private
   */
  private async cacheWorkspace(workspace: Workspace): Promise<void> {
    const cacheKey = `${this.WORKSPACE_CACHE_PREFIX}${workspace.id}`;

    await redisClient.set(
      cacheKey,
      JSON.stringify(workspace),
      'EX',
      this.CACHE_TTL
    );
  }

  /**
   * Cache a conversation for fast access
   * @param conversation The conversation to cache
   * @private
   */
  private async cacheConversation(conversation: Conversation): Promise<void> {
    const cacheKey = `${this.CONVERSATION_CACHE_PREFIX}${conversation.id}`;

    await redisClient.set(
      cacheKey,
      JSON.stringify(conversation),
      'EX',
      this.CACHE_TTL
    );
  }
}
