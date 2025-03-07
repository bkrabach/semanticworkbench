# Cortex Chat API Integration

_Date: 2025-03-07_

This document describes how the Cortex Chat frontend integrates with the Cortex Core backend API, focusing on the frontend implementation details. For complete API specifications, refer to the [Client API Reference](../../cortex-core/docs/CLIENT_API_REFERENCE.md) in the Cortex Core documentation.

## API Client Structure

The API integration is built around a centralized client in `src/api/client.ts` that provides:

- Base URL configuration
- Authentication token management
- Standardized request/response handling
- Error normalization

```typescript
// Core fetch functions
export async function fetchData<T>(url: string): Promise<T>;
export async function postData<T>(url: string, data?: unknown): Promise<T>;
export async function putData<T>(url: string, data?: unknown): Promise<T>;
export async function deleteData<T>(url: string): Promise<T>;

// Authentication-specific functions
export function getToken(): string | null;
export function setToken(token: string): void;
export function clearToken(): void;
export function isAuthenticated(): boolean;
export async function authenticateWithToken(token: string): Promise<AuthResponse>;
export async function validateToken(): Promise<boolean>;
```

## API Endpoints

All API endpoints are centrally defined in `api/client.ts`:

```typescript
export const API_ENDPOINTS = {
    conversations: '/api/conversations',
    conversation: (id: string) => `/api/conversations/${id}`,
    messages: (conversationId: string) => `/api/conversations/${conversationId}/messages`,
    message: (conversationId: string, messageId: string) => 
        `/api/conversations/${conversationId}/messages/${messageId}`,
    workspaces: '/api/workspaces',
    workspace: (id: string) => `/api/workspaces/${id}`,
    auth: '/api/auth',
    token: '/api/auth/token',
    sseConversation: (id: string) => `/api/sse/conversations/${id}`,
    mcpServers: '/api/mcp-servers',
};
```

## Data Models

TypeScript interfaces in `src/api/types.ts` define the data structures used to communicate with the Cortex Core API:

- `User`: User profile information
- `Workspace`: Workspace representation
- `Conversation`: Conversation with messages
- `Message`: Individual message in a conversation
- `ToolExecution`: Tool invocation and results
- `McpServer`: MCP server connection status
- `McpTool`: Tool definition from MCP
- `McpResource`: Resource available from MCP

These interfaces align with the models defined in the Cortex Core API documentation. See the backend's [Client API Reference](../../cortex-core/docs/CLIENT_API_REFERENCE.md) for complete model definitions.

## React Query Hooks

The API layer is exposed to components through React Query hooks that provide a clean, declarative way to interact with the backend:

### Conversations

```typescript
// In src/api/hooks/useConversations.ts
export function useConversations(params?: GetConversationsParams);
export function useConversation(conversationId: string);
export function useCreateConversation();
export function useUpdateConversation();
export function useDeleteConversation();
```

### Messages

```typescript
// In src/api/hooks/useMessages.ts
export function useMessages(conversationId: string);
export function useSendMessage();
```

### Real-time Updates

```typescript
// In src/api/hooks/useSSE.ts
export function useSSE(conversationId: string);
```

## Authentication Flow

1. The user provides a token through the LoginPage
2. `authenticateWithToken` validates the token with the backend
3. On success, the token is stored in localStorage
4. API requests include the token in the Authorization header
5. Token validation occurs on application startup
6. If a token becomes invalid, the user is redirected to login

## Real-time Communication with SSE

The application uses Server-Sent Events (SSE) for real-time updates:

1. The `useSSE` hook establishes an SSE connection when a conversation is active
2. Events are processed based on their type (defined in `SseEventType` enum)
3. React Query cache is updated based on event data
4. UI components re-render with the updated data

Event types include:
- `MESSAGE_CREATED`: A new message was added
- `MESSAGE_UPDATED`: A message was modified
- `TOOL_EXECUTION_STARTED`: A tool began execution
- `TOOL_EXECUTION_COMPLETED`: A tool completed execution
- `CONVERSATION_UPDATED`: Conversation metadata changed

## Error Handling

The API client normalizes errors into a consistent `ApiError` format:

```typescript
export interface ApiError {
    status: number;
    message: string;
    details?: unknown;
}
```

React Query handles these errors through:
- `onError` callbacks
- Error states in query results
- Global error handlers

## Integration with Cortex Core Architecture

The Cortex Chat frontend is designed to integrate seamlessly with the broader Cortex Platform architecture, which follows a central AI core with an adaptive ecosystem model:

1. **Connectivity with the Central Core**: The frontend communicates with the Cortex Core, which serves as the central orchestrator for all platform capabilities.

2. **Access to Domain Expert Entities**: Through the API, the frontend can leverage specialized Domain Expert modules like Code Assistant or Deep Research, which are autonomously managed by the Cortex Core.

3. **Input/Output Modality**: The chat interface represents one of multiple potential input/output modalities in the platform's ecosystem, with the architecture supporting future expansion to voice, canvas, and other interfaces.

## Example Usage

```typescript
// Component using API hooks
function ConversationPage({ conversationId }) {
  // Get conversation data
  const { data: conversation, isLoading } = useConversation(conversationId);
  
  // Get messages
  const { data: messages } = useMessages(conversationId);
  
  // Send message function
  const { mutate: sendMessage } = useSendMessage();
  
  // Connect to real-time updates
  useSSE(conversationId);
  
  // Handler for sending a message
  const handleSend = (content) => {
    sendMessage({ conversationId, content });
  };
  
  // Render UI with data
  if (isLoading) return <LoadingIndicator />;
  
  return (
    <div>
      <h1>{conversation.title}</h1>
      <MessageList messages={messages} />
      <MessageInput onSend={handleSend} />
    </div>
  );
}
```

## Further Reference

For detailed information about the backend API that this frontend integrates with, see the Cortex Core documentation:

- [Client API Reference](../../cortex-core/docs/CLIENT_API_REFERENCE.md)
- [Client Integration Guide](../../cortex-core/docs/CLIENT_INTEGRATION_GUIDE.md)
- [Client Quickstart](../../cortex-core/docs/CLIENT_QUICKSTART.md)