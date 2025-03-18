# Cortex Core Implementation Plan

A detailed implementation plan for enhancing the Cortex Core architecture based on the provided documentation. This plan will break down the work into sequential, testable chunks that can be implemented incrementally to minimize risk.

## Implementation Philosophy

Since we have no existing users and can freely reset the database, we can optimize for a clean implementation without worrying about backward compatibility, except for maintaining MCP server connections. This gives us freedom to make significant architectural improvements with minimal constraints.

## Phase 1: Foundation Layer (2-3 weeks)

This phase establishes the core architectural patterns that everything else will build upon.

### Task 1.1: Event System Implementation (3-4 days) ✅ COMPLETED

**Goal:** Create a centralized event system based on the publisher/subscriber pattern

**Implementation Completed:**

1. Implemented a robust `EventSystem` with standardized payload structure
2. Added comprehensive event tracing and correlation capabilities
3. Implemented pattern-based subscriptions with wildcard support
4. Added error isolation between subscribers to improve system resilience
5. Implemented event statistics monitoring endpoint

**Key Features:**

- **Standardized Event Payload**: Consistent structure for all events with source, timestamp, and tracing information
- **Event Tracing**: Each event carries a trace ID to track event chains across components
- **Event Correlation**: Related events can be linked through correlation IDs
- **Pattern-Based Routing**: Subscribe to event types with flexible wildcard patterns
- **Concurrent Processing**: Efficient handling of multiple subscribers with asyncio
- **Error Resilience**: Subscriber errors don't affect other subscribers
- **Monitoring**: Statistics endpoint for observability at `/monitoring/events/stats`

**Documentation:**

- Updated COMPONENTS.md with detailed implementation information
- Updated API_REFERENCE.md with new monitoring endpoint
- Updated OVERVIEW.md to better describe the event system architecture
- Added testing guidance to DEVELOPMENT.md

**Testing:**

- Unit tests for event publication and subscription
- Tests for pattern matching and wildcards
- Tests for error handling and isolation
- Tests for tracing and correlation
- Performance tests with many subscribers
- Tests for concurrent event publishing

### Task 1.2: Core Interfaces Definition (2-3 days)

**Goal:** Define clear interface contracts for all major components

**Implementation:**

1. Create abstract base classes for all major components
2. Document interface responsibilities and contracts
3. Implement dependency injection container

**Code Example:**

```python
# interfaces.py
import abc
from typing import Dict, Any, List, Optional, Protocol

class MessageRouterInterface(abc.ABC):
    @abc.abstractmethod
    async def route_message(self, message_type: str, message: Dict[str, Any],
                          sender_id: Optional[str] = None) -> Dict[str, Any]:
        """Route a message to the appropriate handler"""
        pass

    @abc.abstractmethod
    def register_handler(self, message_type: str, handler: Any) -> None:
        """Register a handler for a specific message type"""
        pass

class ContextManagerInterface(abc.ABC):
    @abc.abstractmethod
    async def get_context(self, session_id: str, workspace_id: str,
                        query: Optional[str] = None) -> Dict[str, Any]:
        """Get context for a session/workspace"""
        pass
```

**Testing:**

- Test interface implementations with mock objects
- Validate interface contracts with type checking
- Test dependency injection

### Task 1.3: Component Lifecycle Management (3-4 days)

**Goal:** Implement explicit initialization and shutdown sequence

**Implementation:**

1. Create a `ComponentManager` class to handle startup/shutdown
2. Implement dependency tracking between components
3. Add health checking for component monitoring

**Code Example:**

```python
# lifecycle.py
from typing import Dict, Any, List, Set, Callable
import asyncio

class ComponentManager:
    def __init__(self):
        self.components = {}
        self.dependencies = {}
        self.initialized = set()

    def register(self, name: str, component: Any,
                dependencies: List[str] = None):
        """Register a component with its dependencies"""
        self.components[name] = component
        self.dependencies[name] = set(dependencies or [])

    async def initialize_all(self):
        """Initialize all components in dependency order"""
        initialization_order = self._resolve_initialization_order()

        for component_name in initialization_order:
            component = self.components[component_name]
            if hasattr(component, 'initialize') and callable(component.initialize):
                await component.initialize()
            self.initialized.add(component_name)

    async def shutdown_all(self):
        """Shutdown all components in reverse initialization order"""
        shutdown_order = list(reversed(list(self.initialized)))

        for component_name in shutdown_order:
            component = self.components[component_name]
            if hasattr(component, 'shutdown') and callable(component.shutdown):
                await component.shutdown()
```

**Testing:**

- Test component initialization order
- Test graceful shutdown sequence
- Test dependency resolution

### Task 1.4: Database Schema and ORM Models (4-5 days)

**Goal:** Create clean, optimized database schema with ORM models

**Implementation:**

1. Design normalized database schema
2. Implement SQLAlchemy ORM models
3. Add migrations framework
4. Create repository pattern implementations

**Code Example:**

```python
# models.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    owner_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    sessions = relationship("Session", back_populates="workspace")

class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    user_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)

    workspace = relationship("Workspace", back_populates="sessions")
    messages = relationship("Message", back_populates="session")
```

**Testing:**

- Test database migration scripts
- Test CRUD operations through repositories
- Test relationship integrity

## Phase 2: Core Services (3-4 weeks)

This phase implements the essential services needed for the application.

### Task 2.1: Message Router Implementation (4-5 days)

**Goal:** Create a central message routing system

**Implementation:**

1. Implement `MessageRouter` that acts as the central hub
2. Create handler registration mechanism
3. Implement message routing logic with tracing
4. Add error handling and retry mechanisms

**Code Example:**

