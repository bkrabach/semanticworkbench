/**
 * Main entry point for Cortex Core
 */

import { logger } from './utils/logger';
import config from './config';
import { CortexAPI } from './api';
import { connectDatabase } from './database/connection';
import { connectRedis } from './cache/redis';

/**
 * Bootstrap the application
 */
async function bootstrap() {
  try {
    logger.info('Starting Cortex Core');
    
    // Connect to database
    logger.info('Connecting to database');
    await connectDatabase();
    
    // Connect to Redis
    logger.info('Connecting to Redis');
    await connectRedis();
    
    // Initialize API
    const api = new CortexAPI(config.server.port);
    await api.initialize();
    
    logger.info(`Cortex Core started successfully on port ${config.server.port}`);
    
    // Handle shutdown gracefully
    process.on('SIGTERM', shutdown);
    process.on('SIGINT', shutdown);
    
  } catch (error) {
    logger.error('Failed to start Cortex Core', error);
    process.exit(1);
  }
}

/**
 * Graceful shutdown
 */
async function shutdown() {
  logger.info('Shutting down Cortex Core');
  
  try {
    // Close database connection
    await disconnectDatabase();
    
    // Close Redis connection
    await disconnectRedis();
    
    logger.info('Shutdown complete');
    process.exit(0);
  } catch (error) {
    logger.error('Error during shutdown', error);
    process.exit(1);
  }
}

// External functions to be implemented
async function disconnectDatabase() {
  // Implementation would go here
}

async function disconnectRedis() {
  // Implementation would go here
}

// Start the application
bootstrap();
