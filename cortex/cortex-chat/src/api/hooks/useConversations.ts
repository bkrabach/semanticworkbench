import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    Conversation,
    GetConversationsParams
} from '../types';
import {
    API_ENDPOINTS,
    fetchData,
    postData,
    putData,
    deleteData
} from '../client';

/**
 * Hook to fetch conversations list
 */
export function useConversations(params?: GetConversationsParams) {
    const queryKey = ['conversations', params];

    return useQuery({
        queryKey,
        queryFn: async () => {
            const endpoint = params?.workspaceId
                ? `${API_ENDPOINTS.workspaces}/${params.workspaceId}/conversations`
                : API_ENDPOINTS.conversations;

            const urlParams = new URLSearchParams();
            if (params?.limit) urlParams.append('limit', params.limit.toString());
            if (params?.offset) urlParams.append('offset', params.offset.toString());

            const urlWithParams = `${endpoint}${urlParams.toString() ? `?${urlParams.toString()}` : ''}`;
            return await fetchData<Conversation[]>(urlWithParams);
        },
    });
}

/**
 * Hook to fetch a single conversation by ID
 */
export function useConversation(id: string | undefined) {
    return useQuery({
        queryKey: ['conversation', id],
        queryFn: async () => {
            if (!id) throw new Error('Conversation ID is required');
            return await fetchData<Conversation>(API_ENDPOINTS.conversation(id));
        },
        enabled: !!id, // Only run query if id is provided
    });
}

/**
 * Hook to create a new conversation
 */
export function useCreateConversation() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (data: { title: string; workspaceId?: string }) => {
            return await postData<Conversation>(API_ENDPOINTS.conversations, data);
        },
        onSuccess: (newConversation) => {
            // Invalidate conversations query to refetch the list
            queryClient.invalidateQueries({ queryKey: ['conversations'] });

            // Add new conversation to cache
            queryClient.setQueryData(['conversation', newConversation.id], newConversation);
        },
    });
}

/**
 * Hook to update a conversation
 */
export function useUpdateConversation() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (data: { id: string; title?: string; isFavorite?: boolean }) => {
            const { id, ...updateData } = data;
            return await putData<Conversation>(API_ENDPOINTS.conversation(id), updateData);
        },
        onSuccess: (updatedConversation) => {
            // Update conversation in cache
            queryClient.setQueryData(['conversation', updatedConversation.id], updatedConversation);

            // Invalidate conversations list to reflect changes
            queryClient.invalidateQueries({ queryKey: ['conversations'] });
        },
    });
}

/**
 * Hook to delete a conversation
 */
export function useDeleteConversation() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (id: string) => {
            return await deleteData<void>(API_ENDPOINTS.conversation(id));
        },
        onSuccess: (_data, deletedId) => {
            // Remove conversation from cache
            queryClient.removeQueries({ queryKey: ['conversation', deletedId] });

            // Invalidate conversations list to reflect changes
            queryClient.invalidateQueries({ queryKey: ['conversations'] });
        },
    });
}

/**
 * Utility function to update conversation in the cache with a new message
 */
export function updateConversationWithMessage(
    conversation: Conversation | undefined,
    message: Conversation['messages'][0]
): Conversation | undefined {
    if (!conversation) return undefined;

    // Check if the message already exists in the conversation
    const existingMessageIndex = conversation.messages.findIndex(m => m.id === message.id);

    if (existingMessageIndex >= 0) {
        // Update existing message
        const updatedMessages = [...conversation.messages];
        updatedMessages[existingMessageIndex] = message;

        return {
            ...conversation,
            messages: updatedMessages,
            updatedAt: new Date().toISOString(),
        };
    } else {
        // Add new message
        return {
            ...conversation,
            messages: [...conversation.messages, message],
            updatedAt: new Date().toISOString(),
        };
    }
}