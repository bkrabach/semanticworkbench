/**
 * REST API implementation for Cortex Core
 */

import express, { Request, Response, NextFunction } from 'express';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import { createServer } from 'http';
import { Server as SocketIOServer } from 'socket.io';
import { v4 as uuidv4 } from 'uuid';
import { logger } from '../utils/logger';
import { SessionManager, Session } from '../components/session-manager';
import { Dispatcher } from '../components/dispatcher';
import { ContextManager } from '../components/context-manager';
import { WorkspaceManager } from '../components/workspace-manager';
import { SecurityManager } from '../components/security-manager';
import { IntegrationHub } from '../components/integration-hub';
import { WhiteboardMemorySystem } from '../components/whiteboard-memory';
import { ModalityInterface } from '../interfaces/modality-interface';
import { DomainExpertInterface } from '../interfaces/domain-expert-interface';

// Extend the Response interface to include optional metadata
interface ExtendedResponse {
  requestId: string;
  status: "success" | "error" | "pending";
  content: any;
  timestamp: Date;
  metadata?: Record<string, any>;
}

export class CortexAPI {
  private app: express.Application;
  private httpServer: ReturnType<typeof createServer>;
  private io: SocketIOServer;
  private port: number;

  // Core components
  private sessionManager: SessionManager;
  private dispatcher: Dispatcher;
  private contextManager: ContextManager;
  private workspaceManager: WorkspaceManager;
  private securityManager: SecurityManager;
  private integrationHub: IntegrationHub;
  private memorySystem: WhiteboardMemorySystem;
  private modalityInterface: ModalityInterface;
  private domainExpertInterface: DomainExpertInterface;

  constructor(port = 4000) {
    this.port = port;
    this.app = express();
    this.httpServer = createServer(this.app);
    this.io = new SocketIOServer(this.httpServer, {
      cors: {
        origin: '*', // In production, limit this to specific origins
        methods: ['GET', 'POST']
      }
    });

    // Initialize components
    // These would be properly injected in a real implementation
    this.memorySystem = new WhiteboardMemorySystem();
    this.sessionManager = new SessionManager();
    this.contextManager = new ContextManager(this.memorySystem);
    this.domainExpertInterface = {} as DomainExpertInterface; // Placeholder
    this.dispatcher = new Dispatcher(this.contextManager, this.domainExpertInterface, this.sessionManager);
    this.workspaceManager = new WorkspaceManager();
    this.securityManager = new SecurityManager({
      jwtSecret: process.env.JWT_SECRET || 'default-secret-change-me',
      encryptionKey: process.env.ENCRYPTION_KEY || 'default-encryption-key-change-me'
    });
    this.integrationHub = new IntegrationHub();
    this.modalityInterface = {} as ModalityInterface; // Placeholder
  }

  /**
   * Initialize the API
   */
  async initialize(): Promise<void> {
    try {
      logger.info('Initializing Cortex API');

      // Configure Express middleware
      this.configureMiddleware();

      // Initialize components
      await this.initializeComponents();

      // Set up routes
      this.setupRoutes();

      // Set up Socket.IO
      this.setupSocketIO();

      // Start HTTP server
      await this.startServer();

      logger.info(`Cortex API initialized and listening on port ${this.port}`);
    } catch (error) {
      logger.error('Failed to initialize Cortex API', error);
      throw error;
    }
  }

  /**
   * Configure Express middleware
   * @private
   */
  private configureMiddleware(): void {
    // Security middleware
    this.app.use(helmet());

    // CORS
    this.app.use(cors());

    // Request parsing
    this.app.use(express.json({ limit: '10mb' }));
    this.app.use(express.urlencoded({ extended: true, limit: '10mb' }));

    // Compression
    this.app.use(compression());

    // Request logging
    this.app.use((req: Request, res: Response, next: NextFunction) => {
      logger.info(`${req.method} ${req.url}`);
      next();
    });

    // Authentication middleware
    this.app.use(async (req: Request, res: Response, next: NextFunction) => {
      // Skip auth for public endpoints
      if (
        req.path === '/auth/login' ||
        req.path === '/auth/refresh' ||
        req.path === '/health'
      ) {
        return next();
      }

      const authHeader = req.headers.authorization;

      if (!authHeader || !authHeader.startsWith('Bearer ')) {
        return res.status(401).json({ error: 'Authentication required' });
      }

      const token = authHeader.split(' ')[1];
      const result = await this.securityManager.verifyToken(token);

      if (!result.valid) {
        return res.status(401).json({ error: result.error || 'Invalid token' });
      }

      // Add user to request
      (req as any).user = {
        id: result.userId,
        scopes: result.scopes || []
      };

      next();
    });

    // Error handling middleware
    this.app.use((err: Error, req: Request, res: Response, next: NextFunction) => {
      logger.error('API error', err);
      res.status(500).json({ error: 'Internal server error' });
    });
  }

