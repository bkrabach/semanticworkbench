/**
 * Model Context Protocol (MCP) client/server utility for Cortex Core
 * This is a simplified implementation of the MCP protocol for the MVP
 */

import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';
import { logger } from './logger';

/**
 * MCP message types
 */
export enum MCPMessageType {
  REQUEST = 'request',
  RESPONSE = 'response',
  NOTIFICATION = 'notification'
}

/**
 * MCP message interface
 */
export interface MCPMessage {
  jsonrpc: '2.0';
  id?: string | number;
  method?: string;
  params?: any;
  result?: any;
  error?: {
    code: number;
    message: string;
    data?: any;
  };
}

/**
 * MCP connection interface
 */
export interface MCPConnection {
  clientName: string;
  clientVersion: string;
  endpoint: string;
  capabilities: Record<string, any>;
  send(message: MCPMessage): Promise<void>;
  close(): Promise<void>;
}

/**
 * MCP server implementation
 */
export class MCPServer extends EventEmitter {
  private readonly name: string;
  private readonly version: string;
  private readonly capabilities: Record<string, any>;
  private readonly connections: Map<string, MCPConnection> = new Map();
  private readonly requestHandlers: Map<string, (params: any) => Promise<any>> = new Map();
  private readonly notificationHandlers: Map<string, (params: any) => Promise<void>> = new Map();
  private isRunning = false;

  /**
   * Create a new MCP server
   * @param config Server configuration
   */
  constructor(config: {
    name: string;
    version: string;
    capabilities: Record<string, any>;
  }) {
    super();
    this.name = config.name;
    this.version = config.version;
    this.capabilities = config.capabilities;

    // Register initialize handler
    this.registerRequestHandler('initialize', this.handleInitialize.bind(this));

    // Register initialized notification handler
    this.registerNotificationHandler('initialized', this.handleInitialized.bind(this));
  }

  /**
   * Start the MCP server
   */
  async start(): Promise<void> {
    logger.info('Starting MCP server');
    this.isRunning = true;
  }

  /**
   * Stop the MCP server
   */
  async stop(): Promise<void> {
    logger.info('Stopping MCP server');

    // Close all connections
    const closePromises = Array.from(this.connections.values()).map(connection => {
      return connection.close();
    });

    await Promise.all(closePromises);
    this.connections.clear();
    this.isRunning = false;
  }

  /**
   * Register a request handler
   * @param method The method name
   * @param handler The handler function
   */
  registerRequestHandler(method: string, handler: (params: any) => Promise<any>): void {
    this.requestHandlers.set(method, handler);
    logger.debug(`Registered request handler for method: ${method}`);
  }

  /**
   * Register a notification handler
   * @param method The method name
   * @param handler The handler function
   */
  registerNotificationHandler(method: string, handler: (params: any) => Promise<void>): void {
    this.notificationHandlers.set(method, handler);
    logger.debug(`Registered notification handler for method: ${method}`);
  }

  /**
   * Handle a new client connection
   * @param connection The client connection
   */
  async handleConnection(connection: MCPConnection): Promise<void> {
    logger.info(`New MCP connection from ${connection.clientName}`);

    // Generate connection ID
    const connectionId = uuidv4();

    // Store connection
    this.connections.set(connectionId, connection);

    // Emit connection event
    this.emit('connection', {
      connectionId,
      clientName: connection.clientName,
      clientVersion: connection.clientVersion,
      endpoint: connection.endpoint,
      capabilities: connection.capabilities
    });
  }

  /**
   * Handle a client disconnection
   * @param connectionId The connection ID
   */
  async handleDisconnection(connectionId: string): Promise<void> {
    logger.info(`MCP client disconnected: ${connectionId}`);

    // Remove connection
    this.connections.delete(connectionId);

    // Emit disconnection event
    this.emit('disconnection', { connectionId });
  }

  /**
   * Handle incoming message from a client
   * @param connectionId The connection ID
   * @param message The message
   */
  async handleMessage(connectionId: string, message: MCPMessage): Promise<void> {
    logger.debug(`Received MCP message from ${connectionId}`, message);

    // Get connection
    const connection = this.connections.get(connectionId);
    if (!connection) {
      logger.warn(`Received message from unknown connection: ${connectionId}`);
      return;
    }

    try {
      // Handle based on message type
      if (message.method !== undefined && message.id !== undefined) {
        // Request
        await this.handleRequest(connection, message);
      } else if (message.method !== undefined && message.id === undefined) {
        // Notification
        await this.handleNotification(connection, message);
      } else if (message.id !== undefined && (message.result !== undefined || message.error !== undefined)) {
        // Response (we don't handle responses in the server)
        logger.warn(`Received unexpected response message from ${connectionId}`);
      } else {
        // Invalid message
        logger.warn(`Received invalid MCP message from ${connectionId}`);
      }
    } catch (error) {
      logger.error(`Error handling MCP message from ${connectionId}`, error);
    }
  }

  /**
   * Handle initialize request
   * @param params Initialize parameters
   * @returns Initialize result
   * @private
   */
  private async handleInitialize(params: any): Promise<any> {
    logger.info(`Initialize request with protocol version ${params.protocolVersion}`);

    // Validate protocol version
    if (params.protocolVersion !== '0.1.0') {
      throw new Error(`Unsupported protocol version: ${params.protocolVersion}`);
    }

    // Return server information
    return {
      serverInfo: {
        name: this.name,
        version: this.version
      },
      capabilities: this.capabilities,
      protocolVersion: '0.1.0'
    };
  }

  /**
   * Handle initialized notification
   * @param params Initialized parameters
   * @private
   */
  private async handleInitialized(params: any): Promise<void> {
    logger.info('Received initialized notification');

    // Nothing to do here for MVP
  }

