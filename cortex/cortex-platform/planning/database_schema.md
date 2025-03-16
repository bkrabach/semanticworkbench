# Simplified Cortex Database Schema

## Design Principles

1. **Minimal but Complete**: Only essential tables and fields while supporting core functionality
2. **Proper Relationships**: Clear foreign key relationships that enforce data integrity
3. **Efficient Queries**: Indexed fields for common query patterns
4. **Flexible Metadata**: JSON fields for extensible metadata without schema changes
5. **PostgreSQL Features**: Leverage PostgreSQL-specific features (JSONB, text search)

## Core Tables

### Users Table

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    hashed_password VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_users_email ON users(email);
```

### Workspaces Table

```sql
CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_workspaces_name ON workspaces(name);
```

### User Workspace Access Table

```sql
CREATE TABLE user_workspace_access (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL, -- 'owner', 'editor', 'viewer'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    PRIMARY KEY (user_id, workspace_id)
);

CREATE INDEX idx_user_workspace_access_user ON user_workspace_access(user_id);
CREATE INDEX idx_user_workspace_access_workspace ON user_workspace_access(workspace_id);
```

### Conversations Table

```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    modality VARCHAR(50) DEFAULT 'text',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_active_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_conversations_workspace ON conversations(workspace_id);
CREATE INDEX idx_conversations_last_active ON conversations(last_active_at);
```

### Messages Table

```sql
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    role VARCHAR(50) NOT NULL, -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_messages_user ON messages(user_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);
-- To support text search
CREATE INDEX idx_messages_content_gin ON messages USING GIN (to_tsvector('english', content));
```

### Memory Items Table

```sql
CREATE TABLE memory_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    item_type VARCHAR(50) NOT NULL, -- 'message', 'entity', 'file', etc.
    content TEXT, -- Plain content when text-based
    binary_content BYTEA, -- Binary content when needed
    content_type VARCHAR(100), -- MIME type or format
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE, -- NULL means no expiration
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_memory_items_workspace ON memory_items(workspace_id);
CREATE INDEX idx_memory_items_type ON memory_items(item_type);
CREATE INDEX idx_memory_items_created ON memory_items(created_at);
CREATE INDEX idx_memory_items_expires ON memory_items(expires_at);
-- Allow filtering on common metadata fields
CREATE INDEX idx_memory_items_metadata ON memory_items USING GIN (metadata);
```

### Domain Experts Table

```sql
CREATE TABLE domain_experts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    endpoint_url VARCHAR(255) NOT NULL,
    auth_token VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    capabilities JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_connected_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_domain_experts_name ON domain_experts(name);
CREATE INDEX idx_domain_experts_active ON domain_experts(is_active);
```

### Domain Expert Tools Table

```sql
CREATE TABLE domain_expert_tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    expert_id UUID REFERENCES domain_experts(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    parameters JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    UNIQUE (expert_id, name)
);

CREATE INDEX idx_domain_expert_tools_expert ON domain_expert_tools(expert_id);
CREATE INDEX idx_domain_expert_tools_name ON domain_expert_tools(name);
```

## SQLAlchemy Models 

### Base Models

```python
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, LargeBinary
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID, primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255))
    hashed_password = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    metadata = Column(JSONB, default={})

