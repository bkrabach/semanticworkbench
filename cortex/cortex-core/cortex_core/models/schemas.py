from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum
import uuid

# Utility function for ID generation
def generate_id() -> str:
    """Generate a UUID string."""
    return str(uuid.uuid4())

# Enums for better type safety
class MessageRole(str, Enum):
    """Role of a message in a conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"

class ToolExecutionStatus(str, Enum):
    """Status of a tool execution."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class AccountType(str, Enum):
    """Type of login account."""
    AAD = "aad"  # Microsoft Azure AD
    MSA = "msa"  # Microsoft Account (consumer)
    LOCAL = "local"  # Local account
    OAUTH = "oauth"  # Generic OAuth provider

# Base model for all login account types
class LoginAccount(BaseModel):
    """Base model for all login account types."""
    id: str = Field(default_factory=generate_id)
    type: AccountType
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_primary: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = {
        "from_attributes": True
    }

# Microsoft AAD specific account
class AADAccount(LoginAccount):
    """Microsoft Azure AD account."""
    type: AccountType = AccountType.AAD
    object_id: str  # AAD object ID
    tenant_id: str  # AAD tenant ID
    email: Optional[str] = None
    display_name: Optional[str] = None

# Core data models
class User(BaseModel):
    """User model."""
    id: str = Field(default_factory=generate_id)
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    accounts: List[LoginAccount] = Field(default_factory=list)  # Associated login accounts
    primary_account_id: Optional[str] = None  # Reference to primary account
    
    model_config = {
        "from_attributes": True
    }

class Session(BaseModel):
    """Session model."""
    id: str = Field(default_factory=generate_id)
    user_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = {
        "from_attributes": True
    }

class Message(BaseModel):
    """Message in a conversation."""
    id: str = Field(default_factory=generate_id)
    conversation_id: str
    role: MessageRole
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # For tool usage tracking
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    
    # For message chunking/streaming
    is_complete: bool = True
    
    model_config = {
        "from_attributes": True
    }

class Conversation(BaseModel):
    """Conversation model."""
    id: str = Field(default_factory=generate_id)
    user_id: str
    title: str = "New Conversation"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # We'll store messages separately in the database
    # This is just for API responses
    messages: List[Message] = Field(default_factory=list)
    
    model_config = {
        "from_attributes": True
    }

class MemoryEntry(BaseModel):
    """Memory entry model."""
    id: str = Field(default_factory=generate_id)
    user_id: str
    conversation_id: str
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    type: str = "conversation"  # Type of memory entry (conversation, fact, etc.)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = {
        "from_attributes": True
    }

class MCPToolParameter(BaseModel):
    """Parameter for an MCP tool."""
    name: str
    type: str
    description: str
    required: bool = False
    default: Optional[Any] = None
    
    model_config = {
        "from_attributes": True
    }

class MCPTool(BaseModel):
    """MCP tool model."""
    id: str = Field(default_factory=generate_id)
    server_id: str
    name: str
    description: str
    parameters: List[MCPToolParameter] = Field(default_factory=list)
    
    model_config = {
        "from_attributes": True
    }

class MCPServer(BaseModel):
    """MCP server model."""
    id: str = Field(default_factory=generate_id)
    name: str
    url: str
    status: str = "connected"
    tools: List[MCPTool] = Field(default_factory=list)
    
    model_config = {
        "from_attributes": True
    }

class ToolExecution(BaseModel):
    """Tool execution model."""
    id: str = Field(default_factory=generate_id)
    conversation_id: str
    message_id: str
    tool_id: str
    server_id: str
    status: ToolExecutionStatus = ToolExecutionStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    inputs: Dict[str, Any]
    outputs: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    model_config = {
        "from_attributes": True
    }

class SSEConnection(BaseModel):
    """SSE connection model."""
    id: str = Field(default_factory=generate_id)
    user_id: str
    conversation_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = {
        "from_attributes": True
    }

# API Request/Response Models
class TokenRequest(BaseModel):
    """Request for token validation."""
    token: str

class TokenResponse(BaseModel):
    """Response for token validation."""
    valid: bool
    user: Optional[User] = None

class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    title: Optional[str] = "New Conversation"

class CreateConversationResponse(BaseModel):
    """Response for creating a new conversation."""
    conversation: Conversation

class ListConversationsResponse(BaseModel):
    """Response for listing conversations."""
    conversations: List[Conversation]
    total: int

class GetConversationResponse(BaseModel):
    """Response for getting a conversation."""
    conversation: Conversation

class DeleteConversationResponse(BaseModel):
    """Response for deleting a conversation."""
    success: bool

class CreateMessageRequest(BaseModel):
    """Request to create a new message."""
    content: str
    role: MessageRole = MessageRole.USER

class CreateMessageResponse(BaseModel):
    """Response for creating a new message."""
    message: Message

class ListMessagesResponse(BaseModel):
    """Response for listing messages."""
    messages: List[Message]
    total: int

class SSEEvent(BaseModel):
    """SSE event model."""
    event: str
    data: Any

class ErrorResponse(BaseModel):
    """Error response model."""
    detail: str
    code: Optional[str] = None