  /**
   * Handle a request message
   * @param connection The client connection
   * @param message The request message
   * @private
   */
  private async handleRequest(connection: MCPConnection, message: MCPMessage): Promise<void> {
    const method = message.method || '';
    const params = message.params || {};
    const id = message.id;

    logger.debug(`Handling request for method: ${method}`);

    try {
      // Find handler
      const handler = this.requestHandlers.get(method);

      if (!handler) {
        // Method not found
        await connection.send({
          jsonrpc: '2.0',
          id,
          error: {
            code: -32601,
            message: `Method not found: ${method}`
          }
        });
        return;
      }

      // Call handler
      const result = await handler(params);

      // Send response
      await connection.send({
        jsonrpc: '2.0',
        id,
        result
      });
    } catch (error) {
      // Send error response
      await connection.send({
        jsonrpc: '2.0',
        id,
        error: {
          code: -32603,
          message: (error as Error).message || 'Internal error',
          data: (error as Error).stack
        }
      });
    }
  }

  /**
   * Handle a notification message
   * @param connection The client connection
   * @param message The notification message
   * @private
   */
  private async handleNotification(connection: MCPConnection, message: MCPMessage): Promise<void> {
    const method = message.method || '';
    const params = message.params || {};

    logger.debug(`Handling notification for method: ${method}`);

    try {
      // Find handler
      const handler = this.notificationHandlers.get(method);

      if (!handler) {
        // No handler, but that's okay for notifications
        return;
      }

      // Call handler
      await handler(params);
    } catch (error) {
      // Log error but don't send response for notifications
      logger.error(`Error handling notification for method: ${method}`, error);
    }
  }
}

/**
 * MCP client implementation
 */
export class MCPClient extends EventEmitter {
  private readonly connection: MCPConnection;
  private readonly pendingRequests: Map<string | number, {
    resolve: (result: any) => void;
    reject: (error: Error) => void;
  }> = new Map();

  /**
   * Create a new MCP client
   * @param connection The connection to the server
   */
  constructor(connection: MCPConnection) {
    super();
    this.connection = connection;
  }

  /**
   * Send a request to the server
   * @param method The method name
   * @param params The parameters
   * @returns The result
   */
  async sendRequest(method: string, params?: any): Promise<any> {
    const id = uuidv4();

    // Create message
    const message: MCPMessage = {
      jsonrpc: '2.0',
      id,
      method,
      params
    };

    // Create promise for response
    const responsePromise = new Promise<any>((resolve, reject) => {
      this.pendingRequests.set(id, { resolve, reject });
    });

    // Send message
    await this.connection.send(message);

    // Wait for response
    return responsePromise;
  }

  /**
   * Send a notification to the server
   * @param method The method name
   * @param params The parameters
   */
  async sendNotification(method: string, params?: any): Promise<void> {
    // Create message
    const message: MCPMessage = {
      jsonrpc: '2.0',
      method,
      params
    };

    // Send message
    await this.connection.send(message);
  }

  /**
   * Handle a message from the server
   * @param message The message
   */
  async handleMessage(message: MCPMessage): Promise<void> {
    logger.debug(`Received MCP message from server`, message);

    try {
      // Handle based on message type
      if (message.id !== undefined && (message.result !== undefined || message.error !== undefined)) {
        // Response
        await this.handleResponse(message);
      } else if (message.method !== undefined && message.id !== undefined) {
        // Request
        await this.handleRequest(message);
      } else if (message.method !== undefined && message.id === undefined) {
        // Notification
        await this.handleNotification(message);
      } else {
        // Invalid message
        logger.warn(`Received invalid MCP message from server`);
      }
    } catch (error) {
      logger.error(`Error handling MCP message from server`, error);
    }
  }

  /**
   * Handle a response message
   * @param message The response message
   * @private
   */
  private async handleResponse(message: MCPMessage): Promise<void> {
    const id = message.id;

    if (id === undefined) {
      return; // Should never happen if we're in this method
    }

    // Find pending request
    const pendingRequest = this.pendingRequests.get(id);

    if (!pendingRequest) {
      logger.warn(`Received response for unknown request: ${id}`);
      return;
    }

    // Remove from pending requests
    this.pendingRequests.delete(id);

    // Resolve or reject promise
    if (message.error) {
      pendingRequest.reject(new Error(message.error.message));
    } else {
      pendingRequest.resolve(message.result);
    }
  }

  /**
   * Handle a request message
   * @param message The request message
   * @private
   */
  private async handleRequest(message: MCPMessage): Promise<void> {
    const method = message.method || '';
    const params = message.params || {};
    const id = message.id;

    if (id === undefined) {
      return; // Should never happen if we're in this method
    }

    logger.debug(`Handling request from server for method: ${method}`);

    try {
      // Emit request event
      const result = await this.emit('request', { method, params });

      // Send response
      await this.connection.send({
        jsonrpc: '2.0',
        id,
        result
      });
    } catch (error) {
      // Send error response
      await this.connection.send({
        jsonrpc: '2.0',
        id,
        error: {
          code: -32603,
          message: (error as Error).message || 'Internal error',
          data: (error as Error).stack
        }
      });
    }
  }

  /**
   * Handle a notification message
   * @param message The notification message
   * @private
   */
  private async handleNotification(message: MCPMessage): Promise<void> {
    const method = message.method || '';
    const params = message.params || {};

    logger.debug(`Handling notification from server for method: ${method}`);

    try {
      // Emit notification event
      this.emit('notification', { method, params });
    } catch (error) {
      // Log error but don't send response for notifications
      logger.error(`Error handling notification from server for method: ${method}`, error);
    }
  }
}
