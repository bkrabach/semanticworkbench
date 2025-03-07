/**
 * Domain Expert Interface for Cortex Core
 */

import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';
import { logger } from '../utils/logger';

export type TaskId = string;

export interface ExpertTask {
  id?: TaskId;
  type: string;
  content: any;
  context?: any;
  constraints?: TaskConstraints;
  metadata: Record<string, any>;
}

export interface TaskConstraints {
  deadline?: Date;
  maxTokens?: number;
  priorityLevel?: "high" | "normal" | "low";
  maxRetries?: number;
}

export interface TaskStatus {
  id: TaskId;
  state: "queued" | "processing" | "completed" | "failed" | "cancelled";
  progress?: number; // 0-100
  estimatedCompletionTime?: Date;
  statusMessage?: string;
}

export interface ExpertTaskResult {
  taskId: TaskId;
  success: boolean;
  result?: any;
  error?: string;
  metrics?: Record<string, any>;
}

export interface ExpertCapabilities {
  supportedTaskTypes: string[];
  supportsAsyncTasks: boolean;
  supportsCancellation: boolean;
  supportsProgress: boolean;
  maxConcurrentTasks?: number;
}

export interface ExpertInfo {
  type: string;
  name: string;
  capabilities: ExpertCapabilities;
  status: "available" | "busy" | "offline";
}

export interface ExpertHandler {
  handleTask(task: ExpertTask): Promise<TaskId>;
  checkStatus(taskId: TaskId): Promise<TaskStatus>;
  getResult(taskId: TaskId): Promise<ExpertTaskResult>;
  cancelTask(taskId: TaskId): Promise<boolean>;
  getCapabilities(): ExpertCapabilities;
}

/**
 * Domain Expert Interface implementation
 */
export class DomainExpertInterface extends EventEmitter {
  private readonly experts: Map<string, ExpertHandler> = new Map();
  private readonly taskRegistry: Map<TaskId, {
    expertType: string;
    task: ExpertTask;
    status: TaskStatus;
    result?: ExpertTaskResult;
  }> = new Map();

  constructor() {
    super();
  }

  /**
   * Register a new domain expert
   * @param expertType The type of domain expert
   * @param handler The expert handler
   */
  registerExpert(expertType: string, handler: ExpertHandler): void {
    logger.info(`Registering domain expert: ${expertType}`);

    // Check if expert already exists
    if (this.experts.has(expertType)) {
      logger.warn(`Domain expert already registered: ${expertType}, replacing`);
    }

    // Register expert
    this.experts.set(expertType, handler);

    // Emit event
    this.emit('expertRegistered', {
      type: expertType,
      capabilities: handler.getCapabilities()
    });
  }

  /**
   * Unregister a domain expert
   * @param expertType The type of domain expert
   * @returns True if expert was unregistered
   */
  unregisterExpert(expertType: string): boolean {
    logger.info(`Unregistering domain expert: ${expertType}`);

    // Check if expert exists
    if (!this.experts.has(expertType)) {
      logger.warn(`Domain expert not registered: ${expertType}`);
      return false;
    }

    // Unregister expert
    const result = this.experts.delete(expertType);

    // Emit event
    if (result) {
      this.emit('expertUnregistered', { type: expertType });
    }

    return result;
  }

  /**
   * Delegate a task to a domain expert
   * @param expertType The type of domain expert
   * @param task The task to delegate
   * @returns The task ID
   */
  async delegateTask(expertType: string, task: ExpertTask): Promise<TaskId> {
    logger.info(`Delegating task to domain expert: ${expertType}`);

    // Check if expert exists
    const expert = this.experts.get(expertType);
    if (!expert) {
      logger.error(`Domain expert not registered: ${expertType}`);
      throw new Error(`Domain expert not found: ${expertType}`);
    }

    // Generate task ID if not provided
    if (!task.id) {
      task.id = uuidv4();
    }

    try {
      // Delegate task to expert
      const taskId = await expert.handleTask(task);

      // Register task
      this.taskRegistry.set(taskId, {
        expertType,
        task,
        status: {
          id: taskId,
          state: 'queued',
          statusMessage: 'Task queued'
        }
      });

      // Emit event
      this.emit('taskDelegated', { taskId, expertType, task });

      // Start monitoring task
      this.monitorTask(taskId, expertType);

      return taskId;
    } catch (error) {
      logger.error(`Failed to delegate task to domain expert: ${expertType}`, error);
      throw new Error(`Failed to delegate task: ${(error as Error).message}`);
    }
  }

  /**
   * Check the status of a delegated task
   * @param taskId The task ID
   * @returns The task status
   */
  async checkTaskStatus(taskId: TaskId): Promise<TaskStatus> {
    logger.debug(`Checking status of task: ${taskId}`);

    // Check if task exists
    const taskInfo = this.taskRegistry.get(taskId);
    if (!taskInfo) {
      logger.error(`Task not found: ${taskId}`);
      throw new Error(`Task not found: ${taskId}`);
    }

    try {
      // Get status from expert
      const expert = this.experts.get(taskInfo.expertType);
      if (!expert) {
        logger.error(`Domain expert not registered: ${taskInfo.expertType}`);
        throw new Error(`Domain expert not found: ${taskInfo.expertType}`);
      }

      const status = await expert.checkStatus(taskId);

      // Update task registry
      taskInfo.status = status;
      this.taskRegistry.set(taskId, taskInfo);

      return status;
    } catch (error) {
      logger.error(`Failed to check status of task: ${taskId}`, error);
      throw new Error(`Failed to check task status: ${(error as Error).message}`);
    }
  }