```python
# message_router.py
from typing import Dict, Any, Callable, Optional
import logging
import traceback

class MessageRouter:
    def __init__(self, event_system):
        self.handlers = {}
        self.event_system = event_system
        self.logger = logging.getLogger(__name__)

    def register_handler(self, message_type: str, handler: Callable):
        """Register a handler for a specific message type"""
        self.handlers[message_type] = handler

    async def route_message(self, message_type: str, message: Dict[str, Any],
                          sender_id: Optional[str] = None) -> Dict[str, Any]:
        """Route a message to the appropriate handler"""
        if message_type not in self.handlers:
            raise ValueError(f"No handler registered for message type: {message_type}")

        try:
            # Track message routing
            await self.event_system.publish(
                "message.routing.started",
                {"message_type": message_type, "sender_id": sender_id},
                "message_router"
            )

            # Call the appropriate handler
            result = await self.handlers[message_type](message, sender_id)

            # Publish successful routing
            await self.event_system.publish(
                "message.routing.completed",
                {"message_type": message_type, "sender_id": sender_id},
                "message_router"
            )

            return result
        except Exception as e:
            self.logger.error(f"Error routing message: {str(e)}")
            self.logger.debug(traceback.format_exc())

            # Publish routing error
            await self.event_system.publish(
                "message.routing.error",
                {
                    "message_type": message_type,
                    "sender_id": sender_id,
                    "error": str(e)
                },
                "message_router"
            )

            raise
```

**Testing:**

- Test message routing to correct handlers
- Test error handling and retries
- Test event publishing during routing

### Task 2.2: Context Management System (4-5 days)

**Goal:** Implement centralized conversation context handling

**Implementation:**

1. Create `ContextManager` to manage conversation context
2. Implement context retrieval, updating, and pruning
3. Add context windowing and token counting
4. Implement context serialization/deserialization

**Code Example:**

```python
# context_manager.py
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

class ContextManager:
    def __init__(self, database, event_system):
        self.db = database
        self.event_system = event_system

    async def get_context(self, session_id: str, workspace_id: str,
                        query: Optional[str] = None,
                        max_tokens: int = 4000) -> Dict[str, Any]:
        """Get context for a specific session/workspace"""
        # Retrieve recent messages
        messages = await self.db.get_recent_messages(
            session_id=session_id,
            workspace_id=workspace_id,
            limit=50  # Start with recent 50 messages
        )

        # Calculate token usage
        token_count = self._calculate_tokens(messages)

        # If we have too many tokens, prune older messages
        if token_count > max_tokens:
            messages = self._prune_messages(messages, max_tokens)

        # Format context
        context = {
            "messages": messages,
            "workspace_id": workspace_id,
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Add query-specific context if provided
        if query:
            # Add relevant memory items based on query
            memory_items = await self.db.search_memory_items(
                workspace_id=workspace_id,
                query=query,
                limit=5
            )
            context["relevant_items"] = memory_items

        return context
```

**Testing:**

- Test context retrieval with different queries
- Test token counting and pruning
- Test context updates

### Task 2.3: LLM Integration (5-6 days)

**Goal:** Create robust LLM client with advanced features

**Implementation:**

1. Create `LLMClient` with model fallback capabilities
2. Implement token counting and budget management
3. Add support for streaming responses
4. Implement comprehensive error handling and retries

**Code Example:**

```python
# llm_client.py
from typing import Dict, Any, List, Optional, AsyncGenerator
import asyncio
import time
import logging

class LLMClient:
    def __init__(self, event_system, config):
        self.event_system = event_system
        self.config = config
        self.logger = logging.getLogger(__name__)

    async def generate_response(self, messages: List[Dict[str, Any]],
                              model: Optional[str] = None,
                              streaming: bool = False,
                              max_tokens: int = 1000,
                              temperature: float = 0.7,
                              max_retries: int = 2,
                              timeout: int = 30) -> Dict[str, Any] or AsyncGenerator:
        """Generate a response from the LLM with fallback handling"""
        model = model or self.config.get("default_model")
        retry_count = 0

        while retry_count <= max_retries:
            try:
                # Track token usage
                token_estimate = self._estimate_tokens(messages)

                # Publish event for tracking
                await self.event_system.publish(
                    "llm.request.started",
                    {
                        "model": model,
                        "token_estimate": token_estimate,
                        "streaming": streaming
                    },
                    "llm_client"
                )

                # Set timeout for the request
                start_time = time.time()

                if streaming:
                    return self._generate_streaming(
                        messages, model, max_tokens, temperature
                    )
                else:
                    # Make the actual request to the LLM provider
                    response = await self._make_llm_request(
                        messages, model, max_tokens, temperature
                    )

                    # Track completion
                    await self.event_system.publish(
                        "llm.request.completed",
                        {
                            "model": model,
                            "token_estimate": token_estimate,
                            "tokens_used": response.get("usage", {}).get("total_tokens", 0),
                            "duration_ms": int((time.time() - start_time) * 1000)
                        },
                        "llm_client"
                    )

                    return response

            except Exception as e:
                retry_count += 1
                self.logger.warning(f"LLM request failed ({retry_count}/{max_retries}): {str(e)}")

                if retry_count <= max_retries:
                    # Try fallback model if available
                    fallback_model = self._get_fallback_model(model)
                    if fallback_model and fallback_model != model:
                        self.logger.info(f"Trying fallback model: {fallback_model}")
                        model = fallback_model

                    # Wait before retrying
                    await asyncio.sleep(1 * retry_count)  # Exponential backoff
                else:
                    # Publish failure event
                    await self.event_system.publish(
                        "llm.request.failed",
                        {
                            "model": model,
                            "error": str(e),
                            "retry_count": retry_count
                        },
                        "llm_client"
                    )
                    raise
```

**Testing:**

- Test response generation with different models
- Test streaming response handling
- Test fallback mechanisms and retries
- Test token counting

### Task 2.4: Session Management (3-4 days)

**Goal:** Implement robust session management with workspace context

**Implementation:**

1. Create `SessionManager` with proper session lifecycle
2. Add workspace awareness and auto-creation
3. Implement session tracking and expiration
4. Add secure authentication integration

**Code Example:**

