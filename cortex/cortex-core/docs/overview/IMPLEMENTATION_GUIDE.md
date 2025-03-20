# Cortex Core Implementation Guide

This document provides step-by-step implementation instructions for the Cortex Core system. It outlines a structured approach to implementing the core components, backend services, and integration points needed for a functioning MVP.

## Prerequisites

Before beginning implementation, ensure you have the following:

- Python 3.10 or higher
- Knowledge of FastAPI, asyncio, and Pydantic
- Familiarity with the MCP protocol
- Access to the project specifications and requirements

## Project Structure

Create the following directory and file structure:

```
cortex-core/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI application entry point
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py              # Authentication endpoints
│   │   ├── input.py             # Input endpoint
│   │   ├── output.py            # Output streaming endpoint
│   │   └── config.py            # Configuration endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   ├── event_bus.py         # Event bus implementation
│   │   └── mcp_client.py        # MCP client implementation
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py              # Base models with metadata field
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── request.py       # API request models
│   │   │   └── response.py      # API response models
│   │   └── domain.py            # Domain models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── memory.py            # Memory service client
│   │   └── cognition.py         # Cognition service client
│   └── utils/
│       ├── __init__.py
│       └── auth.py              # Authentication utilities
├── backend/
│   ├── __init__.py
│   ├── memory_service.py        # Memory service implementation
│   └── cognition_service.py     # Cognition service implementation
├── tests/
│   ├── __init__.py
│   ├── test_api.py              # API endpoint tests
│   ├── test_event_bus.py        # Event bus tests
│   ├── test_mcp_client.py       # MCP client tests
│   └── test_integration.py      # Integration tests
├── .env.example                 # Example environment variables
└── requirements.txt             # Project dependencies
```

## Implementation Steps

Follow these steps in order to implement the Cortex Core MVP:

### Step 1: Project Setup

1. **Create project structure**

   ```bash
   mkdir -p cortex-core/app/api cortex-core/app/core cortex-core/app/models/api cortex-core/app/services cortex-core/app/utils cortex-core/backend cortex-core/tests
   touch cortex-core/app/__init__.py cortex-core/app/main.py
   touch cortex-core/app/api/__init__.py cortex-core/app/api/auth.py cortex-core/app/api/input.py cortex-core/app/api/output.py cortex-core/app/api/config.py
   touch cortex-core/app/core/__init__.py cortex-core/app/core/event_bus.py cortex-core/app/core/mcp_client.py
   touch cortex-core/app/models/__init__.py cortex-core/app/models/base.py cortex-core/app/models/domain.py
   touch cortex-core/app/models/api/__init__.py cortex-core/app/models/api/request.py cortex-core/app/models/api/response.py
   touch cortex-core/app/services/__init__.py cortex-core/app/services/memory.py cortex-core/app/services/cognition.py
   touch cortex-core/app/utils/__init__.py cortex-core/app/utils/auth.py
   touch cortex-core/backend/__init__.py cortex-core/backend/memory_service.py cortex-core/backend/cognition_service.py
   touch cortex-core/tests/__init__.py cortex-core/tests/test_api.py cortex-core/tests/test_event_bus.py cortex-core/tests/test_mcp_client.py cortex-core/tests/test_integration.py
   touch cortex-core/.env.example cortex-core/requirements.txt
   ```

2. **Set up dependencies**

   Create a `requirements.txt` file with:

   ```
   fastapi>=0.96.0
   uvicorn>=0.22.0
   pydantic>=2.0.0
   python-jose>=3.3.0
   python-multipart>=0.0.6
   httpx>=0.24.1
   mcp>=1.0.0
   ```

