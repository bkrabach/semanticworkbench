# Mock LLM Implementation Cleanup Plan

This document outlines how to move the mock LLM implementation to a test-specific location and simplify it to focus exclusively on test needs.

## Current Issues

1. **Improper Location**: The mock LLM is currently in the main app directory, mixed with production code.

2. **Dual Purpose**: The mock tries to serve both development and testing needs, creating unnecessary complexity.

3. **Import Confusion**: The way it's imported and used creates circular dependencies.

4. **Complex Logic**: It contains complex conditional logic not needed for testing.

## Implementation Plan

### 1. Create a Test-Specific Directory Structure

First, we'll create a dedicated location for test mocks:

```
tests/
  mocks/
    __init__.py
    mock_llm.py
    mock_services.py
```

### 2. Simplify and Move the MockLLM Implementation

```python
# tests/mocks/mock_llm.py

"""
Mock LLM implementation for testing.

This module provides a simplified mock implementation of an LLM for testing purposes.
It should not be imported in production code.
"""

import logging
import json
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MockLLM:
    """Simple mock implementation of an LLM for testing purposes."""

    def __init__(self) -> None:
        """Initialize the mock LLM."""
        logger.info("Initializing Mock LLM")
        self.responses = {
            "greeting": "Hello! How can I assist you today?",
            "help": "I'm here to help. What would you like to know?",
            "default": "I understand your message. How else can I assist you?",
        }
        self.tools = {
            "get_current_time": {
                "response": "Let me check the current time for you.",
                "input": {}
            },
            "get_user_info": {
                "response": "Let me get that user information for you.",
                "input": {"user_id": "MOCK_USER_ID"}
            },
            "list_workspaces": {
                "response": "Here are your workspaces.",
                "input": {"user_id": "MOCK_USER_ID", "limit": 5}
            },
            "get_context": {
                "response": "Let me retrieve some relevant context.",
                "input": {"user_id": "MOCK_USER_ID", "query": "MOCK_QUERY"}
            }
        }
        self.tool_mode = False
        
    async def generate_mock_response(
        self, messages: List[Dict[str, str]], with_tool: bool = False
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
        # Override with_tool if tool_mode is set
        if self.tool_mode:
            with_tool = True
            
        # Simple pattern matching to determine response
        if not messages:
            return {"content": self.responses["default"]}

        # Get the last user message
        last_message = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_message = msg.get("content", "")
                break

        if not last_message:
            return {"content": self.responses["default"]}

        # Clean the content for comparison
        content = last_message.lower().strip()

        # Check for tool requests in the message
        if with_tool:
            # Check for patterns indicating tool usage
            tool_patterns = {
                r"time|current time|what time": "get_current_time",
                r"user info|about me|who am i": "get_user_info",
                r"workspaces|my workspaces|list workspace": "list_workspaces",
                r"context|relevant context|background": "get_context",
            }
            
            for pattern, tool_name in tool_patterns.items():
                if re.search(pattern, content):
                    logger.info(f"Mock LLM executing tool: {tool_name}")
                    return {
                        "tool": tool_name, 
                        "input": self.tools[tool_name]["input"]
                    }

        # Default responses based on content
        if "hello" in content or "hi" in content:
            return {"content": self.responses["greeting"]}
        elif "help" in content:
            return {"content": self.responses["help"]}
        else:
            # Default response
            return {"content": self.responses["default"]}
            
    def set_test_response(self, keyword: str, response: str) -> None:
        """
        Set a specific response for a keyword pattern to be used in tests.
        
        Args:
            keyword: The keyword to match in messages
            response: The response to return
        """
        self.responses[keyword] = response
    
    def set_test_tool_response(self, tool_name: str, response: str, input_params: Dict[str, Any]) -> None:
        """
        Set a specific tool response for tests.
        
        Args:
            tool_name: The name of the tool
            response: The text response to include
            input_params: The input parameters for the tool
        """
        self.tools[tool_name] = {
            "response": response,
            "input": input_params
        }
        
    def set_tool_mode(self, enabled: bool) -> None:
        """
        Force the mock to always return tool calls when enabled.
        
        Args:
            enabled: Whether to force tool mode
        """
        self.tool_mode = enabled


# Create a singleton instance for tests to use
mock_llm = MockLLM()


# Convenience function for backward compatibility
async def generate_mock_response(
    messages: List[Dict[str, str]], with_tool: bool = False
) -> Dict[str, Any]:
    """
    Generate a mock response based on the input messages.
    
    Args:
        messages: List of message dictionaries with "role" and "content" keys
        with_tool: Whether to potentially include a tool call in the response
        
    Returns:
        Dict with either {"content": "..."} for a final answer,
        or {"tool": "...", "input": {...}} for a tool request
    """
    return await mock_llm.generate_mock_response(messages, with_tool)
```

### 3. Update Tests to Use the New Mock Location

Any test that imports the mock LLM should be updated to use the new location:

```python
# Before
from app.core.mock_llm import mock_llm

# After
from tests.mocks.mock_llm import mock_llm
```

### 4. Update LLMAdapter to Use the New Mock Location

The LLMAdapter class needs to be updated to use the new mock location:

```python
# Before (in app/core/llm_adapter.py)
from .mock_llm import mock_llm

# After (in app/core/llm_adapter.py)
def _get_mock_response(self, messages: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
    """Get a response from the mock LLM if we're in test mode."""
    if self.use_mock:
        try:
            # Import here to avoid circular dependencies
            from tests.mocks.mock_llm import generate_mock_response
            return await generate_mock_response(messages)
        except ImportError:
            logger.warning("Mock LLM not available. This should only happen in production.")
            return {"content": "Mock LLM not available. This is a fallback response."}
    return None
```

### 5. Add Test Helper for Setting Up the Mock

Create helper functions in the test fixtures to make mocking easier:

```python
# tests/conftest.py
import pytest
from tests.mocks.mock_llm import mock_llm

@pytest.fixture
def setup_mock_llm():
    """Setup the mock LLM with default responses."""
    # Reset mock to default state
    mock_llm.responses = {
        "greeting": "Hello! How can I assist you today?",
        "help": "I'm here to help. What would you like to know?",
        "default": "I understand your message. How else can I assist you?",
    }
    mock_llm.tool_mode = False
    
    # Return the mock for further customization
    return mock_llm
```

## Required Changes

1. Create the tests/mocks directory structure
2. Move mock_llm.py to tests/mocks/
3. Simplify the MockLLM implementation
4. Update imports in tests that use the mock
5. Create test fixtures for setting up the mock
6. Update any code that directly imports the mock

## Testing Updates

1. All tests that use the mock LLM should be updated to import from the new location
2. Tests should use the new helper methods and fixtures
3. Ensure all test scenarios still work with the simplified implementation
4. Verify that production code doesn't import from tests/

## Benefits

1. **Clear Separation**: Mock code is clearly separated from production code
2. **Simplified Implementation**: Mock is focused solely on testing needs
3. **Better Testing Control**: New methods allow more control in tests
4. **Reduced Dependencies**: Production code doesn't depend on test code
5. **Improved Organization**: Code is organized by its purpose