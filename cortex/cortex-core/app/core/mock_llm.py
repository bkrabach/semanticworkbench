"""
Mock LLM implementation for development and testing.

This module provides a mock implementation of the LLM adapter that can be used
when real LLM providers are not available or for testing purposes.
"""

import logging
import random
import uuid
from typing import Any, Dict, List

from ..models.domain.pydantic_ai import (
    AssistantMessage,
    ChatMessage,
    LLMInput,
    LLMOutput,
    SystemMessage,
    ToolCall,
    UserMessage,
)

logger = logging.getLogger(__name__)


class MockLLMAgent:
    """Mock Agent implementation for testing."""

    def __init__(self):
        """Initialize the mock agent."""
        self.response_templates = [
            "I understand you're asking about {topic}. Let me help with that.",
            "That's an interesting question about {topic}. Here's what I know:",
            "Regarding {topic}, I can provide you with the following information:",
            "Let me address your question about {topic} with some helpful information.",
        ]

    def model_config(self):
        """Define the model configuration for the agent."""
        return {
            "model": "mock-model",
            "temperature": 0.0,
            "max_tokens": 1000,
        }

    async def run(self, input_data: LLMInput) -> LLMOutput:
        """
        Execute the mock agent with the given input.

        Args:
            input_data: The structured input for the LLM

        Returns:
            The structured output from the mock LLM
        """
        # Get the user message
        user_message = input_data.user_message.content

        # 30% chance of returning a tool call if tools are enabled
        if random.random() < 0.3 or "time" in user_message.lower():
            return LLMOutput(
                response=AssistantMessage(content=""),
                tool_calls=[ToolCall(id=str(uuid.uuid4()), name="get_current_time", arguments={})],
            )

        if random.random() < 0.3 or "user" in user_message.lower():
            return LLMOutput(
                response=AssistantMessage(content=""),
                tool_calls=[ToolCall(id=str(uuid.uuid4()), name="get_user_info", arguments={"user_id": "user123"})],
            )

        # Extract potential topic from the user message
        words = user_message.split()
        topic = words[-1] if len(words) > 0 else "your question"

        # Select a random template and format it
        template = random.choice(self.response_templates)
        response = template.format(topic=topic)

        # Add some generic content
        response += "\n\n"
        response += (
            f"Based on the information available, {topic} refers to a concept or entity "
            f"that has various aspects to consider. I'd be happy to provide more specific "
            f"information if you could clarify your question about {topic}."
        )

        return LLMOutput(response=AssistantMessage(content=response), tool_calls=None)


class MockLLM:
    """Mock LLM implementation that returns predefined responses."""

    def __init__(self):
        """Initialize the mock LLM with predefined responses."""
        self.agent = MockLLMAgent()
        self.response_templates = [
            "I understand you're asking about {topic}. Let me help with that.",
            "That's an interesting question about {topic}. Here's what I know:",
            "Regarding {topic}, I can provide you with the following information:",
            "Let me address your question about {topic} with some helpful information.",
        ]

    async def generate_mock_response(self, messages: List[Dict[str, str]], with_tool: bool = False) -> Dict[str, Any]:
        """
        Generate a mock response based on the input messages.

        Args:
            messages: List of message dictionaries with "role" and "content" keys
            with_tool: Whether to include a tool call in the response

        Returns:
            Dict with either {"content": "..."} for a final answer,
            or {"tool": "...", "input": {...}} for a tool request
        """
        # Extract system message if present
        system_message = None
        chat_history = []
        user_message = None

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                system_message = SystemMessage(content=content)
            elif role == "user":
                # Keep track of the last user message
                user_message = UserMessage(content=content)
            else:
                # Add to history
                chat_history.append(ChatMessage(role=role, content=content))

        # If no user message was found, use the last message
        if not user_message and messages:
            last_msg = messages[-1]
            user_message = UserMessage(content=last_msg.get("content", ""))

        # Make sure we have a user message
        if not user_message:
            user_message = UserMessage(content="")

        # Create input for the agent
        input_data = LLMInput(user_message=user_message, system_message=system_message, history=chat_history)

        # Force tool response if requested
        if with_tool:
            # Alternate between time and user info tools
            if random.random() < 0.5:
                return {"tool": "get_current_time", "input": {}}
            else:
                return {"tool": "get_user_info", "input": {"user_id": "user123"}}

        # Run the mock agent
        try:
            output = await self.agent.run(input_data)

            # Convert the output to the expected format
            if output.tool_calls:
                # Return the first tool call
                tool_call = output.tool_calls[0]
                return {"tool": tool_call.name, "input": tool_call.arguments}
            else:
                # Return the content
                return {"content": output.response.content}
        except Exception as e:
            logger.error(f"Mock LLM failed: {str(e)}")
            return {"content": "I apologize, but I encountered an error."}


# Create singleton instance
mock_llm = MockLLM()