3. **Create virtual environment**

   ```bash
   cd cortex-core
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

### Step 2: Implement Base Models

1. **Create base model with metadata field**

   In `app/models/base.py`:

   ```python
   from pydantic import BaseModel, Field
   from typing import Dict, Any

   class BaseModelWithMetadata(BaseModel):
       """
       Base model with metadata field for storing extra information such as
       experimental flags or debug data.
       """
       metadata: Dict[str, Any] = Field(default_factory=dict)
   ```

2. **Implement domain models**

   In `app/models/domain.py`:

   ```python
   import uuid
   from datetime import datetime
   from typing import List
   from .base import BaseModelWithMetadata

   class User(BaseModelWithMetadata):
       """System user model"""
       user_id: str
       name: str
       email: str

   class Workspace(BaseModelWithMetadata):
       """Workspace model"""
       id: str
       name: str
       description: str
       owner_id: str

   class Conversation(BaseModelWithMetadata):
       """Conversation model"""
       id: str
       workspace_id: str
       topic: str
       participant_ids: List[str]

   class Message(BaseModelWithMetadata):
       """Message model"""
       id: str
       conversation_id: str
       sender_id: str
       content: str
       timestamp: str

   def generate_id() -> str:
       """Generate a unique ID"""
       return str(uuid.uuid4())
   ```

3. **Implement API request models**

   In `app/models/api/request.py`:

   ```python
   from pydantic import BaseModel, Field
   from typing import Dict, Any, List, Optional
   from ..base import BaseModelWithMetadata

   class LoginRequest(BaseModel):
       email: str
       password: str

   class InputRequest(BaseModelWithMetadata):
       """Input data from dumb input clients"""
       content: str
       conversation_id: Optional[str] = None

   class WorkspaceCreate(BaseModelWithMetadata):
       """Request to create a workspace"""
       name: str
       description: str

   class ConversationCreate(BaseModelWithMetadata):
       """Request to create a conversation"""
       workspace_id: str
       topic: str
       participant_ids: List[str] = Field(default_factory=list)
   ```

4. **Implement API response models**

   In `app/models/api/response.py`:

   ```python
   from pydantic import BaseModel, Field
   from typing import Dict, Any, List, Optional
   from ..base import BaseModelWithMetadata
   from ..domain import Workspace, Conversation

   class LoginResponse(BaseModel):
       access_token: str
       token_type: str
       expires_in: int
       claims: Dict[str, Any]

   class InputResponse(BaseModel):
       status: str
       data: Dict[str, Any]

   class WorkspaceResponse(BaseModel):
       status: str
       workspace: Workspace

   class WorkspacesListResponse(BaseModel):
       workspaces: List[Workspace]

   class ConversationResponse(BaseModel):
       status: str
       conversation: Conversation

   class ConversationsListResponse(BaseModel):
       conversations: List[Conversation]

   class ErrorResponse(BaseModel):
       error: Dict[str, Any]
   ```

### Step 3: Implement Event Bus

Create a simple in-memory event bus in `app/core/event_bus.py`:

```python
import asyncio
import logging
from typing import Dict, List, Any, Callable, Awaitable

logger = logging.getLogger(__name__)

class EventBus:
    """
    Simple in-memory event bus for internal communication.
    """
    def __init__(self):
        self.subscribers = []

    def subscribe(self, queue: asyncio.Queue) -> None:
        """
        Register a queue to receive events.

        Args:
            queue: An asyncio.Queue to receive events
        """
        self.subscribers.append(queue)

    async def publish(self, event: Dict[str, Any]) -> None:
        """
        Publish an event to all subscribers.

        Args:
            event: The event to publish
        """
        for queue in self.subscribers:
            try:
                await queue.put(event)
            except Exception as e:
                logger.error(f"Failed to publish event to subscriber: {e}")

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """
        Unregister a queue from receiving events.

        Args:
            queue: The queue to unregister
        """
        if queue in self.subscribers:
            self.subscribers.remove(queue)

