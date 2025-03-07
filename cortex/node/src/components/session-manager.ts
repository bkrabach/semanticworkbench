/**
 * Implementation of the Session Manager component for Cortex Core
 */

import { v4 as uuidv4 } from 'uuid';
import { db } from '../database/connection';
import { redisClient } from '../cache/redis';
import { logger } from '../utils/logger';
import { stringifyJson, parseJsonString } from '../utils/json-helpers';

export interface SessionConfig {
  timeoutMinutes: number;
  defaultWorkspaceId?: string;
  preferredModalities?: string[];
}

export interface Session {
  id: string;
  userId: string;
  createdAt: Date;
  lastActiveAt: Date;
  activeWorkspaceId: string;
  config: SessionConfig;
  metadata: Record<string, any>;
}

export class SessionManager {
  private readonly DEFAULT_TIMEOUT_MINUTES = 60;
  private readonly SESSION_CACHE_PREFIX = 'session:';

  /**
   * Create a new user session
   * @param userId The ID of the user
   * @param config Optional session configuration
   * @returns The newly created session
   */
  async createSession(userId: string, config?: Partial<SessionConfig>): Promise<Session> {
    try {
      const sessionId = uuidv4();

      // Generate default workspace if none specified
      let defaultWorkspaceId = config?.defaultWorkspaceId;
      if (!defaultWorkspaceId) {
        const workspace = await db.workspaces.create({
          data: {
            userId,
            name: 'Default Workspace',
            createdAt: new Date(),
            lastActiveAt: new Date(),
            config: '{}',   // Empty JSON object as string
            metadata: '{}'  // Empty JSON object as string
          }
        });
        defaultWorkspaceId = workspace.id;
      }

      const sessionConfig: SessionConfig = {
        timeoutMinutes: config?.timeoutMinutes || this.DEFAULT_TIMEOUT_MINUTES,
        defaultWorkspaceId,
        preferredModalities: config?.preferredModalities || ['chat']
      };

      const now = new Date();
      const session: Session = {
        id: sessionId,
        userId,
        createdAt: now,
        lastActiveAt: now,
        // Make sure defaultWorkspaceId is never undefined
        activeWorkspaceId: defaultWorkspaceId || '',
        config: sessionConfig,
        metadata: {}
      };

      // Store in DB with JSON serialization
      await db.sessions.create({
        data: {
          id: session.id,
          userId: session.userId,
          createdAt: session.createdAt,
          lastActiveAt: session.lastActiveAt,
          activeWorkspaceId: session.activeWorkspaceId,
          config: stringifyJson(session.config),     // Convert to JSON string
          metadata: stringifyJson(session.metadata)  // Convert to JSON string
        }
      });

      // Cache session for fast access
      await this.cacheSession(session);

      logger.info(`Created new session ${sessionId} for user ${userId}`);
      return session;
    } catch (error) {
      logger.error(`Failed to create session for user ${userId}`, error);
      throw new Error(`Failed to create session: ${(error as Error).message}`);
    }
  }

  /**
   * Retrieve an existing session
   * @param sessionId The ID of the session to retrieve
   * @returns The session or null if not found
   */
  async getSession(sessionId: string): Promise<Session | null> {
    try {
      // Try to get from cache first
      const cachedSession = await redisClient.get(`${this.SESSION_CACHE_PREFIX}${sessionId}`);
      if (cachedSession) {
        return JSON.parse(cachedSession) as Session;
      }

      // If not in cache, get from DB
      const sessionRecord = await db.sessions.findUnique({
        where: { id: sessionId }
      });

      if (!sessionRecord) {
        return null;
      }

      // Parse JSON strings to objects
      const session: Session = {
        id: sessionRecord.id,
        userId: sessionRecord.userId,
        createdAt: sessionRecord.createdAt,
        lastActiveAt: sessionRecord.lastActiveAt,
        activeWorkspaceId: sessionRecord.activeWorkspaceId,
        config: parseJsonString(sessionRecord.config, { timeoutMinutes: this.DEFAULT_TIMEOUT_MINUTES }),
        metadata: parseJsonString(sessionRecord.metadata, {})
      };

      // Cache for future retrieval
      await this.cacheSession(session);

      return session;
    } catch (error) {
      logger.error(`Failed to retrieve session ${sessionId}`, error);
      throw new Error(`Failed to retrieve session: ${(error as Error).message}`);
    }
  }