```python
# session_manager.py
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import uuid

class SessionManager:
    def __init__(self, database, event_system):
        self.db = database
        self.event_system = event_system
        self.active_sessions = {}  # In-memory cache of active sessions

    async def create_session(self, user_id: str,
                           workspace_id: Optional[str] = None,
                           config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a new user session"""
        # If no workspace provided, create or find default workspace
        if not workspace_id:
            workspace = await self._get_default_workspace(user_id)
            workspace_id = workspace["id"]

        # Create the session record
        session_id = str(uuid.uuid4())
        session = {
            "id": session_id,
            "user_id": user_id,
            "workspace_id": workspace_id,
            "created_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            "config": config or {}
        }

        # Store in database
        await self.db.create_session(session)

        # Add to active sessions cache
        self.active_sessions[session_id] = session

        # Publish event
        await self.event_system.publish(
            "session.created",
            {"session_id": session_id, "user_id": user_id, "workspace_id": workspace_id},
            "session_manager"
        )

        return session
```

**Testing:**

- Test session creation and retrieval
- Test workspace auto-creation
- Test session expiration and cleanup
- Test concurrent session handling

## Phase 3: Communication Layer (2-3 weeks)

This phase implements the API and real-time communication components.

### Task 3.1: Unified FastAPI Server (4-5 days)

**Goal:** Create a unified server with consolidated API endpoints

**Implementation:**

1. Implement FastAPI application with lifespan management
2. Create consistent API routing structure
3. Implement proper error handling and response formatting
4. Add health check endpoints

**Code Example:**

```python
# main.py
from fastapi import FastAPI, Depends, HTTPException
from contextlib import asynccontextmanager
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create component manager
from lifecycle import ComponentManager
component_manager = ComponentManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("Starting Cortex Core")

    # Initialize all components
    await component_manager.initialize_all()

    # Store components in app state
    app.state.event_system = component_manager.get_component("event_system")
    app.state.message_router = component_manager.get_component("message_router")
    app.state.context_manager = component_manager.get_component("context_manager")
    app.state.llm_client = component_manager.get_component("llm_client")
    app.state.session_manager = component_manager.get_component("session_manager")

    yield

    # Shutdown all components
    logger.info("Shutting down Cortex Core")
    await component_manager.shutdown_all()

# Create FastAPI app
app = FastAPI(lifespan=lifespan)

# Include routers
from api.conversation import router as conversation_router
from api.workspace import router as workspace_router
from api.session import router as session_router

app.include_router(conversation_router, prefix="/api/v1/conversations", tags=["Conversations"])
app.include_router(workspace_router, prefix="/api/v1/workspaces", tags=["Workspaces"])
app.include_router(session_router, prefix="/api/v1/sessions", tags=["Sessions"])

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
```

**Testing:**

- Test API endpoint functionality
- Test server startup and shutdown
- Test error handling and response formatting

### Task 3.2: Real-Time Communication (3-4 days)

**Goal:** Implement efficient SSE/WebSocket communication

**Implementation:**

1. Create SSE endpoint for streaming updates
2. Implement message publishing to connections
3. Add channel-based subscription model
4. Implement connection management and monitoring

**Code Example:**

```python
# sse.py
from fastapi import APIRouter, Request, Response, Depends
from sse_starlette.sse import EventSourceResponse
import asyncio
from typing import Dict, Any, Optional
import json

router = APIRouter()

class SSEManager:
    def __init__(self, event_system):
        self.event_system = event_system
        self.connections = {}  # channel_id -> list of queues

    async def add_connection(self, channel_id: str) -> asyncio.Queue:
        """Add a new SSE connection for a channel"""
        if channel_id not in self.connections:
            self.connections[channel_id] = []

        # Create queue for this connection
        queue = asyncio.Queue()
        self.connections[channel_id].append(queue)

        # Subscribe to events for this channel
        async def handle_event(event):
            if event.data.get("channel_id") == channel_id:
                await queue.put({
                    "event": event.event_type,
                    "data": json.dumps(event.data)
                })

        self.event_system.subscribe("channel.*", handle_event)

        return queue

    async def remove_connection(self, channel_id: str, queue: asyncio.Queue):
        """Remove an SSE connection"""
        if channel_id in self.connections and queue in self.connections[channel_id]:
            self.connections[channel_id].remove(queue)

        # Clean up empty channels
        if channel_id in self.connections and not self.connections[channel_id]:
            del self.connections[channel_id]

@router.get("/sse/{channel_id}")
async def sse_endpoint(request: Request, channel_id: str,
                     sse_manager: SSEManager = Depends(get_sse_manager)):
    """SSE endpoint for real-time updates"""
    queue = await sse_manager.add_connection(channel_id)

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break

                # Get message from queue (with timeout to check for disconnection)
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield message
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield {"event": "ping", "data": ""}
        finally:
            # Clean up connection
            await sse_manager.remove_connection(channel_id, queue)

    return EventSourceResponse(event_generator())
```

**Testing:**

- Test SSE connection establishment
- Test message delivery to clients
- Test disconnection handling
- Test channel-based filtering

### Task 3.3: Conversation Processing (4-5 days)

**Goal:** Implement streamlined conversation handler

**Implementation:**

1. Create `ConversationProcessor` class for conversation flow
2. Implement message handling with context management
3. Add streaming support with progress tracking
4. Implement conversation state management

**Code Example:**

