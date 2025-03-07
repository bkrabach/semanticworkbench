import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Message, SendMessageParams } from '../types';
import { API_ENDPOINTS, postData, putData, deleteData } from '../client';
import { updateConversationWithMessage } from './useConversations';

/**
 * Hook to send a new message to a conversation
 */
export function useSendMessage() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (params: SendMessageParams) => {
            return await postData<Message>(API_ENDPOINTS.messages(params.conversationId), {
                content: params.content,
                role: params.role,
            });
        },
        onSuccess: (data, variables) => {
            // Update conversation in cache with the new message
            queryClient.setQueryData(
                ['conversation', variables.conversationId],
                (oldData: unknown) => {
                    return updateConversationWithMessage(oldData as ReturnType<typeof updateConversationWithMessage>, data);
                }
            );
        },
    });
}

/**
 * Hook to update a message
 */
export function useUpdateMessage() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (params: { conversationId: string; messageId: string; content: string }) => {
            const { conversationId, messageId, content } = params;
            return await putData<Message>(
                API_ENDPOINTS.message(conversationId, messageId),
                { content }
            );
        },
        onSuccess: (data, variables) => {
            // Update conversation in cache with the updated message
            queryClient.setQueryData(
                ['conversation', variables.conversationId],
                (oldData: unknown) => {
                    return updateConversationWithMessage(oldData as ReturnType<typeof updateConversationWithMessage>, data);
                }
            );
        },
    });
}

/**
 * Hook to delete a message
 */
export function useDeleteMessage() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (params: { conversationId: string; messageId: string }) => {
            const { conversationId, messageId } = params;
            return await deleteData<void>(API_ENDPOINTS.message(conversationId, messageId));
        },
        onSuccess: (_data, variables) => {
            // Invalidate the conversation query to refetch without the deleted message
            queryClient.invalidateQueries({
                queryKey: ['conversation', variables.conversationId],
            });
        },
    });
}

/**
 * Utility function to add new partial message content during streaming
 */
export function appendStreamContent(
    message: Message,
    contentDelta: string
): Message {
    return {
        ...message,
        content: message.content + contentDelta,
        updatedAt: new Date().toISOString(),
    };
}

/**
 * Utility function to update message with tool execution info
 */
export function updateMessageWithToolExecution(
    message: Message,
    toolExecution: NonNullable<Message['toolExecutions']>[number]
): Message {
    // Check if this tool execution already exists
    const existingIndex = message.toolExecutions?.findIndex(t => t.id === toolExecution.id) ?? -1;

    if (existingIndex >= 0 && message.toolExecutions) {
        // Update existing tool execution
        const updatedToolExecutions = [...message.toolExecutions];
        updatedToolExecutions[existingIndex] = toolExecution;

        return {
            ...message,
            toolExecutions: updatedToolExecutions,
            updatedAt: new Date().toISOString(),
        };
    } else {
        // Add new tool execution
        return {
            ...message,
            toolExecutions: [...(message.toolExecutions || []), toolExecution],
            updatedAt: new Date().toISOString(),
        };
    }
}