  /**
   * Initialize components
   * @private
   */
  private async initializeComponents(): Promise<void> {
    // Initialize memory system
    await this.memorySystem.initialize({
      storageType: 'persistent',
      encryptionEnabled: false
    });

    // Initialize integration hub
    await this.integrationHub.initialize();

    // Additional component initialization would go here
  }

  /**
   * Set up API routes
   * @private
   */
  private setupRoutes(): void {
    // Health check endpoint
    this.app.get('/health', (req: Request, res: Response) => {
      res.json({ status: 'ok' });
    });

    // Authentication endpoints
    this.setupAuthRoutes();

    // Workspace endpoints
    this.setupWorkspaceRoutes();

    // Conversation endpoints
    this.setupConversationRoutes();

    // Input/Output endpoints
    this.setupIORoutes();

    // Integration endpoints
    this.setupIntegrationRoutes();

    // MCP endpoint
    this.setupMCPRoutes();

    // Catch-all for 404s
    this.app.use((req: Request, res: Response) => {
      res.status(404).json({ error: 'Not found' });
    });
  }

  /**
   * Set up authentication routes
   * @private
   */
  private setupAuthRoutes(): void {
    const router = express.Router();

    // Login
    router.post('/login', async (req: Request, res: Response) => {
      try {
        const { type, identifier, secret } = req.body;

        if (!type || !identifier) {
          return res.status(400).json({ error: 'Missing required fields' });
        }

        const result = await this.securityManager.authenticate({
          type,
          identifier,
          secret
        });

        if (!result.success) {
          return res.status(401).json({ error: result.error || 'Authentication failed' });
        }

        res.json({
          token: result.token,
          expiresAt: result.expiresAt,
          userId: result.userId
        });
      } catch (error) {
        logger.error('Login error', error);
        res.status(500).json({ error: 'Authentication failed' });
      }
    });

    // Token refresh
    router.post('/refresh', async (req: Request, res: Response) => {
      // Token refresh logic would go here
      res.status(501).json({ error: 'Not implemented' });
    });

    // Logout
    router.post('/logout', async (req: Request, res: Response) => {
      // Token invalidation logic would go here
      res.status(200).json({ message: 'Logged out successfully' });
    });

    // API key generation
    router.post('/key/generate', async (req: Request, res: Response) => {
      try {
        const userId = (req as any).user.id;
        const { scopes, expiryDays } = req.body;

        // Calculate expiry date if provided
        let expiry: Date | undefined;
        if (expiryDays) {
          expiry = new Date();
          expiry.setDate(expiry.getDate() + expiryDays);
        }

        const apiKey = await this.securityManager.generateApiKey(
          userId,
          scopes || ['*'],
          expiry
        );

        res.json({
          key: apiKey.key,
          expiresAt: apiKey.expiresAt
        });
      } catch (error) {
        logger.error('API key generation error', error);
        res.status(500).json({ error: 'Failed to generate API key' });
      }
    });

    this.app.use('/auth', router);
  }

  /**
   * Set up workspace routes
   * @private
   */
  private setupWorkspaceRoutes(): void {
    const router = express.Router();

    // List workspaces
    router.get('/', async (req: Request, res: Response) => {
      try {
        const userId = (req as any).user.id;
        const workspaces = await this.workspaceManager.listWorkspaces(userId);
        res.json({ workspaces });
      } catch (error) {
        logger.error('List workspaces error', error);
        res.status(500).json({ error: 'Failed to list workspaces' });
      }
    });

    // Create workspace
    router.post('/', async (req: Request, res: Response) => {
      try {
        const userId = (req as any).user.id;
        const { name, config } = req.body;

        if (!name) {
          return res.status(400).json({ error: 'Workspace name is required' });
        }

        const workspace = await this.workspaceManager.createWorkspace(userId, name, config);
        res.status(201).json({ workspace });
      } catch (error) {
        logger.error('Create workspace error', error);
        res.status(500).json({ error: 'Failed to create workspace' });
      }
    });

    // Get workspace
    router.get('/:id', async (req: Request, res: Response) => {
      try {
        const userId = (req as any).user.id;
        const workspaceId = req.params.id;

        // Check access
        const hasAccess = await this.securityManager.checkAccess(
          userId,
          `workspace:${workspaceId}`,
          'read_workspace'
        );

        if (!hasAccess) {
          return res.status(403).json({ error: 'Access denied' });
        }

        const workspace = await this.workspaceManager.getWorkspace(workspaceId);

        if (!workspace) {
          return res.status(404).json({ error: 'Workspace not found' });
        }

        res.json({ workspace });
      } catch (error) {
        logger.error('Get workspace error', error);
        res.status(500).json({ error: 'Failed to get workspace' });
      }
    });

    // Update workspace - would be implemented here

    // Delete workspace - would be implemented here

    this.app.use('/workspaces', router);
  }