```python
# conversation_processor.py
from typing import Dict, Any, List, Optional, AsyncGenerator
import uuid
from datetime import datetime

class ConversationProcessor:
    def __init__(self, database, context_manager, llm_client, event_system):
        self.db = database
        self.context_manager = context_manager
        self.llm_client = llm_client
        self.event_system = event_system

    async def process_message(self, conversation_id: str, user_id: str,
                            content: str, streaming: bool = True) -> Dict[str, Any]:
        """Process a user message and generate a response"""
        # Create message ID
        message_id = str(uuid.uuid4())

        # Record user message
        user_message = {
            "id": message_id,
            "conversation_id": conversation_id,
            "role": "user",
            "content": content,
            "user_id": user_id,
            "created_at": datetime.utcnow()
        }
        await self.db.create_message(user_message)

        # Publish event
        await self.event_system.publish(
            "conversation.message.created",
            {"conversation_id": conversation_id, "message_id": message_id, "role": "user"},
            "conversation_processor"
        )

        # Get conversation context
        context = await self.context_manager.get_context(
            conversation_id=conversation_id,
            workspace_id=await self.db.get_conversation_workspace(conversation_id),
            query=content
        )

        # Format messages for LLM
        formatted_messages = self._format_messages_for_llm(context["messages"])

        # Generate response (streaming or non-streaming)
        assistant_message_id = str(uuid.uuid4())
        if streaming:
            # Create placeholder message
            assistant_message = {
                "id": assistant_message_id,
                "conversation_id": conversation_id,
                "role": "assistant",
                "content": "",
                "streaming": True,
                "created_at": datetime.utcnow()
            }
            await self.db.create_message(assistant_message)

            # Process streaming response
            final_content = await self._handle_streaming_response(
                conversation_id, assistant_message_id, formatted_messages
            )

            # Update final message
            await self.db.update_message(
                message_id=assistant_message_id,
                updates={"content": final_content, "streaming": False}
            )

            return {
                "message_id": assistant_message_id,
                "content": final_content,
                "conversation_id": conversation_id
            }
        else:
            # Generate non-streaming response
            response = await self.llm_client.generate_response(
                messages=formatted_messages,
                streaming=False
            )

            # Create assistant message
            assistant_message = {
                "id": assistant_message_id,
                "conversation_id": conversation_id,
                "role": "assistant",
                "content": response["choices"][0]["message"]["content"],
                "created_at": datetime.utcnow()
            }
            await self.db.create_message(assistant_message)

            # Publish event
            await self.event_system.publish(
                "conversation.message.created",
                {"conversation_id": conversation_id, "message_id": assistant_message_id, "role": "assistant"},
                "conversation_processor"
            )

            return assistant_message
```

**Testing:**

- Test conversation message processing
- Test streaming response handling
- Test context fetching and updates
- Test error handling

### Task 3.4: Authentication & Authorization (3-4 days)

**Goal:** Implement simplified but secure authentication

**Implementation:**

1. Create JWT-based authentication system
2. Implement API key support for programmatic access
3. Create middleware for request authentication
4. Implement role-based authorization

**Code Example:**

```python
# auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from jose import jwt, JWTError
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os

# Security schemes
oauth2_scheme = HTTPBearer()
api_key_scheme = APIKeyHeader(name="X-API-Key")

class AuthManager:
    def __init__(self, database, config):
        self.db = database
        self.config = config
        self.secret_key = config.get("jwt_secret_key", os.environ.get("JWT_SECRET_KEY"))
        self.algorithm = config.get("jwt_algorithm", "HS256")
        self.access_token_expire_minutes = config.get("access_token_expire_minutes", 60)

    def create_access_token(self, data: Dict[str, Any]) -> str:
        """Create a new JWT access token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire})

        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    async def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate a JWT token and return payload"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id = payload.get("sub")

            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                )

            # Check if user exists
            user = await self.db.get_user(user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                )

            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )

    async def validate_api_key(self, api_key: str) -> Dict[str, Any]:
        """Validate an API key and return associated user"""
        # Look up API key in database
        api_key_data = await self.db.get_api_key(api_key)

        if not api_key_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )

        # Check if API key is expired
        if api_key_data.get("expires_at") and datetime.fromisoformat(api_key_data["expires_at"]) < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key has expired",
            )

        # Get associated user
        user = await self.db.get_user(api_key_data["user_id"])
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        return {
            "sub": user["id"],
            "user": user,
            "scopes": api_key_data.get("scopes", [])
        }
```

**Testing:**

- Test token generation and validation
- Test API key validation
- Test authorization middleware
- Test role-based access control

## Phase 4: Advanced Features (3-4 weeks)

This phase implements more advanced features on top of the core foundation.

### Task 4.1: Tool Execution Framework (4-5 days)

**Goal:** Create a framework for executing tools with proper lifecycle

**Implementation:**

1. Create tool registration and discovery system
2. Implement tool execution with validation
3. Add asynchronous execution support
4. Maintain MCP client compatibility

**Code Example:**

```python
# tool_execution.py
from typing import Dict, Any, List, Optional, Callable
import asyncio
import uuid
import inspect
from pydantic import BaseModel, ValidationError

class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable

class ToolManager:
    def __init__(self, event_system, database):
        self.event_system = event_system
        self.db = database
        self.tools = {}

    def register_tool(self, tool_definition: ToolDefinition):
        """Register a new tool"""
        self.tools[tool_definition.name] = tool_definition

    async def execute_tool(self, conversation_id: str,
                         tool_name: str,
                         inputs: Dict[str, Any],
                         message_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute a tool with proper lifecycle management"""
        if tool_name not in self.tools:
            raise ValueError(f"Tool not found: {tool_name}")

        tool = self.tools[tool_name]
        execution_id = str(uuid.uuid4())

        # Create execution record
        execution = {
            "id": execution_id,
            "conversation_id": conversation_id,
            "message_id": message_id,
            "tool_name": tool_name,
            "inputs": inputs,
            "status": "pending",
            "created_at": datetime.utcnow()
        }
        await self.db.create_tool_execution(execution)

        # Publish event
        await self.event_system.publish(
            "tool.execution.started",
            {
                "execution_id": execution_id,
                "tool_name": tool_name,
                "conversation_id": conversation_id
            },
            "tool_manager"
        )

        try:
            # Validate inputs
            try:
                # If tool has a validation schema, use it
                if hasattr(tool.handler, "validate_inputs"):
                    validated_inputs = tool.handler.validate_inputs(inputs)
                else:
                    validated_inputs = inputs
            except ValidationError as e:
                # Update execution record with validation error
                await self.db.update_tool_execution(
                    execution_id,
                    {
                        "status": "failed",
                        "error": str(e),
                        "completed_at": datetime.utcnow()
                    }
                )

                # Publish validation error
                await self.event_system.publish(
                    "tool.execution.failed",
                    {
                        "execution_id": execution_id,
                        "error": "Validation error",
                        "details": str(e)
                    },
                    "tool_manager"
                )

                return {
                    "status": "error",
                    "error": "Validation error",
                    "details": str(e)
                }

            # Update status to running
            await self.db.update_tool_execution(
                execution_id,
                {"status": "running"}
            )

            # Execute the tool
            if inspect.iscoroutinefunction(tool.handler):
                result = await tool.handler(validated_inputs)
            else:
                # Run synchronous tools in a thread pool
                result = await asyncio.to_thread(tool.handler, validated_inputs)

            # Update execution record with success
            await self.db.update_tool_execution(
                execution_id,
                {
                    "status": "completed",
                    "result": result,
                    "completed_at": datetime.utcnow()
                }
            )

            # Publish success event
            await self.event_system.publish(
                "tool.execution.completed",
                {
                    "execution_id": execution_id,
                    "result": result
                },
                "tool_manager"
            )

            return {
                "status": "success",
                "result": result,
                "execution_id": execution_id
            }

        except Exception as e:
            # Update execution record with error
            await self.db.update_tool_execution(
                execution_id,
                {
                    "status": "failed",
                    "error": str(e),
                    "completed_at": datetime.utcnow()
                }
            )

            # Publish error event
            await self.event_system.publish(
                "tool.execution.failed",
                {
                    "execution_id": execution_id,
                    "error": str(e)
                },
                "tool_manager"
            )

            return {
                "status": "error",
                "error": str(e),
                "execution_id": execution_id
            }
```

