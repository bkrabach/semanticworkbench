"""
SQLAlchemy Models

This module defines SQLAlchemy ORM models for database tables.
The models include relationship definitions and column types.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLAEnum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.schemas.base import MemoryItemType as SchemaMemoryItemType
from app.schemas.base import UserRole as SchemaUserRole
from app.schemas.base import WorkspaceRole as SchemaWorkspaceRole

# Create declarative base
Base = declarative_base()


# Use SQLAlchemy 2.0 style for compatibility with both 1.x and 2.x
class UserRole(str, Enum):
    """User role enumeration"""

    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class WorkspaceRole(str, Enum):
    """Workspace user role enumeration"""

    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class MemoryItemType(str, Enum):
    """Memory item type enumeration"""

    CONVERSATION = "conversation"
    DOCUMENT = "document"
    IMAGE = "image"
    CODE = "code"
    THOUGHT = "thought"
    NOTE = "note"
    SUMMARY = "summary"
    REFERENCE = "reference"
    CUSTOM = "custom"


# SQLAlchemy has special handling for SQLite
def get_uuid_column():
    """Get UUID column type compatible with both SQLite and PostgreSQL"""
    try:
        # Use UUID type for PostgreSQL
        return Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    except Exception:
        # Fallback to String for SQLite
        return Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))


class User(Base):
    """User model"""

    __tablename__ = "users"

    id = get_uuid_column()
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(SQLAEnum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    sessions = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan"
    )
    workspaces = relationship(
        "WorkspaceUser", back_populates="user", cascade="all, delete-orphan"
    )
    memory_items = relationship(
        "MemoryItem", back_populates="owner", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User {self.email}>"


class Session(Base):
    """User session model for refresh tokens"""

    __tablename__ = "sessions"

    id = get_uuid_column()
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    refresh_token = Column(String(255), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    user_agent = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 can be up to 45 chars
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="sessions")

    def __repr__(self):
        return f"<Session {self.id} for user {self.user_id}>"


class Workspace(Base):
    """Workspace model"""

    __tablename__ = "workspaces"

    id = get_uuid_column()
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    settings = Column(JSON, default=dict, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    users = relationship(
        "WorkspaceUser", back_populates="workspace", cascade="all, delete-orphan"
    )
    memory_items = relationship(
        "MemoryItem", back_populates="workspace", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Workspace {self.name}>"


class WorkspaceUser(Base):
    """Workspace user association model"""

    __tablename__ = "workspace_users"

    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role = Column(SQLAEnum(WorkspaceRole), default=WorkspaceRole.VIEWER, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    workspace = relationship("Workspace", back_populates="users")
    user = relationship("User", back_populates="workspaces")

    def __repr__(self):
        return f"<WorkspaceUser {self.user_id} in {self.workspace_id} as {self.role}>"


class MemoryItem(Base):
    """Memory item model"""

    __tablename__ = "memory_items"

    id = get_uuid_column()
    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    owner_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    parent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("memory_items.id", ondelete="CASCADE"),
        nullable=True,
    )
    type = Column(SQLAEnum(MemoryItemType), nullable=False)
    content = Column(JSON, nullable=False)
    metadata = Column(JSON, default=dict, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    workspace = relationship("Workspace", back_populates="memory_items")
    owner = relationship("User", back_populates="memory_items")
    parent = relationship("MemoryItem", remote_side=[id], backref="children")

    # Indexes
    __table_args__ = (
        Index("ix_memory_items_workspace_id_type", "workspace_id", "type"),
        Index("ix_memory_items_parent_id", "parent_id"),
        Index("ix_memory_items_expires_at", "expires_at"),
    )

    def __repr__(self):
        return f"<MemoryItem {self.id} of type {self.type}>"


class File(Base):
    """File model for uploaded files"""

    __tablename__ = "files"

    id = get_uuid_column()
    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    owner_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    memory_item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("memory_items.id", ondelete="CASCADE"),
        nullable=True,
    )
    filename = Column(String(255), nullable=False)
    filepath = Column(String(511), nullable=False)
    mimetype = Column(String(127), nullable=False)
    size = Column(Integer, nullable=False)
    metadata = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    workspace = relationship("Workspace")
    owner = relationship("User")
    memory_item = relationship("MemoryItem")

    def __repr__(self):
        return f"<File {self.filename}>"


class ApiKey(Base):
    """API key model for machine-to-machine authentication"""

    __tablename__ = "api_keys"

    id = get_uuid_column()
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(255), nullable=False)
    key_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User")

    # Constraints
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uix_api_keys_user_id_name"),
    )

    def __repr__(self):
        return f"<ApiKey {self.name} for user {self.user_id}>"


# Type conversion helpers
def schema_to_model_user_role(role: SchemaUserRole) -> UserRole:
    """Convert schema UserRole to model UserRole"""
    return UserRole(role)


def model_to_schema_user_role(role: UserRole) -> SchemaUserRole:
    """Convert model UserRole to schema UserRole"""
    return SchemaUserRole(role)


def schema_to_model_workspace_role(role: SchemaWorkspaceRole) -> WorkspaceRole:
    """Convert schema WorkspaceRole to model WorkspaceRole"""
    return WorkspaceRole(role)


def model_to_schema_workspace_role(role: WorkspaceRole) -> SchemaWorkspaceRole:
    """Convert model WorkspaceRole to schema WorkspaceRole"""
    return SchemaWorkspaceRole(role)


def schema_to_model_memory_item_type(type_: SchemaMemoryItemType) -> MemoryItemType:
    """Convert schema MemoryItemType to model MemoryItemType"""
    return MemoryItemType(type_)


def model_to_schema_memory_item_type(type_: MemoryItemType) -> SchemaMemoryItemType:
    """Convert model MemoryItemType to schema MemoryItemType"""
    return SchemaMemoryItemType(type_)


# Export public symbols
__all__ = [
    "Base",
    "UserRole",
    "WorkspaceRole",
    "MemoryItemType",
    "User",
    "Session",
    "Workspace",
    "WorkspaceUser",
    "MemoryItem",
    "File",
    "ApiKey",
    "schema_to_model_user_role",
    "model_to_schema_user_role",
    "schema_to_model_workspace_role",
    "model_to_schema_workspace_role",
    "schema_to_model_memory_item_type",
    "model_to_schema_memory_item_type",
]
