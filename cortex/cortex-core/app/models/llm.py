"""
Structured LLM output models for Cortex Core.

These Pydantic models define the structured outputs that might come from
an LLM, such as tool requests or final answers.
"""
from pydantic import BaseModel
from typing import Dict, Any


class ToolRequest(BaseModel):
    """
    Represents an AI request to invoke an external tool or service.
    Used when the LLM needs to use a tool to fulfill a request.
    """
    tool: str  # Name/identifier of the tool to use
    args: Dict[str, Any]  # Arguments for the tool


class FinalAnswer(BaseModel):
    """
    Represents the AI's final answer to be delivered to the user.
    Used when the LLM has a direct response with no further action needed.
    """
    answer: str  # The answer text to send to the user