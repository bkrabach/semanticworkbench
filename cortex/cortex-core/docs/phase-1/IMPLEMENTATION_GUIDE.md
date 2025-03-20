# Cortex Core Phase 1: Implementation Guide

This guide provides detailed step-by-step instructions for implementing Phase 1 of the Cortex Core system. It focuses on practical implementation details, with code examples and specific guidance for each component.

## Prerequisites

Before starting implementation, ensure you have the following set up:

1. **Python Environment**:

   - Python 3.10 or higher installed
   - Virtual environment tool (venv, conda, etc.)

2. **Development Tools**:
   - Git for version control
   - VS Code, PyCharm, or another Python IDE
   - Postman, curl, or similar for API testing

## Project Setup

### Create Project Structure

Create the following directory and file structure:

```
cortex-core/
├── app/
│   ├── __init__.py
│   ├── main.py                # FastAPI application entry point
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py            # Authentication endpoints
│   │   ├── input.py           # Input endpoint
│   │   ├── output.py          # Output streaming endpoint
│   │   └── config.py          # Configuration endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   └── event_bus.py       # Event bus implementation
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py            # Base models
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── request.py     # API request models
│   │   │   └── response.py    # API response models
│   │   └── domain.py          # Domain models
│   └── utils/
│       ├── __init__.py
│       └── auth.py            # Authentication utilities
├── tests/
│   ├── __init__.py
│   ├── test_api.py            # API endpoint tests
│   ├── test_event_bus.py      # Event bus tests
│   └── test_integration.py    # Integration tests
├── .env.example               # Example environment variables
└── requirements.txt           # Project dependencies
```

You can create this structure with the following commands:

```bash
mkdir -p cortex-core/app/api cortex-core/app/core cortex-core/app/models/api cortex-core/app/utils cortex-core/tests
touch cortex-core/app/__init__.py cortex-core/app/main.py
touch cortex-core/app/api/__init__.py cortex-core/app/api/auth.py cortex-core/app/api/input.py cortex-core/app/api/output.py cortex-core/app/api/config.py
touch cortex-core/app/core/__init__.py cortex-core/app/core/event_bus.py
touch cortex-core/app/models/__init__.py cortex-core/app/models/base.py cortex-core/app/models/domain.py
touch cortex-core/app/models/api/__init__.py cortex-core/app/models/api/request.py cortex-core/app/models/api/response.py
touch cortex-core/app/utils/__init__.py cortex-core/app/utils/auth.py
touch cortex-core/tests/__init__.py cortex-core/tests/test_api.py cortex-core/tests/test_event_bus.py cortex-core/tests/test_integration.py
touch cortex-core/.env.example cortex-core/requirements.txt
```

### Set Up Dependencies

Create a `requirements.txt` file with the following content:

```
fastapi>=0.96.0
uvicorn>=0.22.0
pydantic>=2.0.0
python-jose>=3.3.0
python-multipart>=0.0.6
httpx>=0.24.1
python-dotenv>=1.0.0
pytest>=7.3.1
pytest-asyncio>=0.21.0
```

### Create Virtual Environment and Install Dependencies

```bash
cd cortex-core
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Create Environment Configuration

Create a `.env` file based on `.env.example`:

```
# Core configuration
PORT=8000
ENV=development
LOG_LEVEL=INFO

# Auth configuration (JWT)
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# CORS settings (for development)
ALLOW_ORIGINS=*
```

Create `.env.example` with the same content but with generic values.

## Step 1: FastAPI Application Setup

### Create Main Application File

In `app/main.py`, set up the FastAPI application:

```python
import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Cortex Core",
    description="Cortex Core API for input and output processing",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOW_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint for health checks
@app.get("/", tags=["status"])
async def root():
    """API status endpoint."""
    return {"status": "online", "service": "Cortex Core"}

# Include routers (will be added later)
# app.include_router(auth_router)
# app.include_router(input_router)
# app.include_router(output_router)
# app.include_router(config_router)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
```

### Test the Basic Application

Run the application to verify it works:

```bash
python -m app.main
```

Visit `http://localhost:8000` in your browser, and you should see:

