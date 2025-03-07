/**
 * Implementation of the Integration Hub component for Cortex Core
 */

import { v4 as uuidv4 } from 'uuid';
import { logger } from '../utils/logger';
import { db } from '../database/connection';
import { MCPServer, MCPClient } from '../utils/mcp';
import { EventEmitter } from 'events';
import { stringifyJson, parseJsonString, parseStringArray } from '../utils/json-helpers';
import config from '../config';

export interface Integration {
  id: string;
  name: string;
  type: "vscode" | "m365" | "browser" | "other";
  connectionDetails: ConnectionDetails;
  capabilities: string[];
  status: "connected" | "disconnected" | "error";
  lastActive: Date;
}

export interface ConnectionDetails {
  protocol: "mcp" | "rest" | "websocket";
  endpoint: string;
  authToken?: string;
  metadata?: Record<string, any>;
}

export class IntegrationHub extends EventEmitter {
  private readonly integrations: Map<string, Integration> = new Map();
  private readonly mcpClients: Map<string, MCPClient> = new Map();
  private readonly mcpServer: MCPServer;

  constructor() {
    super();

    // Initialize MCP server
    this.mcpServer = new MCPServer({
      name: 'cortex-core',
      version: '1.0.0',
      capabilities: {
        resources: {},
        tools: {},
        prompts: {}
      }
    });

    // Set up MCP server event handlers
    this.mcpServer.on('connection', this.handleMCPConnection.bind(this));
    this.mcpServer.on('disconnection', this.handleMCPDisconnection.bind(this));
  }

  /**
   * Initialize the Integration Hub
   */
  async initialize(): Promise<void> {
    try {
      logger.info('Initializing Integration Hub');

      // Start MCP server
      await this.mcpServer.start();

      // Load previously registered integrations from DB
      const storedIntegrations = await db.integrations.findMany();

      for (const integration of storedIntegrations) {
        // Parse JSON strings into proper objects
        this.integrations.set(integration.id, {
          id: integration.id,
          name: integration.name,
          type: integration.type as "vscode" | "m365" | "browser" | "other",
          connectionDetails: parseJsonString(integration.connectionDetails, {
            protocol: 'mcp',
            endpoint: ''
          }),
          capabilities: parseStringArray(integration.capabilitiesJson),
          status: 'disconnected', // All stored integrations start as disconnected
          lastActive: new Date(integration.lastActive)
        });
      }

      logger.info(`Loaded ${storedIntegrations.length} integrations from database`);

      // Register configured MCP endpoints from config
      if (config.mcp && config.mcp.endpoints && config.mcp.endpoints.length > 0) {
        logger.info(`Registering ${config.mcp.endpoints.length} configured MCP endpoints`);

        for (const endpoint of config.mcp.endpoints) {
          try {
            logger.info(`Registering MCP endpoint: ${endpoint.name} at ${endpoint.endpoint}`);

            // Check if this endpoint is already registered
            const existingIntegration = Array.from(this.integrations.values()).find(
              integration =>
                integration.connectionDetails.endpoint === endpoint.endpoint &&
                integration.name === endpoint.name
            );

            if (existingIntegration) {
              logger.info(`MCP endpoint ${endpoint.name} already registered with ID ${existingIntegration.id}`);
              continue;
            }

            // Register new integration
            await this.registerIntegration({
              name: endpoint.name,
              type: endpoint.type as "vscode" | "m365" | "browser" | "other",
              connectionDetails: {
                protocol: 'mcp',
                endpoint: endpoint.endpoint
              },
              capabilities: []
            });

            logger.info(`Successfully registered MCP endpoint: ${endpoint.name}`);
          } catch (error) {
            logger.error(`Failed to register MCP endpoint: ${endpoint.name}`, error);
          }
        }
      } else {
        logger.info('No MCP endpoints configured');
      }
    } catch (error) {
      logger.error('Failed to initialize Integration Hub', error);
      throw new Error(`Failed to initialize Integration Hub: ${(error as Error).message}`);
    }
  }

