"""
Standalone Cognition Service.

This module implements a standalone Cognition Service that serves 
MCP tools and resources over HTTP and SSE.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Cognition Service",
    description="MCP Cognition Service for context retrieval and analysis",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOW_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Memory service client
memory_client = None


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize the service on startup."""
    global memory_client
    
    logger.info("Initializing Cognition Service...")
    
    # Create Memory Service client
    memory_service_url = os.getenv("MEMORY_SERVICE_URL", "http://localhost:9000")
    memory_client = httpx.AsyncClient(base_url=memory_service_url, timeout=30.0)
    
    logger.info(f"Connected to Memory Service at {memory_service_url}")
    logger.info("Cognition Service started successfully")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Clean up resources on shutdown."""
    global memory_client
    
    logger.info("Shutting down Cognition Service...")
    
    # Close HTTP client
    if memory_client:
        await memory_client.aclose()
        memory_client = None
    
    logger.info("Cognition Service shutdown complete")


@app.get("/health")
async def health_check() -> Dict[str, str] | JSONResponse:
    """Health check endpoint for service discovery."""
    try:
        # Check memory service health
        memory_healthy = await _check_memory_service_health()
        
        # Return health status
        if memory_healthy:
            return {"status": "healthy"}
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "degraded",
                    "details": {
                        "memory_service": "unhealthy"
                    }
                }
            )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )


async def _check_memory_service_health() -> bool:
    """
    Check if the memory service is healthy.
    
    Returns:
        True if healthy, False otherwise
    """
    global memory_client
    
    try:
        # Check if we can connect to the Memory Service
        if memory_client:
            response = await memory_client.get("/health")
            return response.status_code == 200
        return False
    except Exception as e:
        logger.error(f"Memory service health check failed: {e}")
        return False


async def _dispatch_tool(tool_name: str, arguments: dict) -> dict:
    """
    Dispatch a tool call to the appropriate tool function.
    
    Args:
        tool_name: The name of the tool to call
        arguments: Arguments for the tool
    
    Returns:
        Tool result
    
    Raises:
        ValueError: If tool not found
    """
    # Call the appropriate tool based on the tool name
    if tool_name == "get_context":
        return await get_context(**arguments)
    elif tool_name == "analyze_conversation":
        return await analyze_conversation(**arguments)
    elif tool_name == "search_history":
        return await search_history(**arguments)
    else:
        raise ValueError(f"Tool not found: {tool_name}")


def _parse_resource_path(resource_path: str) -> tuple[str, str, dict]:
    """
    Parse a resource path into components.
    
    Args:
        resource_path: The resource path string
    
    Returns:
        Tuple of (resource_type, resource_id, params)
    
    Raises:
        ValueError: If path format is invalid
    """
    parts = resource_path.split("/")
    
    if len(parts) < 2:
        raise ValueError(f"Invalid resource path format: {resource_path}")
    
    resource_type = parts[0]
    resource_id = parts[1]
    params = {}
    
    # Handle special cases
    if resource_type == "conversation_analysis":
        if len(parts) < 3:
            raise ValueError("Invalid conversation analysis path. Format: conversation_analysis/{id}/{type}")
        params["analysis_type"] = parts[2]
    
    return resource_type, resource_id, params


@app.post("/tool/{tool_name}")
async def call_tool(tool_name: str, request: Request):
    """
    Endpoint for calling a tool on the Cognition Service.
    
    Args:
        tool_name: The name of the tool to call
        request: The HTTP request containing tool arguments
    
    Returns:
        The tool result
    """
    # Parse request body
    try:
        body = await request.json()
        arguments = body.get("arguments", {})
    except Exception as e:
        logger.error(f"Invalid request body: {e}")
        raise HTTPException(
            status_code=400, 
            detail={"error": {"code": "invalid_request", "message": "Invalid request body"}}
        )
    
    # Call the appropriate tool
    try:
        result = await _dispatch_tool(tool_name, arguments)
        return {"result": result}
    except ValueError as e:
        # Tool not found
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "tool_not_found", "message": str(e)}}
        )
    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "tool_execution_error",
                    "message": f"Error executing tool: {str(e)}",
                    "details": {"tool_name": tool_name}
                }
            }
        )


@app.get("/resource/{resource_path:path}")
async def get_resource(resource_path: str, request: Request):
    """
    Endpoint for accessing a resource stream.
    
    Args:
        resource_path: The resource path
        request: The HTTP request
    
    Returns:
        SSE stream of resource data
    """
    try:
        # Parse the resource path
        try:
            resource_type, resource_id, path_params = _parse_resource_path(resource_path)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": "invalid_resource_path",
                        "message": str(e)
                    }
                }
            )
        
        # Get user ID from query parameter - required for all endpoints
        user_id = request.query_params.get("user_id", "")
        if not user_id:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": "missing_parameter",
                        "message": "user_id parameter is required"
                    }
                }
            )
        
        if resource_type == "context":
            # Get query parameter
            query = request.query_params.get("query", "")
            
            # Get limit parameter
            limit_str = request.query_params.get("limit", "10")
            try:
                limit = int(limit_str)
            except ValueError:
                limit = 10
            
            # Create SSE stream for context data
            return StreamingResponse(
                get_context_stream(user_id, query, limit),
                media_type="text/event-stream"
            )
            
        elif resource_type == "conversation_analysis":
            # Analysis type should be in path_params from _parse_resource_path
            analysis_type = path_params.get("analysis_type", "summary")
            conversation_id = resource_id
            
            # Create SSE stream for conversation analysis
            return StreamingResponse(
                get_conversation_analysis_stream(user_id, conversation_id, analysis_type),
                media_type="text/event-stream"
            )
            
        else:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": "resource_not_found",
                        "message": f"Resource '{resource_path}' not found"
                    }
                }
            )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error accessing resource {resource_path}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "resource_access_error",
                    "message": f"Error accessing resource: {str(e)}",
                    "details": {"resource_path": resource_path}
                }
            }
        )


# Tool implementations

async def get_context(
    user_id: str,
    query: Optional[str] = None,
    limit: Optional[int] = 10,
    recency_weight: Optional[float] = 0.5,
    **kwargs
) -> Dict[str, Any]:
    """
    Get relevant context for a user based on their history and optional query.

    Args:
        user_id: The unique user identifier
        query: Optional search query to filter context
        limit: Maximum number of items to return (default: 10)
        recency_weight: Weight to apply to recency in ranking (0-1, default: 0.5)
        **kwargs: Additional arguments

    Returns:
        Dictionary containing context information
    """
    try:
        global memory_client
        
        # Validate user_id
        if not user_id:
            return {"context": [], "user_id": "", "query": query, "count": 0, "error": "User ID is required"}

        # Verify memory client
        if not memory_client:
            return {"context": [], "user_id": user_id, "query": query, "count": 0, "error": "Memory service not available"}
        
        # Retrieve user history from Memory Service
        history = []
        
        try:
            # Use limit * 2 to have more items for ranking
            fetch_limit = limit * 2 if limit else 20
            
            # Get user history via SSE stream
            async with memory_client.stream(
                "GET", f"/resource/history/{user_id}/limit/{fetch_limit}"
            ) as response:
                response.raise_for_status()
                
                # Process SSE stream
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            # Skip end marker
                            if not isinstance(data, dict) or "end" not in data:
                                history.append(data)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON in SSE stream: {line[6:]}")
                
        except Exception as e:
            logger.error(f"Error retrieving history from Memory Service: {e}")
            return {"context": [], "user_id": user_id, "query": query, "count": 0, "error": f"Failed to retrieve history: {str(e)}"}

        # If no history, return empty context
        if not history:
            return {"context": [], "user_id": user_id, "query": query, "count": 0}

        # Process and rank items
        ranked_items = _rank_context_items(history, query, recency_weight or 0.5)

        # Limit results
        context_items = ranked_items[:limit] if limit else ranked_items
        
        # Filter out error information from each item's metadata
        for item in context_items:
            if 'metadata' in item and item['metadata'] is not None:
                metadata = item['metadata']
                if isinstance(metadata.get('context'), dict) and 'error' in metadata['context']:
                    del metadata['context']['error']

        return {"context": context_items, "user_id": user_id, "query": query, "count": len(context_items)}
    except Exception as e:
        logger.error(f"Error generating context for user {user_id}: {e}")
        return {"context": [], "user_id": user_id, "query": query, "count": 0, "error": str(e)}


async def analyze_conversation(
    user_id: str, 
    conversation_id: str, 
    analysis_type: Optional[str] = "summary",
    **kwargs
) -> Dict[str, Any]:
    """
    Analyze a conversation for patterns and insights.

    Args:
        user_id: The unique user identifier
        conversation_id: The conversation ID to analyze
        analysis_type: Type of analysis to perform (summary, topics, sentiment)
        **kwargs: Additional arguments

    Returns:
        Dictionary containing analysis results
    """
    try:
        global memory_client
        
        # Validate parameters
        if not user_id or not conversation_id:
            return {
                "type": analysis_type,
                "results": {},
                "conversation_id": conversation_id,
                "error": "User ID and conversation ID are required",
            }

        # Verify memory client
        if not memory_client:
            return {
                "type": analysis_type,
                "results": {},
                "conversation_id": conversation_id,
                "error": "Memory service not available"
            }
        
        # Get conversation history from Memory Service
        conversation_items = []
        
        try:
            # Get conversation messages via SSE stream
            async with memory_client.stream(
                "GET", f"/resource/conversation/{conversation_id}"
            ) as response:
                response.raise_for_status()
                
                # Process SSE stream
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            # Skip end marker
                            if not isinstance(data, dict) or "end" not in data:
                                conversation_items.append(data)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON in SSE stream: {line[6:]}")
                
        except Exception as e:
            logger.error(f"Error retrieving conversation from Memory Service: {e}")
            return {
                "type": analysis_type,
                "results": {},
                "conversation_id": conversation_id,
                "error": f"Failed to retrieve conversation: {str(e)}"
            }

        if not conversation_items:
            return {
                "type": analysis_type,
                "results": {},
                "conversation_id": conversation_id,
                "error": "Conversation not found",
            }

        # Filter out error information from each item's metadata
        for item in conversation_items:
            if 'metadata' in item and item['metadata'] is not None:
                metadata = item['metadata']
                if isinstance(metadata.get('context'), dict) and 'error' in metadata['context']:
                    del metadata['context']['error']

        # Perform requested analysis
        if analysis_type == "summary":
            results = _generate_conversation_summary(conversation_items)
        elif analysis_type == "topics":
            results = _extract_conversation_topics(conversation_items)
        elif analysis_type == "sentiment":
            results = _analyze_conversation_sentiment(conversation_items)
        else:
            return {
                "type": analysis_type,
                "results": {},
                "conversation_id": conversation_id,
                "error": f"Unknown analysis type: {analysis_type}",
            }

        return {"type": analysis_type, "results": results, "conversation_id": conversation_id}
    except Exception as e:
        logger.error(f"Error analyzing conversation {conversation_id}: {e}")
        return {"type": analysis_type, "results": {}, "conversation_id": conversation_id, "error": str(e)}


async def search_history(
    user_id: str, 
    query: str, 
    limit: Optional[int] = 10, 
    include_conversations: Optional[bool] = True,
    **kwargs
) -> Dict[str, Any]:
    """
    Search user history for specific terms or patterns.

    Args:
        user_id: The unique user identifier
        query: Search query string
        limit: Maximum number of results to return (default: 10)
        include_conversations: Whether to include conversation data (default: True)
        **kwargs: Additional arguments

    Returns:
        Dictionary containing search results
    """
    try:
        global memory_client
        
        # Validate parameters
        if not user_id or not query:
            return {"results": [], "count": 0, "query": query, "error": "User ID and query are required"}

        # Verify memory client
        if not memory_client:
            return {"results": [], "count": 0, "query": query, "error": "Memory service not available"}
        
        # Get user history from Memory Service
        history = []
        
        try:
            # Get user history via SSE stream
            async with memory_client.stream(
                "GET", f"/resource/history/{user_id}"
            ) as response:
                response.raise_for_status()
                
                # Process SSE stream
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            # Skip end marker
                            if not isinstance(data, dict) or "end" not in data:
                                history.append(data)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON in SSE stream: {line[6:]}")
                
        except Exception as e:
            logger.error(f"Error retrieving history from Memory Service: {e}")
            return {"results": [], "count": 0, "query": query, "error": f"Failed to retrieve history: {str(e)}"}

        # Filter out error information from each item's metadata
        for item in history:
            if 'metadata' in item and item['metadata'] is not None:
                metadata = item['metadata']
                if isinstance(metadata.get('context'), dict) and 'error' in metadata['context']:
                    del metadata['context']['error']

        # Perform search
        results = []
        query_terms = query.lower().split()

        for item in history:
            # Extract content
            content = ""
            if "content" in item:
                content = item["content"].lower()
            elif "message" in item:
                content = item["message"].lower()

            # Check if any query term matches
            if any(term in content for term in query_terms):
                # If including conversations, add conversation data
                if include_conversations and "conversation_id" in item:
                    conversation_id = item["conversation_id"]

                    # Add a flag to indicate we'll fetch conversation data
                    # Avoid copying the entire conversation for efficiency
                    item["_has_conversation"] = True
                    item["_conversation_id"] = conversation_id

                results.append(item)

        # Sort by relevance
        scored_results = [(item, _calculate_relevance(item, query)) for item in results]
        scored_results.sort(key=lambda x: x[1], reverse=True)

        # Limit results
        limited_results = [item for item, _ in scored_results[:limit]] if limit else [item for item, _ in scored_results]

        # If we're including conversations and have results with conversation IDs
        if include_conversations and any("_has_conversation" in item for item in limited_results):
            # Fetch conversation data for all items in a single iteration
            conversation_ids = set(
                item["_conversation_id"] for item in limited_results if "_has_conversation" in item
            )

            # Fetch conversations and build a lookup map
            conversation_data = {}
            for conv_id in conversation_ids:
                conversation = []
                
                try:
                    # Get conversation via SSE stream
                    async with memory_client.stream(
                        "GET", f"/resource/conversation/{conv_id}"
                    ) as response:
                        response.raise_for_status()
                        
                        # Process SSE stream
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                try:
                                    data = json.loads(line[6:])
                                    # Skip end marker
                                    if not isinstance(data, dict) or "end" not in data:
                                        conversation.append(data)
                                except json.JSONDecodeError:
                                    logger.warning(f"Invalid JSON in SSE stream: {line[6:]}")
                    
                    if conversation:
                        # For each conversation, create a simple summary
                        conversation_data[conv_id] = {
                            "message_count": len(conversation),
                            "participants": len(set(msg.get("sender_id", "") for msg in conversation)),
                            "first_message": conversation[0]["content"] if conversation else "",
                        }
                        
                except Exception as e:
                    logger.error(f"Error retrieving conversation {conv_id} from Memory Service: {e}")

            # Add conversation data to results
            for item in limited_results:
                if "_has_conversation" in item:
                    conv_id = item["_conversation_id"]
                    if conv_id in conversation_data:
                        item["_conversation_data"] = conversation_data[conv_id]

                    # Remove temporary fields
                    del item["_has_conversation"]
                    del item["_conversation_id"]

        return {"results": limited_results, "count": len(limited_results), "query": query}
    except Exception as e:
        logger.error(f"Error searching history for user {user_id}: {e}")
        return {"results": [], "count": 0, "query": query, "error": str(e)}


# Resource stream implementations

async def get_context_stream(user_id: str, query: str, limit: int):
    """
    Generate SSE stream for context items.
    
    Args:
        user_id: The user ID
        query: The search query
        limit: Maximum items to return
        
    Yields:
        SSE-formatted context items
    """
    try:
        # Call the get_context tool and stream the results
        context_result = await get_context(user_id, query, limit)
        
        if "error" in context_result:
            yield f"data: {json.dumps({'error': context_result['error']})}\n\n"
            return
        
        # Stream each context item
        for item in context_result.get("context", []):
            yield f"data: {json.dumps(item)}\n\n"
            # Small delay for client processing
            await asyncio.sleep(0.01)
        
        # End of stream
        yield f"data: {json.dumps({'end': True})}\n\n"
    except Exception as e:
        logger.error(f"Error streaming context for user {user_id}: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


async def get_conversation_analysis_stream(user_id: str, conversation_id: str, analysis_type: str):
    """
    Generate SSE stream for conversation analysis.
    
    Args:
        user_id: The user ID
        conversation_id: The conversation ID
        analysis_type: The type of analysis to perform
        
    Yields:
        SSE-formatted analysis results
    """
    try:
        # Call the analyze_conversation tool
        analysis_result = await analyze_conversation(user_id, conversation_id, analysis_type)
        
        if "error" in analysis_result:
            yield f"data: {json.dumps({'error': analysis_result['error']})}\n\n"
            return
        
        # Stream the analysis result
        yield f"data: {json.dumps(analysis_result)}\n\n"
        
        # End of stream
        yield f"data: {json.dumps({'end': True})}\n\n"
    except Exception as e:
        logger.error(f"Error streaming analysis for conversation {conversation_id}: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


# Helper functions

def _rank_context_items(
    items: List[Dict[str, Any]], query: Optional[str], recency_weight: float
) -> List[Dict[str, Any]]:
    """
    Rank context items based on relevance and recency.

    Args:
        items: History items to rank
        query: Optional query to rank against
        recency_weight: Weight for recency (0-1)

    Returns:
        Ranked list of items
    """
    # Convert timestamps to datetime objects
    for item in items:
        if "timestamp" in item:
            try:
                item["_datetime"] = datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00"))
            except (ValueError, TypeError):
                # If timestamp can't be parsed, use current time
                item["_datetime"] = datetime.now()
        else:
            item["_datetime"] = datetime.now()

    # Sort by recency (newest first)
    items_by_recency = sorted(items, key=lambda x: x.get("_datetime", datetime.min), reverse=True)

    # If query provided, calculate relevance
    if query:
        for item in items:
            # Simple relevance calculation
            item["_relevance"] = _calculate_relevance(item, query)

        # Sort by combined score
        ranked_items = sorted(
            items,
            key=lambda x: (
                (1 - recency_weight) * x.get("_relevance", 0)
                + recency_weight * (1.0 - items_by_recency.index(x) / max(len(items), 1))
            ),
            reverse=True,
        )
    else:
        # If no query, sort by recency only
        ranked_items = items_by_recency

    # Remove temporary ranking fields
    for item in ranked_items:
        if "_datetime" in item:
            del item["_datetime"]
        if "_relevance" in item:
            del item["_relevance"]

    return ranked_items


def _calculate_relevance(item: Dict[str, Any], query: str) -> float:
    """
    Calculate relevance score for an item against a query.

    Args:
        item: The history item
        query: The search query

    Returns:
        Relevance score (0-1)
    """
    if not query:
        return 0.0

    query_terms = query.lower().split()

    # Search in item content
    content = ""
    if "content" in item:
        content = item["content"].lower()
    elif "message" in item:
        content = item["message"].lower()

    # Simple term matching
    matches = sum(1 for term in query_terms if term in content)
    if not query_terms:
        return 0.0

    # Return proportion of matching terms
    return matches / len(query_terms)


def _generate_conversation_summary(conversation_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate a summary of the conversation.

    Args:
        conversation_items: List of conversation messages

    Returns:
        Dictionary with summary information
    """
    # Simple count-based summary
    message_count = len(conversation_items)

    # Count messages by sender
    senders = {}
    for item in conversation_items:
        sender = item.get("sender_id", "unknown")
        senders[sender] = senders.get(sender, 0) + 1

    # Extract timestamps for duration calculation
    timestamps = []
    for item in conversation_items:
        if "timestamp" in item:
            try:
                ts = datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00"))
                timestamps.append(ts)
            except (ValueError, TypeError):
                pass

    # Calculate duration if possible
    duration_seconds = 0.0
    if len(timestamps) >= 2:
        duration_seconds = (max(timestamps) - min(timestamps)).total_seconds()

    return {
        "message_count": message_count,
        "participants": len(senders),
        "duration_seconds": duration_seconds,
        "participant_counts": senders,
    }