  /**
   * Set up conversation routes
   * @private
   */
  private setupConversationRoutes(): void {
    const router = express.Router();

    // List conversations in workspace
    router.get('/workspaces/:id/conversations', async (req: Request, res: Response) => {
      try {
        const userId = (req as any).user.id;
        const workspaceId = req.params.id;

        // Check access
        const hasAccess = await this.securityManager.checkAccess(
          userId,
          `workspace:${workspaceId}`,
          'read_workspace'
        );

        if (!hasAccess) {
          return res.status(403).json({ error: 'Access denied' });
        }

        // Parse filter parameters
        const filter = {
          modality: req.query.modality as string,
          fromDate: req.query.fromDate ? new Date(req.query.fromDate as string) : undefined,
          toDate: req.query.toDate ? new Date(req.query.toDate as string) : undefined,
          searchText: req.query.search as string
        };

        const conversations = await this.workspaceManager.listConversations(workspaceId, filter);
        res.json({ conversations });
      } catch (error) {
        logger.error('List conversations error', error);
        res.status(500).json({ error: 'Failed to list conversations' });
      }
    });

    // Create conversation
    router.post('/workspaces/:id/conversations', async (req: Request, res: Response) => {
      try {
        const userId = (req as any).user.id;
        const workspaceId = req.params.id;
        const { modality, title } = req.body;

        if (!modality) {
          return res.status(400).json({ error: 'Modality is required' });
        }

        // Check access
        const hasAccess = await this.securityManager.checkAccess(
          userId,
          `workspace:${workspaceId}`,
          'add_conversation'
        );

        if (!hasAccess) {
          return res.status(403).json({ error: 'Access denied' });
        }

        const conversation = await this.workspaceManager.createConversation(
          workspaceId,
          modality,
          title
        );

        res.status(201).json({ conversation });
      } catch (error) {
        logger.error('Create conversation error', error);
        res.status(500).json({ error: 'Failed to create conversation' });
      }
    });

    // Get conversation
    router.get('/conversations/:id', async (req: Request, res: Response) => {
      try {
        const userId = (req as any).user.id;
        const conversationId = req.params.id;

        const conversation = await this.workspaceManager.getConversation(conversationId);

        if (!conversation) {
          return res.status(404).json({ error: 'Conversation not found' });
        }

        // Check access to the conversation's workspace
        const hasAccess = await this.securityManager.checkAccess(
          userId,
          `workspace:${conversation.workspaceId}`,
          'read_workspace'
        );

        if (!hasAccess) {
          return res.status(403).json({ error: 'Access denied' });
        }

        res.json({ conversation });
      } catch (error) {
        logger.error('Get conversation error', error);
        res.status(500).json({ error: 'Failed to get conversation' });
      }
    });

    // Add message to conversation
    router.post('/conversations/:id/messages', async (req: Request, res: Response) => {
      try {
        const userId = (req as any).user.id;
        const conversationId = req.params.id;
        const { content, type, metadata } = req.body;

        if (!content || !type) {
          return res.status(400).json({ error: 'Content and type are required' });
        }

        const conversation = await this.workspaceManager.getConversation(conversationId);

        if (!conversation) {
          return res.status(404).json({ error: 'Conversation not found' });
        }

        // Check access to the conversation's workspace
        const hasAccess = await this.securityManager.checkAccess(
          userId,
          `workspace:${conversation.workspaceId}`,
          'add_conversation'
        );

        if (!hasAccess) {
          return res.status(403).json({ error: 'Access denied' });
        }

        const entry = await this.workspaceManager.addConversationEntry(conversationId, {
          type,
          content,
          timestamp: new Date(),
          metadata: metadata || {}
        });

        // If this is a user message, process it through the dispatcher
        if (type === 'user') {
          // Get active session for this user
          // In a real implementation, this would be tracked properly
          const sessions = await this.sessionManager.getActiveSessionsForUser(userId);
          let sessionId: string;

          if (sessions.length > 0) {
            sessionId = sessions[0].id;
          } else {
            const newSession = await this.createSessionForUser(userId);
            sessionId = newSession;
          }

          // Create a request for the dispatcher
          const request = {
            id: uuidv4(),
            type: 'message',
            sessionId,
            modality: conversation.modality,
            content,
            metadata: {
              conversationId,
              workspaceId: conversation.workspaceId,
              ...(metadata || {})
            },
            timestamp: new Date()
          };

          // Dispatch the request (non-blocking)
          this.dispatcher.dispatch(request).then((response: ExtendedResponse) => {
            if (response.status === 'success') {
              // Add assistant response to conversation
              this.workspaceManager.addConversationEntry(conversationId, {
                type: 'assistant',
                content: response.content,
                timestamp: response.timestamp,
                metadata: response.metadata || {}
              });

              // Emit event to connected clients
              this.io.to(`conversation:${conversationId}`).emit('message', {
                type: 'assistant',
                content: response.content,
                timestamp: response.timestamp,
                metadata: response.metadata || {}
              });
            } else {
              logger.error(`Request ${request.id} failed: ${JSON.stringify(response.content)}`);
            }
          }).catch(error => {
            logger.error(`Error dispatching request: ${(error as Error).message}`);
          });
        }

        res.status(201).json({ entry });
      } catch (error) {
        logger.error('Add message error', error);
        res.status(500).json({ error: 'Failed to add message' });
      }
    });

    this.app.use('/', router);
  }

