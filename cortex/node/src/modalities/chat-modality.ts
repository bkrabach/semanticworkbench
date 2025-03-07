/**
 * Chat Modality Implementation for Cortex Core
 */

import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';
import { logger } from '../utils/logger';
import {
  ModalityInput, ModalityOutput, ModalityCapabilities,
  InputModalityHandler, OutputModalityHandler
} from '../interfaces/modality-interface';
import { Dispatcher } from '../components/dispatcher';

/**
 * Chat Modality Implementation
 * Handles both input and output for the chat modality
 */
export class ChatModality extends EventEmitter implements InputModalityHandler, OutputModalityHandler {
  private readonly dispatcher: Dispatcher;
  private readonly activeChats: Map<string, {
    sessionId: string;
    lastActive: Date;
  }> = new Map();

  constructor(dispatcher: Dispatcher) {
    super();
    this.dispatcher = dispatcher;
  }

  /**
   * Handle input from chat modality
   * @param input The input data
   */
  async handleInput(input: ModalityInput): Promise<void> {
    logger.debug(`Handling chat input for session ${input.sessionId}`);

    try {
      // Track active chat
      this.activeChats.set(input.sessionId, {
        sessionId: input.sessionId,
        lastActive: new Date()
      });

      // Create request for dispatcher
      const request = {
        id: uuidv4(),
        type: 'message',
        sessionId: input.sessionId,
        modality: 'chat',
        content: input.content,
        metadata: input.metadata,
        timestamp: input.timestamp || new Date()
      };

      // Dispatch request
      this.dispatcher.dispatch(request)
        .then(response => {
          // Emit response event
          this.emit('response', {
            sessionId: input.sessionId,
            requestId: request.id,
            response
          });
        })
        .catch(error => {
          logger.error(`Error dispatching chat request: ${(error as Error).message}`);

          // Emit error event
          this.emit('error', {
            sessionId: input.sessionId,
            requestId: request.id,
            error: error.message
          });
        });

      // Emit input event
      this.emit('input', {
        sessionId: input.sessionId,
        requestId: request.id,
        content: input.content
      });
    } catch (error) {
      logger.error(`Error processing chat input: ${(error as Error).message}`);
      throw error;
    }
  }

  /**
   * Handle output to chat modality
   * @param output The output data
   */
  async handleOutput(output: ModalityOutput): Promise<void> {
    logger.debug(`Handling chat output for session ${output.sessionId}`);

    try {
      // Update last active time
      const chatInfo = this.activeChats.get(output.sessionId);
      if (chatInfo) {
        chatInfo.lastActive = new Date();
        this.activeChats.set(output.sessionId, chatInfo);
      }

      // Emit output event
      this.emit('output', {
        sessionId: output.sessionId,
        content: output.content,
        metadata: output.metadata,
        timestamp: new Date()
      });
    } catch (error) {
      logger.error(`Error handling chat output: ${(error as Error).message}`);
      throw error;
    }
  }

  /**
   * Get capabilities of the chat modality
   * @returns Modality capabilities
   */
  getCapabilities(): ModalityCapabilities {
    return {
      supportedContentTypes: [
        'text/plain',
        'text/markdown',
        'application/json'
      ],
      supportsPrioritization: true,
      supportsInterruption: false,
      supportsMultipleDestinations: false
    };
  }

  /**
   * Get active chat sessions
   * @returns Map of active chat sessions
   */
  getActiveChats(): Map<string, { sessionId: string; lastActive: Date; }> {
    return new Map(this.activeChats);
  }

  /**
   * Check if a chat session is active
   * @param sessionId Session ID to check
   * @returns True if session is active
   */
  isSessionActive(sessionId: string): boolean {
    return this.activeChats.has(sessionId);
  }

  /**
   * End a chat session
   * @param sessionId Session ID to end
   * @returns True if session was ended
   */
  endSession(sessionId: string): boolean {
    logger.info(`Ending chat session: ${sessionId}`);

    const wasActive = this.activeChats.has(sessionId);
    this.activeChats.delete(sessionId);

    if (wasActive) {
      this.emit('sessionEnded', { sessionId });
    }

    return wasActive;
  }

  /**
   * Cleanup inactive sessions
   * @param maxInactiveMinutes Maximum inactive time in minutes
   * @returns Number of cleaned up sessions
   */
  cleanupInactiveSessions(maxInactiveMinutes: number = 60): number {
    logger.debug(`Cleaning up inactive chat sessions (max inactive: ${maxInactiveMinutes} minutes)`);

    const now = new Date();
    const maxInactiveMs = maxInactiveMinutes * 60 * 1000;
    let cleanedCount = 0;

    for (const [sessionId, info] of this.activeChats.entries()) {
      const inactiveMs = now.getTime() - info.lastActive.getTime();

      if (inactiveMs > maxInactiveMs) {
        this.activeChats.delete(sessionId);
        this.emit('sessionExpired', { sessionId });
        cleanedCount++;
      }
    }

    if (cleanedCount > 0) {
      logger.info(`Cleaned up ${cleanedCount} inactive chat sessions`);
    }

    return cleanedCount;
  }
}

export default ChatModality;