**Testing:**

- Test tool registration and discovery
- Test input validation
- Test execution lifecycle
- Test error handling
- Test MCP client compatibility

### Task 4.2: Memory System Improvements (5-6 days)

**Goal:** Create advanced memory system with better context management

**Implementation:**

1. Implement hierarchical memory storage
2. Add automatic summarization capabilities
3. Create token-aware context windowing
4. Implement memory item retrieval with relevance scoring

**Code Example:**

```python
# memory_system.py
from typing import Dict, Any, List, Optional, Union
import uuid
from datetime import datetime

class MemorySystem:
    def __init__(self, database, llm_client, event_system):
        self.db = database
        self.llm_client = llm_client
        self.event_system = event_system

    async def create_memory_item(self, workspace_id: str,
                               content: Dict[str, Any],
                               item_type: str,
                               metadata: Optional[Dict[str, Any]] = None,
                               parent_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a new memory item"""
        item_id = str(uuid.uuid4())

        memory_item = {
            "id": item_id,
            "workspace_id": workspace_id,
            "content": content,
            "item_type": item_type,
            "metadata": metadata or {},
            "parent_id": parent_id,
            "created_at": datetime.utcnow()
        }

        # Store in database
        await self.db.create_memory_item(memory_item)

        # Publish event
        await self.event_system.publish(
            "memory.item.created",
            {
                "item_id": item_id,
                "workspace_id": workspace_id,
                "item_type": item_type
            },
            "memory_system"
        )

        return memory_item

    async def search_memory_items(self, workspace_id: str,
                                query: str,
                                item_types: Optional[List[str]] = None,
                                limit: int = 10) -> List[Dict[str, Any]]:
        """Search for relevant memory items"""
        # Create embedding for the query
        query_embedding = await self._create_embedding(query)

        # Search for items with similar embeddings
        items = await self.db.search_memory_items_by_embedding(
            workspace_id=workspace_id,
            embedding=query_embedding,
            item_types=item_types,
            limit=limit
        )

        return items

    async def summarize_conversation(self, conversation_id: str,
                                   max_tokens: int = 500) -> Dict[str, Any]:
        """Create a summary of a conversation"""
        # Get conversation messages
        messages = await self.db.get_conversation_messages(conversation_id)

        # Format for summarization
        formatted_content = "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in messages
        ])

        # Generate summary
        summary_prompt = f"Please provide a concise summary of the following conversation:\n\n{formatted_content}\n\nSummary:"

        summary_response = await self.llm_client.generate_response([
            {"role": "user", "content": summary_prompt}
        ], max_tokens=max_tokens)

        summary = summary_response["choices"][0]["message"]["content"]

        # Create memory item for the summary
        workspace_id = await self.db.get_conversation_workspace(conversation_id)

        summary_item = await self.create_memory_item(
            workspace_id=workspace_id,
            content={"text": summary},
            item_type="conversation_summary",
            metadata={
                "conversation_id": conversation_id,
                "message_count": len(messages)
            }
        )

        return summary_item
```

**Testing:**

- Test memory item creation and retrieval
- Test hierarchical memory relationships
- Test search functionality with embeddings
- Test automatic summarization

### Task 4.3: API Client Libraries (3-4 days)

**Goal:** Create client libraries for easy integration

**Implementation:**

1. Create Python client library
2. Implement TypeScript/JavaScript client
3. Add documentation and examples
4. Create testing utilities

**Code Example:**

```python
# python_client.py
import aiohttp
import asyncio
from typing import Dict, Any, List, Optional, Union
import json

class CortexClient:
    def __init__(self, base_url: str, api_key: Optional[str] = None, token: Optional[str] = None):
        self.base_url = base_url
        self.api_key = api_key
        self.token = token
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def _get_headers(self):
        """Get headers for requests"""
        headers = {
            "Content-Type": "application/json"
        }

        if self.api_key:
            headers["X-API-Key"] = self.api_key
        elif self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        return headers

    async def _request(self, method: str, path: str,
                     data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a request to the API"""
        if not self.session:
            self.session = aiohttp.ClientSession()

        url = f"{self.base_url}{path}"

        async with self.session.request(
            method=method,
            url=url,
            headers=self._get_headers(),
            json=data
        ) as response:
            response_data = await response.json()

            if response.status >= 400:
                raise Exception(f"API Error: {response_data.get('detail', 'Unknown error')}")

            return response_data

    async def create_conversation(self, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a new conversation"""
        data = {}
        if workspace_id:
            data["workspace_id"] = workspace_id

        return await self._request("POST", "/api/v1/conversations", data)

    async def send_message(self, conversation_id: str, content: str,
                         streaming: bool = False) -> Dict[str, Any]:
        """Send a message to a conversation"""
        data = {
            "content": content,
            "streaming": streaming
        }

        return await self._request(
            "POST",
            f"/api/v1/conversations/{conversation_id}/messages",
            data
        )

    async def get_conversation_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get all messages in a conversation"""
        return await self._request("GET", f"/api/v1/conversations/{conversation_id}/messages")
```

