/**
 * Types for the Cortex Chat API
 */

// User profile
export interface User {
    id: string;
    username: string;
    email?: string;
}

// Workspace representation
export interface Workspace {
    id: string;
    name: string;
    description?: string;
    createdAt: string;
    updatedAt: string;
}

// Message roles
export type MessageRole = 'user' | 'assistant' | 'system';

// Tool execution status
export interface ToolExecution {
    id: string;
    name: string;
    parameters?: Record<string, unknown>;
    result?: string;
    error?: string;
    isComplete: boolean;
    startedAt?: string;
    completedAt?: string;
}

// Message representation
export interface Message {
    id: string;
    conversationId: string;
    role: MessageRole;
    content: string;
    createdAt: string;
    updatedAt: string;
    isComplete?: boolean;
    toolExecutions?: ToolExecution[];
}

// Conversation representation
export interface Conversation {
    id: string;
    workspaceId: string;
    title: string;
    createdAt: string;
    updatedAt: string;
    messages: Message[];
    isFavorite?: boolean;
}

// MCP Server status
export interface McpServer {
    id: string;
    name: string;
    status: 'connected' | 'disconnected' | 'error';
    lastConnected?: string;
    error?: string;
    tools?: McpTool[];
    resources?: McpResource[];
}

// MCP Tool definition
export interface McpTool {
    name: string;
    description: string;
    inputSchema: Record<string, unknown>;
}

// MCP Resource definition
export interface McpResource {
    uri: string;
    name: string;
    description?: string;
    mimeType?: string;
}

// SSE Event types
export enum SseEventType {
    MESSAGE_CREATED = 'message_created',
    MESSAGE_UPDATED = 'message_updated',
    TOOL_EXECUTION_STARTED = 'tool_execution_started',
    TOOL_EXECUTION_COMPLETED = 'tool_execution_completed',
    CONVERSATION_UPDATED = 'conversation_updated'
}

// API Request/Response types
export interface GetConversationsParams {
    workspaceId?: string;
    limit?: number;
    offset?: number;
}

export interface CreateConversationRequest {
    workspaceId: string;
    title?: string;
}

export interface SendMessageParams {
    conversationId: string;
    content: string;
    role?: MessageRole;
}

export interface SendMessageRequest {
    conversationId: string;
    content: string;
    role?: MessageRole;
}

// Authentication types
export interface LoginRequest {
    token: string;
}

export interface AuthResponse {
    token: string;
    user: User;
}

// API Error response
export interface ApiError {
    status: number;
    message: string;
    details?: unknown;
}