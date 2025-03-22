"""
Mock LLM implementation for development and testing.

This module provides a mock implementation of the LLM adapter that can be used
when real LLM providers are not available or for testing purposes.
"""
import logging
import random
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class MockLLM:
    """Mock LLM implementation that returns predefined responses."""
    
    def __init__(self):
        """Initialize the mock LLM with predefined responses."""
        self.response_templates = [
            "I understand you're asking about {topic}. Let me help with that.",
            "That's an interesting question about {topic}. Here's what I know:",
            "Regarding {topic}, I can provide you with the following information:",
            "Let me address your question about {topic} with some helpful information."
        ]
        
    async def generate_mock_response(
        self, 
        messages: List[Dict[str, str]], 
        with_tool: bool = False
    ) -> Dict[str, Any]:
        """
        Generate a mock response based on the input messages.
        
        Args:
            messages: List of message dictionaries with "role" and "content" keys
            with_tool: Whether to include a tool call in the response
            
        Returns:
            Dict with either {"content": "..."} for a final answer,
            or {"tool": "...", "input": {...}} for a tool request
        """
        # Extract the last user message
        user_message = ""
        for msg in reversed(messages):
            if msg["role"] == "user":
                user_message = msg["content"]
                break
                
        # If with_tool is True or random chance (20%), return a tool response
        if with_tool or (random.random() < 0.2 and "time" in user_message.lower()):
            return {
                "tool": "get_current_time",
                "input": {}
            }
            
        if with_tool or (random.random() < 0.2 and "user" in user_message.lower()):
            return {
                "tool": "get_user_info",
                "input": {"user_id": "user123"}  # Mock user ID
            }
        
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
        
        return {"content": response}


# Create singleton instance
mock_llm = MockLLM()