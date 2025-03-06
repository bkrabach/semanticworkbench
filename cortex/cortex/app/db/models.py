import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
import json

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, JSON, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from app.models.schemas import (
    User as UserSchema,
    LoginAccount as LoginAccountSchema,
    AADAccount as AADAccountSchema,
    Session as SessionSchema,
    Message as MessageSchema,
    Conversation as ConversationSchema,
    MemoryEntry as MemoryEntrySchema,
    MCPServer as MCPServerSchema,
    MCPTool as MCPToolSchema,
    MCPToolParameter as MCPToolParameterSchema,
    ToolExecution as ToolExecutionSchema,
    SSEConnection as SSEConnectionSchema,
    MessageRole,
    ToolExecutionStatus,
    AccountType
)

# Create base class
Base = declarative_base()

def generate_id() -> str:
    """Generate a UUID string."""
    return str(uuid.uuid4())

class User(Base):
    """User model for the database."""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=generate_id)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    primary_account_id = Column(String, nullable=True)
    
    # Relationships
    accounts = relationship("LoginAccount", back_populates="user")
    conversations = relationship("Conversation", back_populates="user")
    sessions = relationship("Session", back_populates="user")
    
    def to_schema(self) -> UserSchema:
        """Convert to Pydantic schema."""
        accounts = [account.to_schema() for account in self.accounts]
        
        return UserSchema(
            id=self.id,
            name=self.name,
            created_at=self.created_at,
            accounts=accounts,
            primary_account_id=self.primary_account_id
        )

class LoginAccount(Base):
    """Login account model for the database."""
    __tablename__ = "login_accounts"
    
    id = Column(String, primary_key=True, default=generate_id)
    user_id = Column(String, ForeignKey("users.id"))
    type = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_primary = Column(Boolean, default=False)
    metadata = Column(JSON, default=dict)
    
    # AAD specific fields
    object_id = Column(String, nullable=True)
    tenant_id = Column(String, nullable=True)
    email = Column(String, nullable=True)
    display_name = Column(String, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="accounts")
    
    def to_schema(self) -> LoginAccountSchema:
        """Convert to Pydantic schema."""
        if self.type == AccountType.AAD.value:
            return AADAccountSchema(
                id=self.id,
                type=AccountType.AAD,
                created_at=self.created_at,
                is_primary=self.is_primary,
                metadata=self.metadata,
                object_id=self.object_id,
                tenant_id=self.tenant_id,
                email=self.email,
                display_name=self.display_name
            )
        
        # Generic account
        return LoginAccountSchema(
            id=self.id,
            type=AccountType(self.type),
            created_at=self.created_at,
            is_primary=self.is_primary,
            metadata=self.metadata
        )

class Session(Base):
    """Session model for the database."""
    __tablename__ = "sessions"
    
    id = Column(String, primary_key=True, default=generate_id)
    user_id = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSON, default=dict)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    def to_schema(self) -> SessionSchema:
        """Convert to Pydantic schema."""
        return SessionSchema(
            id=self.id,
            user_id=self.user_id,
            created_at=self.created_at,
            last_active=self.last_active,
            metadata=self.metadata
        )

class Conversation(Base):
    """Conversation model for the database."""
    __tablename__ = "conversations"
    
    id = Column(String, primary_key=True, default=generate_id)
    user_id = Column(String, ForeignKey("users.id"))
    title = Column(String, default="New Conversation")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata = Column(JSON, default=dict)
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    memory_entries = relationship("MemoryEntry", back_populates="conversation", cascade="all, delete-orphan")
    tool_executions = relationship("ToolExecution", back_populates="conversation", cascade="all, delete-orphan")
    
    def to_schema(self, include_messages: bool = False) -> ConversationSchema:
        """Convert to Pydantic schema."""
        result = ConversationSchema(
            id=self.id,
            user_id=self.user_id,
            title=self.title,
            created_at=self.created_at,
            updated_at=self.updated_at,
            metadata=self.metadata,
            messages=[]
        )
        
        if include_messages:
            result.messages = [message.to_schema() for message in self.messages]
        
        return result

