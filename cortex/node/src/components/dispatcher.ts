/**
 * Implementation of the Dispatcher component for Cortex Core
 */

import { v4 as uuidv4 } from 'uuid';
import { logger } from '../utils/logger';
import { ContextManager } from './context-manager';
import { DomainExpertInterface } from '../interfaces/domain-expert-interface';
import { SessionManager } from './session-manager';

export interface Request {
  id: string;
  type: string;
  sessionId: string;
  modality: string;
  content: any;
  metadata: Record<string, any>;
  timestamp: Date;
}

export interface Response {
  requestId: string;
  status: "success" | "error" | "pending";
  content: any;
  timestamp: Date;
  metadata?: Record<string, any>; // Added metadata field
}

export interface Task {
  id: string;
  type: string;
  content: any;
  context?: any;
  constraints?: {
    deadline?: Date;
    maxTokens?: number;
    priorityLevel?: "high" | "normal" | "low";
    maxRetries?: number;
  };
  metadata: Record<string, any>;
}

export interface TaskResult {
  taskId: string;
  success: boolean;
  result?: any;
  error?: string;
  metrics?: Record<string, any>;
}

export interface RequestHandler {
  handleRequest(request: Request): Promise<Response>;
  canHandle(request: Request): boolean;
}

export class Dispatcher {
  private readonly handlers: Map<string, RequestHandler[]> = new Map();
  private readonly inProgressRequests: Map<string, {
    request: Request,
    resolve: (value: Response) => void,
    reject: (reason: any) => void
  }> = new Map();
  private readonly contextManager: ContextManager;
  private readonly domainExpertInterface: DomainExpertInterface;
  private readonly sessionManager: SessionManager;

  constructor(
    contextManager: ContextManager,
    domainExpertInterface: DomainExpertInterface,
    sessionManager: SessionManager
  ) {
    this.contextManager = contextManager;
    this.domainExpertInterface = domainExpertInterface;
    this.sessionManager = sessionManager;
  }

  /**
   * Register a handler for a specific request type
   * @param requestType The type of request to handle
   * @param handler The handler for this request type
   */
  registerHandler(requestType: string, handler: RequestHandler): void {
    const existingHandlers = this.handlers.get(requestType) || [];
    this.handlers.set(requestType, [...existingHandlers, handler]);
    logger.info(`Registered handler for request type: ${requestType}`);
  }

  /**
   * Dispatch an incoming request to the appropriate handler
   * @param request The request to dispatch
   * @returns The response from the handler
   */
  async dispatch(request: Request): Promise<Response> {
    try {
      // If no ID is provided, generate one
      if (!request.id) {
        request.id = uuidv4();
      }

      // Set timestamp if not provided
      if (!request.timestamp) {
        request.timestamp = new Date();
      }

      logger.info(`Dispatching request ${request.id} of type ${request.type}`);

      // Validate session
      const sessionValid = await this.sessionManager.validateSession(request.sessionId);
      if (!sessionValid) {
        return {
          requestId: request.id,
          status: 'error',
          content: { error: 'Invalid or expired session' },
          timestamp: new Date()
        };
      }

      // Find handlers for this request type
      const handlers = this.handlers.get(request.type) || [];
      const eligibleHandlers = handlers.filter(handler => handler.canHandle(request));

      if (eligibleHandlers.length === 0) {
        logger.warn(`No handlers found for request type: ${request.type}`);
        return {
          requestId: request.id,
          status: 'error',
          content: { error: `No handler available for request type: ${request.type}` },
          timestamp: new Date()
        };
      }

      // Store in-progress request for cancellation support
      const responsePromise = new Promise<Response>((resolve, reject) => {
        this.inProgressRequests.set(request.id, { request, resolve, reject });
      });

      // Process request with the first eligible handler
      const handler = eligibleHandlers[0];

      try {
        // Get the session for context
        const session = await this.sessionManager.getSession(request.sessionId);

        if (!session) {
          throw new Error(`Invalid session: ${request.sessionId}`);
        }

        // Update context with this request
        await this.contextManager.updateContext(
          request.sessionId,
          session.activeWorkspaceId,
          {
            addMessages: [{
              id: request.id,
              role: 'user',
              content: JSON.stringify(request.content),
              timestamp: request.timestamp
            }]
          }
        );

        // Handle the request
        const response = await handler.handleRequest(request);

        // Update context with the response
        if (response.status === 'success') {
          await this.contextManager.updateContext(
            request.sessionId,
            session.activeWorkspaceId,
            {
              addMessages: [{
                id: `response-${request.id}`,
                role: 'assistant',
                content: JSON.stringify(response.content),
                timestamp: response.timestamp
              }]
            }
          );
        }

        // Resolve the promise with the response
        const requestInfo = this.inProgressRequests.get(request.id);
        if (requestInfo) {
          requestInfo.resolve(response);
          this.inProgressRequests.delete(request.id);
        }

        return response;
      } catch (error) {
        logger.error(`Error handling request ${request.id}`, error);

        const errorResponse: Response = {
          requestId: request.id,
          status: 'error',
          content: { error: (error as Error).message || 'Unknown error occurred' },
          timestamp: new Date()
        };

        // Resolve the promise with the error response
        const requestInfo = this.inProgressRequests.get(request.id);
        if (requestInfo) {
          requestInfo.resolve(errorResponse);
          this.inProgressRequests.delete(request.id);
        }

        return errorResponse;
      }
    } catch (error) {
      logger.error(`Failed to dispatch request`, error);
      return {
        requestId: request.id || 'unknown',
        status: 'error',
        content: { error: (error as Error).message || 'Unknown error occurred during dispatch' },
        timestamp: new Date()
      };
    }
  }