  /**
   * Set up input/output routes
   * @private
   */
  private setupIORoutes(): void {
    const router = express.Router();

    // Send input through a specific modality
    router.post('/input/:modality', async (req: Request, res: Response) => {
      try {
        const userId = (req as any).user.id;
        const modality = req.params.modality;
        const { content, sessionId, metadata } = req.body;

        if (!content) {
          return res.status(400).json({ error: 'Content is required' });
        }

        // Get or create session
        let session: Session | null = null;
        let finalSessionId: string;

        if (sessionId) {
          session = await this.sessionManager.getSession(sessionId);
        }

        if (!session) {
          finalSessionId = await this.createSessionForUser(userId);
        } else {
          finalSessionId = session.id;
        }

        // Create a request for the dispatcher
        const request = {
          id: uuidv4(),
          type: 'input',
          sessionId: finalSessionId,
          modality,
          content,
          metadata: metadata || {},
          timestamp: new Date()
        };

        // Dispatch the request (non-blocking)
        this.dispatcher.dispatch(request).then((response: ExtendedResponse) => {
          // Send response through SSE
          const clientId = req.body.clientId;
          if (clientId) {
            this.io.to(clientId).emit('response', response);
          }
        }).catch(error => {
          logger.error(`Error dispatching request: ${(error as Error).message}`);
        });

        // Return request ID for tracking
        res.status(202).json({
          requestId: request.id,
          sessionId: finalSessionId
        });
      } catch (error) {
        logger.error('Input error', error);
        res.status(500).json({ error: 'Failed to process input' });
      }
    });

    // Stream outputs for a specific modality (SSE)
    // This is handled through Socket.IO

    this.app.use('/', router);
  }

  /**
   * Set up integration routes
   * @private
   */
  private setupIntegrationRoutes(): void {
    const router = express.Router();

    // List integrations
    router.get('/', async (req: Request, res: Response) => {
      try {
        const integrations = await this.integrationHub.listIntegrations();
        res.json({ integrations });
      } catch (error) {
        logger.error('List integrations error', error);
        res.status(500).json({ error: 'Failed to list integrations' });
      }
    });

    // Register integration
    router.post('/', async (req: Request, res: Response) => {
      try {
        const { name, type, connectionDetails, capabilities } = req.body;

        if (!name || !type || !connectionDetails) {
          return res.status(400).json({ error: 'Missing required fields' });
        }

        const integration = await this.integrationHub.registerIntegration({
          name,
          type,
          connectionDetails,
          capabilities: capabilities || []
        });

        res.status(201).json({ integration });
      } catch (error) {
        logger.error('Register integration error', error);
        res.status(500).json({ error: 'Failed to register integration' });
      }
    });

    // Get integration
    router.get('/:id', async (req: Request, res: Response) => {
      try {
        const integrationId = req.params.id;
        const integration = await this.integrationHub.getIntegration(integrationId);

        if (!integration) {
          return res.status(404).json({ error: 'Integration not found' });
        }

        res.json({ integration });
      } catch (error) {
        logger.error('Get integration error', error);
        res.status(500).json({ error: 'Failed to get integration' });
      }
    });

    // Send request to integration
    router.post('/:id/request', async (req: Request, res: Response) => {
      try {
        const integrationId = req.params.id;
        const request = req.body;

        const response = await this.integrationHub.forwardRequest(integrationId, request);
        res.json(response);
      } catch (error) {
        logger.error('Forward integration request error', error);
        res.status(500).json({ error: 'Failed to forward request to integration' });
      }
    });

    this.app.use('/integrations', router);
  }

