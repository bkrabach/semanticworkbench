/**
 * Implementation of the Security Manager component for Cortex Core
 */

import { v4 as uuidv4 } from 'uuid';
import { logger } from '../utils/logger';
import { db } from '../database/connection';
import { redisClient } from '../cache/redis';
import { createHash, randomBytes, createCipheriv, createDecipheriv } from 'crypto';
import jwt from 'jsonwebtoken';
import { ConfidentialClientApplication } from '@azure/msal-node';
import { stringifyJson, parseJsonString, parseStringArray } from '../utils/json-helpers';

export interface UserCredentials {
  type: "password" | "api_key" | "oauth" | "msal";
  identifier: string;
  secret?: string;
  provider?: string;
}

export interface AuthResult {
  success: boolean;
  userId?: string;
  token?: string;
  expiresAt?: Date;
  error?: string;
}

export interface VerificationResult {
  valid: boolean;
  userId?: string;
  scopes?: string[];
  error?: string;
}

export interface ApiKey {
  key: string;
  userId: string;
  scopes: string[];
  createdAt: Date;
  expiresAt?: Date;
}

export class SecurityManager {
  private readonly JWT_SECRET: string;
  private readonly ENCRYPTION_KEY: Buffer;
  private readonly ENCRYPTION_IV: Buffer;
  private readonly TOKEN_EXPIRY = 24 * 60 * 60; // 24 hours in seconds
  private readonly API_KEY_PREFIX = 'sk-';
  private readonly TOKEN_BLACKLIST_PREFIX = 'blacklist:token:';
  private readonly msalClient?: ConfidentialClientApplication;

  constructor(config: {
    jwtSecret: string;
    encryptionKey: string;
    msalConfig?: {
      clientId: string;
      clientSecret: string;
      authority: string;
    }
  }) {
    this.JWT_SECRET = config.jwtSecret;

    // Derive encryption key and IV from the provided key
    const hash = createHash('sha256').update(config.encryptionKey).digest();
    this.ENCRYPTION_KEY = hash.slice(0, 32);
    this.ENCRYPTION_IV = hash.slice(0, 16);

    // Initialize MSAL client if config is provided
    if (config.msalConfig) {
      this.msalClient = new ConfidentialClientApplication({
        auth: {
          clientId: config.msalConfig.clientId,
          clientSecret: config.msalConfig.clientSecret || '',
          authority: config.msalConfig.authority
        }
      });
    }
  }

  /**
   * Authenticate a user and create a session token
   * @param credentials The user credentials
   * @returns Authentication result
   */
  async authenticate(credentials: UserCredentials): Promise<AuthResult> {
    try {
      logger.info(`Authentication attempt for ${credentials.identifier} using ${credentials.type}`);

      let userId: string = '';

      switch (credentials.type) {
        case 'password':
          const authResult = await this.authenticateWithPassword(
            credentials.identifier,
            credentials.secret || ''
          );

          if (!authResult.success) {
            return authResult;
          }

          userId = authResult.userId || '';
          break;

        case 'api_key':
          const apiKeyResult = await this.authenticateWithApiKey(credentials.identifier);

          if (!apiKeyResult.success) {
            return apiKeyResult;
          }

          userId = apiKeyResult.userId || '';
          break;

        case 'oauth':
          return {
            success: false,
            error: 'OAuth authentication not implemented in MVP'
          };

        case 'msal':
          if (!this.msalClient) {
            return {
              success: false,
              error: 'MSAL not configured'
            };
          }

          const msalResult = await this.authenticateWithMSAL(
            credentials.identifier,
            credentials.secret
          );

          if (!msalResult.success) {
            return msalResult;
          }

          userId = msalResult.userId || '';
          break;

        default:
          return {
            success: false,
            error: `Unsupported authentication type: ${credentials.type}`
          };
      }

      // Generate JWT token
      const expiresAt = new Date();
      expiresAt.setSeconds(expiresAt.getSeconds() + this.TOKEN_EXPIRY);

      const token = jwt.sign(
        {
          sub: userId,
          exp: Math.floor(expiresAt.getTime() / 1000)
        },
        this.JWT_SECRET
      );

      logger.info(`User ${userId} authenticated successfully`);

      return {
        success: true,
        userId,
        token,
        expiresAt
      };
    } catch (error) {
      logger.error('Authentication failed', error);
      return {
        success: false,
        error: 'Authentication failed'
      };
    }
  }