  /**
   * Route a task to a domain expert
   * @param expertType The type of domain expert to use
   * @param task The task to delegate
   * @returns The result from the domain expert
   */
  async delegateToExpert(expertType: string, task: Task): Promise<TaskResult> {
    try {
      logger.info(`Delegating task ${task.id || '(new)'} to expert: ${expertType}`);

      // If no ID is provided, generate one
      if (!task.id) {
        task.id = uuidv4();
      }

      // Check if the expert type is available
      const experts = await this.domainExpertInterface.listExperts();
      const expertExists = experts.some(expert => expert.type === expertType);

      if (!expertExists) {
        throw new Error(`Domain expert of type ${expertType} not available`);
      }

      // Delegate the task
      const taskId = await this.domainExpertInterface.delegateTask(expertType, task);

      // Start monitoring the task status
      const checkInterval = setInterval(async () => {
        try {
          const status = await this.domainExpertInterface.checkTaskStatus(taskId);

          if (status.state === 'completed' || status.state === 'failed' || status.state === 'cancelled') {
            clearInterval(checkInterval);
          }
        } catch (error) {
          logger.error(`Error checking task status for ${taskId}`, error);
          clearInterval(checkInterval);
        }
      }, 1000); // Check every second

      // Wait for task completion
      let currentStatus = await this.domainExpertInterface.checkTaskStatus(taskId);

      while (currentStatus.state !== 'completed' &&
        currentStatus.state !== 'failed' &&
        currentStatus.state !== 'cancelled') {
        // Wait before checking again
        await new Promise(resolve => setTimeout(resolve, 500));
        currentStatus = await this.domainExpertInterface.checkTaskStatus(taskId);
      }

      // Get the task result
      const result = await this.domainExpertInterface.getTaskResult(taskId);
      return result;
    } catch (error) {
      logger.error(`Failed to delegate task to expert ${expertType}`, error);
      return {
        taskId: task.id,
        success: false,
        error: (error as Error).message || 'Unknown error occurred during expert delegation'
      };
    }
  }

  /**
   * Cancel an in-progress request
   * @param requestId The ID of the request to cancel
   * @returns True if successfully cancelled
   */
  async cancelRequest(requestId: string): Promise<boolean> {
    try {
      logger.info(`Attempting to cancel request: ${requestId}`);

      const requestInfo = this.inProgressRequests.get(requestId);
      if (!requestInfo) {
        logger.warn(`Request ${requestId} not found or already completed`);
        return false;
      }

      // Reject the promise with a cancellation error
      requestInfo.reject(new Error('Request was cancelled'));

      // Remove from in-progress requests
      this.inProgressRequests.delete(requestId);

      return true;
    } catch (error) {
      logger.error(`Failed to cancel request ${requestId}`, error);
      return false;
    }
  }
}
