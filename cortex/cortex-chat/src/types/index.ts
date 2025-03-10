// User types
export interface User {
    id: string;
    email: string;
    name?: string;
}

// Authentication types
export interface AuthState {
    user: User | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    error: string | null;
}

// Workspace types
export interface Workspace {
    id: string;
    name: string;
    config?: {
        default_modality: string;
        sharingEnabled: boolean;
        retentionDays: number;
    };
    created_at_utc: string;
}

// Conversation types
export interface Conversation {
    id: string;
    title: string;
    workspace_id: string;
    modality: string;
    created_at_utc: string;
    messages?: Message[];
}

// Message types
export interface Message {
    id: string;
    conversation_id: string;
    content: string;
    role: 'user' | 'assistant' | 'system';
    created_at_utc: string;
    metadata?: Record<string, any>;
}

// SSE types
export type ChannelType = 'global' | 'workspace' | 'conversation';

export interface SSEEvent {
    id?: string;
    type: string;
    data: any;
    created_at_utc: string;
}

export enum ConnectionStatus {
    CONNECTING = 'connecting',
    CONNECTED = 'connected',
    DISCONNECTED = 'disconnected',
    ERROR = 'error',
    RECONNECTING = 'reconnecting',
}

// API response types
export interface ApiResponse<T> {
    data: T;
    status: number;
    message?: string;
}

export interface ErrorResponse {
    error: {
        code: string;
        message: string;
        details?: Record<string, any>;
    };
}