  /**
   * Register a new external integration
   * @param integration The integration to register
   */
  async registerIntegration(integration: Omit<Integration, 'id' | 'status' | 'lastActive'>): Promise<Integration> {
    try {
      logger.info(`Registering new integration: ${integration.name} (${integration.type})`);

      const newIntegration: Integration = {
        ...integration,
        id: uuidv4(),
        status: 'disconnected',
        lastActive: new Date()
      };

      // Save to database with JSON serialization
      await db.integrations.create({
        data: {
          id: newIntegration.id,
          name: newIntegration.name,
          type: newIntegration.type,
          connectionDetails: stringifyJson(newIntegration.connectionDetails),  // Convert to JSON string
          capabilitiesJson: stringifyJson(newIntegration.capabilities),        // Convert to JSON string
          lastActive: newIntegration.lastActive
        }
      });

      // Add to in-memory map
      this.integrations.set(newIntegration.id, newIntegration);

      logger.info(`Successfully registered integration with ID: ${newIntegration.id}`);
      return newIntegration;
    } catch (error) {
      logger.error(`Failed to register integration: ${integration.name}`, error);
      throw new Error(`Failed to register integration: ${(error as Error).message}`);
    }
  }

  /**
   * Get an integration by ID
   * @param integrationId The ID of the integration to retrieve
   * @returns The integration or null if not found
   */
  async getIntegration(integrationId: string): Promise<Integration | null> {
    try {
      return this.integrations.get(integrationId) || null;
    } catch (error) {
      logger.error(`Failed to get integration: ${integrationId}`, error);
      return null;
    }
  }

  /**
   * Forward a request to an external integration
   * @param integrationId The ID of the integration to forward to
   * @param request The request to forward
   * @returns The response from the integration
   */
  async forwardRequest(integrationId: string, request: any): Promise<any> {
    try {
      logger.info(`Forwarding request to integration: ${integrationId}`);

      const integration = await this.getIntegration(integrationId);
      if (!integration) {
        throw new Error(`Integration not found: ${integrationId}`);
      }

      if (integration.status !== 'connected') {
        throw new Error(`Integration is not connected: ${integrationId}`);
      }

      // Handle based on protocol
      if (integration.connectionDetails.protocol === 'mcp') {
        // Get MCP client
        const client = this.mcpClients.get(integrationId);
        if (!client) {
          throw new Error(`MCP client not found for integration: ${integrationId}`);
        }

        // Forward via MCP
        const response = await client.sendRequest(request.method, request.params);

        // Update last active timestamp
        await this.updateIntegrationLastActive(integrationId);

        return response;
      } else if (integration.connectionDetails.protocol === 'rest') {
        // Implement REST forwarding
        throw new Error('REST protocol not implemented yet');
      } else if (integration.connectionDetails.protocol === 'websocket') {
        // Implement WebSocket forwarding
        throw new Error('WebSocket protocol not implemented yet');
      } else {
        throw new Error(`Unsupported protocol: ${integration.connectionDetails.protocol}`);
      }
    } catch (error) {
      logger.error(`Failed to forward request to integration: ${integrationId}`, error);
      throw new Error(`Failed to forward request: ${(error as Error).message}`);
    }
  }

  /**
   * Handle incoming requests from external integrations
   * @param integrationId The ID of the integration sending the request
   * @param request The incoming request
   * @returns The response to send back
   */
  async handleExternalRequest(integrationId: string, request: any): Promise<any> {
    try {
      logger.info(`Handling external request from integration: ${integrationId}`);

      const integration = await this.getIntegration(integrationId);
      if (!integration) {
        throw new Error(`Integration not found: ${integrationId}`);
      }

      // Update last active timestamp
      await this.updateIntegrationLastActive(integrationId);

      // Emit an event for this request
      this.emit('externalRequest', {
        integrationId,
        request,
        integration
      });

      // For now, return a simple acknowledgment
      // In a real implementation, this would route the request to the appropriate handler
      return {
        success: true,
        message: 'Request received'
      };
    } catch (error) {
      logger.error(`Failed to handle external request from integration: ${integrationId}`, error);
      return {
        success: false,
        error: (error as Error).message || 'Unknown error'
      };
    }
  }

