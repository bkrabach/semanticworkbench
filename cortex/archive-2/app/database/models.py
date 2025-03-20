"""Database models for the Cortex application."""
import uuid

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, LargeBinary, String, Text, func
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database.connection import Base


def generate_uuid() -> str:
    """Generate a UUID for database primary keys."""
    return str(uuid.uuid4())


class User(Base):
    """SQLAlchemy model for a user."""
    
    __tablename__ = "users"
    
    id = Column(UUID, primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255))
    hashed_password = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    metadata = Column(JSONB, default={})
    
    # Relationships
    workspaces = relationship("UserWorkspaceAccess", back_populates="user", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="user")


class Workspace(Base):
    """SQLAlchemy model for a workspace."""
    
    __tablename__ = "workspaces"
    
    id = Column(UUID, primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    metadata = Column(JSONB, default={})
    
    # Relationships
    users = relationship("UserWorkspaceAccess", back_populates="workspace", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="workspace", cascade="all, delete-orphan")
    memory_items = relationship("MemoryItem", back_populates="workspace", cascade="all, delete-orphan")


class UserWorkspaceAccess(Base):
    """SQLAlchemy model for user access to a workspace."""
    
    __tablename__ = "user_workspace_access"
    
    user_id = Column(UUID, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    workspace_id = Column(UUID, ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True)
    role = Column(String(50), nullable=False)  # 'owner', 'editor', 'viewer'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    metadata = Column(JSONB, default={})
    
    # Relationships
    user = relationship("User", back_populates="workspaces")
    workspace = relationship("Workspace", back_populates="users")


class Conversation(Base):
    """SQLAlchemy model for a conversation."""
    
    __tablename__ = "conversations"
    
    id = Column(UUID, primary_key=True, default=generate_uuid)
    workspace_id = Column(UUID, ForeignKey("workspaces.id", ondelete="CASCADE"))
    title = Column(String(255), nullable=False)
    modality = Column(String(50), default="text")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_active_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    metadata = Column(JSONB, default={})
    
    # Relationships
    workspace = relationship("Workspace", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    """SQLAlchemy model for a message in a conversation."""
    
    __tablename__ = "messages"
    
    id = Column(UUID, primary_key=True, default=generate_uuid)
    conversation_id = Column(UUID, ForeignKey("conversations.id", ondelete="CASCADE"))
    user_id = Column(UUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    role = Column(String(50), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    metadata = Column(JSONB, default={})
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    user = relationship("User", back_populates="messages")


class MemoryItem(Base):
    """SQLAlchemy model for a memory item."""
    
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
    
    # Relationships
    workspace = relationship("Workspace", back_populates="memory_items")


class DomainExpert(Base):
    """SQLAlchemy model for a domain expert."""
    
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
    
    # Relationships
    tools = relationship("DomainExpertTool", back_populates="expert", cascade="all, delete-orphan")


class DomainExpertTool(Base):
    """SQLAlchemy model for a tool provided by a domain expert."""
    
    __tablename__ = "domain_expert_tools"
    
    id = Column(UUID, primary_key=True, default=generate_uuid)
    expert_id = Column(UUID, ForeignKey("domain_experts.id", ondelete="CASCADE"))
    name = Column(String(100), nullable=False)
    description = Column(Text)
    parameters = Column(JSONB, nullable=False, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    metadata = Column(JSONB, default={})
    
    # Relationships
    expert = relationship("DomainExpert", back_populates="tools")