  /**
   * Get the result of a completed task
   * @param taskId The task ID
   * @returns The task result
   */
  async getTaskResult(taskId: TaskId): Promise<ExpertTaskResult> {
    logger.debug(`Getting result of task: ${taskId}`);

    // Check if task exists
    const taskInfo = this.taskRegistry.get(taskId);
    if (!taskInfo) {
      logger.error(`Task not found: ${taskId}`);
      throw new Error(`Task not found: ${taskId}`);
    }

    // Check if result is already in registry
    if (taskInfo.result) {
      return taskInfo.result;
    }

    try {
      // Get result from expert
      const expert = this.experts.get(taskInfo.expertType);
      if (!expert) {
        logger.error(`Domain expert not registered: ${taskInfo.expertType}`);
        throw new Error(`Domain expert not found: ${taskInfo.expertType}`);
      }

      const result = await expert.getResult(taskId);

      // Update task registry
      taskInfo.result = result;
      this.taskRegistry.set(taskId, taskInfo);

      return result;
    } catch (error) {
      logger.error(`Failed to get result of task: ${taskId}`, error);
      throw new Error(`Failed to get task result: ${(error as Error).message}`);
    }
  }

  /**
   * Cancel an in-progress task
   * @param taskId The task ID
   * @returns True if task was cancelled
   */
  async cancelTask(taskId: TaskId): Promise<boolean> {
    logger.info(`Cancelling task: ${taskId}`);

    // Check if task exists
    const taskInfo = this.taskRegistry.get(taskId);
    if (!taskInfo) {
      logger.error(`Task not found: ${taskId}`);
      throw new Error(`Task not found: ${taskId}`);
    }

    try {
      // Cancel task
      const expert = this.experts.get(taskInfo.expertType);
      if (!expert) {
        logger.error(`Domain expert not registered: ${taskInfo.expertType}`);
        throw new Error(`Domain expert not found: ${taskInfo.expertType}`);
      }

      const result = await expert.cancelTask(taskId);

      // Update task registry if cancelled
      if (result) {
        taskInfo.status = {
          id: taskId,
          state: 'cancelled',
          statusMessage: 'Task cancelled by user'
        };
        this.taskRegistry.set(taskId, taskInfo);

        // Emit event
        this.emit('taskCancelled', { taskId });
      }

      return result;
    } catch (error) {
      logger.error(`Failed to cancel task: ${taskId}`, error);
      throw new Error(`Failed to cancel task: ${(error as Error).message}`);
    }
  }

  /**
   * List all registered domain experts
   * @returns Array of expert info
   */
  async listExperts(): Promise<ExpertInfo[]> {
    logger.debug('Listing domain experts');

    const experts: ExpertInfo[] = [];

    for (const [type, handler] of this.experts.entries()) {
      // Get capabilities
      const capabilities = handler.getCapabilities();

      // Determine status
      let status: "available" | "busy" | "offline" = "available";

      // Check if expert is busy
      if (capabilities.maxConcurrentTasks) {
        const activeTasks = Array.from(this.taskRegistry.values())
          .filter(info => info.expertType === type &&
            (info.status.state === 'queued' || info.status.state === 'processing'))
          .length;

        if (activeTasks >= capabilities.maxConcurrentTasks) {
          status = "busy";
        }
      }

      // Add to list
      experts.push({
        type,
        name: type, // For MVP, just use type as name
        capabilities,
        status
      });
    }

    return experts;
  }

  /**
   * Monitor a task for status changes
   * @param taskId The task ID
   * @param expertType The expert type
   * @private
   */
  private async monitorTask(taskId: TaskId, expertType: string): Promise<void> {
    try {
      // Get expert
      const expert = this.experts.get(expertType);
      if (!expert) {
        logger.error(`Domain expert not registered: ${expertType}`);
        return;
      }

      // Initial delay
      await new Promise(resolve => setTimeout(resolve, 500));

      // Get current status
      let status = await expert.checkStatus(taskId);

      // Update task registry
      const taskInfo = this.taskRegistry.get(taskId);
      if (taskInfo) {
        taskInfo.status = status;
        this.taskRegistry.set(taskId, taskInfo);

        // Emit status update event
        this.emit('taskStatusUpdated', { taskId, status });
      }

      // Continue monitoring if not completed
      if (status.state !== 'completed' && status.state !== 'failed' && status.state !== 'cancelled') {
        // Schedule next check
        setTimeout(() => this.monitorTask(taskId, expertType), 1000);
      } else if (status.state === 'completed') {
        // Task completed, get result
        const result = await expert.getResult(taskId);

        // Update task registry
        if (taskInfo) {
          taskInfo.result = result;
          this.taskRegistry.set(taskId, taskInfo);

          // Emit completion event
          this.emit('taskCompleted', { taskId, result });
        }
      } else if (status.state === 'failed') {
        // Emit failure event
        this.emit('taskFailed', {
          taskId,
          error: status.statusMessage || 'Task failed without specific error message'
        });
      }
    } catch (error) {
      logger.error(`Error monitoring task ${taskId}`, error);
    }
  }
}

export default DomainExpertInterface;