  /**
   * Verify if a token is valid
   * @param token The token to verify
   * @returns Verification result
   */
  async verifyToken(token: string): Promise<VerificationResult> {
    try {
      // Check if token is blacklisted
      const isBlacklisted = await redisClient.exists(`${this.TOKEN_BLACKLIST_PREFIX}${token}`);
      if (isBlacklisted) {
        return {
          valid: false,
          error: 'Token has been revoked'
        };
      }

      // Verify JWT token
      const decoded = jwt.verify(token, this.JWT_SECRET) as { sub: string; exp: number };

      return {
        valid: true,
        userId: decoded.sub,
        scopes: [] // JWT tokens don't have scopes in MVP
      };
    } catch (error) {
      logger.error('Token verification failed', error);

      if ((error as Error).name === 'TokenExpiredError') {
        return {
          valid: false,
          error: 'Token has expired'
        };
      }

      return {
        valid: false,
        error: 'Invalid token'
      };
    }
  }

  /**
   * Generate an API key for programmatic access
   * @param userId The ID of the user
   * @param scope The scopes for the API key
   * @param expiry Optional expiry date
   * @returns The generated API key
   */
  async generateApiKey(userId: string, scopes: string[], expiry?: Date): Promise<ApiKey> {
    try {
      logger.info(`Generating API key for user ${userId}`);

      // Generate random key
      const randomKey = randomBytes(32).toString('base64').replace(/[+/=]/g, '');
      const key = `${this.API_KEY_PREFIX}${randomKey}`;

      const now = new Date();

      // Store API key in database
      await db.apiKeys.create({
        data: {
          key: await this.encrypt(key), // Store encrypted version
          userId,
          scopesJson: stringifyJson(scopes), // Store as JSON array string
          createdAt: now,
          expiresAt: expiry
        }
      });

      logger.info(`API key generated for user ${userId}`);

      return {
        key,
        userId,
        scopes,
        createdAt: now,
        expiresAt: expiry
      };
    } catch (error) {
      logger.error(`Failed to generate API key for user ${userId}`, error);
      throw new Error(`Failed to generate API key: ${(error as Error).message}`);
    }
  }

  /**
   * Validate access permissions for a specific resource
   * @param userId The ID of the user
   * @param resource The resource being accessed
   * @param action The action being performed
   * @returns True if access is allowed
   */
  async checkAccess(userId: string, resource: string, action: string): Promise<boolean> {
    try {
      logger.debug(`Checking access for user ${userId} to perform ${action} on ${resource}`);

      // In MVP, we implement a simple access control system
      // This would be expanded in future versions

      // Get user's permissions from database
      const user = await db.users.findUnique({
        where: { id: userId },
        include: { roles: true }
      });

      if (!user) {
        logger.warn(`User ${userId} not found when checking access`);
        return false;
      }

      // In MVP, only implement basic user roles
      const isAdmin = user.roles.some((role: any) => role.name === 'admin');

      // Admins can do anything
      if (isAdmin) {
        return true;
      }

      // Check resource-specific permissions
      if (resource.startsWith('workspace:')) {
        return this.checkWorkspaceAccess(userId, resource.split(':')[1], action);
      }

      // Default permissions - users can access basic resources
      const userAllowedActions = [
        'read_own_profile',
        'update_own_profile',
        'create_workspace',
        'list_own_workspaces'
      ];

      return userAllowedActions.includes(action);
    } catch (error) {
      logger.error(`Access check failed for user ${userId}`, error);
      return false; // Deny access on error
    }
  }

  /**
   * Encrypt sensitive data
   * @param data The data to encrypt
   * @returns The encrypted data
   */
  async encrypt(data: string): Promise<string> {
    const cipher = createCipheriv('aes-256-cbc', this.ENCRYPTION_KEY, this.ENCRYPTION_IV);
    let encrypted = cipher.update(data, 'utf8', 'hex');
    encrypted += cipher.final('hex');
    return encrypted;
  }

