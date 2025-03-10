# Cortex Chat Implementation Plan

## Overview

This document outlines a comprehensive plan to implement all functionality from the reference `web-client.html` into the React-based Cortex Chat application. The implementation will prioritize clean architecture, simplicity, and adherence to the established architectural patterns while eliminating unnecessary complexity.

## Core Principles

1. **Mirroring Reference Implementation**: The implementation should directly match the functionality and patterns in `web-client.html`
2. **Architectural Alignment**: Adhere to the layered architecture (UI, Application Core, Communication Layer)
3. **Simplicity First**: Favor direct, straightforward implementations over complex abstractions
4. **Type Safety**: Leverage TypeScript for robust type checking and developer experience
5. **Performance Awareness**: Ensure efficient rendering and proper resource management
6. **Event-Driven Architecture**: Use SSE for real-time updates following ADR-001

## Current Status

The current implementation has:

1. Core SSE infrastructure with a singleton manager
2. Basic UI components for conversations and messages
3. Partial authentication flow
4. Some workspace and conversation management

However, it lacks:
1. Complete end-to-end functionality for the entire chat workflow
2. Robust error handling and reconnection strategies
3. Proper state management for optimistic updates
4. Complete alignment with the reference implementation in `web-client.html`

## Implementation Phases

### Phase 1: Authentication and Core Infrastructure

#### 1.1. Auth Service Refinement

Update `authService.ts` to precisely match the reference implementation:

```typescript
// src/services/auth/authService.ts
export async function login(email: string, password: string): Promise<User> {
  try {
    const response = await fetch(`${API_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    
    if (!response.ok) throw new Error('Authentication failed');
    
    const data = await response.json();
    
    // Store exactly as in web-client.html
    localStorage.setItem('authToken', data.access_token);
    localStorage.setItem('userId', data.user.id);
    localStorage.setItem('userEmail', data.user.email);
    
    return data.user;
  } catch (error) {
    console.error('Login error:', error);
    throw error;
  }
}

export function logout(): void {
  // Clear state
  localStorage.removeItem('authToken');
  localStorage.removeItem('userId');
  localStorage.removeItem('userEmail');
}

export function checkSession(): {isAuthenticated: boolean, user: User | null, token: string | null} {
  const token = localStorage.getItem('authToken');
  if (token) {
    return {
      isAuthenticated: true,
      user: {
        id: localStorage.getItem('userId') || '',
        email: localStorage.getItem('userEmail') || ''
      },
      token
    };
  }
  return { isAuthenticated: false, user: null, token: null };
}
```

#### 1.2. API Client Simplification

Streamline `apiClient.ts` to match the direct fetch approach in the reference:

```typescript
// src/services/api/apiClient.ts
import { API_URL } from '@/config';

function getAuthToken(): string | null {
  return localStorage.getItem('authToken');
}

async function request<T>(
  endpoint: string, 
  method: string = 'GET', 
  body?: any
): Promise<T> {
  const url = `${API_URL}${endpoint}`;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json'
  };
  
  const token = getAuthToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  const options: RequestInit = {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined
  };
  
  const response = await fetch(url, options);
  
  if (!response.ok) {
    // Extract error details from response if available
    try {
      const errorData = await response.json();
      throw new Error(errorData.message || `Request failed with status ${response.status}`);
    } catch (e) {
      throw new Error(`Request failed with status ${response.status}`);
    }
  }
  
  // For empty responses
  if (response.status === 204) {
    return {} as T;
  }
  
  return response.json();
}