# Global event bus instance
event_bus = EventBus()
```

### Step 4: Implement Authentication

1. **Create authentication utilities**

   In `app/utils/auth.py`:

   ```python
   import os
   from datetime import datetime, timedelta
   from typing import Dict, Any, Optional

   from fastapi import Depends, HTTPException, status
   from fastapi.security import OAuth2PasswordBearer
   from jose import JWTError, jwt
   from pydantic import BaseModel

   # Configuration
   SECRET_KEY = os.getenv("JWT_SECRET_KEY", "devsecretkey")
   ALGORITHM = "HS256"
   ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

   oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

   class TokenData(BaseModel):
       user_id: str
       name: str
       email: str

   def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
       """
       Create a JWT access token.

       Args:
           data: The data to encode in the token
           expires_delta: Optional expiration time override

       Returns:
           JWT token string
       """
       to_encode = data.copy()
       expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
       to_encode.update({"exp": expire})
       return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

   async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
       """
       Validate the JWT token and extract user data.

       Args:
           token: JWT token from the request

       Returns:
           User data from the token

       Raises:
           HTTPException: If token is invalid
       """
       credentials_exception = HTTPException(
           status_code=status.HTTP_401_UNAUTHORIZED,
           detail="Invalid authentication credentials",
           headers={"WWW-Authenticate": "Bearer"},
       )

       try:
           payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
           user_id = payload.get("oid")
           name = payload.get("name")
           email = payload.get("email")

           if user_id is None:
               raise credentials_exception

           token_data = TokenData(user_id=user_id, name=name, email=email)
       except JWTError:
           raise credentials_exception

       return {"user_id": token_data.user_id, "name": token_data.name, "email": token_data.email}
   ```

2. **Implement authentication endpoints**

   In `app/api/auth.py`:

   ```python
   from datetime import timedelta
   from fastapi import APIRouter, Depends, HTTPException, status
   from fastapi.security import OAuth2PasswordRequestForm

   from ..utils.auth import create_access_token, get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
   from ..models.api.request import LoginRequest
   from ..models.api.response import LoginResponse

   router = APIRouter(prefix="/auth", tags=["auth"])

   # For development, a simple in-memory user store
   # In production, this would use Azure B2C
   USERS = {
       "user@example.com": {
           "password": "password123",
           "user_id": "550e8400-e29b-41d4-a716-446655440000",
           "name": "Test User",
           "email": "user@example.com"
       }
   }

   @router.post("/login", response_model=LoginResponse)
   async def login(form_data: OAuth2PasswordRequestForm = Depends()):
       """
       Authenticate a user and return a JWT token.

       Args:
           form_data: OAuth2 password request form

       Returns:
           JWT token and user claims

       Raises:
           HTTPException: If authentication fails
       """
       # This is a simple stub for development
       # In production, this would authenticate via Azure B2C
       user = USERS.get(form_data.username)
       if not user or user["password"] != form_data.password:
           raise HTTPException(
               status_code=status.HTTP_401_UNAUTHORIZED,
               detail="Invalid credentials",
               headers={"WWW-Authenticate": "Bearer"},
           )

       # Create token with user data
       token_data = {
           "sub": form_data.username,
           "oid": user["user_id"],
           "name": user["name"],
           "email": user["email"]
       }

       access_token = create_access_token(token_data)

       return LoginResponse(
           access_token=access_token,
           token_type="bearer",
           expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
           claims={
               "oid": user["user_id"],
               "name": user["name"],
               "email": user["email"]
           }
       )

   @router.get("/verify")
   async def verify_token(current_user: dict = Depends(get_current_user)):
       """
       Verify a JWT token and return the user data.

       Args:
           current_user: The current user from the token

       Returns:
           User data from the token
       """
       return current_user
   ```

### Step 5: Implement MCP Clients

1. **Create MCP client implementation**

   In `app/core/mcp_client.py`:

   ```python
   import os
   import asyncio
   import logging
   from typing import Dict, Any, Optional, Tuple

   from mcp import ClientSession, types
   from mcp.client.sse import sse_client

   logger = logging.getLogger(__name__)

   class McpClient:
       """
       Generic MCP client for connecting to MCP servers.
       """
       def __init__(self, url: str):
           self.url = url
           self.session: Optional[ClientSession] = None

       async def connect(self) -> None:
           """
           Connect to the MCP server.

           Raises:
               RuntimeError: If connection fails
           """
           try:
               read_stream, write_stream = await sse_client(self.url)
               self.session = ClientSession(read_stream, write_stream)
               await self.session.initialize()
               logger.info(f"Connected to MCP server at {self.url}")
           except Exception as e:
               logger.error(f"Failed to connect to MCP server at {self.url}: {e}")
               raise RuntimeError(f"Failed to connect to MCP server: {e}")

       async def close(self) -> None:
           """Close the MCP connection."""
           if self.session:
               await self.session.close()
               self.session = None

       async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
           """
           Call a tool on the MCP server.

           Args:
               name: Tool name
               arguments: Tool arguments

           Returns:
               Tool result

           Raises:
               RuntimeError: If the tool call fails
           """
           if not self.session:
               await self.connect()

           try:
               result = await self.session.call_tool(name, arguments)
               return result
           except Exception as e:
               logger.error(f"Error calling tool {name}: {e}")
               raise RuntimeError(f"Error calling tool {name}: {e}")

       async def read_resource(self, uri: str) -> Tuple[Any, Optional[str]]:
           """
           Read a resource from the MCP server.

           Args:
               uri: Resource URI

           Returns:
               Tuple of (resource content, mime type)

           Raises:
               RuntimeError: If resource reading fails
           """
           if not self.session:
               await self.connect()

           try:
               return await self.session.read_resource(uri)
           except Exception as e:
               logger.error(f"Error reading resource {uri}: {e}")
               raise RuntimeError(f"Error reading resource {uri}: {e}")
   ```

2. **Implement Memory Service client**

   In `app/services/memory.py`:

   ```python
   import os
   import logging
   from typing import Dict, List, Any

   from ..core.mcp_client import McpClient

   logger = logging.getLogger(__name__)

   class MemoryServiceClient:
       """
       Client for the Memory Service MCP server.
       """
       def __init__(self, url: str = None):
           self.url = url or os.getenv("MEMORY_SERVICE_URL", "http://localhost:9000")
           self.client = McpClient(self.url)

       async def store_input(self, user_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
           """
           Store input data for a user.

           Args:
               user_id: The user ID
               input_data: The input data to store

           Returns:
               Status response from the Memory Service
           """
           try:
               return await self.client.call_tool("store_input", {
                   "user_id": user_id,
                   "input_data": input_data
               })
           except Exception as e:
               logger.error(f"Failed to store input for user {user_id}: {e}")
               return {"status": "error", "message": str(e)}

       async def get_history(self, user_id: str) -> List[Dict[str, Any]]:
           """
           Get history for a user.

           Args:
               user_id: The user ID

           Returns:
               List of history items
           """
           try:
               history, _ = await self.client.read_resource(f"history/{user_id}")
               return history
           except Exception as e:
               logger.error(f"Failed to get history for user {user_id}: {e}")
               return []

       async def close(self) -> None:
           """Close the connection to the Memory Service."""
           await self.client.close()
   ```

3. **Implement Cognition Service client**

   In `app/services/cognition.py`:

   ```python
   import os
   import logging
   from typing import Dict, Any, Optional

   from ..core.mcp_client import McpClient

   logger = logging.getLogger(__name__)

   class CognitionServiceClient:
       """
       Client for the Cognition Service MCP server.
       """
       def __init__(self, url: str = None):
           self.url = url or os.getenv("COGNITION_SERVICE_URL", "http://localhost:9100")
           self.client = McpClient(self.url)

       async def get_context(
           self,
           user_id: str,
           query: Optional[str] = None,
           limit: Optional[int] = 10
       ) -> Dict[str, Any]:
           """
           Get context for a user.

           Args:
               user_id: The user ID
               query: Optional query string
               limit: Maximum number of items to return

           Returns:
               Context data from the Cognition Service
           """
           try:
               return await self.client.call_tool("get_context", {
                   "user_id": user_id,
                   "query": query,
                   "limit": limit
               })
           except Exception as e:
               logger.error(f"Failed to get context for user {user_id}: {e}")
               return {"context": [], "user_id": user_id, "count": 0, "error": str(e)}

       async def close(self) -> None:
           """Close the connection to the Cognition Service."""
           await self.client.close()
   ```

### Step 6: Implement API Endpoints

1. **Implement input endpoint**

   In `app/api/input.py`:

   ```python
   import logging
   from fastapi import APIRouter, Depends, HTTPException

   from ..utils.auth import get_current_user
   from ..models.api.request import InputRequest
   from ..models.api.response import InputResponse
   from ..core.event_bus import event_bus
   from ..services.memory import MemoryServiceClient

   logger = logging.getLogger(__name__)
   router = APIRouter(tags=["input"])

   @router.post("/input", response_model=InputResponse)
   async def receive_input(request: InputRequest, current_user: dict = Depends(get_current_user)):
       """
       Receive input from a dumb input client.

       Args:
           request: The input request
           current_user: The authenticated user

       Returns:
           Status response
       """
       user_id = current_user["user_id"]

       # Create event with user ID
       event = {
           "type": "input",
           "data": request.dict(),
           "user_id": user_id,
           "metadata": request.metadata
       }

       # Publish event to event bus
       await event_bus.publish(event)

       # Store input in Memory Service
       memory_client = MemoryServiceClient()
       try:
           await memory_client.store_input(user_id, request.dict())
       except Exception as e:
           logger.error(f"Failed to store input in Memory Service: {e}")
           # Continue even if Memory Service fails

       # Return response
       return InputResponse(
           status="received",
           data=request.dict()
       )
   ```

2. **Implement output endpoint**

   In `app/api/output.py`:

   ```python
   import json
   import asyncio
   import logging
   from fastapi import APIRouter, Depends, Request
   from fastapi.responses import StreamingResponse

   from ..utils.auth import get_current_user
   from ..core.event_bus import event_bus

   logger = logging.getLogger(__name__)
   router = APIRouter(tags=["output"])

   @router.get("/output/stream")
   async def output_stream(request: Request, current_user: dict = Depends(get_current_user)):
       """
       Server-Sent Events (SSE) endpoint for streaming output to clients.

       Args:
           request: The HTTP request
           current_user: The authenticated user

       Returns:
           SSE streaming response
       """
       user_id = current_user["user_id"]

       # Create queue for this connection
       queue = asyncio.Queue()

       # Subscribe to event bus
       event_bus.subscribe(queue)

       async def event_generator():
           """Generate SSE events from the queue."""
           try:
               while True:
                   # Wait for next event
                   event = await queue.get()

                   # Filter events for this user
                   if event.get("user_id") == user_id:
                       # Format as SSE event
                       yield f"data: {json.dumps(event)}\n\n"

                   # Add small delay to prevent CPU hogging
                   await asyncio.sleep(0.01)
           except asyncio.CancelledError:
               # Client disconnected
               event_bus.unsubscribe(queue)
               logger.debug(f"Client disconnected: {user_id}")
               raise
           except Exception as e:
               logger.error(f"Error in SSE stream: {e}")
               event_bus.unsubscribe(queue)
               raise

       return StreamingResponse(
           event_generator(),
           media_type="text/event-stream"
       )
   ```

3. **Implement configuration endpoints**

   In `app/api/config.py`:

   ```python
   import uuid
   import logging
   from fastapi import APIRouter, Depends, HTTPException
   from typing import List

   from ..utils.auth import get_current_user
   from ..models.api.request import WorkspaceCreate, ConversationCreate
   from ..models.api.response import WorkspaceResponse, WorkspacesListResponse, ConversationResponse, ConversationsListResponse
   from ..models.domain import Workspace, Conversation

   logger = logging.getLogger(__name__)
   router = APIRouter(prefix="/config", tags=["config"])

   # For development, simple in-memory storage
   workspaces = {}
   conversations = {}

   @router.post("/workspace", response_model=WorkspaceResponse)
   async def create_workspace(request: WorkspaceCreate, current_user: dict = Depends(get_current_user)):
       """
       Create a new workspace.

       Args:
           request: The workspace creation request
           current_user: The authenticated user

       Returns:
           The created workspace
       """
       workspace_id = str(uuid.uuid4())

       # Create workspace
       workspace = Workspace(
           id=workspace_id,
           name=request.name,
           description=request.description,
           owner_id=current_user["user_id"],
           metadata=request.metadata
       )

       # Store workspace
       workspaces[workspace_id] = workspace.dict()

       return WorkspaceResponse(
           status="workspace created",
           workspace=workspace
       )

   @router.get("/workspace", response_model=WorkspacesListResponse)
   async def list_workspaces(current_user: dict = Depends(get_current_user)):
       """
       List workspaces for the current user.

       Args:
           current_user: The authenticated user

       Returns:
           List of workspaces owned by the user
       """
       user_id = current_user["user_id"]

       # Filter workspaces by owner
       user_workspaces = [
           Workspace(**workspace)
           for workspace in workspaces.values()
           if workspace["owner_id"] == user_id
       ]

       return WorkspacesListResponse(
           workspaces=user_workspaces
       )

   @router.post("/conversation", response_model=ConversationResponse)
   async def create_conversation(request: ConversationCreate, current_user: dict = Depends(get_current_user)):
       """
       Create a new conversation in a workspace.

       Args:
           request: The conversation creation request
           current_user: The authenticated user

       Returns:
           The created conversation
       """
       user_id = current_user["user_id"]
       workspace_id = request.workspace_id

       # Verify workspace exists and user has access
       if workspace_id not in workspaces:
           raise HTTPException(status_code=404, detail="Workspace not found")

       workspace = workspaces[workspace_id]
       if workspace["owner_id"] != user_id:
           raise HTTPException(status_code=403, detail="Access denied")

       # Create conversation
       conversation_id = str(uuid.uuid4())

       # Ensure current user is in participants
       participants = list(request.participant_ids)
       if user_id not in participants:
           participants.append(user_id)

       conversation = Conversation(
           id=conversation_id,
           workspace_id=workspace_id,
           topic=request.topic,
           participant_ids=participants,
           metadata=request.metadata
       )

       # Store conversation
       conversations[conversation_id] = conversation.dict()

       return ConversationResponse(
           status="conversation created",
           conversation=conversation
       )

   @router.get("/conversation", response_model=ConversationsListResponse)
   async def list_conversations(workspace_id: str, current_user: dict = Depends(get_current_user)):
       """
       List conversations in a workspace.

       Args:
           workspace_id: The workspace ID
           current_user: The authenticated user

       Returns:
           List of conversations in the workspace
       """
       user_id = current_user["user_id"]

       # Verify workspace exists and user has access
       if workspace_id not in workspaces:
           raise HTTPException(status_code=404, detail="Workspace not found")

       workspace = workspaces[workspace_id]
       if workspace["owner_id"] != user_id:
           raise HTTPException(status_code=403, detail="Access denied")

       # Filter conversations by workspace
       workspace_conversations = [
           Conversation(**conversation)
           for conversation in conversations.values()
           if conversation["workspace_id"] == workspace_id
       ]

       return ConversationsListResponse(
           conversations=workspace_conversations
       )
   ```

### Step 7: Implement Main Application

Create the FastAPI application entry point in `app/main.py`:

```python
import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import auth, input, output, config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Create FastAPI app
app = FastAPI(title="Cortex Core")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(input.router)
app.include_router(output.router)
app.include_router(config.router)

@app.get("/", tags=["status"])
async def root():
    """API status endpoint."""
    return {"status": "online", "service": "Cortex Core"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
```

### Step 8: Implement Backend Services

1. **Implement Memory Service**

   In `backend/memory_service.py`:

   ```python
   import os
   import uuid
   from datetime import datetime
   from typing import Dict, List, Any, Optional
   from mcp.server.fastmcp import FastMCP

   # Initialize the MCP server
   mcp = FastMCP("MemoryService")

   # In-memory storage by user_id
   memory_store: Dict[str, List[Dict[str, Any]]] = {}

   @mcp.tool()
   def store_input(user_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
       """
       Store input data for a specific user.

       Args:
           user_id: The unique user identifier
           input_data: The input data to store

       Returns:
           Status object with operation result
       """
       # Create user store if it doesn't exist
       if user_id not in memory_store:
           memory_store[user_id] = []

       # Add timestamp if not present
       if "timestamp" not in input_data:
           input_data["timestamp"] = datetime.now().isoformat()

       # Add unique ID if not present
       if "id" not in input_data:
           input_data["id"] = str(uuid.uuid4())

       # Store the input
       memory_store[user_id].append(input_data)

       # Return status
       return {
           "status": "stored",
           "user_id": user_id,
           "item_id": input_data["id"]
       }

   @mcp.resource("history/{user_id}")
   def get_history(user_id: str) -> List[Dict[str, Any]]:
       """
       Get history for a specific user.

       Args:
           user_id: The unique user identifier

       Returns:
           List containing the user's history
       """
       # Get history (or empty list if not found)
       history = memory_store.get(user_id, [])

       # Return history
       return history

   @mcp.resource("history/{user_id}/limit/{limit}")
   def get_limited_history(user_id: str, limit: int) -> List[Dict[str, Any]]:
       """
       Get limited history for a specific user.

       Args:
           user_id: The unique user identifier
           limit: Maximum number of items to return

       Returns:
           List containing the user's limited history
       """
       # Get history (or empty list if not found)
       history = memory_store.get(user_id, [])

       # Apply limit (most recent items first)
       limited_history = sorted(
           history,
           key=lambda x: x.get("timestamp", ""),
           reverse=True
       )[:int(limit)]

       # Return limited history
       return limited_history

   if __name__ == "__main__":
       # Get port from environment or use default
       port = int(os.getenv("PORT", 9000))

       # Run the MCP server
       mcp.run()
   ```

2. **Implement Cognition Service**

   In `backend/cognition_service.py`:

   ```python
   import os
   import httpx
   from typing import Dict, List, Any, Optional
   from mcp.server.fastmcp import FastMCP

   # Initialize the MCP server
   mcp = FastMCP("CognitionService")

   # Configuration
   MEMORY_SERVICE_URL = os.environ.get("MEMORY_SERVICE_URL", "http://localhost:9000")

   @mcp.tool()
   async def get_context(
       user_id: str,
       query: Optional[str] = None,
       limit: Optional[int] = 10
   ) -> Dict[str, Any]:
       """
       Get relevant context for a user.

       Args:
           user_id: The unique user identifier
           query: Optional search query to filter context
           limit: Maximum number of items to return

       Returns:
           Object containing relevant context items
       """
       try:
           # For MVP, simply retrieve history from Memory Service
           async with httpx.AsyncClient() as client:
               # Use limit parameter if provided
               url = f"{MEMORY_SERVICE_URL}/resource/history/{user_id}/limit/{limit}"

               response = await client.get(url)
               response.raise_for_status()

               # Get history from response
               history = response.json()

               # For MVP, just return the history as context
               # In future versions, this would implement relevance sorting,
               # semantic search, etc.
               return {
                   "context": history,
                   "user_id": user_id,
                   "query": query,
                   "count": len(history)
               }
       except Exception as e:
           # Return empty context on error
           return {
               "context": [],
               "user_id": user_id,
               "query": query,
               "count": 0,
               "error": str(e)
           }

   if __name__ == "__main__":
       # Get port from environment or use default
       port = int(os.getenv("PORT", 9100))

       # Run the MCP server
       mcp.run()
   ```

### Step 9: Create Example Environment Variables

Create a `.env.example` file:

```
# Core configuration
PORT=8000
JWT_SECRET_KEY=your-secret-key-here

# Backend service endpoints
MEMORY_SERVICE_URL=http://localhost:9000
COGNITION_SERVICE_URL=http://localhost:9100
```

### Step 10: Implement Basic Tests

1. **Test event bus**

   In `tests/test_event_bus.py`:

   ```python
   import pytest
   import asyncio
   from app.core.event_bus import EventBus

   @pytest.mark.asyncio
   async def test_event_bus_publish_subscribe():
       """Test event bus publish and subscribe functionality."""
       bus = EventBus()
       queue = asyncio.Queue()

       # Subscribe to events
       bus.subscribe(queue)

       # Test event
       test_event = {"type": "test", "data": "hello", "user_id": "test-user"}

       # Publish event
       await bus.publish(test_event)

       # Get event from queue
       received_event = await asyncio.wait_for(queue.get(), timeout=1.0)

       # Verify event
       assert received_event == test_event

       # Unsubscribe
       bus.unsubscribe(queue)

       # Publish another event
       await bus.publish({"type": "test2", "data": "world", "user_id": "test-user"})

       # Verify queue is empty (no more events after unsubscribe)
       assert queue.empty()
   ```

2. **Test API endpoints**

   The full test suite should include more comprehensive tests for all endpoints.

## Running the System

To run the complete system:

1. **Start the Memory Service**:

   ```bash
   cd cortex-core
   python -m backend.memory_service
   ```

2. **Start the Cognition Service**:

   ```bash
   cd cortex-core
   python -m backend.cognition_service
   ```

3. **Start the Cortex Core**:

   ```bash
   cd cortex-core
   python -m app.main
   ```

4. **Test the API**:
   - Access the Swagger docs at: `http://localhost:8000/docs`
   - Test authentication: `POST /auth/login`
   - Create a workspace: `POST /config/workspace`
   - Create a conversation: `POST /config/conversation`
   - Send input: `POST /input`
   - Connect to output stream: `GET /output/stream`

## Next Steps

After implementing the MVP, consider these enhancements:

1. **Persistent Storage**:

   - Add SQLite/PostgreSQL database integration
   - Implement proper data repositories

2. **Enhanced Authentication**:

   - Integrate with Azure B2C
   - Add proper user management

3. **Domain Expert Entities**:

   - Integrate with existing domain experts
   - Develop custom domain expert implementations

4. **Advanced Memory System**:

   - Implement vector-based retrieval
   - Add semantic search capabilities

5. **Robust Error Handling**:

   - Implement centralized error handling
   - Add detailed logging and monitoring

6. **Testing**:
   - Increase test coverage
   - Add integration tests
   - Implement CI/CD pipeline