  /**
   * Get all active sessions for a user
   * @param userId The ID of the user
   * @returns Array of active sessions
   */
  async getActiveSessionsForUser(userId: string): Promise<Session[]> {
    try {
      logger.debug(`Getting active sessions for user ${userId}`);

      // Get from database
      const sessionRecords = await db.sessions.findMany({
        where: {
          userId,
          // Only include sessions that haven't expired
          lastActiveAt: {
            gte: new Date(Date.now() - (this.DEFAULT_TIMEOUT_MINUTES * 60 * 1000))
          }
        }
      });

      // Parse JSON strings to objects
      const sessions: Session[] = sessionRecords.map((record: any) => ({
        id: record.id,
        userId: record.userId,
        createdAt: record.createdAt,
        lastActiveAt: record.lastActiveAt,
        activeWorkspaceId: record.activeWorkspaceId,
        config: parseJsonString(record.config, { timeoutMinutes: this.DEFAULT_TIMEOUT_MINUTES }),
        metadata: parseJsonString(record.metadata, {})
      }));

      return sessions;
    } catch (error) {
      logger.error(`Failed to get active sessions for user ${userId}`, error);
      return []; // Return empty array on error
    }
  }

  /**
   * Terminate an existing session
   * @param sessionId The ID of the session to terminate
   * @returns True if successfully terminated
   */
  async terminateSession(sessionId: string): Promise<boolean> {
    try {
      // Remove from DB
      await db.sessions.delete({
        where: { id: sessionId }
      });

      // Remove from cache
      await redisClient.del(`${this.SESSION_CACHE_PREFIX}${sessionId}`);

      logger.info(`Terminated session ${sessionId}`);
      return true;
    } catch (error) {
      logger.error(`Failed to terminate session ${sessionId}`, error);
      return false;
    }
  }

  /**
   * Validate if a session is active and valid
   * @param sessionId The ID of the session to validate
   * @returns True if the session is valid
   */
  async validateSession(sessionId: string): Promise<boolean> {
    try {
      const session = await this.getSession(sessionId);

      if (!session) {
        return false;
      }

      // Check if session has expired
      const now = new Date();
      const lastActive = new Date(session.lastActiveAt);
      const timeoutMs = session.config.timeoutMinutes * 60 * 1000;

      if (now.getTime() - lastActive.getTime() > timeoutMs) {
        // Session has expired, terminate it
        await this.terminateSession(sessionId);
        return false;
      }

      return true;
    } catch (error) {
      logger.error(`Failed to validate session ${sessionId}`, error);
      return false;
    }
  }

  /**
   * Update session metadata or configuration
   * @param sessionId The ID of the session to update
   * @param updates The updates to apply
   * @returns The updated session
   */
  async updateSession(sessionId: string, updates: Partial<SessionConfig> & { metadata?: Record<string, any> }): Promise<Session> {
    try {
      const session = await this.getSession(sessionId);

      if (!session) {
        throw new Error(`Session ${sessionId} not found`);
      }

      // Update the session
      const updatedSession: Session = {
        ...session,
        lastActiveAt: new Date(),
        config: {
          ...session.config,
          ...updates
        },
        metadata: {
          ...session.metadata,
          ...(updates.metadata || {})
        }
      };

      // Update in DB with JSON serialization
      await db.sessions.update({
        where: { id: sessionId },
        data: {
          lastActiveAt: updatedSession.lastActiveAt,
          config: stringifyJson(updatedSession.config),     // Convert to JSON string
          metadata: stringifyJson(updatedSession.metadata)  // Convert to JSON string
        }
      });

      // Update in cache
      await this.cacheSession(updatedSession);

      return updatedSession;
    } catch (error) {
      logger.error(`Failed to update session ${sessionId}`, error);
      throw new Error(`Failed to update session: ${(error as Error).message}`);
    }
  }

  /**
   * Set the active workspace for a session
   * @param sessionId The ID of the session
   * @param workspaceId The ID of the workspace to set as active
   * @returns The updated session
   */
  async setActiveWorkspace(sessionId: string, workspaceId: string): Promise<Session> {
    try {
      const session = await this.getSession(sessionId);

      if (!session) {
        throw new Error(`Session ${sessionId} not found`);
      }

      // Verify workspace exists and belongs to user
      const workspace = await db.workspaces.findFirst({
        where: {
          id: workspaceId,
          userId: session.userId
        }
      });

      if (!workspace) {
        throw new Error(`Workspace ${workspaceId} not found or not accessible`);
      }

      // Update session with new active workspace
      const updatedSession: Session = {
        ...session,
        activeWorkspaceId: workspaceId,
        lastActiveAt: new Date()
      };

      // Update in DB
      await db.sessions.update({
        where: { id: sessionId },
        data: {
          activeWorkspaceId: workspaceId,
          lastActiveAt: updatedSession.lastActiveAt
        }
      });

      // Update in cache
      await this.cacheSession(updatedSession);

      return updatedSession;
    } catch (error) {
      logger.error(`Failed to set active workspace for session ${sessionId}`, error);
      throw new Error(`Failed to set active workspace: ${(error as Error).message}`);
    }
  }

  /**
   * Cache a session for fast access
   * @param session The session to cache
   * @private
   */
  private async cacheSession(session: Session): Promise<void> {
    const cacheKey = `${this.SESSION_CACHE_PREFIX}${session.id}`;
    const ttlSeconds = session.config.timeoutMinutes * 60;

    await redisClient.set(
      cacheKey,
      JSON.stringify(session),
      'EX',
      ttlSeconds
    );
  }
}