export const apiClient = {
  get: <T>(endpoint: string) => request<T>(endpoint),
  post: <T>(endpoint: string, data?: any) => request<T>(endpoint, 'POST', data),
  put: <T>(endpoint: string, data?: any) => request<T>(endpoint, 'PUT', data),
  delete: <T>(endpoint: string) => request<T>(endpoint, 'DELETE')
};
```

#### 1.3. SSE Manager Refinement

Ensure the SSE manager exactly matches the reference implementation:

```typescript
// src/services/sse/sseManager.ts
export class SSEManager {
  private baseUrl: string;
  private eventSources: Record<string, EventSource> = {};
  private reconnectAttempts: Record<string, number> = {};
  private tokenProvider: () => string | null = () => null;
  private MAX_RECONNECT_ATTEMPTS = 5;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }
  
  setTokenProvider(provider: () => string | null): void {
    this.tokenProvider = provider;
  }
  
  connectToSSE(type: ChannelType, resourceId?: string): EventSource | null {
    const token = this.tokenProvider();
    
    // Verify we have a valid token before connecting
    if (!token) {
      console.error(`[SSE:${type}] Cannot connect: No auth token available`);
      return null;
    }
    
    // For non-global channels, resourceId is required
    if (type !== 'global' && (!resourceId || resourceId === 'undefined' || resourceId === 'null')) {
      console.error(`[SSE:${type}] Cannot connect: Invalid resource ID ${resourceId}`);
      return null;
    }

    // Close existing connection if any
    this.closeConnection(type);
    
    // Build the SSE URL based on channel type
    const url = this.buildSseUrl(type, resourceId);
    
    try {
      console.log(`[SSE:${type}] Connecting to ${url}`);
      
      // Create new EventSource connection - exactly as in web-client.html
      const eventSource = new EventSource(url);
      
      // Set up common event handlers
      this.setupCommonEventHandlers(eventSource, type, resourceId);
      
      // Store connection
      this.eventSources[type] = eventSource;
      
      return eventSource;
    } catch (error) {
      console.error(`[SSE:${type}] Error creating connection:`, error);
      this.reconnect(type, resourceId);
      return null;
    }
  }
  
  // ... other methods from current implementation ...
}
```

### Phase 2: Core UI Component Implementation

#### 2.1. WorkspaceList Component

```typescript
// src/components/workspace/WorkspaceList.tsx
export const WorkspaceList: React.FC<WorkspaceListProps> = ({
  workspaces,
  selectedWorkspaceId,
  onSelectWorkspace,
  onCreateWorkspace,
  isLoading
}) => {
  const styles = useStyles();
  
  const handleCreateWorkspace = async () => {
    const name = prompt('Enter workspace name:');
    if (!name) return;
    onCreateWorkspace(name);
  };
  
  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <Subtitle1>Workspaces</Subtitle1>
        <Button 
          appearance="subtle" 
          size="small" 
          icon={<AddRegular />}
          onClick={handleCreateWorkspace}
          disabled={isLoading}
        >
          New
        </Button>
      </div>
      
      {isLoading ? (
        <Spinner size="tiny" />
      ) : (
        <Select
          value={selectedWorkspaceId}
          onChange={(e, data) => onSelectWorkspace(data.value as string)}
        >
          <option value="">Select Workspace</option>
          {workspaces.map(workspace => (
            <option key={workspace.id} value={workspace.id}>
              {workspace.name}
            </option>
          ))}
        </Select>
      )}
    </div>
  );
};
```

#### 2.2. ConversationList Component

```typescript
// src/components/workspace/ConversationList.tsx
export const ConversationList: React.FC<ConversationListProps> = ({
  conversations,
  currentConversationId,
  onSelectConversation,
  onCreateConversation,
  isLoading
}) => {
  const styles = useStyles();
  
  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <Subtitle1>Conversations</Subtitle1>
        <Button
          appearance="subtle"
          size="small"
          icon={<AddRegular />}
          onClick={onCreateConversation}
          disabled={isLoading}
        >
          New
        </Button>
      </div>
      
      {isLoading ? (
        <Spinner size="tiny" />
      ) : conversations.length === 0 ? (
        <Text size={200} className={styles.emptyText}>No conversations yet</Text>
      ) : (
        <ul className={styles.list}>
          {conversations.map(conversation => (
            <li
              key={conversation.id}
              className={`${styles.item} ${conversation.id === currentConversationId ? styles.selected : ''}`}
              onClick={() => onSelectConversation(conversation.id)}
            >
              <Text>{conversation.title}</Text>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};
```

#### 2.3. Message Components Enhancement

```typescript
// src/components/chat/MessageItem.tsx
export const MessageItem: React.FC<MessageItemProps> = ({ message }) => {
  const styles = useStyles();
  
  // Function to format message content with code blocks
  const formattedContent = React.useMemo(() => {
    if (typeof message.content !== 'string') {
      return JSON.stringify(message.content, null, 2);
    }
    
    // Split by code blocks to render differently
    const parts = message.content.split(/(```[\s\S]*?```)/g);
    
    return parts.map((part, index) => {
      if (part.startsWith('```') && part.endsWith('```')) {
        // This is a code block - extract and render it
        const code = part.slice(3, -3).trim();
        return (
          <div key={index} className={styles.codeBlock}>
            {code}
          </div>
        );
      }
      // Regular text content
      return <span key={index}>{part}</span>;
    });
  }, [message.content, styles.codeBlock]);
  
  // Format timestamp
  const formattedTime = React.useMemo(() => {
    if (!message.created_at_utc) return '';
    
    const date = new Date(message.created_at_utc);
    return date.toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: true 
    });
  }, [message.created_at_utc]);
  
  // Copy message text to clipboard
  const copyToClipboard = () => {
    if (typeof message.content === 'string') {
      navigator.clipboard.writeText(message.content);
    } else {
      navigator.clipboard.writeText(JSON.stringify(message.content));
    }
  };
  
  // Render component
  return (
    // ... existing component render logic ...
  );
};
```

### Phase 3: Application State Management

#### 3.1. App Component Refactoring

Simplify and reorganize state management in App.tsx to match the reference implementation:

```typescript
// src/App.tsx
function Dashboard() {
  const { user, logout } = useAuth();
  const [workspaceState, setWorkspaceState] = useState({
    workspaces: [] as Workspace[],
    selectedWorkspaceId: null as string | null,
  });
  
  const [conversationState, setConversationState] = useState({
    conversations: [] as Conversation[],
    currentConversation: null as Conversation | null,
    messages: [] as Message[],
    isTyping: false,
  });
  
  const [loading, setLoading] = useState({
    workspaces: false,
    conversations: false,
    messages: false,
  });
  
  const [error, setError] = useState<string | null>(null);
  
  // Fetch workspaces on mount
  useEffect(() => {
    fetchWorkspaces();
  }, []);
  
  // Fetch conversations when workspace changes
  useEffect(() => {
    if (workspaceState.selectedWorkspaceId) {
      fetchConversations(workspaceState.selectedWorkspaceId);
    } else {
      setConversationState(prev => ({
        ...prev,
        conversations: [],
        currentConversation: null,
        messages: []
      }));
    }
  }, [workspaceState.selectedWorkspaceId]);
  
  // Connect to SSE channels (global, workspace, conversation)
  useSSE('global', undefined, {
    notification: handleGlobalNotification,
    system_update: handleSystemUpdate,
  });
  
  useSSE(
    'workspace',
    workspaceState.selectedWorkspaceId || undefined,
    {
      conversation_created: handleConversationCreated,
      conversation_deleted: handleConversationDeleted,
      workspace_update: handleWorkspaceUpdate,
    },
    !!workspaceState.selectedWorkspaceId
  );
  
  useSSE(
    'conversation',
    conversationState.currentConversation?.id || undefined,
    {
      message_received: handleMessageReceived,
      typing_indicator: handleTypingIndicator,
      status_update: handleStatusUpdate,
    },
    !!conversationState.currentConversation
  );
  
  // Handler functions for SSE events
  function handleMessageReceived(data: any) {
    // Implement message replacement and optimistic update logic
    // ...
  }
  
  function handleTypingIndicator(data: any) {
    setConversationState(prev => ({
      ...prev,
      isTyping: !!data.isTyping
    }));
  }
  
  // Functions for actions
  async function fetchWorkspaces() {
    // ...
  }
  
  async function createWorkspace(name: string) {
    // ...
  }
  
  async function sendMessage(content: string) {
    // ...
  }
  
  // ...more handler functions...
  
  return (
    // ... component rendering ...
  );
}
```

#### 3.2. Implement Service Functions for API Calls

Create dedicated service functions for all API operations:

```typescript
// src/services/workspace/workspaceService.ts
import { apiClient } from '@/services/api/apiClient';
import { Workspace } from '@/types';

export async function getWorkspaces(): Promise<Workspace[]> {
  try {
    const response = await apiClient.get<{ workspaces: Workspace[] }>('/workspaces');
    return response.workspaces || [];
  } catch (error) {
    console.error('Error fetching workspaces:', error);
    throw error;
  }
}

export async function createWorkspace(name: string): Promise<Workspace> {
  try {
    const response = await apiClient.post<Workspace>('/workspaces', {
      name,
      config: {
        default_modality: 'chat',
        sharingEnabled: false,
        retentionDays: 90
      }
    });
    return response;
  } catch (error) {
    console.error('Error creating workspace:', error);
    throw error;
  }
}

// ...more service functions...
```

```typescript
// src/services/conversation/conversationService.ts
import { apiClient } from '@/services/api/apiClient';
import { Conversation, Message } from '@/types';

export async function getConversations(workspaceId: string): Promise<Conversation[]> {
  try {
    const response = await apiClient.get<{ conversations: Conversation[] }>(
      `/workspaces/${workspaceId}/conversations`
    );
    return response.conversations || [];
  } catch (error) {
    console.error('Error fetching conversations:', error);
    throw error;
  }
}

export async function createConversation(
  workspaceId: string,
  title?: string
): Promise<Conversation> {
  try {
    const defaultTitle = `Chat ${new Date().toLocaleTimeString()}`;
    
    const response = await apiClient.post<Conversation>(
      `/workspaces/${workspaceId}/conversations`,
      {
        modality: 'chat',
        title: title || defaultTitle
      }
    );
    
    return response;
  } catch (error) {
    console.error('Error creating conversation:', error);
    throw error;
  }
}

export async function getConversation(conversationId: string): Promise<Conversation> {
  try {
    return await apiClient.get<Conversation>(`/conversations/${conversationId}`);
  } catch (error) {
    console.error('Error fetching conversation:', error);
    throw error;
  }
}

export async function getMessages(conversationId: string): Promise<Message[]> {
  try {
    const response = await apiClient.get<{ messages: Message[] }>(
      `/conversations/${conversationId}/messages`
    );
    return response.messages || [];
  } catch (error) {
    console.error('Error fetching messages:', error);
    throw error;
  }
}

export async function sendMessage(
  conversationId: string,
  content: string,
  role: 'user' | 'system' = 'user'
): Promise<Message> {
  try {
    return await apiClient.post<Message>(
      `/conversations/${conversationId}/messages`,
      { content, role }
    );
  } catch (error) {
    console.error('Error sending message:', error);
    throw error;
  }
}

// ...more service functions...
```

### Phase 4: Message Handling and UI Updates

#### 4.1. Implement Message Optimistic Updates

Enhance App.tsx with optimistic update handling:

```typescript
async function handleSendMessage(content: string) {
  if (!conversationState.currentConversation) return;
  
  try {
    // Create temporary message
    const tempMessage: Message = {
      id: `temp-${Date.now()}`,
      conversation_id: conversationState.currentConversation.id,
      content: content,
      role: 'user',
      created_at_utc: new Date().toISOString()
    };
    
    // Add to UI immediately (optimistic update)
    setConversationState(prev => ({
      ...prev,
      messages: [...prev.messages, tempMessage]
    }));
    
    // Send to server
    await sendMessage(conversationState.currentConversation.id, content);
    
    // Set typing indicator (actual response will come via SSE)
    setConversationState(prev => ({
      ...prev,
      isTyping: true
    }));
  } catch (error) {
    setError('Failed to send message');
    // Remove optimistic message
    setConversationState(prev => ({
      ...prev,
      messages: prev.messages.filter(m => !m.id.toString().startsWith('temp-')),
      isTyping: false
    }));
  }
}

// Handle message_received SSE event
function handleMessageReceived(message: Message) {
  if (!conversationState.currentConversation || 
      conversationState.currentConversation.id !== message.conversation_id) {
    return;
  }
  
  setConversationState(prev => {
    // Check if we already have this message by ID
    const hasMessage = prev.messages.some(m => m.id === message.id);
    if (hasMessage) return prev;
    
    let updatedMessages;
    
    // For user messages, check if we have a temporary message to replace
    if (message.role === 'user') {
      const tempIndex = prev.messages.findIndex(m => 
        m.role === 'user' && 
        m.content === message.content && 
        m.id.toString().startsWith('temp-')
      );
      
      if (tempIndex !== -1) {
        // Replace temp message with server version
        updatedMessages = [...prev.messages];
        updatedMessages[tempIndex] = message;
      } else {
        updatedMessages = [...prev.messages, message];
      }
    } else {
      updatedMessages = [...prev.messages, message];
      
      // Hide typing indicator for assistant messages
      if (message.role === 'assistant') {
        return {
          ...prev,
          messages: updatedMessages,
          isTyping: false
        };
      }
    }
    
    return {
      ...prev,
      messages: updatedMessages
    };
  });
}
```

#### 4.2. Add Typing Indicator Component

```typescript
// src/components/chat/TypingIndicator.tsx
interface TypingIndicatorProps {
  isVisible: boolean;
}

export const TypingIndicator: React.FC<TypingIndicatorProps> = ({ isVisible }) => {
  const styles = useStyles();
  
  if (!isVisible) return null;
  
  return (
    <div className={styles.container}>
      <Avatar size={24} name="Assistant" color="brand" />
      <div className={styles.dots}>
        <div className={styles.dot}></div>
        <div className={`${styles.dot} ${styles.dot2}`}></div>
        <div className={`${styles.dot} ${styles.dot3}`}></div>
      </div>
    </div>
  );
};
```

#### 4.3. Improve Message Formatting

```typescript
// src/utils/formatters.ts
export function formatMessageContent(content: string | object): string {
  if (typeof content !== 'string') {
    return JSON.stringify(content, null, 2);
  }
  
  // Convert markdown code blocks to HTML
  const formattedContent = content
    .replace(/```([^`]+)```/g, '<pre><code>$1</code></pre>');
  
  return formattedContent;
}

export function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    hour12: true
  });
}
```

### Phase 5: Error Handling and Edge Cases

#### 5.1. Add Comprehensive Error Boundaries

```typescript
// src/components/shared/ErrorBoundary.tsx
export class ErrorBoundary extends React.Component<
  {children: React.ReactNode, fallback?: React.ReactNode},
  {hasError: boolean}
> {
  constructor(props: {children: React.ReactNode, fallback?: React.ReactNode}) {
    super(props);
    this.state = { hasError: false };
  }
  
  static getDerivedStateFromError(error: any) {
    return { hasError: true };
  }
  
  componentDidCatch(error: any, errorInfo: any) {
    console.error('Component error:', error, errorInfo);
  }
  
  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div style={{ padding: '1rem', margin: '1rem', border: '1px solid #f0ad4e' }}>
          <h3>Something went wrong</h3>
          <p>There was an error rendering this component. Try refreshing the page.</p>
          <button onClick={() => this.setState({ hasError: false })}>
            Try again
          </button>
        </div>
      );
    }
    
    return this.props.children;
  }
}
```

#### 5.2. Add Network Status Monitoring

```typescript
// src/hooks/useNetworkStatus.ts
export function useNetworkStatus() {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  
  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);
  
  return { isOnline };
}
```

#### 5.3. Implement SSE Reconnection Strategy

Enhance useSSE hook with better reconnection handling:

```typescript
export function useSSE(
  type: ChannelType,
  resourceId: string | undefined,
  eventHandlers: Record<string, EventHandler>,
  enabled: boolean = true
) {
  const [status, setStatus] = useState<ConnectionStatus>(ConnectionStatus.DISCONNECTED);
  const { isOnline } = useNetworkStatus();
  
  // Reconnect when network status changes to online
  useEffect(() => {
    if (isOnline && enabled && status === ConnectionStatus.ERROR) {
      console.log(`[useSSE:${type}] Network reconnected, reestablishing connection`);
      sseManager.connectToSSE(type, resourceId);
    }
  }, [isOnline, enabled, status, type, resourceId]);
  
  // Rest of hook implementation...
}
```

## Implementation Schedule

### Week 1: Foundation and Core Infrastructure

#### Day 1-2: Authentication and API Layer
- Update Auth Context to match reference implementation
- Simplify API client for direct fetch operations
- Ensure SSE manager matches reference implementation exactly
- Implement token provider mechanism

#### Day 3-4: Component Foundations
- Implement WorkspaceList component
- Implement ConversationList component
- Enhance Message components (MessageList, MessageItem)
- Implement TypingIndicator component

#### Day 5: State Management
- Refactor App.tsx for cleaner state management
- Implement service functions for all API operations
- Add error handling to all service calls

### Week 2: Feature Implementation and Polish

#### Day 1-2: Message Handling
- Implement optimistic updates for messages
- Add message replacement logic
- Enhance message formatting
- Implement typing indicators

#### Day 3: Error Handling and Edge Cases
- Add error boundaries
- Implement network status monitoring
- Enhance SSE reconnection strategy
- Add loading states to all operations

#### Day 4-5: Testing and Refinement
- Test all user flows end-to-end
- Verify SSE connections and reconnection
- Optimize performance and rendering
- Fix edge cases and polish UI

## Success Criteria

The implementation will be considered successful when:

1. All functionality from web-client.html is working properly in the React app:
   - Authentication flow
   - Workspace management
   - Conversation management
   - Real-time messaging with SSE
   - Typing indicators
   - Optimistic updates

2. The architecture is clean and follows the established patterns:
   - Clear separation of concerns
   - Proper error handling
   - Type safety throughout
   - Performance optimization

3. The application is stable and handles edge cases:
   - Network interruptions
   - Authentication issues
   - Resource cleanup
   - Error recovery

4. The implementation aligns with the core principles:
   - Simplicity
   - Clean design
   - Direct mapping to reference implementation
   - Elimination of unnecessary complexity

## Technical Considerations

### SSE Connection Management

The SSE implementation will follow ADR-001 and the reference implementation in web-client.html:

1. Connection Types
   - Global events for system-wide notifications
   - Workspace events for workspace-specific updates
   - Conversation events for real-time messages

2. Connection Lifecycle
   - Create connections when components mount
   - Properly clean up on unmount
   - Reconnect on network issues or errors

3. Event Handling
   - Type-safe event handlers
   - Proper error boundaries for event processing
   - Clear logging for debugging

### State Management

The application will use a combination of:

1. React Context for global state (authentication)
2. Component state for UI-specific concerns
3. Custom hooks for reusable logic
4. Explicit props for component communication

### Error Handling Strategy

A multi-layered approach to error handling:

1. Service Layer
   - Try/catch blocks in all API calls
   - Error logging and propagation
   - Structured error responses

2. Component Layer
   - Error boundaries for UI components
   - Loading/error states for async operations
   - User-friendly error messages

3. SSE Layer
   - Reconnection strategies
   - Error event handling
   - Connection status tracking

### Performance Considerations

1. Minimize Re-renders
   - Proper use of React.memo
   - Careful state updates
   - Object reference stability

2. Optimize Resource Usage
   - Proper cleanup of SSE connections
   - Efficient DOM updates
   - Avoid unnecessary API calls

3. User Experience
   - Optimistic updates for immediate feedback
   - Clear loading indicators
   - Smooth transitions