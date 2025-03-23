"""
Cognition Service - Main Entrypoint

This module initializes and runs the FastMCP server for the Cognition Service,
handling SSE connections from the Core orchestrator and processing LLM requests.
"""

import logging
import sys
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from .config import settings
from .logic import evaluate_context, generate_ai_response

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("cognition_service")

# Create MCP server instance
mcp = FastMCP("CognitionService")


@mcp.tool()
async def generate_reply(user_id: str, conversation_id: str, content: str) -> str:
    """
    Generate an assistant reply for a new user message.

    Args:
        user_id: The user's ID
        conversation_id: The conversation ID
        content: The user's message content

    Returns:
        The generated AI response text
    """
    logger.info(f"generate_reply called for user {user_id}, conversation {conversation_id}")

    try:
        return await generate_ai_response(user_id, conversation_id, content)
    except Exception as e:
        logger.error(f"Error in generate_reply: {e}")
        return "I apologize, but I encountered an error processing your request. Please try again."


@mcp.tool()
async def evaluate_context_tool(
    user_id: str,
    conversation_id: str,
    message: str,
    memory_snippets: Optional[List[Dict[str, Any]]] = None,
    expert_insights: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Evaluate context and generate response with optional memory and expert insights.

    Args:
        user_id: The ID of the user
        conversation_id: The ID of the conversation
        message: The user's message
        memory_snippets: Optional list of memory snippets for context
        expert_insights: Optional list of domain expert insights

    Returns:
        A dictionary containing the response message and any additional metadata
    """
    logger.info(f"evaluate_context called for user {user_id}, conversation {conversation_id}")

    try:
        response = await evaluate_context(
            user_id=user_id,
            conversation_id=conversation_id,
            message=message,
            memory_snippets=memory_snippets or [],
            expert_insights=expert_insights or [],
        )
        return {"message": response}
    except Exception as e:
        logger.error(f"Error in evaluate_context: {e}")
        return {"message": "I apologize, but I encountered an error processing your request. Please try again."}


@mcp.tool()
async def health() -> Dict[str, Any]:
    """
    Health check endpoint to verify service is running.

    Returns:
        A dictionary with service status information
    """
    return {
        "status": "healthy",
        "service": "cognition",
        "version": "0.1.0",
        "provider": settings.llm_provider,
        "model": settings.model_name,
    }


def run() -> None:
    """Run the Cognition Service."""
    logger.info(f"Starting Cognition Service on {settings.host}:{settings.port}")
    mcp.settings.host = settings.host
    mcp.settings.port = settings.port
    mcp.run(transport="sse")


if __name__ == "__main__":
    run()