  /**
   * Set up MCP routes
   * @private
   */
  private setupMCPRoutes(): void {
    // MCP message endpoint
    this.app.post('/mcp', async (req: Request, res: Response) => {
      try {
        const userId = (req as any).user.id;
        const integrationId = req.query.integration as string || req.body.integrationId;

        if (!integrationId) {
          return res.status(400).json({ error: 'Integration ID is required' });
        }

        // Get the integration
        const integration = await this.integrationHub.getIntegration(integrationId);

        if (!integration) {
          return res.status(404).json({ error: 'Integration not found' });
        }

        // Forward the message
        const response = await this.integrationHub.forwardRequest(integrationId, req.body);

        res.json(response);
      } catch (error) {
        logger.error('MCP message handling error', error);
        res.status(500).json({
          error: 'Failed to process MCP message',
          message: (error as Error).message
        });
      }
    });

    // MCP SSE endpoint for real-time communication
    this.app.get('/mcp/events', async (req: Request, res: Response) => {
      try {
        const userId = (req as any).user.id;
        const integrationId = req.query.integration as string;

        if (!integrationId) {
          return res.status(400).json({ error: 'Integration ID is required' });
        }

        // Get the integration
        const integration = await this.integrationHub.getIntegration(integrationId);

        if (!integration) {
          return res.status(404).json({ error: 'Integration not found' });
        }

        // Set up SSE connection
        res.writeHead(200, {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive'
        });

        // Helper function to send events
        const sendEvent = (event: string, data: any) => {
          res.write(`event: ${event}\n`);
          res.write(`data: ${JSON.stringify(data)}\n\n`);
        };

        // Send initial connection event
        sendEvent('connection', {
          integration: {
            id: integration.id,
            name: integration.name,
            type: integration.type,
            status: integration.status
          },
          message: 'SSE connection established'
        });

        // Set up event handler for integration events
        const handleIntegrationEvent = (eventData: any) => {
          if (eventData.integrationId === integrationId) {
            sendEvent('integration-event', eventData);
          }
        };

        // Register event listener
        this.integrationHub.on('integration-event', handleIntegrationEvent);

        // Handle client disconnect
        req.on('close', () => {
          this.integrationHub.removeListener('integration-event', handleIntegrationEvent);
          res.end();
        });
      } catch (error) {
        logger.error('MCP SSE setup error', error);
        res.status(500).json({
          error: 'Failed to set up SSE connection',
          message: (error as Error).message
        });
      }
    });

    // List available MCP integrations
    this.app.get('/mcp/integrations', async (req: Request, res: Response) => {
      try {
        const integrations = await this.integrationHub.listIntegrations();

        // Filter to only show MCP integrations
        const mcpIntegrations = integrations.filter(integration =>
          integration.connectionDetails.protocol === 'mcp'
        );

        res.json({ integrations: mcpIntegrations });
      } catch (error) {
        logger.error('List MCP integrations error', error);
        res.status(500).json({
          error: 'Failed to list MCP integrations',
          message: (error as Error).message
        });
      }
    });
  }

  /**
   * Set up Socket.IO
   * @private
   */
  private setupSocketIO(): void {
    this.io.on('connection', (socket) => {
      logger.info(`Socket connected: ${socket.id}`);

      // Join a conversation room
      socket.on('join-conversation', (conversationId: string) => {
        socket.join(`conversation:${conversationId}`);
        logger.debug(`Socket ${socket.id} joined conversation ${conversationId}`);
      });

      // Leave a conversation room
      socket.on('leave-conversation', (conversationId: string) => {
        socket.leave(`conversation:${conversationId}`);
        logger.debug(`Socket ${socket.id} left conversation ${conversationId}`);
      });

      // Clean up on disconnect
      socket.on('disconnect', () => {
        logger.info(`Socket disconnected: ${socket.id}`);
      });
    });
  }

  /**
   * Start HTTP server
   * @private
   */
  private async startServer(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.httpServer.listen(this.port, () => {
        logger.info(`Server listening on port ${this.port}`);
        resolve();
      }).on('error', (error) => {
        logger.error(`Server failed to start: ${(error as Error).message}`);
        reject(error);
      });
    });
  }

  /**
   * Create a session for a user
   * @param userId The user ID
   * @private
   */
  private async createSessionForUser(userId: string): Promise<string> {
    const session = await this.sessionManager.createSession(userId);
    return session.id;
  }
}
