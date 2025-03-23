"""
Cognition API endpoints.

This module provides endpoints for accessing Cognition Service capabilities directly.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from ..core.exceptions import AccessDeniedError
from ..core.tools import analyze_conversation, get_context, search_history
from ..models.api.request import AnalyzeConversationRequest, GetContextRequest, SearchHistoryRequest
from ..models.api.response import AnalyzeConversationResponse, ErrorResponse, GetContextResponse, SearchHistoryResponse
from ..utils.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["cognition"])


@router.post(
    "/cognition/context",
    response_model=GetContextResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def get_user_context(request: GetContextRequest, current_user: dict = Depends(get_current_user)):
    """
    Get relevant context for the current user.

    Args:
        request: The context request
        current_user: The authenticated user

    Returns:
        Context response with relevant information
    """
    user_id = current_user["user_id"]
    logger.info(f"Retrieving context for user {user_id}")

    try:
        # Ensure limit has a valid value before passing it to the function
        limit = 10 if request.limit is None else request.limit
        
        # Call the get_context tool function
        result = await get_context(user_id=user_id, query=request.query, limit=limit)

        # Return the result
        return GetContextResponse(status="success", data=result)
    except Exception as e:
        logger.error(f"Error retrieving context: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "internal_error",
                    "message": "An error occurred while retrieving context",
                    "details": {"error": str(e)},
                }
            },
        )


@router.post(
    "/cognition/analyze",
    response_model=AnalyzeConversationResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def analyze_user_conversation(
    request: AnalyzeConversationRequest, current_user: dict = Depends(get_current_user)
):
    """
    Analyze a conversation for patterns and insights.

    Args:
        request: The analysis request
        current_user: The authenticated user

    Returns:
        Analysis response with results
    """
    user_id = current_user["user_id"]
    logger.info(f"Analyzing conversation {request.conversation_id} for user {user_id}")

    try:
        # Ensure analysis_type has a valid value
        analysis_type = "summary" if request.analysis_type is None else request.analysis_type
        
        # Call the analyze_conversation tool function
        result = await analyze_conversation(
            user_id=user_id, conversation_id=request.conversation_id, analysis_type=analysis_type
        )

        # Return the result
        return AnalyzeConversationResponse(status="success", data=result)
    except AccessDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "permission_denied", "message": str(e)}},
        )
    except Exception as e:
        logger.error(f"Error analyzing conversation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "internal_error",
                    "message": "An error occurred while analyzing conversation",
                    "details": {"error": str(e)},
                }
            },
        )


@router.post(
    "/cognition/search",
    response_model=SearchHistoryResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def search_user_history(request: SearchHistoryRequest, current_user: dict = Depends(get_current_user)):
    """
    Search user history for specific terms or patterns.

    Args:
        request: The search request
        current_user: The authenticated user

    Returns:
        Search response with results
    """
    user_id = current_user["user_id"]
    logger.info(f"Searching history for user {user_id} with query '{request.query}'")

    try:
        # Ensure parameters have valid values
        limit = 10 if request.limit is None else request.limit
        include_conversations = True if request.include_conversations is None else request.include_conversations
        
        # Call the search_history tool function
        result = await search_history(
            user_id=user_id,
            query=request.query,
            limit=limit,
            include_conversations=include_conversations,
        )

        # Return the result
        return SearchHistoryResponse(status="success", data=result)
    except Exception as e:
        logger.error(f"Error searching history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "internal_error",
                    "message": "An error occurred while searching history",
                    "details": {"error": str(e)},
                }
            },
        )