  /**
   * List all active integrations
   * @returns Array of registered integrations
   */
  async listIntegrations(): Promise<Integration[]> {
    try {
      return Array.from(this.integrations.values());
    } catch (error) {
      logger.error('Failed to list integrations', error);
      return [];
    }
  }

  /**
   * Handle new MCP connection
   * @param connection The MCP connection details
   * @private
   */
  private async handleMCPConnection(connection: any): Promise<void> {
    try {
      logger.info(`New MCP connection from: ${connection.clientName}`);

      // Find if this is an existing integration by endpoint or create a new one
      let integration = Array.from(this.integrations.values()).find(
        i => i.connectionDetails.endpoint === connection.endpoint
      );

      if (!integration) {
        // This is a new integration, register it
        integration = await this.registerIntegration({
          name: connection.clientName,
          type: 'other', // Default type
          connectionDetails: {
            protocol: 'mcp',
            endpoint: connection.endpoint
          },
          capabilities: []
        });
      }

      // Update status to connected
      integration.status = 'connected';
      await this.updateIntegration(integration.id, { status: 'connected' });

      // Create and store MCP client
      const client = new MCPClient(connection);
      this.mcpClients.set(integration.id, client);

      // Set up client event handlers
      client.on('request', async (req) => {
        const response = await this.handleExternalRequest(integration.id, req);
        return response;
      });

      client.on('disconnected', () => {
        this.handleMCPDisconnection(connection);
      });

      // Emit connection event
      this.emit('integrationConnected', integration);
    } catch (error) {
      logger.error('Failed to handle MCP connection', error);
    }
  }

  /**
   * Handle MCP disconnection
   * @param connection The MCP connection details
   * @private
   */
  private async handleMCPDisconnection(connection: any): Promise<void> {
    try {
      logger.info(`MCP disconnection from: ${connection.clientName}`);

      // Find the integration
      const integration = Array.from(this.integrations.values()).find(
        i => i.connectionDetails.endpoint === connection.endpoint
      );

      if (integration) {
        // Update status to disconnected
        integration.status = 'disconnected';
        await this.updateIntegration(integration.id, { status: 'disconnected' });

        // Remove MCP client
        this.mcpClients.delete(integration.id);

        // Emit disconnection event
        this.emit('integrationDisconnected', integration);
      }
    } catch (error) {
      logger.error('Failed to handle MCP disconnection', error);
    }
  }

  /**
   * Update integration details
   * @param integrationId The ID of the integration to update
   * @param updates The updates to apply
   * @private
   */
  private async updateIntegration(integrationId: string, updates: Partial<Integration>): Promise<void> {
    try {
      const integration = this.integrations.get(integrationId);

      if (integration) {
        // Apply updates to in-memory integration
        Object.assign(integration, updates);

        // Prepare database updates with JSON serialization
        const dbUpdates: any = { ...updates };

        // Convert objects to JSON strings for database storage
        if (updates.connectionDetails) {
          dbUpdates.connectionDetails = stringifyJson(updates.connectionDetails);
        }

        if (updates.capabilities) {
          dbUpdates.capabilitiesJson = stringifyJson(updates.capabilities);
          delete dbUpdates.capabilities; // Remove the original object
        }

        // Update in database
        await db.integrations.update({
          where: { id: integrationId },
          data: dbUpdates
        });
      }
    } catch (error) {
      logger.error(`Failed to update integration: ${integrationId}`, error);
    }
  }

  /**
   * Update the last active timestamp for an integration
   * @param integrationId The ID of the integration
   * @private
   */
  private async updateIntegrationLastActive(integrationId: string): Promise<void> {
    const now = new Date();
    await this.updateIntegration(integrationId, { lastActive: now });
  }
}
