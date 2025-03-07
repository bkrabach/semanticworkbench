# Cortex Chat Architecture Overview

_Date: 2025-03-07_

## Project Overview

Cortex Chat is a modern React-based chat interface for interacting with the Cortex Core backend. It provides a real-time, conversational user interface with support for streaming responses, tool executions, markdown rendering, and authentication. This frontend is part of the broader Cortex Platform that features a central AI core with an adaptive ecosystem of capabilities.

## Technology Stack

- **Framework**: React 19 with TypeScript
- **Build Tool**: Vite
- **Package Management**: pnpm
- **UI Library**: Fluent UI Components (@fluentui/react-components)
- **Data Fetching**: TanStack React Query (@tanstack/react-query)
- **Routing**: React Router DOM
- **API Communication**: Fetch API with custom client
- **Real-time Updates**: Server-Sent Events (SSE)
- **Content Rendering**: react-markdown with syntax highlighting

## Project Structure

```
cortex-chat/
├── src/
│   ├── api/              # API integration
│   │   ├── client.ts     # Core API client
│   │   ├── hooks/        # React Query hooks
│   │   └── types.ts      # TypeScript interfaces
│   ├── assets/           # Static assets
│   ├── components/       # React components
│   │   ├── auth/         # Authentication components
│   │   ├── common/       # Shared components
│   │   ├── conversation/ # Conversation UI components
│   │   ├── layout/       # Layout structure components
│   │   └── workspace/    # Workspace components
│   ├── context/          # React context providers
│   ├── hooks/            # Custom React hooks
│   ├── utils/            # Utility functions
│   ├── App.tsx           # Main application component
│   └── main.tsx          # Application entry point
└── ...                   # Config files
```

## Key Components

### API Layer

- **client.ts**: Centralized client for REST API communication with the Cortex Core backend
- **types.ts**: TypeScript interfaces for API models (Conversation, Message, User, etc.)
- **API hooks**: React Query hooks for data fetching, mutation, and cache management

### Authentication

- **AuthContext/AuthProvider**: Manages authentication state and token handling
- **LoginPage**: User authentication interface

### Layout

- **AppLayout**: Main application shell with navigation and content areas
- **Sidebar**: Navigation for conversations and workspaces
- **StatusBar**: System status information

### Conversation

- **ConversationView**: Main chat interface container
- **MessageList**: Renders conversation messages with appropriate styling
- **MessageInput**: User input area for sending messages
- **StreamingIndicator**: Visual indicator for streaming message state

### Common Components

- **MarkdownRenderer**: Renders markdown content with syntax highlighting
- **ToolResultView**: Displays results from tool executions

## State Management

The application uses a combination of:

1. **React Query**: For server state management (conversations, messages)
2. **React Context**: For global application state (auth, theme)
3. **Component State**: For local UI state

## Data Flow

1. User authentication is handled through token-based auth with the backend
2. Conversations and messages are fetched using React Query hooks
3. Real-time updates come through SSE connections to the backend
4. User actions trigger React Query mutations with optimistic updates
5. API responses update the React Query cache
6. Components re-render based on query data changes

## Real-time Communication

Server-Sent Events (SSE) provide real-time updates for:
- New messages
- Message updates (streaming content)
- Tool execution status changes
- Conversation modifications

## Integration with Cortex Core

Cortex Chat is the frontend user interface for the Cortex Core platform. It integrates with the Cortex Core backend through:

1. **REST API**: For CRUD operations on conversations, messages, and workspaces
2. **SSE**: For real-time updates and streaming content
3. **Token-based Authentication**: For secure API access

The Cortex Core platform follows a central AI core architecture with an adaptive ecosystem of specialized components, as described in the broader platform documentation.

## Error Handling

- API errors are normalized and propagated through React Query
- UI error states display appropriate feedback to users
- Authentication errors redirect to login
- Network disconnections trigger automatic reconnection attempts

## Security

- Token-based authentication with localStorage storage
- Token validation on application startup
- Automatic token renewal
- Secured API requests through authorization headers

## Future Improvements

- Implement offline capability with service workers
- Add end-to-end tests with Testing Library
- Create reusable component library
- Add advanced workspace collaboration features
- Integrate with additional input/output modalities (voice, canvas)