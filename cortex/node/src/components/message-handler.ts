/**
 * Implementation of the Message Handler component for Cortex Core
 * Processes user messages via OpenAI API
 */

import { RequestHandler, Request, Response } from './dispatcher';
import { logger } from '../utils/logger';

interface OpenAIMessage {
    role: 'system' | 'user' | 'assistant';
    content: string;
}

interface OpenAIRequest {
    model: string;
    messages: OpenAIMessage[];
    stream?: boolean;
}

interface OpenAIChoice {
    index: number;
    message: {
        role: string;
        content: string;
    };
    finish_reason: string;
}

interface OpenAIResponse {
    id: string;
    object: string;
    created: number;
    model: string;
    choices: OpenAIChoice[];
    usage: {
        prompt_tokens: number;
        completion_tokens: number;
        total_tokens: number;
    };
}

export class MessageHandler implements RequestHandler {
    private readonly apiKey: string;
    private readonly model: string;

    constructor() {
        this.apiKey = process.env.OPENAI_API_KEY || '';

        // Default to GPT-4o, but allow configuration via env var
        this.model = process.env.OPENAI_MODEL || 'gpt-4o';

        if (!this.apiKey) {
            logger.warn('OPENAI_API_KEY environment variable not set - will use mock responses');
        }
    }

    async handleRequest(request: Request): Promise<Response> {
        try {
            logger.info(`Handling ${request.type} request: ${request.id}`);

            // Extract user message
            const userMessage = request.content;

            let assistantMessage: string;
            let metadata: Record<string, any> = {};

            // Check if we have an API key
            if (this.apiKey) {
                // Create OpenAI request
                const openaiRequest: OpenAIRequest = {
                    model: this.model,
                    messages: [
                        {
                            role: 'user',
                            content: userMessage
                        }
                    ]
                };

                // Call OpenAI API
                const openaiResponse = await fetch('https://api.openai.com/v1/chat/completions', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${this.apiKey}`
                    },
                    body: JSON.stringify(openaiRequest)
                });

                if (!openaiResponse.ok) {
                    const errorText = await openaiResponse.text();
                    throw new Error(`OpenAI API error: ${openaiResponse.status} ${errorText}`);
                }

                const data = await openaiResponse.json() as OpenAIResponse;

                // Extract assistant message
                assistantMessage = data.choices[0].message.content;
                metadata = {
                    model: data.model,
                    usage: data.usage
                };
            } else {
                // If no API key, use a mock response
                assistantMessage = `I received your message: "${userMessage}"\n\n` +
                    `This is a mock response since no OpenAI API key is configured. ` +
                    `To use the real OpenAI service, set the OPENAI_API_KEY environment variable.`;

                metadata = {
                    mock: true,
                    model: "mock-gpt-4o"
                };
            }

            return {
                requestId: request.id,
                status: 'success',
                content: assistantMessage,
                timestamp: new Date(),
                metadata
            };

        } catch (error) {
            logger.error(`Error handling message request: ${(error as Error).message}`, error);
            return {
                requestId: request.id,
                status: 'error',
                content: { error: `Failed to process message: ${(error as Error).message}` },
                timestamp: new Date(),
                metadata: { error: true }
            };
        }
    }

    canHandle(request: Request): boolean {
        // This handler can handle 'message' type requests
        return request.type === 'message';
    }
}