def _extract_conversation_topics(conversation_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract topics from the conversation.

    Args:
        conversation_items: List of conversation messages

    Returns:
        Dictionary with topic information
    """
    # Simple keyword-based topic extraction
    # Combine all content
    combined_content = " ".join([item.get("content", "") for item in conversation_items])

    # Remove common stop words
    stop_words = {"the", "a", "an", "and", "or", "but", "of", "to", "in", "is", "it", "that", "this", "for", "with"}

    # Split into words and count frequencies
    words = combined_content.lower().split()
    word_counts = {}

    for word in words:
        if word not in stop_words and len(word) > 3:
            word_counts[word] = word_counts.get(word, 0) + 1

    # Get top keywords
    sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
    topics = sorted_words[:10]

    return {"keywords": [{"word": word, "count": count} for word, count in topics], "word_count": len(words)}


def _analyze_conversation_sentiment(conversation_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze sentiment in the conversation.

    Args:
        conversation_items: List of conversation messages

    Returns:
        Dictionary with sentiment information
    """
    # Very simple rule-based sentiment analysis
    positive_words = {
        "good",
        "great",
        "excellent",
        "amazing",
        "awesome",
        "fantastic",
        "wonderful",
        "happy",
        "like",
        "love",
    }
    negative_words = {
        "bad",
        "terrible",
        "awful",
        "horrible",
        "disappointing",
        "sad",
        "hate",
        "dislike",
        "wrong",
        "problem",
    }

    positive_count = 0
    negative_count = 0

    for item in conversation_items:
        content = item.get("content", "").lower()

        # Count positive and negative words
        for word in positive_words:
            if word in content:
                positive_count += 1

        for word in negative_words:
            if word in content:
                negative_count += 1

    # Calculate simple sentiment score (-1 to 1)
    total = positive_count + negative_count
    sentiment_score = 0.0
    if total > 0:
        sentiment_score = (positive_count - negative_count) / total

    return {"sentiment_score": sentiment_score, "positive_count": positive_count, "negative_count": negative_count}


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Get port from environment or use default
    port = int(os.getenv("COGNITION_SERVICE_PORT", 9100))
    
    # Start server
    uvicorn.run(
        "app.services.standalone_cognition_service:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )