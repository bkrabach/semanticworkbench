/**
 * Modality Interface for Cortex Core
 * Provides a unified way to handle different input and output modalities
 */

import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';
import { logger } from '../utils/logger';

export interface ModalityInput {
  sessionId: string;
  content: any;
  metadata: Record<string, any>;
  timestamp: Date;
}

export interface ModalityOutput {
  sessionId: string;
  content: any;
  metadata: Record<string, any>;
  priority: "high" | "normal" | "low";
}

export interface ModalityCapabilities {
  supportedContentTypes: string[];
  supportsPrioritization: boolean;
  supportsInterruption: boolean;
  supportsMultipleDestinations: boolean;
}

export interface ModalityInfo {
  type: string;
  direction: "input" | "output" | "both";
  capabilities: ModalityCapabilities;
  status: "active" | "inactive";
}

export interface InputModalityHandler {
  handleInput(input: ModalityInput): Promise<void>;
  getCapabilities(): ModalityCapabilities;
}

export interface OutputModalityHandler {
  handleOutput(output: ModalityOutput): Promise<void>;
  getCapabilities(): ModalityCapabilities;
}

/**
 * Modality Interface Implementation
 */
export class ModalityInterface extends EventEmitter {
  private readonly inputHandlers: Map<string, InputModalityHandler> = new Map();
  private readonly outputHandlers: Map<string, OutputModalityHandler> = new Map();

  constructor() {
    super();
  }

  /**
   * Register a new input modality
   * @param modalityType Type of modality (e.g., "chat", "voice")
   * @param handler Handler for this modality
   */
  registerInputModality(modalityType: string, handler: InputModalityHandler): void {
    logger.info(`Registering input modality: ${modalityType}`);

    // Check if modality already exists
    if (this.inputHandlers.has(modalityType)) {
      logger.warn(`Input modality already registered: ${modalityType}, replacing`);
    }

    // Register handler
    this.inputHandlers.set(modalityType, handler);

    // Emit event
    this.emit('inputModalityRegistered', {
      type: modalityType,
      capabilities: handler.getCapabilities()
    });
  }

  /**
   * Register a new output modality
   * @param modalityType Type of modality (e.g., "chat", "voice")
   * @param handler Handler for this modality
   */
  registerOutputModality(modalityType: string, handler: OutputModalityHandler): void {
    logger.info(`Registering output modality: ${modalityType}`);

    // Check if modality already exists
    if (this.outputHandlers.has(modalityType)) {
      logger.warn(`Output modality already registered: ${modalityType}, replacing`);
    }

    // Register handler
    this.outputHandlers.set(modalityType, handler);

    // Emit event
    this.emit('outputModalityRegistered', {
      type: modalityType,
      capabilities: handler.getCapabilities()
    });
  }

  /**
   * Process input from a specific modality
   * @param modalityType Type of modality
   * @param input Input data
   */
  async processInput(modalityType: string, input: ModalityInput): Promise<void> {
    logger.debug(`Processing input from modality: ${modalityType}`);

    // Check if modality exists
    const handler = this.inputHandlers.get(modalityType);
    if (!handler) {
      logger.error(`Input modality not registered: ${modalityType}`);
      throw new Error(`Input modality not found: ${modalityType}`);
    }

    try {
      // Process input
      await handler.handleInput(input);

      // Emit event
      this.emit('inputProcessed', {
        type: modalityType,
        sessionId: input.sessionId,
        timestamp: input.timestamp || new Date()
      });
    } catch (error) {
      logger.error(`Failed to process input from modality: ${modalityType}`, error);
      throw new Error(`Failed to process input: ${(error as Error).message}`);
    }
  }