  /**
   * Decrypt sensitive data
   * @param encryptedData The data to decrypt
   * @returns The decrypted data
   */
  async decrypt(encryptedData: string): Promise<string> {
    const decipher = createDecipheriv('aes-256-cbc', this.ENCRYPTION_KEY, this.ENCRYPTION_IV);
    let decrypted = decipher.update(encryptedData, 'hex', 'utf8');
    decrypted += decipher.final('utf8');
    return decrypted;
  }

  /**
   * Authenticate user with password
   * @param email User email
   * @param password User password
   * @returns Authentication result
   * @private
   */
  // private async authenticateWithPassword(email: string, password: string): Promise<AuthResult> {
  //   try {
  //     // Get user from database
  //     const user = await db.users.findUnique({
  //       where: { email }
  //     });

  //     if (!user) {
  //       logger.warn(`User not found: ${email}`);
  //       return {
  //         success: false,
  //         error: 'Invalid email or password'
  //       };
  //     }

  //     // Verify password hash (this would use proper password hashing in real implementation)
  //     const passwordMatches = await this.verifyPassword(password, user.passwordHash || '');

  //     if (!passwordMatches) {
  //       logger.warn(`Invalid password for user: ${email}`);
  //       return {
  //         success: false,
  //         error: 'Invalid email or password'
  //       };
  //     }

  //     return {
  //       success: true,
  //       userId: user.id
  //     };
  //   } catch (error) {
  //     logger.error(`Password authentication failed for ${email}`, error);
  //     return {
  //       success: false,
  //       error: 'Authentication failed'
  //     };
  //   }
  // }
  /**
   * Modified authenticateWithPassword method for SecurityManager to auto-create test user
   */
  // FIXME: Remove this method and use the original authenticateWithPassword method
  private async authenticateWithPassword(email: string, password: string): Promise<AuthResult> {
    try {
      // Get user from database
      let user = await db.users.findUnique({
        where: { email }
      });

      // For development: auto-create test user if it doesn't exist
      if (!user && process.env.NODE_ENV !== 'production' &&
        email === 'test@example.com' && password === 'password') {

        // Create default test user with password hash
        const passwordHash = createHash('sha256').update(password).digest('hex');

        // Create test user
        user = await db.users.create({
          data: {
            id: uuidv4(),
            email,
            name: 'Test User',
            passwordHash: passwordHash,
            createdAt: new Date(),
            updatedAt: new Date()
          }
        });

        logger.info(`Created test user: ${email}`);

        // Create default workspace for test user
        const workspace = await db.workspaces.create({
          data: {
            id: uuidv4(),
            userId: user.id,
            name: 'Default Workspace',
            createdAt: new Date(),
            lastActiveAt: new Date(),
            config: stringifyJson({
              defaultModality: 'chat',
              sharingEnabled: false,
              retentionDays: 90
            }),
            metadata: stringifyJson({})
          }
        });

        logger.info(`Created default workspace for test user`);
      }

      if (!user) {
        logger.warn(`User not found: ${email}`);
        return {
          success: false,
          error: 'Invalid email or password'
        };
      }

      // Verify password hash
      const passwordMatches = await this.verifyPassword(password, user.passwordHash || '');

      if (!passwordMatches) {
        logger.warn(`Invalid password for user: ${email}`);
        return {
          success: false,
          error: 'Invalid email or password'
        };
      }

      return {
        success: true,
        userId: user.id
      };
    } catch (error) {
      logger.error(`Password authentication failed for ${email}`, error);
      return {
        success: false,
        error: 'Authentication failed'
      };
    }
  }

