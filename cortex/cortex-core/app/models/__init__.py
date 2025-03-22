"""
Models package for Cortex Core.

This package contains all the data models for the application:
- Domain models: core business entities
- API schemas: request/response schemas for API endpoints
- LLM models: structured outputs for LLM interactions
"""

__all__ = [
    # Domain models
    "User",
    "Workspace",
    "Conversation",
    "Message",
    # API schemas
    "LoginRequest",
    "LoginResponse",
    "WorkspaceCreateRequest",
    "ConversationCreateRequest",
    "InputMessage",
    "MessageAck",
    "WorkspaceListResponse",
    "ConversationListResponse",
    "UserProfileResponse",
    # LLM models
    "ToolRequest",
    "FinalAnswer",
]
# Domain models
# API schemas
from app.models.api import (
    ConversationCreateRequest,
    ConversationListResponse,
    InputMessage,
    LoginRequest,
    LoginResponse,
    MessageAck,
    UserProfileResponse,
    WorkspaceCreateRequest,
    WorkspaceListResponse,
)
from app.models.domain import Conversation, Message, User, Workspace

# LLM structured output models
from app.models.llm import FinalAnswer, ToolRequest
