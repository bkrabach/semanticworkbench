/**
 * Configuration for Cortex Core
 */

import dotenv from 'dotenv';
import path from 'path';

// Load environment variables from .env file
dotenv.config();

export interface DatabaseConfig {
  url: string;
}

export interface CacheConfig {
  host: string;
  port: number;
  password?: string;
  ttl: number;
}

export interface SecurityConfig {
  jwtSecret: string;
  encryptionKey: string;
  tokenExpirySeconds: number;
  msalConfig?: {
    clientId: string;
    clientSecret: string;
    authority: string;
  };
}

export interface ServerConfig {
  port: number;
  host: string;
  logLevel: string;
}

export interface MemoryConfig {
  type: 'whiteboard' | 'jake';
  retentionDays: number;
  maxItems: number;
}

export interface MCPEndpoint {
  name: string;
  endpoint: string;
  type: string;
}

export interface MCPConfig {
  endpoints: MCPEndpoint[];
}

export interface CoreConfig {
  database: DatabaseConfig;
  cache: CacheConfig;
  security: SecurityConfig;
  server: ServerConfig;
  memory: MemoryConfig;
  mcp: MCPConfig;
}

/**
 * Get configuration based on environment
 */
export function getConfig(): CoreConfig {
  const env = process.env.NODE_ENV || 'development';

  // Default configuration
  const config: CoreConfig = {
    database: {
      url: process.env.DATABASE_URL || 'file:./prisma/dev.db'
    },
    cache: {
      host: process.env.REDIS_HOST || 'localhost',
      port: parseInt(process.env.REDIS_PORT || '6379', 10),
      password: process.env.REDIS_PASSWORD,
      ttl: parseInt(process.env.REDIS_TTL || '3600', 10)
    },
    security: {
      jwtSecret: process.env.JWT_SECRET || 'default-jwt-secret-change-me',
      encryptionKey: process.env.ENCRYPTION_KEY || 'default-encryption-key-change-me',
      tokenExpirySeconds: parseInt(process.env.TOKEN_EXPIRY_SECONDS || '86400', 10),
      msalConfig: process.env.MSAL_CLIENT_ID ? {
        clientId: process.env.MSAL_CLIENT_ID,
        clientSecret: process.env.MSAL_CLIENT_SECRET || '',
        authority: process.env.MSAL_AUTHORITY || 'https://login.microsoftonline.com/common'
      } : undefined
    },
    server: {
      port: parseInt(process.env.PORT || '4000', 10),
      host: process.env.HOST || 'localhost',
      logLevel: process.env.LOG_LEVEL || 'info'
    },
    memory: {
      type: (process.env.MEMORY_TYPE as 'whiteboard' | 'jake') || 'whiteboard',
      retentionDays: parseInt(process.env.MEMORY_RETENTION_DAYS || '90', 10),
      maxItems: parseInt(process.env.MEMORY_MAX_ITEMS || '10000', 10)
    },
    mcp: {
      endpoints: []
    }
  };

  // Load MCP endpoints from environment variables
  if (process.env.MCP_ENDPOINTS) {
    try {
      config.mcp.endpoints = JSON.parse(process.env.MCP_ENDPOINTS);
    } catch (error) {
      console.error('Failed to parse MCP_ENDPOINTS environment variable:', error);
    }
  }

  // Add individual MCP endpoints if configured
  // Format: MCP_ENDPOINT_name=endpoint_url|type
  // Example: MCP_ENDPOINT_VSCODE=http://localhost:5000|vscode
  Object.keys(process.env).forEach(key => {
    if (key.startsWith('MCP_ENDPOINT_')) {
      const name = key.replace('MCP_ENDPOINT_', '');
      const value = process.env[key] || '';
      const [endpoint, type] = value.split('|');

      if (endpoint && type) {
        config.mcp.endpoints.push({
          name,
          endpoint,
          type
        });
      }
    }
  });

  // Environment-specific overrides
  if (env === 'production') {
    // Ensure secure secrets in production
    if (
      config.security.jwtSecret === 'default-jwt-secret-change-me' ||
      config.security.encryptionKey === 'default-encryption-key-change-me'
    ) {
      throw new Error('Production environment requires secure JWT secret and encryption key');
    }
  } else if (env === 'test') {
    // Test-specific configuration
    config.database.url = 'file:./prisma/test.db';
  }

  return config;
}

export default getConfig();
