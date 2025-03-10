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
   npm start
   # or 
   yarn start
   ```

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
  onRetry 
}) => {
  if (isLoading) {
    return <div className="loading-indicator">Loading messages...</div>;
  }
  
  if (messages.length === 0) {
    return <div className="empty-state">No messages yet</div>;
  }
  
  return (
    <div className="message-list">
      {messages.map(message => (
        <MessageItem 
          key={message.id} 
          message={message} 
        />
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

Handle Server-Sent Events connections with proper lifecycle management:

```tsx
// sseManager.ts
export class SSEManager {
  private eventSources: Record<string, EventSource> = {};
  private eventHandlers: Record<string, Function[]> = {};
  private reconnectTimeouts: Record<string, NodeJS.Timeout> = {};
  
  connect(channel: string, resourceId?: string) {
    const key = resourceId ? `${channel}_${resourceId}` : channel;
    const url = this.buildUrl(channel, resourceId);
    
    // Close existing connection if any
    this.close(key);
    
    try {
      const eventSource = new EventSource(url);
      
      eventSource.onopen = () => {
        console.log(`Connected to ${channel} events`);
        // Clear any reconnect timeouts
        if (this.reconnectTimeouts[key]) {
          clearTimeout(this.reconnectTimeouts[key]);
          delete this.reconnectTimeouts[key];
        }
      };
      
      eventSource.onerror = (error) => {
        console.error(`Error in ${channel} events:`, error);
        this.handleConnectionError(key, channel, resourceId);
      };
      
      // Store the connection
      this.eventSources[key] = eventSource;
      
      return eventSource;
    } catch (error) {
      console.error(`Error creating SSE connection:`, error);
      this.handleConnectionError(key, channel, resourceId);
      return null;
    }
  }
  
  // Additional methods for connection management, event handling, etc.
}
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