**Testing:**

- Test client initialization and authentication
- Test conversation creation and message sending
- Test streaming message handling
- Test error handling and retries

### Task 4.4: Testing and Documentation (4-5 days)

**Goal:** Create comprehensive testing and documentation

**Implementation:**

1. Implement test client for end-to-end testing
2. Create documentation for all APIs
3. Add user guides and tutorials
4. Implement API playground

**Code Example:**

```python
# test_client.py
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator, Callable
import json
import aiohttp
from aiohttp import ClientSession, ClientWebSocketResponse
import uuid

class TestClient:
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url
        self.api_key = api_key
        self.session = None
        self.sse_connections = {}

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def _get_headers(self):
        """Get headers for requests"""
        headers = {
            "Content-Type": "application/json"
        }

        if self.api_key:
            headers["X-API-Key"] = self.api_key

        return headers

    async def request(self, method: str, path: str,
                    data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a request to the API"""
        if not self.session:
            self.session = aiohttp.ClientSession()

        url = f"{self.base_url}{path}"

        async with self.session.request(
            method=method,
            url=url,
            headers=self._get_headers(),
            json=data
        ) as response:
            response_data = await response.json()

            if response.status >= 400:
                raise Exception(f"API Error: {response.status} - {response_data.get('detail', 'Unknown error')}")

            return response_data

    async def create_user(self, username: str, email: str,
                        password: str) -> Dict[str, Any]:
        """Create a test user"""
        data = {
            "username": username,
            "email": email,
            "password": password
        }

        return await self.request("POST", "/api/v1/test/users", data)

    async def create_api_key(self, user_id: str) -> Dict[str, Any]:
        """Create an API key for a user"""
        data = {
            "user_id": user_id
        }

        return await self.request("POST", "/api/v1/test/api-keys", data)

    async def subscribe_to_events(self, channel_id: str,
                               callback: Callable[[Dict[str, Any]], None]) -> None:
        """Subscribe to SSE events for a channel"""
        if not self.session:
            self.session = aiohttp.ClientSession()

        url = f"{self.base_url}/api/v1/sse/{channel_id}"

        # Create background task to process events
        async def event_listener():
            async with self.session.get(url, headers=self._get_headers()) as response:
                if response.status != 200:
                    raise Exception(f"SSE connection failed: {response.status}")

                # Process SSE events
                buffer = ""
                async for line in response.content:
                    line = line.decode('utf-8')
                    buffer += line

                    if buffer.endswith('\n\n'):
                        # Process complete event
                        event_data = buffer.strip().splitlines()
                        event = {}

                        for part in event_data:
                            if part.startswith('data:'):
                                event['data'] = json.loads(part[5:].strip())
                            elif part.startswith('event:'):
                                event['event'] = part[6:].strip()

                        if event.get('data'):
                            callback(event)

                        buffer = ""

        # Start background task
        task = asyncio.create_task(event_listener())
        self.sse_connections[channel_id] = task

    async def unsubscribe_from_events(self, channel_id: str) -> None:
        """Unsubscribe from SSE events"""
        if channel_id in self.sse_connections:
            self.sse_connections[channel_id].cancel()
            del self.sse_connections[channel_id]

    async def run_conversation_test(self, messages: List[str]) -> Dict[str, Any]:
        """Run a full conversation test with multiple messages"""
        # Create a conversation
        conversation = await self.request("POST", "/api/v1/conversations")
        conversation_id = conversation["id"]

        results = []

        # Send each message
        for message in messages:
            response = await self.request(
                "POST",
                f"/api/v1/conversations/{conversation_id}/messages",
                {"content": message}
            )
            results.append(response)

        # Get full conversation
        conversation_data = await self.request(
            "GET",
            f"/api/v1/conversations/{conversation_id}"
        )

        return {
            "conversation": conversation_data,
            "message_results": results
        }
```

**Testing:**

- Test API endpoints with the test client
- Test event subscription and delivery
- Test end-to-end conversation flows
- Test documentation accuracy

## Phase 5: Integration and Deployment (2-3 weeks)

This phase focuses on integrating all components and preparing for deployment.

### Task 5.1: MCP Server Compatibility (4-5 days)

**Goal:** Ensure compatibility with MCP servers

**Implementation:**

1. Create MCP client adapter
2. Implement tool registration from MCP
3. Add proper request/response handling
4. Test compatibility with existing MCP implementations

**Code Example:**