  /**
   * Send output to a specific modality
   * @param modalityType Type of modality
   * @param output Output data
   */
  async sendOutput(modalityType: string, output: ModalityOutput): Promise<void> {
    logger.debug(`Sending output to modality: ${modalityType}`);

    // Check if modality exists
    const handler = this.outputHandlers.get(modalityType);
    if (!handler) {
      logger.error(`Output modality not registered: ${modalityType}`);
      throw new Error(`Output modality not found: ${modalityType}`);
    }

    try {
      // Send output
      await handler.handleOutput(output);

      // Emit event
      this.emit('outputSent', {
        type: modalityType,
        sessionId: output.sessionId,
        timestamp: new Date()
      });
    } catch (error) {
      logger.error(`Failed to send output to modality: ${modalityType}`, error);
      throw new Error(`Failed to send output: ${(error as Error).message}`);
    }
  }

  /**
   * Broadcast output to multiple modalities
   * @param modalityTypes Types of modalities to send to
   * @param output Output data
   */
  async broadcastOutput(modalityTypes: string[], output: ModalityOutput): Promise<void> {
    logger.debug(`Broadcasting output to modalities: ${modalityTypes.join(', ')}`);

    const sendPromises: Promise<void>[] = [];

    // Send to each modality
    for (const modalityType of modalityTypes) {
      sendPromises.push(this.sendOutput(modalityType, output));
    }

    // Wait for all sends to complete
    await Promise.all(sendPromises);
  }

  /**
   * List all registered modalities
   * @returns Array of modality information
   */
  listModalities(): ModalityInfo[] {
    logger.debug('Listing modalities');

    const modalities: ModalityInfo[] = [];

    // Add input modalities
    for (const [type, handler] of this.inputHandlers.entries()) {
      // Check if there's also an output handler
      const outputHandler = this.outputHandlers.get(type);

      modalities.push({
        type,
        direction: outputHandler ? "both" : "input",
        capabilities: handler.getCapabilities(),
        status: "active"
      });
    }

    // Add output-only modalities
    for (const [type, handler] of this.outputHandlers.entries()) {
      // Skip if already added as "both"
      if (this.inputHandlers.has(type)) {
        continue;
      }

      modalities.push({
        type,
        direction: "output",
        capabilities: handler.getCapabilities(),
        status: "active"
      });
    }

    return modalities;
  }

  /**
   * Get the best output modality for a specific content type
   * @param contentType Content type to find modality for
   * @param sessionPreferences Optional session preferences
   * @returns Best modality type or null if none found
   */
  findBestOutputModality(
    contentType: string,
    sessionPreferences?: { preferredModalities?: string[] }
  ): string | null {
    logger.debug(`Finding best output modality for content type: ${contentType}`);

    // First check preferred modalities if provided
    if (sessionPreferences?.preferredModalities?.length) {
      for (const preferredType of sessionPreferences.preferredModalities) {
        const handler = this.outputHandlers.get(preferredType);

        if (handler && handler.getCapabilities().supportedContentTypes.includes(contentType)) {
          return preferredType;
        }
      }
    }

    // If no match in preferences, find any modality that supports this content type
    for (const [type, handler] of this.outputHandlers.entries()) {
      if (handler.getCapabilities().supportedContentTypes.includes(contentType)) {
        return type;
      }
    }

    // No suitable modality found
    return null;
  }

  /**
   * Unregister an input modality
   * @param modalityType Type of modality to unregister
   * @returns True if unregistered, false if not found
   */
  unregisterInputModality(modalityType: string): boolean {
    logger.info(`Unregistering input modality: ${modalityType}`);

    const result = this.inputHandlers.delete(modalityType);

    if (result) {
      this.emit('inputModalityUnregistered', { type: modalityType });
    }

    return result;
  }

  /**
   * Unregister an output modality
   * @param modalityType Type of modality to unregister
   * @returns True if unregistered, false if not found
   */
  unregisterOutputModality(modalityType: string): boolean {
    logger.info(`Unregistering output modality: ${modalityType}`);

    const result = this.outputHandlers.delete(modalityType);

    if (result) {
      this.emit('outputModalityUnregistered', { type: modalityType });
    }

    return result;
  }
}

export default ModalityInterface;
