# Development Guide

This document provides guidelines, workflows, and best practices for developing the Cortex Chat client.

## Development Environment Setup

### Prerequisites

- Node.js (LTS version recommended)
- npm or yarn
- Modern web browser with developer tools
- Git

### Setup Steps

1. Clone the repository:

    ```bash
    git clone https://github.com/your-org/cortex-chat.git
    cd cortex-chat
    ```

2. Install dependencies:

    ```bash
    npm install
    # or
    yarn install
    ```

3. Configure development environment:

    - Copy `.env.example` to `.env`
    - Update the API endpoint and other configuration as needed

4. Start the development server:

    ```bash
    pnpm dev
    ```

    The server will start on port 5000 (http://localhost:5000)

## Development Workflow

### Branch Management

- `main` - Stable, production-ready code
- `develop` - Integration branch for feature work
- `feature/[name]` - Individual feature branches

Always branch from `develop` for new features:

```bash
git checkout develop
git pull
git checkout -b feature/my-new-feature
```

### Code Style and Linting

This project uses ESLint and Prettier to maintain consistent code style:

- Run linting: `npm run lint`
- Format code: `npm run format`
- Validate: `npm run validate` (runs linting, type checking, and tests)

Configure your editor to use the project's `.eslintrc` and `.prettierrc` files.

### Testing

We use Jest for unit tests and Cypress for integration tests:

- Run unit tests: `npm test`
- Run tests in watch mode: `npm test:watch`
- Run integration tests: `npm run cy:run`
- Open Cypress test runner: `npm run cy:open`

### Building for Production

To create a production build:

```bash
npm run build
# or
yarn build
```

This will generate optimized files in the `dist` directory.

## Project Structure

```
cortex-chat/
├── public/              # Static files
├── src/                 # Source code
│   ├── components/      # UI components
│   │   ├── chat/        # Chat-specific components
│   │   ├── workspace/   # Workspace components
│   │   └── shared/      # Shared UI components
│   ├── services/        # Service layer
│   │   ├── api/         # API communication
│   │   ├── auth/        # Authentication
│   │   └── sse/         # Server-Sent Events
│   ├── store/           # State management
│   ├── utils/           # Utility functions
│   ├── hooks/           # Custom React hooks
│   ├── types/           # TypeScript type definitions
│   ├── styles/          # Global styles
│   ├── App.tsx          # Application entry point
│   └── index.tsx        # React rendering entry point
├── docs/                # Documentation
├── tests/               # Test files
│   ├── unit/            # Unit tests
│   └── integration/     # Integration tests
├── .eslintrc            # ESLint configuration
├── .prettierrc          # Prettier configuration
├── tsconfig.json        # TypeScript configuration
├── package.json         # Project dependencies and scripts
└── README.md            # Project overview
```

## Component Development Guidelines

### Component Structure

Each component should:

1. Be focused on a single responsibility
2. Have a clear, documented API (props)
3. Handle its own loading and error states
4. Be tested independently

Example component structure:

```tsx
// MessageList.tsx
import React from 'react';
import { Message } from '../types';
import MessageItem from './MessageItem';

type MessageListProps = {
    messages: Message[];
    isLoading?: boolean;
    onRetry?: () => void;
};

export const MessageList: React.FC<MessageListProps> = ({
    messages,
    isLoading = false,
    onRetry,
}) => {
    if (isLoading) {
        return <div className="loading-indicator">Loading messages...</div>;
    }

    if (messages.length === 0) {
        return <div className="empty-state">No messages yet</div>;
    }

    return (
        <div className="message-list">
            {messages.map((message) => (
                <MessageItem key={message.id} message={message} />
            ))}
        </div>
    );
};
```

### State Management

Use appropriate state management based on scope:

- **Component state**: For UI-specific state (React useState/useReducer)
- **Application state**: For shared state (Context API or Redux)
- **Server state**: For data from API (React Query or SWR)

### Hooks

Create custom hooks to encapsulate reusable logic:

```tsx
// useConversation.ts
import { useState, useEffect } from 'react';
import { ConversationService } from '../services/api';
import { Conversation, Message } from '../types';

export function useConversation(conversationId: string) {
    const [messages, setMessages] = useState<Message[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<Error | null>(null);

    useEffect(() => {
        let mounted = true;

        async function loadMessages() {
            try {
                setIsLoading(true);
                const data = await ConversationService.getMessages(conversationId);
                if (mounted) {
                    setMessages(data);
                    setError(null);
                }
            } catch (err) {
                if (mounted) {
                    setError(err as Error);
                }
            } finally {
                if (mounted) {
                    setIsLoading(false);
                }
            }
        }

        loadMessages();

        return () => {
            mounted = false;
        };
    }, [conversationId]);

    return { messages, isLoading, error };
}
```

## API Integration

### API Client

Use a centralized API client for all HTTP requests:

```tsx
// apiClient.ts
import axios from 'axios';
import { authManager } from './authManager';

const apiClient = axios.create({
    baseURL: process.env.REACT_APP_API_URL,
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Request interceptor for adding auth token
apiClient.interceptors.request.use(
    (config) => {
        const token = authManager.getToken();
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// Response interceptor for handling errors
apiClient.interceptors.response.use(
    (response) => response,
    async (error) => {
        // Handle token refresh on 401 errors
        if (error.response?.status === 401) {
            try {
                await authManager.refreshToken();
                return apiClient(error.config);
            } catch (refreshError) {
                // Handle auth failure
                authManager.logout();
                return Promise.reject(refreshError);
            }
        }
        return Promise.reject(error);
    }
);

export default apiClient;
```

### SSE Integration

Server-Sent Events (SSE) provide real-time updates from the server. For optimal implementation, follow these patterns:

#### SSE Manager

The `SSEManager` class handles connection lifecycle, event routing, and error recovery:

```tsx
// src/services/sse/sseManager.ts
export class SSEManager {
    private baseUrl: string;
    private eventSources: Record<ChannelType, EventSource> = {};
    private reconnectAttempts: Record<ChannelType, number> = {};
    private eventListeners: Record<string, Record<string, EventCallback[]>> = {};
    private hasConnected: Record<ChannelType, boolean> = {};
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

        // Check if we already have a connection to this channel
        if (this.eventSources[type]) {
            const existingConnection = this.eventSources[type];

            // If the connection is open or connecting, don't create a new one
            if (
                existingConnection.readyState === EventSource.OPEN ||
                existingConnection.readyState === EventSource.CONNECTING
            ) {
                return existingConnection;
            }

            // Close the existing connection if it's in a bad state
            this.closeConnection(type);
        }

        // Build the SSE URL based on channel type
        const url = this.buildSseUrl(type, resourceId);

        try {
            // Create new EventSource
            const eventSource = new EventSource(url);

            // Reset connection state
            this.hasConnected[type] = false;
            this.reconnectAttempts[type] = 0;

            // Set up event handlers
            this.setupEventHandlers(eventSource, type, resourceId);

            // Store connection
            this.eventSources[type] = eventSource;

            return eventSource;
        } catch (error) {
            console.error(`[SSE:${type}] Error creating connection:`, error);
            // Only attempt reconnect if we don't already have one in progress
            if (!(type in this.reconnectAttempts) || this.reconnectAttempts[type] === 0) {
                this.reconnect(type, resourceId);
            }
            return null;
        }
    }

    // Additional methods for connection management, event handling, etc.
}
```

#### React Hook for SSE

A custom React hook simplifies SSE integration in components:

```tsx
// src/hooks/useSSE.ts
export function useSSE(
    type: ChannelType,
    resourceId: string | undefined,
    eventHandlers: Record<string, EventHandler>,
    enabled: boolean = true
) {
    const [status, setStatus] = useState<ConnectionStatus>(ConnectionStatus.DISCONNECTED);
    const [isOnline, setIsOnline] = useState<boolean>(navigator.onLine);

    // Use refs to track current values without triggering effect reruns
    const handlerRef = useRef(eventHandlers);
    const resourceIdRef = useRef(resourceId);
    const enabledRef = useRef(enabled);
    const typeRef = useRef(type);

    // Keep refs updated without triggering effects
    useEffect(() => {
        handlerRef.current = eventHandlers;
        resourceIdRef.current = resourceId;
        enabledRef.current = enabled;
        typeRef.current = type;
    }, [eventHandlers, resourceId, enabled, type]);

    // Determine whether we need to connect or disconnect
    const shouldConnect = enabled && (type === 'global' || !!resourceId);

    // Main connection effect - only triggered on enabled/disabled or type/resource changes
    useEffect(() => {
        if (!shouldConnect) {
            sseManager.closeConnection(type);
            setStatus(ConnectionStatus.DISCONNECTED);
            return;
        }

        const eventSource = connect();

        return () => {
            // Cleanup on unmount or when dependencies change
            sseManager.closeConnection(type);
        };
    }, [type, shouldConnect]);

    return { status, isConnected: status === ConnectionStatus.CONNECTED, isOnline };
}
```

#### Best Practices for SSE

1. **Memoize Event Handlers**: When using SSE in components, always memoize event handlers to prevent unnecessary reconnections:

```tsx
const messageReceivedHandler = useCallback(
    (data) => {
        console.log('Message received:', data);
        handleMessage(data);
    },
    [handleMessage]
);

const eventHandlers = useMemo(
    () => ({
        message_received: messageReceivedHandler,
        typing_indicator: handleTypingIndicator,
    }),
    [messageReceivedHandler, handleTypingIndicator]
);

useSSE('conversation', conversationId, eventHandlers);
```

2. **Connect to Multiple Channels**: Connect to all relevant channels and manage them effectively:

```tsx
// Global events (always active)
useSSE('global', undefined, globalEventHandlers, true);

// Workspace events (only when workspace is selected)
useSSE('workspace', selectedWorkspaceId, workspaceEventHandlers, !!selectedWorkspaceId);

// Conversation events (only when conversation is selected)
useSSE('conversation', selectedConversationId, conversationEventHandlers, !!selectedConversationId);
```

3. **Handle Network Status**: Monitor network status and reconnect when it changes:

```tsx
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
```

4. **Implement Proper Cleanup**: Always clean up connections when components unmount:

```tsx
useEffect(() => {
    // Setup connection
    const connection = sseManager.connect(channel, resourceId);

    return () => {
        // Clean up connection on unmount
        sseManager.disconnect(channel);
    };
}, [channel, resourceId]);
```

5. **Use Consistent Error Handling**: Implement consistent error handling for connection issues:

```tsx
// In SSE Manager
private handleConnectionError(type: ChannelType, resourceId?: string) {
  // Track number of attempts
  this.reconnectAttempts[type] = (this.reconnectAttempts[type] || 0) + 1;

  // Limit reconnection attempts
  if (this.reconnectAttempts[type] > this.MAX_RECONNECT_ATTEMPTS) {
    console.error(`[SSE:${type}] Max reconnection attempts reached`);
    return;
  }

  // Exponential backoff
  const delay = Math.min(1000 * (2 ** (this.reconnectAttempts[type] - 1)), 30000);

  setTimeout(() => {
    this.connectToSSE(type, resourceId);
  }, delay);
}
```

```

## Error Handling

Implement consistent error handling throughout the application:

1. **API Error Handling**:
   - Centralized error interceptors
   - Error classification (network, auth, validation, server)
   - Appropriate user feedback

2. **UI Error Boundaries**:
   - React Error Boundaries for component errors
   - Fallback UI components for graceful degradation

3. **Logging**:
   - Structured error logging
   - Development vs. production logging levels
   - Error reporting to monitoring services

## Performance Considerations

- Implement code splitting for larger bundles
- Use React.memo for expensive components
- Optimize re-renders with useMemo and useCallback
- Implement virtualization for long lists
- Optimize images and assets
- Set appropriate caching strategies

## Accessibility

- Follow WAI-ARIA practices
- Implement keyboard navigation
- Ensure proper contrast ratios
- Test with screen readers
- Add appropriate ARIA attributes

## Additional Resources

- [React Documentation](https://reactjs.org/docs/getting-started.html)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/intro.html)
- [WAI-ARIA Practices](https://www.w3.org/TR/wai-aria-practices-1.1/)
- [Cortex Core API Reference](../cortex-core/docs/API_REFERENCE.md)
```
