# Tools Implementation Cleanup Plan

This document outlines the steps to simplify the Tools implementation by removing fallback mechanisms and relying exclusively on the MCP architecture.

## Current Issues

1. **Fallback Implementations**: The tools.py file contains multiple fallback implementations for when the MCP client is not available, adding unnecessary complexity.

2. **Conditional MCP Checks**: Every tool function includes code to check for MCP client availability, creating redundant patterns.

3. **Import Try/Except Pattern**: The module uses a try/except pattern to handle importing the MCP client, which obscures dependencies.

4. **Direct Database Access in Fallbacks**: Fallback implementations access the database directly, duplicating business logic that should remain in the services.

## Implementation Plan

### 1. Simplify MCP Client Import

Replace the try/except pattern with a direct import:

```python
"""
Tool implementation module.

This module provides implementations of various tools that can be used by the ResponseHandler.
Tools are defined using Pydantic models for input and output schemas to ensure
type safety and proper documentation through the Pydantic AI framework.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..database.unit_of_work import UnitOfWork
from .response_handler import register_tool
from .mcp import get_client

logger = logging.getLogger(__name__)
```

### 2. Remove Fallback Logic from `get_context` Tool

Simplify to use MCP exclusively:

```python
@register_tool("get_context")
async def get_context(user_id: str, query: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
    """
    Get relevant context for a conversation based on user history.

    Args:
        user_id: The user ID to get context for
        query: Optional search query to filter context
        limit: Maximum number of items to return

    Returns:
        Dictionary with context information
    """
    try:
        logger.info(f"Getting context for user {user_id}")

        # Get the MCP client
        mcp_client = get_client()

        # Get context from cognition service
        result = await mcp_client.get_resource(
            service_name="cognition", resource_name="context", 
            params={"user_id": user_id, "query": query, "limit": limit}
        )
        
        # Ensure result is a dictionary
        if not isinstance(result, dict):
            result = {"context": [], "user_id": user_id, "query": query, "count": 0, "error": "Invalid response format"}

        logger.info(f"Found {result.get('count', 0)} context items for user {user_id}")
        return result
    except Exception as e:
        logger.error(f"Error getting context: {e}")
        return {"context": [], "user_id": user_id, "query": query, "count": 0, "error": str(e)}
```

### 3. Remove Fallback Logic from `analyze_conversation` Tool

Simplify to use MCP exclusively:

```python
@register_tool("analyze_conversation")
async def analyze_conversation(user_id: str, conversation_id: str, analysis_type: str = "summary") -> Dict[str, Any]:
    """
    Analyze a conversation for patterns and insights.

    Args:
        user_id: The user ID requesting the analysis
        conversation_id: The conversation ID to analyze
        analysis_type: Type of analysis (summary, topics, sentiment)

    Returns:
        Dictionary with analysis results
    """
    try:
        logger.info(f"Analyzing conversation {conversation_id} for user {user_id}")

        # Get the MCP client
        mcp_client = get_client()

        # Get analysis from cognition service
        result = await mcp_client.get_resource(
            service_name="cognition",
            resource_name="analyze_conversation",
            params={"user_id": user_id, "conversation_id": conversation_id, "analysis_type": analysis_type},
        )
        
        # Ensure result is a dictionary
        if not isinstance(result, dict):
            result = {"type": analysis_type, "results": {}, "conversation_id": conversation_id, "error": "Invalid response format"}

        logger.info(f"Completed {analysis_type} analysis for conversation {conversation_id}")
        return result
    except Exception as e:
        logger.error(f"Error analyzing conversation: {e}")
        return {"type": analysis_type, "results": {}, "conversation_id": conversation_id, "error": str(e)}
```

### 4. Remove Fallback Logic from `search_history` Tool

Simplify to use MCP exclusively:

```python
@register_tool("search_history")
async def search_history(
    user_id: str, query: str, limit: int = 10, include_conversations: bool = True
) -> Dict[str, Any]:
    """
    Search user history for specific terms or patterns.

    Args:
        user_id: The user ID to search history for
        query: Search query string
        limit: Maximum number of results to return
        include_conversations: Whether to include conversation data

    Returns:
        Dictionary with search results
    """
    try:
        logger.info(f"Searching history for user {user_id} with query '{query}'")

        # Get the MCP client
        mcp_client = get_client()

        # Search history via cognition service
        result = await mcp_client.get_resource(
            service_name="cognition",
            resource_name="search_history",
            params={
                "user_id": user_id,
                "query": query,
                "limit": limit,
                "include_conversations": include_conversations,
            },
        )
        
        # Ensure result is a dictionary
        if not isinstance(result, dict):
            result = {"results": [], "count": 0, "query": query, "error": "Invalid response format"}

        logger.info(f"Found {result.get('count', 0)} matches for query '{query}'")
        return result
    except Exception as e:
        logger.error(f"Error searching history: {e}")
        return {"results": [], "count": 0, "query": query, "error": str(e)}
```

### 5. Remove MCPClientProtocol and Related Code

The `MCPClientProtocol` and its runtime_checkable decorator can be removed as we're relying directly on the MCP implementation.

## Required Changes

1. Remove the try/except block around importing `get_client`
2. Remove the fallback implementation in `get_context`
3. Remove the fallback implementation in `analyze_conversation`
4. Remove the fallback implementation in `search_history`
5. Remove the MCPClientProtocol definition
6. Update docstrings to reflect MCP-exclusive approach
7. Directly reference the MCP client without additional checks

## Testing Updates

1. Update tests to assume MCP is always available
2. Remove tests for the fallback paths
3. Focus test coverage on the MCP integration paths
4. Update any mocks to simulate the MCP client rather than bypassing it

## Benefits

1. **Simpler Code**: The tools implementation is significantly simplified by removing conditional paths.
2. **Clear Dependencies**: Dependencies are explicitly stated in imports without obfuscation.
3. **Consistency**: All tools follow the same pattern of using MCP for service access.
4. **Reduced Duplication**: Business logic remains in the services accessed through MCP.