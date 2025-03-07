# Cortex Chat Component Relationships

_Date: 2025-03-07_

This document outlines the key component relationships within the Cortex Chat application, showing how data and control flow between components.

## Component Hierarchy

```
App
├── AuthProvider
│   └── ThemeProvider
│       └── AppLayout
│           ├── Sidebar
│           │   └── ConversationList
│           ├── MainContent
│           │   ├── ConversationView (route: /conversations/:conversationId)
│           │   │   ├── MessageList
│           │   │   │   └── Message
│           │   │   │       └── ToolResultView
│           │   │   └── MessageInput
│           │   └── LoginPage (route: /login)
│           └── StatusBar
```

## Data Flow Relationships

### Authentication Flow

```
AuthContext (global state) <──> AuthProvider (logic)
     ↑                             │
     │                             ↓
LoginPage (UI) ───────────> API Client (api/client.ts)
                                    │
                                    ↓
                              Backend Server
```

- **AuthProvider**: Manages authentication state and provides login/logout functions
- **LoginPage**: Collects user credentials and triggers authentication
- **AuthContext**: Stores auth state and provides it to components
- **API Client**: Handles token storage, API calls with auth headers

### Conversation Flow

```
useConversations (hook) ←→ React Query Cache ←→ useMessages (hook)
      ↑                          ↑                   ↑
      │                          │                   │
      ↓                          │                   ↓
Sidebar (list) ────────────→ ConversationView ←─── MessageInput (send)
                                   │
                                   ↓
                              MessageList
                                   │
                                   ↓
                             Message Components
```

- **useConversations**: Fetches conversation list, manages selection
- **useMessages**: Fetches messages for selected conversation, handles sending
- **Sidebar**: Displays conversations, allows selection
- **ConversationView**: Container for messages and input
- **MessageList**: Renders messages with appropriate styling
- **MessageInput**: Allows users to compose and send messages

### Real-time Updates Flow

```
useSSE (hook)
   ↑     │
   │     │ (Events)
   │     ↓
React Query Cache
   ↑     │
   │     │ (Updates)
   │     ↓
UI Components
```

- **useSSE**: Establishes SSE connection, processes events
- **React Query**: Cache automatically updates with SSE events
- **UI Components**: Re-render in response to query cache changes

## Key Interactions

### 1. User Authentication

- User enters credentials in LoginPage
- AuthProvider validates via API client
- On success, AuthContext updates
- Protected routes become accessible

### 2. Loading Conversations

- Sidebar uses useConversations hook
- React Query fetches and caches conversations
- Sidebar renders conversation list

### 3. Selecting a Conversation

- User clicks conversation in Sidebar
- Router navigates to conversation route
- ConversationView loads with conversation ID
- useMessages hook fetches messages
- MessageList renders messages

### 4. Sending a Message

- User types in MessageInput
- On submit, useMessages.sendMessage is called
- Optimistic update adds message to UI immediately
- API request sends message to backend
- SSE event notifies of message success/update
- React Query cache updates

### 5. Real-time Updates

- useSSE establishes connection with backend
- When events occur (new messages, updates)
- Events processed and normalized
- React Query cache invalidated or updated
- UI components re-render with new data

## State Management Strategy

The application uses a combination of state management approaches:

1. **React Query**
   - Manages all server state (conversations, messages)
   - Handles data fetching, caching, and synchronization
   - Provides loading, error, and success states
   - Enables optimistic updates for better UX

2. **React Context**
   - AuthContext - Manages authentication state
   - ThemeContext - Manages theme preferences
   - Provides global state accessible throughout the app

3. **Local Component State**
   - Used for UI-specific state (input values, dropdown states)
   - Managed with useState and useReducer hooks
   - Kept localized to the components that need it

This multi-tiered approach ensures separation of concerns while keeping state management efficient:
- Server state stays synchronized with the backend
- Global app state is accessible where needed
- UI state remains encapsulated in components

## Component Dependencies

Components depend on different services:

- **Layout Components**: Minimal dependencies, mostly structural
- **Auth Components**: Depend on AuthContext and API client
- **Conversation Components**: Depend on React Query, API hooks, and SSE
- **Common Components**: Presentation-focused with specialized rendering logic

## Integration with Cortex Core

The component structure is designed to integrate with the broader Cortex Platform architecture:

1. Each component focuses on presenting a specific aspect of the user interface, while the underlying data and business logic are handled by React Query hooks and the Cortex Core backend.

2. The chat interface acts as one of multiple possible input/output modalities in the Cortex Platform's adaptive ecosystem, while maintaining a clean separation of concerns.

3. The StatusBar component provides visibility into the platform's state, including connections to Domain Expert entities and MCP servers.