class Workspace(Base):
    __tablename__ = "workspaces"
    
    id = Column(UUID, primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    metadata = Column(JSONB, default={})

class UserWorkspaceAccess(Base):
    __tablename__ = "user_workspace_access"
    
    user_id = Column(UUID, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    workspace_id = Column(UUID, ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True)
    role = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    metadata = Column(JSONB, default={})

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(UUID, primary_key=True, default=generate_uuid)
    workspace_id = Column(UUID, ForeignKey("workspaces.id", ondelete="CASCADE"))
    title = Column(String(255), nullable=False)
    modality = Column(String(50), default="text")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_active_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    metadata = Column(JSONB, default={})

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(UUID, primary_key=True, default=generate_uuid)
    conversation_id = Column(UUID, ForeignKey("conversations.id", ondelete="CASCADE"))
    user_id = Column(UUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    metadata = Column(JSONB, default={})

class MemoryItem(Base):
    __tablename__ = "memory_items"
    
    id = Column(UUID, primary_key=True, default=generate_uuid)
    workspace_id = Column(UUID, ForeignKey("workspaces.id", ondelete="CASCADE"))
    item_type = Column(String(50), nullable=False)
    content = Column(Text)
    binary_content = Column(LargeBinary)
    content_type = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))
    metadata = Column(JSONB, default={})

class DomainExpert(Base):
    __tablename__ = "domain_experts"
    
    id = Column(UUID, primary_key=True, default=generate_uuid)
    name = Column(String(100), unique=True, nullable=False)
    endpoint_url = Column(String(255), nullable=False)
    auth_token = Column(String(255))
    is_active = Column(Boolean, default=True)
    capabilities = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_connected_at = Column(DateTime(timezone=True))
    metadata = Column(JSONB, default={})

class DomainExpertTool(Base):
    __tablename__ = "domain_expert_tools"
    
    id = Column(UUID, primary_key=True, default=generate_uuid)
    expert_id = Column(UUID, ForeignKey("domain_experts.id", ondelete="CASCADE"))
    name = Column(String(100), nullable=False)
    description = Column(Text)
    parameters = Column(JSONB, nullable=False, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    metadata = Column(JSONB, default={})
```

## Domain Models

```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID, uuid4

class UserInfo(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    email: str
    name: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)

class WorkspaceInfo(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ConversationInfo(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID
    title: str
    modality: str = "text"
    created_at: datetime
    updated_at: datetime
    last_active_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)

class MessageInfo(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    conversation_id: UUID
    user_id: Optional[UUID] = None
    role: str
    content: str
    created_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Conversation(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID
    title: str
    modality: str = "text"
    created_at: datetime
    updated_at: datetime
    last_active_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)
    messages: List[MessageInfo] = Field(default_factory=list)

class MemoryItemInfo(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID
    item_type: str
    content: Optional[str] = None
    binary_content: Optional[bytes] = None
    content_type: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class DomainExpertInfo(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    endpoint_url: str
    is_active: bool = True
    capabilities: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    last_connected_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class DomainExpertToolInfo(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    expert_id: UUID
    name: str
    description: Optional[str] = None
    parameters: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

## API Models

### Request Models

```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from uuid import UUID

class CreateUserRequest(BaseModel):
    email: str
    password: str
    name: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class UpdateUserRequest(BaseModel):
    name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class CreateWorkspaceRequest(BaseModel):
    name: str
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class UpdateWorkspaceRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class CreateConversationRequest(BaseModel):
    title: str
    modality: str = "text"
    metadata: Dict[str, Any] = Field(default_factory=dict)

class UpdateConversationRequest(BaseModel):
    title: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class AddMessageRequest(BaseModel):
    content: str
    role: str = "user"
    metadata: Dict[str, Any] = Field(default_factory=dict)

class CreateMemoryItemRequest(BaseModel):
    item_type: str
    content: Optional[str] = None
    binary_content: Optional[bytes] = None
    content_type: Optional[str] = None
    expires_at: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class RegisterDomainExpertRequest(BaseModel):
    name: str
    endpoint_url: str
    auth_token: Optional[str] = None
    capabilities: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ExecuteToolRequest(BaseModel):
    arguments: Dict[str, Any] = Field(default_factory=dict)
```

### Response Models

```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID

class UserResponse(BaseModel):
    id: UUID
    email: str
    name: Optional[str] = None
    is_active: bool
    created_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)

class WorkspaceResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)

class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    user_id: Optional[UUID] = None
    role: str
    content: str
    created_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ConversationSummaryResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    title: str
    modality: str
    created_at: datetime
    updated_at: datetime
    last_active_at: datetime
    message_count: int
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ConversationDetailResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    title: str
    modality: str
    created_at: datetime
    updated_at: datetime
    last_active_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)
    messages: List[MessageResponse] = Field(default_factory=list)

class MemoryItemResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    item_type: str
    content: Optional[str] = None
    content_type: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class DomainExpertResponse(BaseModel):
    id: UUID
    name: str
    endpoint_url: str
    is_active: bool
    capabilities: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    last_connected_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class DomainExpertToolResponse(BaseModel):
    id: UUID
    expert_id: UUID
    name: str
    description: Optional[str] = None
    parameters: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ToolExecutionResponse(BaseModel):
    expert_name: str
    tool_name: str
    result: Dict[str, Any]
    execution_time: float
    metadata: Dict[str, Any] = Field(default_factory=dict)
```