class Message(Base):
    """Message model for the database."""
    __tablename__ = "messages"
    
    id = Column(String, primary_key=True, default=generate_id)
    conversation_id = Column(String, ForeignKey("conversations.id"))
    role = Column(Enum(*[role.value for role in MessageRole], name="message_role"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSON, default=dict)
    tool_calls = Column(JSON, default=list)
    is_complete = Column(Boolean, default=True)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    tool_executions = relationship("ToolExecution", back_populates="message", cascade="all, delete-orphan")
    
    def to_schema(self) -> MessageSchema:
        """Convert to Pydantic schema."""
        return MessageSchema(
            id=self.id,
            conversation_id=self.conversation_id,
            role=MessageRole(self.role),
            content=self.content,
            created_at=self.created_at,
            metadata=self.metadata,
            tool_calls=self.tool_calls,
            is_complete=self.is_complete
        )

class MemoryEntry(Base):
    """Memory entry model for the database."""
    __tablename__ = "memory_entries"
    
    id = Column(String, primary_key=True, default=generate_id)
    user_id = Column(String, nullable=False)
    conversation_id = Column(String, ForeignKey("conversations.id"))
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    type = Column(String, default="conversation")
    metadata = Column(JSON, default=dict)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="memory_entries")
    
    def to_schema(self) -> MemoryEntrySchema:
        """Convert to Pydantic schema."""
        return MemoryEntrySchema(
            id=self.id,
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            content=self.content,
            created_at=self.created_at,
            type=self.type,
            metadata=self.metadata
        )

class MCPToolParameter(Base):
    """MCP tool parameter model for the database."""
    __tablename__ = "mcp_tool_parameters"
    
    id = Column(String, primary_key=True, default=generate_id)
    tool_id = Column(String, ForeignKey("mcp_tools.id"))
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    required = Column(Boolean, default=False)
    default = Column(JSON, nullable=True)
    
    # Relationships
    tool = relationship("MCPTool", back_populates="parameters")
    
    def to_schema(self) -> MCPToolParameterSchema:
        """Convert to Pydantic schema."""
        return MCPToolParameterSchema(
            name=self.name,
            type=self.type,
            description=self.description,
            required=self.required,
            default=self.default
        )

class MCPTool(Base):
    """MCP tool model for the database."""
    __tablename__ = "mcp_tools"
    
    id = Column(String, primary_key=True, default=generate_id)
    server_id = Column(String, ForeignKey("mcp_servers.id"))
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    
    # Relationships
    server = relationship("MCPServer", back_populates="tools")
    parameters = relationship("MCPToolParameter", back_populates="tool", cascade="all, delete-orphan")
    executions = relationship("ToolExecution", back_populates="tool", cascade="all, delete-orphan")
    
    def to_schema(self) -> MCPToolSchema:
        """Convert to Pydantic schema."""
        return MCPToolSchema(
            id=self.id,
            server_id=self.server_id,
            name=self.name,
            description=self.description,
            parameters=[param.to_schema() for param in self.parameters]
        )

class MCPServer(Base):
    """MCP server model for the database."""
    __tablename__ = "mcp_servers"
    
    id = Column(String, primary_key=True, default=generate_id)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    status = Column(String, default="connected")
    
    # Relationships
    tools = relationship("MCPTool", back_populates="server", cascade="all, delete-orphan")
    executions = relationship("ToolExecution", back_populates="server", cascade="all, delete-orphan")
    
    def to_schema(self) -> MCPServerSchema:
        """Convert to Pydantic schema."""
        return MCPServerSchema(
            id=self.id,
            name=self.name,
            url=self.url,
            status=self.status,
            tools=[tool.to_schema() for tool in self.tools]
        )

class ToolExecution(Base):
    """Tool execution model for the database."""
    __tablename__ = "tool_executions"
    
    id = Column(String, primary_key=True, default=generate_id)
    conversation_id = Column(String, ForeignKey("conversations.id"))
    message_id = Column(String, ForeignKey("messages.id"))
    tool_id = Column(String, ForeignKey("mcp_tools.id"))
    server_id = Column(String, ForeignKey("mcp_servers.id"))
    status = Column(Enum(*[status.value for status in ToolExecutionStatus], name="tool_execution_status"), default=ToolExecutionStatus.PENDING.value)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    inputs = Column(JSON, nullable=False)
    outputs = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="tool_executions")
    message = relationship("Message", back_populates="tool_executions")
    tool = relationship("MCPTool", back_populates="executions")
    server = relationship("MCPServer", back_populates="executions")
    
    def to_schema(self) -> ToolExecutionSchema:
        """Convert to Pydantic schema."""
        return ToolExecutionSchema(
            id=self.id,
            conversation_id=self.conversation_id,
            message_id=self.message_id,
            tool_id=self.tool_id,
            server_id=self.server_id,
            status=ToolExecutionStatus(self.status),
            created_at=self.created_at,
            updated_at=self.updated_at,
            inputs=self.inputs,
            outputs=self.outputs,
            error=self.error
        )

class SSEConnection(Base):
    """SSE connection model for the database."""
    __tablename__ = "sse_connections"
    
    id = Column(String, primary_key=True, default=generate_id)
    user_id = Column(String, nullable=False)
    conversation_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSON, default=dict)
    
    def to_schema(self) -> SSEConnectionSchema:
        """Convert to Pydantic schema."""
        return SSEConnectionSchema(
            id=self.id,
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            created_at=self.created_at,
            last_active=self.last_active,
            metadata=self.metadata
        )