```python
# mcp_adapter.py
from typing import Dict, Any, List, Optional
import aiohttp
import json
import logging

class MCPAdapter:
    def __init__(self, event_system, tool_manager, config):
        self.event_system = event_system
        self.tool_manager = tool_manager
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.servers = {}  # server_id -> server_info

    async def initialize(self):
        """Initialize the MCP adapter"""
        # Load registered servers from database or config
        for server_config in self.config.get("mcp_servers", []):
            await self.register_server(
                server_id=server_config["id"],
                url=server_config["url"],
                api_key=server_config.get("api_key")
            )

    async def register_server(self, server_id: str, url: str,
                            api_key: Optional[str] = None) -> Dict[str, Any]:
        """Register an MCP server"""
        server_info = {
            "id": server_id,
            "url": url,
            "api_key": api_key,
            "status": "connecting"
        }

        # Store server info
        self.servers[server_id] = server_info

        try:
            # Fetch available tools
            tools = await self._fetch_server_tools(server_id)

            # Register tools with tool manager
            for tool in tools:
                await self._register_tool(server_id, tool)

            # Update server status
            server_info["status"] = "connected"
            server_info["tools"] = tools

            # Publish event
            await self.event_system.publish(
                "mcp.server.connected",
                {"server_id": server_id, "tool_count": len(tools)},
                "mcp_adapter"
            )

            return server_info
        except Exception as e:
            self.logger.error(f"Failed to connect to MCP server {server_id}: {str(e)}")
            server_info["status"] = "error"
            server_info["error"] = str(e)

            # Publish event
            await self.event_system.publish(
                "mcp.server.error",
                {"server_id": server_id, "error": str(e)},
                "mcp_adapter"
            )

            return server_info

    async def _fetch_server_tools(self, server_id: str) -> List[Dict[str, Any]]:
        """Fetch available tools from an MCP server"""
        server_info = self.servers[server_id]

        async with aiohttp.ClientSession() as session:
            headers = {}
            if server_info.get("api_key"):
                headers["X-API-Key"] = server_info["api_key"]

            async with session.get(
                f"{server_info['url']}/tools",
                headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Failed to fetch tools: {response.status} - {error_text}")

                data = await response.json()
                return data.get("tools", [])

    async def _register_tool(self, server_id: str, tool_info: Dict[str, Any]):
        """Register an MCP tool with the tool manager"""
        # Create handler for the tool
        async def tool_handler(inputs: Dict[str, Any]) -> Dict[str, Any]:
            return await self._execute_mcp_tool(
                server_id=server_id,
                tool_name=tool_info["name"],
                inputs=inputs
            )

        # Register tool with the tool manager
        self.tool_manager.register_tool({
            "name": f"mcp:{server_id}:{tool_info['name']}",
            "description": tool_info.get("description", ""),
            "parameters": tool_info.get("parameters", {}),
            "handler": tool_handler
        })

    async def _execute_mcp_tool(self, server_id: str, tool_name: str,
                              inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool on an MCP server"""
        server_info = self.servers[server_id]

        async with aiohttp.ClientSession() as session:
            headers = {"Content-Type": "application/json"}
            if server_info.get("api_key"):
                headers["X-API-Key"] = server_info["api_key"]

            async with session.post(
                f"{server_info['url']}/tools/{tool_name}/execute",
                headers=headers,
                json={"inputs": inputs}
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Tool execution failed: {response.status} - {error_text}")

                data = await response.json()
                return data.get("result", {})
```

**Testing:**

- Test MCP server registration
- Test tool discovery and registration
- Test tool execution
- Test error handling and recovery

### Task 5.2: Performance Optimization (3-4 days)

**Goal:** Optimize performance for high-volume usage

**Implementation:**

1. Implement connection pooling for database
2. Add caching for frequently accessed data
3. Optimize database queries
4. Implement load testing and benchmarking

**Code Example:**

```python
# database.py
from typing import Dict, Any, List, Optional
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager
import aiocache

class DatabaseManager:
    def __init__(self, config):
        self.config = config
        self.engine = None
        self.Session = None
        self.cache = aiocache.Cache.from_url("redis://localhost:6379/0")

    async def initialize(self):
        """Initialize the database connection"""
        # Create SQLAlchemy engine with connection pool
        self.engine = create_async_engine(
            self.config["database_url"],
            echo=self.config.get("database_echo", False),
            pool_size=self.config.get("database_pool_size", 10),
            max_overflow=self.config.get("database_max_overflow", 20),
            pool_timeout=self.config.get("database_pool_timeout", 30),
            pool_recycle=self.config.get("database_pool_recycle", 1800)
        )

        # Create session factory
        self.Session = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    @asynccontextmanager
    async def session(self):
        """Get a database session"""
        async with self.Session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get a conversation by ID with caching"""
        cache_key = f"conversation:{conversation_id}"

        # Try to get from cache
        cached = await self.cache.get(cache_key)
        if cached:
            return cached

        # Get from database
        async with self.session() as session:
            result = await session.execute(
                "SELECT * FROM conversations WHERE id = :id",
                {"id": conversation_id}
            )
            conversation = result.fetchone()

            if conversation:
                # Convert to dict
                conversation_dict = dict(conversation)

                # Cache for 5 minutes
                await self.cache.set(cache_key, conversation_dict, ttl=300)

                return conversation_dict

            return None

    async def invalidate_conversation_cache(self, conversation_id: str):
        """Invalidate conversation cache"""
        cache_key = f"conversation:{conversation_id}"
        await self.cache.delete(cache_key)
```

**Testing:**

- Test connection pooling under load
- Test cache hit/miss rates
- Test query performance
- Test system performance under load

### Task 5.3: Monitoring and Logging (3-4 days)

**Goal:** Implement comprehensive monitoring and logging

**Implementation:**

1. Implement structured logging
2. Add metrics collection
3. Create health check endpoints
4. Implement error tracking

**Code Example:**

