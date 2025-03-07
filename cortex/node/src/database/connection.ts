/**
 * Database connection utility for Cortex Core
 */

import { PrismaClient } from '@prisma/client';
import config from '../config';
import { logger } from '../utils/logger';

// Create Prisma client instance
export const prisma = new PrismaClient({
  log: config.server.logLevel === 'debug' ? ['query', 'info', 'warn', 'error'] : ['warn', 'error'],
  datasources: {
    db: {
      url: config.database.url
    }
  }
});

/**
 * Connect to database
 */
export async function connectDatabase(): Promise<void> {
  try {
    logger.info('Connecting to database...');
    await prisma.$connect();
    logger.info('Database connection established');
  } catch (error) {
    logger.error('Failed to connect to database', error);
    throw error;
  }
}

/**
 * Disconnect from database
 */
export async function disconnectDatabase(): Promise<void> {
  try {
    logger.info('Disconnecting from database...');
    await prisma.$disconnect();
    logger.info('Database connection closed');
  } catch (error) {
    logger.error('Failed to disconnect from database', error);
    throw error;
  }
}

/**
 * Database access object with typed collections
 */
export const db = {
  // User-related collections
  users: prisma.user,
  sessions: prisma.session,
  apiKeys: prisma.apiKey,

  // Workspace-related collections
  workspaces: prisma.workspace,
  conversations: prisma.conversation,
  workspaceSharing: prisma.workspaceSharing,

  // Integration-related collections
  integrations: prisma.integration,

  // Memory-related collections
  memoryItems: prisma.memoryItem,

  // Task-related collections
  domainExpertTasks: prisma.domainExpertTask,

  // Raw access to Prisma client
  prisma
};

// Export for use in other modules
export default db;