  /**
   * Authenticate user with API key
   * @param apiKey The API key
   * @returns Authentication result
   * @private
   */
  private async authenticateWithApiKey(apiKey: string): Promise<AuthResult> {
    try {
      // Find API key in database (comparing with encrypted version)
      const encryptedKey = await this.encrypt(apiKey);

      const keyRecord = await db.apiKeys.findUnique({
        where: { key: encryptedKey }
      });

      if (!keyRecord) {
        logger.warn(`API key not found: ${apiKey.substring(0, 8)}...`);
        return {
          success: false,
          error: 'Invalid API key'
        };
      }

      // Check if key has expired
      if (keyRecord.expiresAt && new Date() > new Date(keyRecord.expiresAt)) {
        logger.warn(`Expired API key used: ${apiKey.substring(0, 8)}...`);
        return {
          success: false,
          error: 'API key has expired'
        };
      }

      return {
        success: true,
        userId: keyRecord.userId
      };
    } catch (error) {
      logger.error(`API key authentication failed`, error);
      return {
        success: false,
        error: 'Authentication failed'
      };
    }
  }

  /**
   * Authenticate user with MSAL
   * @param token The MSAL token
   * @param nonce Optional nonce for verification
   * @returns Authentication result
   * @private
   */
  private async authenticateWithMSAL(token: string, nonce?: string): Promise<AuthResult> {
    try {
      if (!this.msalClient) {
        return {
          success: false,
          error: 'MSAL not configured'
        };
      }

      // Verify token with MSAL (in a real implementation, this would use proper MSAL validation)
      // This is a simplified version
      const tokenClaims = jwt.decode(token) as any;

      if (!tokenClaims) {
        return {
          success: false,
          error: 'Invalid token'
        };
      }

      // Get or create user based on email claim
      const email = tokenClaims.preferred_username || tokenClaims.email;

      if (!email) {
        return {
          success: false,
          error: 'Token does not contain user information'
        };
      }

      // Find or create user in database
      let user = await db.users.findUnique({
        where: { email }
      });

      if (!user) {
        // Create new user
        user = await db.users.create({
          data: {
            id: uuidv4(),
            email,
            name: tokenClaims.name || email,
            createdAt: new Date(),
            lastLoginAt: new Date()
          }
        });

        logger.info(`Created new user from MSAL login: ${email}`);
      } else {
        // Update last login time
        await db.users.update({
          where: { id: user.id },
          data: { lastLoginAt: new Date() }
        });
      }

      return {
        success: true,
        userId: user.id
      };
    } catch (error) {
      logger.error(`MSAL authentication failed`, error);
      return {
        success: false,
        error: 'Authentication failed'
      };
    }
  }

  /**
   * Verify a password against a hash
   * @param password The password to verify
   * @param hash The hash to compare against
   * @returns True if password matches
   * @private
   */
  private async verifyPassword(password: string, hash: string): Promise<boolean> {
    // In a real implementation, this would use proper password hashing (bcrypt, etc.)
    // For MVP, using a simple hash
    const passwordHash = createHash('sha256').update(password).digest('hex');
    return passwordHash === hash;
  }

  /**
   * Check access to a specific workspace
   * @param userId The user ID
   * @param workspaceId The workspace ID
   * @param action The action being performed
   * @returns True if access is allowed
   * @private
   */
  private async checkWorkspaceAccess(userId: string, workspaceId: string, action: string): Promise<boolean> {
    try {
      // Get workspace from database
      const workspace = await db.workspaces.findUnique({
        where: { id: workspaceId }
      });

      if (!workspace) {
        return false;
      }

      // Check if user owns the workspace
      const isOwner = workspace.userId === userId;

      if (isOwner) {
        // Owners can do anything with their workspaces
        return true;
      }

      // Parse workspace config
      const workspaceConfig = parseJsonString(workspace.config, {
        sharingEnabled: false
      });

      // Check if workspace is shared with user
      if (workspaceConfig.sharingEnabled) {
        const sharedWith = await db.workspaceSharing.findFirst({
          where: {
            workspaceId,
            userId
          }
        });

        if (sharedWith) {
          // Parse permissions from JSON string
          const permissions = parseStringArray(sharedWith.permissionsJson);

          // Check specific permissions on the sharing
          switch (action) {
            case 'read_workspace':
              return true; // All shared users can read

            case 'add_conversation':
              return permissions.includes('write');

            case 'update_workspace':
            case 'delete_workspace':
              return permissions.includes('admin');

            default:
              return false;
          }
        }
      }

      // No access
      return false;
    } catch (error) {
      logger.error(`Workspace access check failed`, error);
      return false; // Deny access on error
    }
  }
}
