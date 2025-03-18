#!/usr/bin/env python3
"""
Reference Domain Expert MCP Server
This is a minimal example of an MCP server for use with Cortex Core
"""
import asyncio
import os
from typing import Dict, Any, List, AsyncIterator
from contextlib import asynccontextmanager
from mcp.server.fastmcp import FastMCP, Context


# Create a typed context for the lifespan manager
class AppContext:
    """App context for the MCP server lifespan"""

    def __init__(self):
        self.database = {}  # Simple in-memory database

    def add_data(self, key: str, value: Any) -> None:
        """Add data to the in-memory database"""
        self.database[key] = value

    def get_data(self, key: str) -> Any:
        """Get data from the in-memory database"""
        return self.database.get(key)

# Create a lifespan manager for the MCP server
@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """
    Lifespan manager for the MCP server
    - Setup: Initialize resources
    - Cleanup: Release resources
    """
    # Setup
    app_context = AppContext()
    app_context.add_data("version", "1.0.0")

    # Add some example data
    app_context.add_data("example1", {"text": "Example data 1"})
    app_context.add_data("example2", {"text": "Example data 2"})

    print("MCP Server starting...")
    try:
        yield app_context
    finally:
        # Cleanup
        print("MCP Server shutting down...")

# Create the MCP server
mcp = FastMCP(
    name="ReferenceExpert",
    description="A reference domain expert for testing MCP integration",
    lifespan=lifespan
)

@mcp.tool()
async def echo(message: str, ctx: Context) -> Dict[str, Any]:
    """Simple echo tool that returns the input message"""
    return {
        "content": [
            {
                "type": "text",
                "text": message
            }
        ]
    }

@mcp.tool()
async def analyze_text(
    text: str,
    ctx: Context,
    detailed: bool = False
) -> Dict[str, Any]:
    """
    Analyze the given text and return insights

    Args:
        text: The text to analyze
        ctx: The MCP execution context
        detailed: Whether to return detailed analysis
    """
    # Report progress for longer operations
    await ctx.info(f"Analyzing text: {text[:20]}...")

    # Simple analysis
    word_count = len(text.split())
    char_count = len(text)

    # Return basic result if not detailed
    if not detailed:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Analysis complete. Word count: {word_count}, Character count: {char_count}"
                }
            ]
        }

    # Do more detailed analysis (simulated with a delay)
    await asyncio.sleep(1)
    await ctx.report_progress(0.5, 1.0)

    # Create a more detailed response
    sentences = len([s for s in text.split(".") if s.strip()])
    avg_word_length = char_count / word_count if word_count > 0 else 0

    return {
        "content": [
            {
                "type": "text",
                "text": f"Detailed Analysis:\n- Word count: {word_count}\n- Character count: {char_count}\n- Sentence count: {sentences}\n- Avg word length: {avg_word_length:.2f}"
            }
        ]
    }

@mcp.tool()
async def process_data(
    items: List[str],
    ctx: Context,
    operation: str = "count"
) -> Dict[str, Any]:
    """
    Process a list of items with the specified operation

    Args:
        items: List of items to process
        ctx: The MCP execution context
        operation: Operation to perform (count, uppercase, sort)
    """
    total_items = len(items)

    # Show how to report progress for a multi-step operation
    for i, item in enumerate(items):
        await ctx.info(f"Processing item {i+1}/{total_items}: {item}")
        await ctx.report_progress(i, total_items)
        await asyncio.sleep(0.2)  # Simulate processing time

    # Complete progress
    await ctx.report_progress(total_items, total_items)

    # Perform the requested operation
    if operation == "count":
        result = f"Counted {total_items} items"
    elif operation == "uppercase":
        result = [item.upper() for item in items]
    elif operation == "sort":
        result = sorted(items)
    else:
        result = f"Unknown operation: {operation}"

    return {
        "content": [
            {
                "type": "text",
                "text": f"Operation '{operation}' result: {result}"
            }
        ]
    }

@mcp.resource("example://{id}")
def get_example(id: str) -> Dict[str, Any]:
    """
    Get example data by ID

    Args:
        id: The ID of the example to retrieve
    """
    # Get the context
    ctx = mcp.get_context()

    # Get data from the context
    app_context = ctx.request_context.lifespan_context
    example_data = app_context.get_data(f"example{id}")

    if not example_data:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Example with ID '{id}' not found"
                }
            ]
        }

    return {
        "content": [
            {
                "type": "text",
                "text": example_data["text"]
            }
        ]
    }

@mcp.prompt()
def example_prompt(parameter: str) -> str:
    """
    Example prompt template

    Args:
        parameter: A parameter to include in the prompt
    """
    return f"""
    This is an example prompt template.

    It includes a parameter: {parameter}

    Please process this information and respond appropriately.
    """

if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.environ.get("PORT", 5001))

    print(f"Starting MCP server on port {port}")

    # Set the port for the server
    mcp.settings.port = port

    # Run the server with SSE transport
    mcp.run(transport="sse")