```python
# monitoring.py
import logging
import time
from typing import Dict, Any, Optional
import json
from fastapi import FastAPI, Request, Response
import aiohttp
import asyncio
import psutil

class MetricsCollector:
    def __init__(self, app: FastAPI, event_system):
        self.app = app
        self.event_system = event_system
        self.metrics = {
            "requests": 0,
            "errors": 0,
            "request_latency": [],
            "llm_requests": 0,
            "llm_errors": 0,
            "llm_latency": [],
            "tool_executions": 0,
            "tool_errors": 0,
            "tool_latency": []
        }

        # Register middleware
        app.middleware("http")(self.metrics_middleware)

        # Subscribe to events
        event_system.subscribe("llm.request.completed", self.handle_llm_completed)
        event_system.subscribe("llm.request.failed", self.handle_llm_failed)
        event_system.subscribe("tool.execution.completed", self.handle_tool_completed)
        event_system.subscribe("tool.execution.failed", self.handle_tool_failed)

    async def metrics_middleware(self, request: Request, call_next):
        """Middleware to collect request metrics"""
        start_time = time.time()

        try:
            response = await call_next(request)
            self.metrics["requests"] += 1

            # Track latency
            latency = time.time() - start_time
            self.metrics["request_latency"].append(latency)

            # Keep only the last 1000 latency measurements
            if len(self.metrics["request_latency"]) > 1000:
                self.metrics["request_latency"] = self.metrics["request_latency"][-1000:]

            return response
        except Exception as e:
            self.metrics["errors"] += 1
            raise

    async def handle_llm_completed(self, event):
        """Handle LLM request completed event"""
        self.metrics["llm_requests"] += 1

        # Add latency if available
        if "duration_ms" in event.data:
            self.metrics["llm_latency"].append(event.data["duration_ms"] / 1000)

            # Keep only the last 1000 latency measurements
            if len(self.metrics["llm_latency"]) > 1000:
                self.metrics["llm_latency"] = self.metrics["llm_latency"][-1000:]

    async def handle_llm_failed(self, event):
        """Handle LLM request failed event"""
        self.metrics["llm_errors"] += 1

    async def handle_tool_completed(self, event):
        """Handle tool execution completed event"""
        self.metrics["tool_executions"] += 1

    async def handle_tool_failed(self, event):
        """Handle tool execution failed event"""
        self.metrics["tool_errors"] += 1
        self.metrics["tool_executions"] += 1

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        avg_request_latency = 0
        if self.metrics["request_latency"]:
            avg_request_latency = sum(self.metrics["request_latency"]) / len(self.metrics["request_latency"])

        avg_llm_latency = 0
        if self.metrics["llm_latency"]:
            avg_llm_latency = sum(self.metrics["llm_latency"]) / len(self.metrics["llm_latency"])

        # Add system metrics
        system_metrics = {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        }

        return {
            "requests": {
                "total": self.metrics["requests"],
                "errors": self.metrics["errors"],
                "avg_latency": avg_request_latency
            },
            "llm": {
                "total": self.metrics["llm_requests"],
                "errors": self.metrics["llm_errors"],
                "avg_latency": avg_llm_latency
            },
            "tools": {
                "total": self.metrics["tool_executions"],
                "errors": self.metrics["tool_errors"]
            },
            "system": system_metrics
        }
```

**Testing:**

- Test metrics collection
- Test logging output format
- Test health check endpoints
- Test under error conditions

### Task 5.4: Final Integration and Deployment (3-4 days)

**Goal:** Integrate all components and prepare for deployment

**Implementation:**

1. Create Docker and docker-compose files
2. Implement configuration management
3. Add deployment documentation
4. Create startup and shutdown scripts

**Code Example:**

```python
# config.py
from pydantic import BaseSettings, Field
from typing import Dict, Any, List, Optional
import os
import json

class AppConfig(BaseSettings):
    """Application configuration"""
    # Database settings
    database_url: str = Field(..., env="DATABASE_URL")
    database_pool_size: int = Field(10, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(20, env="DATABASE_MAX_OVERFLOW")

    # LLM settings
    default_model: str = Field("gpt-4", env="DEFAULT_MODEL")
    fallback_model: str = Field("gpt-3.5-turbo", env="FALLBACK_MODEL")
    api_key: str = Field(..., env="OPENAI_API_KEY")

    # Authentication settings
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(60, env="ACCESS_TOKEN_EXPIRE_MINUTES")

    # Redis settings
    redis_url: str = Field("redis://localhost:6379/0", env="REDIS_URL")

    # MCP server settings
    mcp_servers: List[Dict[str, Any]] = Field([], env="MCP_SERVERS")

    # Logging settings
    log_level: str = Field("INFO", env="LOG_LEVEL")

    class Config:
        env_file = ".env"

    @classmethod
    def load_from_file(cls, file_path: str) -> "AppConfig":
        """Load configuration from a JSON file"""
        if not os.path.exists(file_path):
            return cls()

        with open(file_path, "r") as f:
            config_data = json.load(f)

        return cls(**config_data)
```

**Testing:**

- Test Docker container builds
- Test configuration loading
- Test deployment process
- Test startup and shutdown procedures

## Timeline and Milestones

1. **Phase 1: Foundation Layer (2-3 weeks)**

   - Milestone 1: Event system working
   - Milestone 2: Core interfaces defined
   - Milestone 3: Component lifecycle management operational
   - Milestone 4: Database schema and ORM models implemented

2. **Phase 2: Core Services (3-4 weeks)**

   - Milestone 1: Message router working
   - Milestone 2: Context management system operational
   - Milestone 3: LLM integration working
   - Milestone 4: Session management operational

3. **Phase 3: Communication Layer (2-3 weeks)**

   - Milestone 1: FastAPI server operational
   - Milestone 2: SSE/WebSocket communication working
   - Milestone 3: Conversation processing operational
   - Milestone 4: Authentication and authorization working

4. **Phase 4: Advanced Features (3-4 weeks)**

   - Milestone 1: Tool execution framework operational
   - Milestone 2: Memory system improvements implemented
   - Milestone 3: API client libraries created
   - Milestone 4: Testing and documentation completed

5. **Phase 5: Integration and Deployment (2-3 weeks)**
   - Milestone 1: MCP server compatibility verified
   - Milestone 2: Performance optimization completed
   - Milestone 3: Monitoring and logging operational
   - Milestone 4: Deployment processes established

## Risks and Mitigations

1. **Integration Complexity**

   - **Risk**: Components may not integrate smoothly
   - **Mitigation**: Define clear interfaces, use dependency injection, and test integration points early

2. **Performance Issues**

   - **Risk**: System may not perform well under load
   - **Mitigation**: Implement performance testing early, use caching, and optimize database queries

3. **LLM Integration Challenges**

   - **Risk**: LLM integration may be unreliable
   - **Mitigation**: Implement robust error handling, retries, and fallback mechanisms

4. **MCP Compatibility**
   - **Risk**: MCP compatibility may be difficult to maintain
   - **Mitigation**: Create thorough tests for MCP integration and maintain clear interface definitions

## Conclusion

This implementation plan provides a comprehensive approach to enhancing the Cortex Core architecture. By breaking the work into sequential, testable chunks, we can minimize risk while making significant improvements to the system. The plan focuses on establishing a strong architectural foundation first, then building core services, followed by the communication layer, advanced features, and finally integration and deployment.

Each task includes clear implementation guidance with code examples to help the development team understand the intended approach. The timeline and milestones provide a roadmap for tracking progress, while the risks and mitigations section helps anticipate and address potential challenges.
