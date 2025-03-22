import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class BaseDbModel:
    """Base database model with common fields."""

    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)


class User(Base, BaseDbModel):
    """User database model."""

    __tablename__ = "users"

    user_id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    metadata_json = Column(Text, default="{}")

    # Relationships
    workspaces = relationship("Workspace", back_populates="owner", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="sender", cascade="all, delete-orphan")


class Workspace(Base, BaseDbModel):
    """Workspace database model."""

    __tablename__ = "workspaces"

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    owner_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    metadata_json = Column(Text, default="{}")

    # Relationships
    owner = relationship("User", back_populates="workspaces")
    conversations = relationship("Conversation", back_populates="workspace", cascade="all, delete-orphan")


class Conversation(Base, BaseDbModel):
    """Conversation database model."""

    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True)
    topic = Column(String(200), nullable=False)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False)
    participant_ids_json = Column(Text, nullable=False, default="[]")  # Store as JSON array
    metadata_json = Column(Text, default="{}")

    # Relationships
    workspace = relationship("Workspace", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base, BaseDbModel):
    """Message database model."""

    __tablename__ = "messages"

    id = Column(String(36), primary_key=True)
    content = Column(Text, nullable=False)
    sender_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False)
    timestamp = Column(String(50), nullable=False)  # ISO format timestamp
    metadata_json = Column(Text, default="{}")

    # Relationships
    sender = relationship("User", back_populates="messages")
    conversation = relationship("Conversation", back_populates="messages")


# Create indexes for frequently queried fields
# User indexes
Index("idx_user_email", User.email, unique=True)

# Workspace indexes
Index("idx_workspace_owner", Workspace.owner_id)

# Conversation indexes
Index("idx_conversation_workspace", Conversation.workspace_id)

# Message indexes
Index("idx_message_conversation", Message.conversation_id)
Index("idx_message_sender", Message.sender_id)
Index("idx_message_timestamp", Message.timestamp)