```json
{ "status": "online", "service": "Cortex Core" }
```

Also check the OpenAPI documentation at `http://localhost:8000/docs`.

## Step 2: Authentication System Implementation

### Create Authentication Utilities

In `app/utils/auth.py`, implement JWT token handling:

```python
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", 24))

# OAuth2 password bearer scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

class TokenData(BaseModel):
    """Token data model."""
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
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
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

### Implement Authentication Endpoints

In `app/api/auth.py`, create the authentication endpoints:

```python
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from ..utils.auth import create_access_token, get_current_user, ACCESS_TOKEN_EXPIRE_HOURS
from ..models.api.request import LoginRequest
from ..models.api.response import LoginResponse

router = APIRouter(prefix="/auth", tags=["auth"])

# For development, a simple in-memory user store
# In production, this would use Azure B2C
USERS = {
    "user@example.com": {
        "password": "password123",
        "oid": "550e8400-e29b-41d4-a716-446655440000",
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
        "oid": user["oid"],
        "name": user["name"],
        "email": user["email"]
    }

    access_token = create_access_token(token_data)

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_HOURS * 3600,  # Convert hours to seconds
        claims={
            "oid": user["oid"],
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

### Create API Models for Authentication

In `app/models/api/request.py`, create the request model:

```python
from pydantic import BaseModel, Field, EmailStr
from typing import Dict, Any, List, Optional

class LoginRequest(BaseModel):
    """Login request model."""
    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")
```

In `app/models/api/response.py`, create the response model:

```python
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

class LoginResponse(BaseModel):
    """Login response model."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(..., description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    claims: Dict[str, Any] = Field(..., description="User claims")
```

### Update Main Application to Include Authentication Router

Update `app/main.py` to include the authentication router:

```python
from app.api.auth import router as auth_router

# Include routers
app.include_router(auth_router)
# app.include_router(input_router)
# app.include_router(output_router)
# app.include_router(config_router)
```

### Test Authentication Endpoints

Now you can test the authentication system:

1. Start the application: `python -m app.main`
2. Use curl or Postman to make a POST request to `/auth/login`:
   ```bash
   curl -X POST "http://localhost:8000/auth/login" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=user@example.com&password=password123"
   ```
3. You should receive a response with an access token:
   ```json
   {
     "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
     "token_type": "bearer",
     "expires_in": 86400,
     "claims": {
       "oid": "550e8400-e29b-41d4-a716-446655440000",
       "name": "Test User",
       "email": "user@example.com"
     }
   }
   ```
4. Test token verification with the received token:
   ```bash
   curl -X GET "http://localhost:8000/auth/verify" \
     -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
   ```
5. You should receive the user data in response.

## Step 3: Data Models Implementation

### Create Base Models

In `app/models/base.py`, implement the base model with metadata:

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

### Create Domain Models

In `app/models/domain.py`, implement the domain models:

```python
import uuid
from datetime import datetime
from typing import List, Optional
from .base import BaseModelWithMetadata

class User(BaseModelWithMetadata):
    """System user model."""
    user_id: str
    name: str
    email: str

class Workspace(BaseModelWithMetadata):
    """Workspace model."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    owner_id: str

class Conversation(BaseModelWithMetadata):
    """Conversation model."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workspace_id: str
    topic: str
    participant_ids: List[str]

class Message(BaseModelWithMetadata):
    """Message model."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str
    sender_id: str
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

def generate_id() -> str:
    """Generate a unique ID."""
    return str(uuid.uuid4())
```

### Create API Request Models

In `app/models/api/request.py`, add input request models:

```python
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from ...models.base import BaseModelWithMetadata

class LoginRequest(BaseModel):
    """Login request model."""
    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")

class InputRequest(BaseModelWithMetadata):
    """Input data from clients."""
    content: str = Field(..., description="Message content")
    conversation_id: Optional[str] = Field(None, description="Conversation ID")

class WorkspaceCreate(BaseModelWithMetadata):
    """Request to create a workspace."""
    name: str = Field(..., min_length=1, max_length=100, description="Workspace name")
    description: str = Field(..., min_length=1, max_length=500, description="Workspace description")

class ConversationCreate(BaseModelWithMetadata):
    """Request to create a conversation."""
    workspace_id: str = Field(..., description="ID of the parent workspace")
    topic: str = Field(..., min_length=1, max_length=200, description="Conversation topic")
    participant_ids: List[str] = Field(default_factory=list, description="List of user IDs")
```

### Create API Response Models

In `app/models/api/response.py`, implement API response models:

```python
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from ...models.domain import Workspace, Conversation

class LoginResponse(BaseModel):
    """Login response model."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(..., description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    claims: Dict[str, Any] = Field(..., description="User claims")

class InputResponse(BaseModel):
    """Input response model."""
    status: str = Field(..., description="Status of the operation")
    data: Dict[str, Any] = Field(..., description="Echoed input data")

class WorkspaceResponse(BaseModel):
    """Workspace response model."""
    status: str = Field(..., description="Status of the operation")
    workspace: Workspace = Field(..., description="Created workspace")

class WorkspacesListResponse(BaseModel):
    """Workspaces list response model."""
    workspaces: List[Workspace] = Field(..., description="List of workspaces")
    total: int = Field(..., description="Total number of workspaces")

class ConversationResponse(BaseModel):
    """Conversation response model."""
    status: str = Field(..., description="Status of the operation")
    conversation: Conversation = Field(..., description="Created conversation")

class ConversationsListResponse(BaseModel):
    """Conversations list response model."""
    conversations: List[Conversation] = Field(..., description="List of conversations")
    total: int = Field(..., description="Total number of conversations")

class ErrorResponse(BaseModel):
    """Error response model."""
    error: Dict[str, Any] = Field(..., description="Error details")
```

## Step 4: In-Memory Storage Implementation

Create a simple in-memory storage module. Create a new file at `app/core/storage.py`:

```python
import logging
from typing import Dict, List, Any, Optional
from ..models.domain import User, Workspace, Conversation, Message

logger = logging.getLogger(__name__)

class InMemoryStorage:
    """
    Simple in-memory storage for development use.
    """
    def __init__(self):
        self.users: Dict[str, Dict[str, Any]] = {}
        self.workspaces: Dict[str, Dict[str, Any]] = {}
        self.conversations: Dict[str, Dict[str, Any]] = {}
        self.messages: Dict[str, Dict[str, Any]] = {}

    # User operations

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        return self.users.get(user_id)

    def create_user(self, user: User) -> Dict[str, Any]:
        """Create a new user."""
        user_dict = user.model_dump()
        self.users[user.user_id] = user_dict
        return user_dict

    # Workspace operations

    def create_workspace(self, workspace: Workspace) -> Dict[str, Any]:
        """Create a new workspace."""
        workspace_dict = workspace.model_dump()
        self.workspaces[workspace.id] = workspace_dict
        return workspace_dict

    def get_workspace(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        """Get workspace by ID."""
        return self.workspaces.get(workspace_id)

    def list_workspaces(self, owner_id: str) -> List[Dict[str, Any]]:
        """List workspaces by owner ID."""
        return [
            workspace for workspace in self.workspaces.values()
            if workspace["owner_id"] == owner_id
        ]

    # Conversation operations

    def create_conversation(self, conversation: Conversation) -> Dict[str, Any]:
        """Create a new conversation."""
        conversation_dict = conversation.model_dump()
        self.conversations[conversation.id] = conversation_dict
        return conversation_dict

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation by ID."""
        return self.conversations.get(conversation_id)

    def list_conversations(self, workspace_id: str) -> List[Dict[str, Any]]:
        """List conversations by workspace ID."""
        return [
            conversation for conversation in self.conversations.values()
            if conversation["workspace_id"] == workspace_id
        ]

    # Message operations

    def create_message(self, message: Message) -> Dict[str, Any]:
        """Create a new message."""
        message_dict = message.model_dump()
        self.messages[message.id] = message_dict
        return message_dict

    def get_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get message by ID."""
        return self.messages.get(message_id)

    def list_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """List messages by conversation ID."""
        return [
            message for message in self.messages.values()
            if message["conversation_id"] == conversation_id
        ]

# Singleton instance
storage = InMemoryStorage()
```

## Step 5: Event Bus Implementation

In `app/core/event_bus.py`, implement the event bus:

```python
import asyncio
import logging
from typing import Dict, List, Any, Set

logger = logging.getLogger(__name__)

class EventBus:
    """
    Simple in-memory event bus for internal communication.
    """
    def __init__(self):
        self.subscribers: List[asyncio.Queue] = []
        self._active_tasks: Set[asyncio.Task] = set()

    def subscribe(self, queue: asyncio.Queue) -> None:
        """
        Register a queue to receive events.

        Args:
            queue: An asyncio.Queue to receive events
        """
        self.subscribers.append(queue)
        logger.debug(f"Subscribed new queue. Total subscribers: {len(self.subscribers)}")

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

        logger.debug(f"Published event: {event.get('type')} to {len(self.subscribers)} subscribers")

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """
        Unregister a queue from receiving events.

        Args:
            queue: The queue to unregister
        """
        if queue in self.subscribers:
            self.subscribers.remove(queue)
            logger.debug(f"Unsubscribed queue. Remaining subscribers: {len(self.subscribers)}")

    def create_background_task(self, coroutine) -> asyncio.Task:
        """
        Create a tracked background task.

        Args:
            coroutine: The coroutine to run as a task

        Returns:
            The created task
        """
        task = asyncio.create_task(coroutine)
        self._active_tasks.add(task)
        task.add_done_callback(self._active_tasks.discard)
        return task

    async def shutdown(self) -> None:
        """
        Shutdown the event bus.
        Cancel all active tasks and clear subscribers.
        """
        # Cancel all active tasks
        for task in self._active_tasks:
            task.cancel()

        # Wait for all tasks to complete
        if self._active_tasks:
            await asyncio.gather(*self._active_tasks, return_exceptions=True)

        # Clear subscribers
        self.subscribers.clear()
        logger.info("Event bus shut down")

# Global event bus instance
event_bus = EventBus()
```

## Step 6: Input API Implementation

In `app/api/input.py`, implement the input endpoint:

```python
import logging
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime

from ..utils.auth import get_current_user
from ..models.api.request import InputRequest
from ..models.api.response import InputResponse
from ..core.event_bus import event_bus
from ..models.domain import Message
from ..core.storage import storage

logger = logging.getLogger(__name__)
router = APIRouter(tags=["input"])

@router.post("/input", response_model=InputResponse)
async def receive_input(request: InputRequest, current_user: dict = Depends(get_current_user)):
    """
    Receive input from a client.

    Args:
        request: The input request
        current_user: The authenticated user

    Returns:
        Status response
    """
    user_id = current_user["user_id"]
    logger.info(f"Received input from user {user_id}")

    # Create a timestamp
    timestamp = datetime.now().isoformat()

    # Create event with user ID
    event = {
        "type": "input",
        "data": {
            "content": request.content,
            "conversation_id": request.conversation_id,
            "timestamp": timestamp,
        },
        "user_id": user_id,
        "timestamp": timestamp,
        "metadata": request.metadata
    }

    # Create and store message
    conversation_id = request.conversation_id or "default"
    message = Message(
        sender_id=user_id,
        content=request.content,
        conversation_id=conversation_id,
        timestamp=timestamp,
        metadata=request.metadata
    )
    storage.create_message(message)

    # Publish event to event bus
    await event_bus.publish(event)

    # Return response
    return InputResponse(
        status="received",
        data={
            "content": request.content,
            "conversation_id": conversation_id,
            "timestamp": timestamp,
            "metadata": request.metadata
        }
    )
```

### Update Main Application to Include Input Router

Update `app/main.py` to include the input router:

```python
from app.api.auth import router as auth_router
from app.api.input import router as input_router

# Include routers
app.include_router(auth_router)
app.include_router(input_router)
# app.include_router(output_router)
# app.include_router(config_router)
```

## Step 7: Output API with SSE Implementation

In `app/api/output.py`, implement the SSE output endpoint:

```python
import json
import asyncio
import logging
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from datetime import datetime

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
    logger.info(f"New SSE connection established for user {user_id}")

    # Create queue for this connection
    queue = asyncio.Queue()

    # Subscribe to event bus
    event_bus.subscribe(queue)

    async def event_generator():
        """Generate SSE events from the queue."""
        try:
            # Send initial connection established event
            connection_event = {
                "type": "connection_established",
                "user_id": user_id,
                "timestamp": datetime.now().isoformat()
            }
            yield f"data: {json.dumps(connection_event)}\n\n"

            # Track when the last heartbeat was sent
            last_heartbeat = datetime.now()
            heartbeat_interval = 30  # seconds

            while True:
                # Check if we need to send a heartbeat
                now = datetime.now()
                if (now - last_heartbeat).total_seconds() >= heartbeat_interval:
                    heartbeat_event = {
                        "type": "heartbeat",
                        "timestamp": now.isoformat()
                    }
                    yield f"data: {json.dumps(heartbeat_event)}\n\n"
                    last_heartbeat = now
                    continue

                # Wait for next event with timeout
                try:
                    # Wait for an event, but timeout before the heartbeat interval
                    event = await asyncio.wait_for(queue.get(), timeout=heartbeat_interval/2)

                    # Filter events for this user
                    if event.get("user_id") == user_id or event.get("type") == "heartbeat":
                        # Format as SSE event
                        yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    # No event received, continue and check heartbeat
                    continue

        except asyncio.CancelledError:
            # Client disconnected
            logger.info(f"SSE connection closed for user {user_id}")
            raise
        except Exception as e:
            logger.error(f"Error in SSE stream for user {user_id}: {e}")
            raise
        finally:
            # Always unsubscribe to prevent memory leaks
            event_bus.unsubscribe(queue)
            logger.info(f"Cleaned up SSE connection for user {user_id}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

### Update Main Application to Include Output Router

Update `app/main.py` to include the output router:

```python
from app.api.auth import router as auth_router
from app.api.input import router as input_router
from app.api.output import router as output_router

# Include routers
app.include_router(auth_router)
app.include_router(input_router)
app.include_router(output_router)
# app.include_router(config_router)
```

## Step 8: Basic Workspace and Conversation Management

In `app/api/config.py`, implement configuration endpoints:

```python
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional

from ..utils.auth import get_current_user
from ..models.api.request import WorkspaceCreate, ConversationCreate
from ..models.api.response import (
    WorkspaceResponse, WorkspacesListResponse,
    ConversationResponse, ConversationsListResponse
)
from ..models.domain import Workspace, Conversation
from ..core.storage import storage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/config", tags=["config"])

# Workspace endpoints

@router.post("/workspace", response_model=WorkspaceResponse)
async def create_workspace(
    request: WorkspaceCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new workspace.

    Args:
        request: The workspace creation request
        current_user: The authenticated user

    Returns:
        The created workspace
    """
    user_id = current_user["user_id"]

    # Create workspace
    workspace = Workspace(
        name=request.name,
        description=request.description,
        owner_id=user_id,
        metadata=request.metadata
    )

    # Store workspace
    workspace_dict = storage.create_workspace(workspace)

    logger.info(f"Created workspace {workspace.id} for user {user_id}")

    return WorkspaceResponse(
        status="workspace created",
        workspace=Workspace(**workspace_dict)
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

    # Get workspaces for user
    workspace_dicts = storage.list_workspaces(user_id)
    workspaces = [Workspace(**w) for w in workspace_dicts]

    logger.info(f"Listed {len(workspaces)} workspaces for user {user_id}")

    return WorkspacesListResponse(
        workspaces=workspaces,
        total=len(workspaces)
    )

# Conversation endpoints

@router.post("/conversation", response_model=ConversationResponse)
async def create_conversation(
    request: ConversationCreate,
    current_user: dict = Depends(get_current_user)
):
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
    workspace = storage.get_workspace(workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )

    if workspace["owner_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Create conversation
    # Ensure current user is in participants
    participants = list(request.participant_ids)
    if user_id not in participants:
        participants.append(user_id)

    conversation = Conversation(
        workspace_id=workspace_id,
        topic=request.topic,
        participant_ids=participants,
        metadata=request.metadata
    )

    # Store conversation
    conversation_dict = storage.create_conversation(conversation)

    logger.info(f"Created conversation {conversation.id} in workspace {workspace_id}")

    return ConversationResponse(
        status="conversation created",
        conversation=Conversation(**conversation_dict)
    )

@router.get("/conversation", response_model=ConversationsListResponse)
async def list_conversations(
    workspace_id: str,
    current_user: dict = Depends(get_current_user)
):
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
    workspace = storage.get_workspace(workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )

    if workspace["owner_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Get conversations for workspace
    conversation_dicts = storage.list_conversations(workspace_id)
    conversations = [Conversation(**c) for c in conversation_dicts]

    logger.info(f"Listed {len(conversations)} conversations for workspace {workspace_id}")

    return ConversationsListResponse(
        conversations=conversations,
        total=len(conversations)
    )
```

### Update Main Application to Include Config Router

Update `app/main.py` to include the config router:

```python
from app.api.auth import router as auth_router
from app.api.input import router as input_router
from app.api.output import router as output_router
from app.api.config import router as config_router

# Include routers
app.include_router(auth_router)
app.include_router(input_router)
app.include_router(output_router)
app.include_router(config_router)
```

### Add Graceful Shutdown to Main Application

Update `app/main.py` to include graceful shutdown logic for the event bus:

```python
from app.core.event_bus import event_bus

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler."""
    logger.info("Application shutting down")
    await event_bus.shutdown()
```

## Step 9: Testing Implementation

### Event Bus Tests

Create `tests/test_event_bus.py`:

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
    test_event = {"type": "test", "data": {"message": "hello"}, "user_id": "test-user"}

    # Publish event
    await bus.publish(test_event)

    # Get event from queue
    received_event = await asyncio.wait_for(queue.get(), timeout=1.0)

    # Verify event
    assert received_event == test_event

    # Unsubscribe
    bus.unsubscribe(queue)

    # Publish another event
    await bus.publish({"type": "test2", "data": {"message": "world"}, "user_id": "test-user"})

    # Verify queue is empty (no more events after unsubscribe)
    assert queue.empty()
```

### API Tests

Create `tests/test_api.py`:

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.utils.auth import create_access_token

client = TestClient(app)

def get_auth_header(user_id="test-user", name="Test User", email="test@example.com"):
    """Create authentication header with test token."""
    token = create_access_token({
        "sub": email,
        "oid": user_id,
        "name": name,
        "email": email
    })
    return {"Authorization": f"Bearer {token}"}

def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "online", "service": "Cortex Core"}

def test_login_endpoint():
    """Test login endpoint."""
    response = client.post(
        "/auth/login",
        data={"username": "user@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_invalid_login():
    """Test login with invalid credentials."""
    response = client.post(
        "/auth/login",
        data={"username": "wrong@example.com", "password": "wrong"}
    )
    assert response.status_code == 401

def test_verify_token():
    """Test token verification."""
    headers = get_auth_header()
    response = client.get("/auth/verify", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "test-user"

def test_input_endpoint():
    """Test input endpoint."""
    headers = get_auth_header()
    response = client.post(
        "/input",
        json={"content": "Test message", "metadata": {}},
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "received"
    assert data["data"]["content"] == "Test message"

def test_workspace_endpoints():
    """Test workspace creation and listing."""
    headers = get_auth_header()

    # Create workspace
    response = client.post(
        "/config/workspace",
        json={"name": "Test Workspace", "description": "Test Description", "metadata": {}},
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "workspace created"
    assert data["workspace"]["name"] == "Test Workspace"
    workspace_id = data["workspace"]["id"]

    # List workspaces
    response = client.get("/config/workspace", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["workspaces"]) > 0
    assert any(w["id"] == workspace_id for w in data["workspaces"])

    # Create conversation
    response = client.post(
        "/config/conversation",
        json={
            "workspace_id": workspace_id,
            "topic": "Test Conversation",
            "metadata": {}
        },
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "conversation created"
    assert data["conversation"]["topic"] == "Test Conversation"
    conversation_id = data["conversation"]["id"]

    # List conversations
    response = client.get(
        f"/config/conversation?workspace_id={workspace_id}",
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["conversations"]) > 0
    assert any(c["id"] == conversation_id for c in data["conversations"])
```

### Integration Test for End-to-End Flow

Create `tests/test_integration.py`:

```python
import pytest
import asyncio
import json
from fastapi.testclient import TestClient
from app.main import app
from app.utils.auth import create_access_token

@pytest.mark.asyncio
async def test_input_to_output_flow():
    """Test the complete flow from input to output."""
    # This test requires running the application
    # It's more complex to set up in pytest, so we'll use a simpler approach

    # Create test token
    token = create_access_token({
        "sub": "test@example.com",
        "oid": "test-user-123",
        "name": "Test User",
        "email": "test@example.com"
    })

    # Set up test client
    client = TestClient(app)

    # Set auth header
    headers = {"Authorization": f"Bearer {token}"}

    # Send test input
    response = client.post(
        "/input",
        json={"content": "Test message for integration", "metadata": {}},
        headers=headers
    )

    # Verify input response
    assert response.status_code == 200
    assert response.json()["status"] == "received"

    # For a true integration test, we would need to use SSE
    # This is complex in a test environment, so this is a simplified version
    # In a real test, you would:
    # 1. Open an SSE connection
    # 2. Send input
    # 3. Wait for and verify the input appears in the SSE stream

    # The test is considered successful if the input endpoint works correctly
    # A full end-to-end test would be part of manual testing or more complex automation
```

### Run Tests

Run the tests with pytest:

```bash
pytest
```

## Running the Complete Application

To run the complete application:

```bash
python -m app.main
```

This will start the FastAPI application on port 8000 (or the port specified in your `.env` file).

## Testing the Complete Flow

### 1. Authenticate a User

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=password123"
```

This will return a JWT token.

### 2. Create a Workspace

```bash
curl -X POST "http://localhost:8000/config/workspace" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Workspace",
    "description": "Test Workspace Description",
    "metadata": {}
  }'
```

### 3. Create a Conversation

```bash
curl -X POST "http://localhost:8000/config/conversation" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "WORKSPACE_ID",
    "topic": "Test Conversation",
    "metadata": {}
  }'
```

### 4. Connect to Output Stream

You can test the SSE connection using a simple HTML page. Create a file named `sse_test.html`:

```html
<!DOCTYPE html>
<html>
  <head>
    <title>SSE Test</title>
  </head>
  <body>
    <h1>SSE Test</h1>
    <div id="events"></div>

    <script>
      const eventsDiv = document.getElementById("events");
      const token = "YOUR_TOKEN"; // Replace with your token

      const eventSource = new EventSource(
        "http://localhost:8000/output/stream",
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        const eventItem = document.createElement("div");
        eventItem.textContent = JSON.stringify(data);
        eventsDiv.appendChild(eventItem);
      };

      eventSource.onerror = (error) => {
        console.error("EventSource error:", error);
        eventSource.close();
      };
    </script>
  </body>
</html>
```

Unfortunately, browsers don't allow adding headers to EventSource connections. For testing, you'll need to either:

1. Use a proxy server that adds the header
2. Use a library like `fetch-event-source` in a Node.js script
3. Use a dedicated tool for SSE testing

### 5. Send Input

```bash
curl -X POST "http://localhost:8000/input" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Hello, Cortex!",
    "conversation_id": "CONVERSATION_ID",
    "metadata": {}
  }'
```

## Conclusion

You have now implemented Phase 1 of the Cortex Core system. This implementation includes:

1. A complete FastAPI application with authentication
2. An in-memory event bus for message passing
3. Input and output API endpoints with SSE streaming
4. Basic workspace and conversation management
5. In-memory data storage
6. Proper user partitioning of data
7. Unit and integration tests

This provides a solid foundation for Phase 2, which will add persistent storage and enhanced configuration capabilities.
