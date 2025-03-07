# Cortex Platform Codebase Structure

This document provides an overview of the Cortex Platform's codebase organization, highlighting the key components of both the backend (cortex-core) and frontend (cortex-chat) projects.

## Cortex Core (Backend)

### Directory Structure

```
cortex-core/
├── cortex_core/
│   ├── __init__.py
│   ├── api/                  # API layer and endpoints
│   │   ├── __init__.py
│   │   ├── endpoints.py      # FastAPI routes
│   │   └── routes/           # Additional route modules
│   ├── core/                 # Core business logic
│   │   ├── __init__.py
│   │   ├── auth.py           # Authentication
│   │   ├── config.py         # Configuration
│   │   ├── conversation.py   # Conversation handling
│   │   ├── llm.py            # LLM integration
│   │   ├── mcp_client.py     # MCP tool integration
│   │   ├── memory.py         # Memory system
│   │   ├── router.py         # Message routing
│   │   └── sse.py            # Server-Sent Events
│   ├── db/                   # Database layer
│   │   ├── __init__.py
│   │   ├── database.py       # DB connection
│   │   └── models.py         # SQLAlchemy models
│   ├── main.py               # Application entry point
│   ├── models/               # Data models
│   │   ├── __init__.py
│   │   └── schemas.py        # Pydantic models
│   └── utils/                # Utility functions
│       └── __init__.py
├── docs/                     # Documentation
├── tests/                    # Test suites
│   ├── test_api/
│   └── test_core/
├── pyproject.toml            # Project configuration
└── README.md                 # Project overview
```

### Key Components

#### API Layer

- **endpoints.py**: Defines RESTful API endpoints using FastAPI
- **routes/**: Additional route modules organized by feature

#### Core Services

- **auth.py**: JWT-based authentication and authorization
- **config.py**: Application configuration management
- **conversation.py**: Handles conversation state and message processing
- **llm.py**: Interfaces with language models via LiteLLM
- **mcp_client.py**: Manages tool execution through MCP protocol
- **memory.py**: Stores and retrieves conversation history
- **router.py**: Routes messages between components
- **sse.py**: Manages real-time events via Server-Sent Events

#### Database Layer

- **database.py**: Database connection and session management
- **models.py**: SQLAlchemy ORM models defining the data schema:
  - User: Authentication and user information
  - Conversation: Chat conversation metadata
  - Message: Individual messages within conversations
  - ToolExecution: Tool call records and results
  - MemoryEntry: Long-term memory storage

#### Data Models

- **schemas.py**: Pydantic models for request/response validation and serialization

## Cortex Chat (Frontend)

### Directory Structure

```
cortex-chat/
├── public/                   # Static assets
├── src/
│   ├── api/                  # API integration
│   │   ├── client.ts         # API client
│   │   ├── hooks/            # React Query hooks
│   │   │   ├── useConversations.ts
│   │   │   ├── useMessages.ts
│   │   │   └── useSSE.ts
│   │   └── types.ts          # API types
│   ├── assets/               # Images and icons
│   ├── components/           # React components
│   │   ├── auth/             # Authentication
│   │   │   └── LoginPage.tsx
│   │   ├── common/           # Shared components
│   │   │   ├── MarkdownRenderer.tsx
│   │   │   └── ToolResultView.tsx
│   │   ├── conversation/     # Conversation UI
│   │   │   ├── ConversationView.tsx
│   │   │   ├── MessageInput.tsx
│   │   │   ├── MessageList.tsx
│   │   │   └── StreamingIndicator.tsx
│   │   ├── layout/           # Layout components
│   │   │   ├── AppLayout.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── StatusBar.tsx
│   │   └── workspace/        # Workspace components
│   ├── context/              # React context providers
│   │   ├── AuthContext.tsx
│   │   ├── AuthProvider.tsx
│   │   ├── ThemeContext.tsx
│   │   ├── ThemeProvider.tsx
│   │   ├── auth-context.ts
│   │   └── theme-context.ts
│   ├── hooks/                # Custom React hooks
│   │   ├── useAuth.ts
│   │   └── useTheme.ts
│   ├── App.css               # App styles
│   ├── App.tsx               # App component
│   ├── index.css             # Global styles
│   ├── main.tsx              # Application entry point
│   ├── utils/                # Utility functions
│   └── vite-env.d.ts         # Vite environment
├── .eslintrc.js              # ESLint config
├── index.html                # HTML template
├── package.json              # Dependencies and scripts
├── pnpm-lock.yaml           # Package lock
├── tsconfig.json             # TypeScript config
└── vite.config.ts            # Vite config
```

### Key Components

#### API Integration

- **client.ts**: Axios-based API client for backend communication
- **hooks/**: React Query hooks for data fetching and state management:
  - **useConversations.ts**: Fetch and manage conversations
  - **useMessages.ts**: Send and receive messages
  - **useSSE.ts**: Establish and manage SSE connections
- **types.ts**: TypeScript interfaces for API data

#### React Components

- **auth/**: Authentication components
  - **LoginPage.tsx**: User login interface
- **common/**: Shared UI components
  - **MarkdownRenderer.tsx**: Renders markdown content
  - **ToolResultView.tsx**: Displays tool execution results
- **conversation/**: Conversation interface
  - **ConversationView.tsx**: Main conversation container
  - **MessageInput.tsx**: User input field
  - **MessageList.tsx**: Message history display
  - **StreamingIndicator.tsx**: Real-time typing indicator
- **layout/**: Application layout
  - **AppLayout.tsx**: Main app structure
  - **Sidebar.tsx**: Navigation sidebar
  - **StatusBar.tsx**: Status information display

#### Context Providers

- **AuthContext.tsx/AuthProvider.tsx**: Authentication state management
- **ThemeContext.tsx/ThemeProvider.tsx**: Theme preferences (light/dark)

#### Custom Hooks

- **useAuth.ts**: Authentication utilities
- **useTheme.ts**: Theme management functions

## Technology Stack

### Backend (Cortex Core)

- **Language**: Python
- **Web Framework**: FastAPI
- **Database**: SQLAlchemy with SQLite
- **Authentication**: JWT
- **Real-time**: Server-Sent Events (SSE)
- **LLM Integration**: LiteLLM
- **Package Management**: uv

### Frontend (Cortex Chat)

- **Language**: TypeScript
- **Framework**: React 19
- **Routing**: React Router
- **State Management**: React Query
- **UI Framework**: Fluent UI v9
- **HTTP Client**: axios
- **Build Tool**: Vite
- **Package Management**: pnpm

## Development Tools

### Backend

- **Formatting**: black
- **Linting**: flake8
- **Type Checking**: mypy
- **Testing**: pytest

### Frontend

- **Linting**: ESLint
- **Type Checking**: TypeScript
- **Format**: Prettier (via ESLint)

## Communication Flow

1. The frontend sends user messages to the backend via REST API
2. The backend processes messages through the Cortex Core
3. LLM integration generates responses, potentially using tools
4. Real-time updates are streamed to the frontend via SSE
5. The frontend renders messages and updates the conversation view
6. Memory is maintained for context across the conversation session