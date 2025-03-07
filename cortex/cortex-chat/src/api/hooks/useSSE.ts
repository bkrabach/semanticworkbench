import { useEffect, useState, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { SseEventType, Message, ToolExecution } from '../types';
import { API_BASE_URL, API_ENDPOINTS, getToken } from '../client';
import { updateConversationWithMessage } from './useConversations';
import { updateMessageWithToolExecution } from './useMessages';
// import { appendStreamContent } from './useMessages'; // Will be used for chunked message streaming

// Define connection status states
export type SseConnectionStatus =
    | 'disconnected'
    | 'connecting'
    | 'connected'
    | 'error';

interface SseOptions {
    onStatusChange?: (status: SseConnectionStatus) => void;
    onError?: (error: Error) => void;
    onEvent?: (eventType: string, data: unknown) => void;
}

/**
 * Hook for managing SSE connection to a specific conversation
 */
export function useConversationStream(
    conversationId: string | undefined,
    options?: SseOptions
) {
    const queryClient = useQueryClient();
    const [status, setStatus] = useState<SseConnectionStatus>('disconnected');
    const [error, setError] = useState<Error | null>(null);

    const updateStatus = useCallback((newStatus: SseConnectionStatus) => {
        setStatus(newStatus);
        options?.onStatusChange?.(newStatus);
    }, [options]);

    useEffect(() => {
        if (!conversationId) {
            updateStatus('disconnected');
            return;
        }

        // Initialize EventSource for SSE connection
        const token = getToken();
        if (!token) {
            setError(new Error('Authentication token is required'));
            updateStatus('error');
            return;
        }

        updateStatus('connecting');

        let eventSource: EventSource;
        try {
            const url = new URL(
                `${API_BASE_URL}${API_ENDPOINTS.sseConversation(conversationId)}`
            );
            url.searchParams.append('token', token);

            eventSource = new EventSource(url.toString());
        } catch (err) {
            const error = err instanceof Error ? err : new Error('Failed to create EventSource');
            setError(error);
            options?.onError?.(error);
            updateStatus('error');
            return;
        }

        // Connection established
        eventSource.onopen = () => {
            updateStatus('connected');
        };

        // Handle generic error
        eventSource.onerror = () => {
            const error = new Error('SSE connection error');
            setError(error);
            options?.onError?.(error);
            updateStatus('error');

            // Attempt to close the connection on error
            try {
                eventSource.close();
            } catch (closeErr) {
                console.error('Error closing SSE connection:', closeErr);
            }
        };

        // Set up event listeners for different event types

        // Message created event
        eventSource.addEventListener(SseEventType.MESSAGE_CREATED, (event) => {
            try {
                const message = JSON.parse(event.data) as Message;
                options?.onEvent?.(SseEventType.MESSAGE_CREATED, message);

                // Update the conversation with the new message
                queryClient.setQueryData(
                    ['conversation', conversationId],
                    (oldData: unknown) => {
                        return updateConversationWithMessage(
                            oldData as ReturnType<typeof updateConversationWithMessage>,
                            message
                        );
                    }
                );
            } catch (err) {
                console.error('Error processing MESSAGE_CREATED event:', err);
            }
        });

        // Message updated event (used for streaming content)
        eventSource.addEventListener(SseEventType.MESSAGE_UPDATED, (event) => {
            try {
                const message = JSON.parse(event.data) as Message;
                options?.onEvent?.(SseEventType.MESSAGE_UPDATED, message);

                // Update conversation with the updated message
                queryClient.setQueryData(
                    ['conversation', conversationId],
                    (oldData: unknown) => {
                        return updateConversationWithMessage(
                            oldData as ReturnType<typeof updateConversationWithMessage>,
                            message
                        );
                    }
                );
            } catch (err) {
                console.error('Error processing MESSAGE_UPDATED event:', err);
            }
        });

        // Tool execution started event
        eventSource.addEventListener(SseEventType.TOOL_EXECUTION_STARTED, (event) => {
            try {
                const data = JSON.parse(event.data) as {
                    messageId: string;
                    toolExecution: ToolExecution;
                };

                options?.onEvent?.(SseEventType.TOOL_EXECUTION_STARTED, data);

                // Update the message with the tool execution
                queryClient.setQueryData(
                    ['conversation', conversationId],
                    (oldData: unknown) => {
                        if (!oldData) return oldData;

                        const conversation = oldData as ReturnType<typeof updateConversationWithMessage>;
                        if (!conversation || !conversation.messages) return conversation;

                        // Find the message that contains this tool execution
                        const messageIndex = conversation.messages.findIndex(
                            m => m.id === data.messageId
                        );

                        if (messageIndex === -1) return conversation;

                        // Update the message with the tool execution
                        const updatedMessages = [...conversation.messages];
                        updatedMessages[messageIndex] = updateMessageWithToolExecution(
                            updatedMessages[messageIndex],
                            data.toolExecution
                        );

                        return {
                            ...conversation,
                            messages: updatedMessages,
                        };
                    }
                );
            } catch (err) {
                console.error('Error processing TOOL_EXECUTION_STARTED event:', err);
            }
        });

        // Tool execution completed event
        eventSource.addEventListener(SseEventType.TOOL_EXECUTION_COMPLETED, (event) => {
            try {
                const data = JSON.parse(event.data) as {
                    messageId: string;
                    toolExecution: ToolExecution;
                };

                options?.onEvent?.(SseEventType.TOOL_EXECUTION_COMPLETED, data);

                // Same update logic as TOOL_EXECUTION_STARTED
                queryClient.setQueryData(
                    ['conversation', conversationId],
                    (oldData: unknown) => {
                        if (!oldData) return oldData;

                        const conversation = oldData as ReturnType<typeof updateConversationWithMessage>;
                        if (!conversation || !conversation.messages) return conversation;

                        const messageIndex = conversation.messages.findIndex(
                            m => m.id === data.messageId
                        );

                        if (messageIndex === -1) return conversation;

                        const updatedMessages = [...conversation.messages];
                        updatedMessages[messageIndex] = updateMessageWithToolExecution(
                            updatedMessages[messageIndex],
                            data.toolExecution
                        );

                        return {
                            ...conversation,
                            messages: updatedMessages,
                        };
                    }
                );
            } catch (err) {
                console.error('Error processing TOOL_EXECUTION_COMPLETED event:', err);
            }
        });

        // Conversation updated event
        eventSource.addEventListener(SseEventType.CONVERSATION_UPDATED, (event) => {
            try {
                const conversation = JSON.parse(event.data);
                options?.onEvent?.(SseEventType.CONVERSATION_UPDATED, conversation);

                // Update the conversation in the cache
                queryClient.setQueryData(['conversation', conversationId], conversation);

                // Also update the conversations list
                queryClient.invalidateQueries({ queryKey: ['conversations'] });
            } catch (err) {
                console.error('Error processing CONVERSATION_UPDATED event:', err);
            }
        });

        // Cleanup function to close the connection when the component unmounts
        // or when the conversation ID changes
        return () => {
            try {
                eventSource.close();
                updateStatus('disconnected');
            } catch (err) {
                console.error('Error closing SSE connection during cleanup:', err);
            }
        };
    }, [conversationId, queryClient, updateStatus, options]);

    return {
        status,
        error,
        isConnected: status === 'connected',
    };
}