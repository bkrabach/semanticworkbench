"""
Pydantic AI models for LLM interactions.

This module defines the models used for structured interactions with LLMs
via the Pydantic AI framework.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from typing_extensions import TypedDict


# Define our own ChatMessage for compatibility with code
class ChatMessage(TypedDict):
    """Format of messages for LLM interactions."""

    role: str
    content: str


class UserMessage(BaseModel):
    """Represents a message from a user."""

    content: str = Field(..., description="The user's message")


class SystemMessage(BaseModel):
    """Represents a system message."""

    content: str = Field(..., description="The system's message")


class AssistantMessage(BaseModel):
    """Represents a message from the assistant."""

    content: str = Field(..., description="The assistant's message")


class ToolCall(BaseModel):
    """Represents a tool call request."""

    id: str = Field(..., description="The ID of the tool call")
    name: str = Field(..., description="The name of the tool being called")
    arguments: Dict[str, Any] = Field(..., description="The arguments to pass to the tool")


class LLMInput(BaseModel):
    """Input structure for LLM requests."""

    user_message: UserMessage
    system_message: Optional[SystemMessage] = None
    history: List[ChatMessage] = Field(default_factory=list, description="The conversation history")
    tools: Optional[List[Dict[str, Any]]] = None


class LLMOutput(BaseModel):
    """Output structure from LLM responses."""

    response: AssistantMessage
    tool_calls: Optional[List[ToolCall]] = None
