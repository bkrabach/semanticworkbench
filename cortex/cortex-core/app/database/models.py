"""
SQLAlchemy models for Cortex Core
"""

from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    Boolean,
    Table,
    Text,
    Integer,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

# Association tables
user_role_association = Table(
    "user_role_association",
    Base.metadata,
    Column("user_id", String(36), ForeignKey("users.id", ondelete="CASCADE")),
    Column("role_id", String(36), ForeignKey("roles.id", ondelete="CASCADE")),
)


class User(Base):
    """User model"""

    __tablename__ = "users"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True)
    name = Column(String(255), nullable=True)
    password_hash = Column(String(255), nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    # Relationships
    sessions = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan"
    )
    workspaces = relationship(
        "Workspace", back_populates="user", cascade="all, delete-orphan"
    )
    api_keys = relationship(
        "ApiKey", back_populates="user", cascade="all, delete-orphan"
    )
    workspace_sharings = relationship(
        "WorkspaceSharing", back_populates="user", cascade="all, delete-orphan"
    )
    roles = relationship(
        "Role", secondary=user_role_association, back_populates="users"
    )


class Role(Base):
    """Role model"""

    __tablename__ = "roles"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    name = Column(String(50), unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    # Relationships
    users = relationship(
        "User", secondary=user_role_association, back_populates="roles"
    )


class Session(Base):
    """Session model"""

    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active_at = Column(DateTime, default=datetime.utcnow)
    active_workspace_id = Column(String(36), nullable=False)
    config = Column(Text, default="{}")  # Stored as JSON string
    meta_data = Column(Text, default="{}")  # Stored as JSON string

    # Relationships
    user = relationship("User", back_populates="sessions")


class ApiKey(Base):
    """API key model"""

    __tablename__ = "api_keys"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    key = Column(String(255), unique=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    scopes_json = Column(Text, default="[]")  # Stored as JSON array string
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="api_keys")


class Workspace(Base):
    """Workspace model"""

    __tablename__ = "workspaces"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active_at = Column(DateTime, default=datetime.utcnow)
    config = Column(Text, default="{}")  # Stored as JSON string
    meta_data = Column(Text, default="{}")  # Stored as JSON string

    # Relationships
    user = relationship("User", back_populates="workspaces")
    conversations = relationship(
        "Conversation", back_populates="workspace", cascade="all, delete-orphan"
    )
    memory_items = relationship(
        "MemoryItem", back_populates="workspace", cascade="all, delete-orphan"
    )
    workspace_sharings = relationship(
        "WorkspaceSharing", back_populates="workspace", cascade="all, delete-orphan"
    )


class WorkspaceSharing(Base):
    """Workspace sharing model"""

    __tablename__ = "workspace_sharings"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String(36), ForeignKey(
        "workspaces.id", ondelete="CASCADE"))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    # Stored as JSON array string
    permissions_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    # Relationships
    workspace = relationship("Workspace", back_populates="workspace_sharings")
    user = relationship("User", back_populates="workspace_sharings")

    # Constraints
    __table_args__ = (
        # Unique constraint for workspace_id and user_id
        {"sqlite_autoincrement": True},
    )


class Conversation(Base):
    """Conversation model"""

    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    workspace_id = Column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    modality = Column(String(50), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active_at = Column(DateTime, default=datetime.utcnow)
    entries = Column(Text, default="[]")  # Stored as JSON array string
    meta_data = Column(Text, default="{}")  # Stored as JSON string

    # Relationships
    workspace = relationship("Workspace", back_populates="conversations")


class MemoryItem(Base):
    """Memory item model"""

    __tablename__ = "memory_items"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    workspace_id = Column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    type = Column(String(50), nullable=False, index=True)
    content = Column(Text, nullable=False)  # Stored as JSON string
    meta_data = Column(Text, default="{}")  # Stored as JSON string
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime, nullable=True)

    # Relationships
    workspace = relationship("Workspace", back_populates="memory_items")


class Integration(Base):
    """Integration model"""

    __tablename__ = "integrations"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)
    connection_details = Column(Text, nullable=False)  # Stored as JSON string
    # Stored as JSON array string
    capabilities_json = Column(Text, default="[]")
    last_active = Column(DateTime, default=datetime.utcnow)


class DomainExpertTask(Base):
    """Domain expert task model"""

    __tablename__ = "domain_expert_tasks"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    expert_type = Column(String(50), nullable=False, index=True)
    task_details = Column(Text, nullable=False)  # Stored as JSON string
    status = Column(String(50), nullable=False, index=True)
    progress = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    result = Column(Text, nullable=True)  # Stored as JSON string
    meta_data = Column(Text, default="{}")  # Stored as JSON string
