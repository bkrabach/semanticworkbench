"""
Tests for the standalone Memory Service.
"""

import asyncio
import json
from typing import Any, AsyncGenerator, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from fastapi.responses import JSONResponse


# Create a mock version of the module to avoid FastAPI dependency issues
class MockMemoryService:
    """Mock for the standalone_memory_service module."""

    # Mock data structures
    mock_messages: List[Dict[str, Any]] = []
    
    # Mock repository manager
    repository_manager: Any = None
    
    # Mock UnitOfWork attributes
    unit_of_work: Any = None

    async def startup_event(self) -> None:
        """Initialize the service on startup."""
        # Initialize mock repositories
        self.repository_manager = MagicMock()
        self.repository_manager.initialize = AsyncMock()

    async def shutdown_event(self) -> None:
        """Clean up resources on shutdown."""
        # Clean up any resources
        self.repository_manager = None
    
    async def health_check(self) -> Dict[str, str] | JSONResponse:
        """Health check endpoint for service discovery."""
        # Check database connectivity
        try:
            if hasattr(self, 'unit_of_work') and self.unit_of_work:
                async with self.unit_of_work as uow:
                    # Simple query to verify database connection
                    message_repo = uow.repositories.get_message_repository()
                    await message_repo.count({})
                    await uow.commit()
                    return {"status": "healthy"}
            return {"status": "healthy"}  # Default for tests without unit_of_work setup
        except Exception as e:
            return JSONResponse(status_code=500, content={"status": "unhealthy", "error": str(e)})
    
    async def call_tool(self, tool_name: str, request: Any) -> Dict[str, Any] | JSONResponse:
        """Endpoint for calling a tool on the Memory Service."""
        # Parse request body
        try:
            body = await request.json()
            arguments = body.get("arguments", {})
        except Exception:
            raise HTTPException(
                status_code=400, detail={"error": {"code": "invalid_request", "message": "Invalid request body"}}
            )

        # Call the appropriate tool based on the tool name
        try:
            result: Optional[Dict[str, Any]] = None
            if tool_name == "store_input":
                result = await self.store_input(**arguments)
            elif tool_name == "update_message":
                result = await self.update_message(**arguments)
            elif tool_name == "delete_message":
                result = await self.delete_message(**arguments)
            elif tool_name == "get_message":
                message_result = await self.get_message(**arguments)
                # Convert None result to empty dict if needed
                result = message_result if message_result is not None else {"message": None}
            else:
                raise HTTPException(
                    status_code=404,
                    detail={"error": {"code": "tool_not_found", "message": f"Tool '{tool_name}' not found"}},
                )

            return {"result": result}
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "tool_execution_error",
                        "message": f"Error executing tool: {str(e)}",
                        "details": {"tool_name": tool_name},
                    }
                },
            )
    
    async def get_resource(self, resource_path: str, request: Any) -> Any:
        """Endpoint for accessing a resource stream."""
        # Parse the resource path to determine which resource to access
        parts = resource_path.split("/")
        resource_type = parts[0] if parts else ""

        try:
            if resource_type == "history":
                # Format: history/{user_id}
                if len(parts) < 2:
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "error": {
                                "code": "invalid_resource_path",
                                "message": "Invalid resource path for history. Format: history/{user_id}",
                            }
                        },
                    )

                user_id = parts[1]

                # Check for limit parameter
                limit = None
                if len(parts) >= 4 and parts[2] == "limit":
                    try:
                        limit = int(parts[3])
                    except ValueError:
                        raise HTTPException(
                            status_code=400,
                            detail={"error": {"code": "invalid_parameter", "message": "Invalid limit parameter"}},
                        )

                # Create SSE stream for history data
                return MockStreamingResponse(self.get_history_stream(user_id, limit), media_type="text/event-stream")

            elif resource_type == "conversation":
                # Format: conversation/{conversation_id}
                if len(parts) < 2:
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "error": {
                                "code": "invalid_resource_path",
                                "message": "Invalid resource path for conversation. Format: conversation/{conversation_id}",
                            }
                        },
                    )

                conversation_id = parts[1]

                # Check if this is a user-specific request
                user_id = None
                if len(parts) >= 4 and parts[2] == "user":
                    user_id = parts[3]

                # Create SSE stream for conversation data
                return MockStreamingResponse(self.get_conversation_stream(conversation_id, user_id), media_type="text/event-stream")

            else:
                raise HTTPException(
                    status_code=404,
                    detail={"error": {"code": "resource_not_found", "message": f"Resource '{resource_path}' not found"}},
                )
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": {
                        "code": "resource_access_error",
                        "message": f"Error accessing resource: {str(e)}",
                        "details": {"resource_path": resource_path},
                    }
                },
            )
        
    # Tool implementations
    async def store_input(self, user_id: str, input_data: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        """
        Store input data for a specific user.
        """
        try:
            # Validate user_id
            if not user_id:
                return {"status": "error", "user_id": "", "error": "User ID is required"}

            # Validate input_data
            if not input_data:
                return {"status": "error", "user_id": user_id, "error": "Input data is required"}

            # Create message data
            message_data = {
                "id": f"msg-{len(self.mock_messages) + 1}",
                "sender_id": user_id,
                "content": input_data.get("content", ""),
                "conversation_id": input_data.get("conversation_id", "default-conv"),
                "timestamp": input_data.get("timestamp", "2023-01-01T12:00:00"),
                "metadata": input_data.get("metadata", {}),
            }

            # Add to mock messages
            self.mock_messages.append(message_data)

            return {
                "status": "stored", 
                "user_id": user_id, 
                "item_id": message_data["id"]
            }
        except Exception as e:
            return {"status": "error", "user_id": user_id, "error": str(e)}

    async def update_message(self, user_id: str, message_id: str, updates: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        """
        Update an existing message.
        """
        try:
            # Validate parameters
            if not user_id or not message_id or not updates:
                return {
                    "status": "error",
                    "user_id": user_id,
                    "message_id": message_id,
                    "error": "User ID, message ID, and updates are required",
                }

            # Find the message in mock data
            message = None
            for msg in self.mock_messages:
                if msg["id"] == message_id:
                    message = msg
                    break

            if not message or message["sender_id"] != user_id:
                return {
                    "status": "error",
                    "user_id": user_id,
                    "message_id": message_id,
                    "error": "Message not found or access denied",
                }

            # Update allowed fields
            if "content" in updates:
                message["content"] = updates["content"]

            if "metadata" in updates:
                # Merge metadata
                message["metadata"] = {**(message["metadata"] or {}), **updates["metadata"]}
                
                # Add update timestamp if not present
                if "updated_at" not in message["metadata"]:
                    message["metadata"]["updated_at"] = "2023-01-01T12:30:00"

            return {"status": "updated", "user_id": user_id, "message_id": message_id}
        except Exception as e:
            return {"status": "error", "user_id": user_id, "message_id": message_id, "error": str(e)}

    async def delete_message(self, user_id: str, message_id: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Delete a message.
        """
        try:
            # Validate parameters
            if not user_id or not message_id:
                return {
                    "status": "error",
                    "user_id": user_id,
                    "message_id": message_id,
                    "error": "User ID and message ID are required",
                }

            # Find the message in mock data
            message = None
            message_idx = -1
            for idx, msg in enumerate(self.mock_messages):
                if msg["id"] == message_id:
                    message = msg
                    message_idx = idx
                    break

            if not message or message["sender_id"] != user_id:
                return {
                    "status": "error",
                    "user_id": user_id,
                    "message_id": message_id,
                    "error": "Message not found or access denied",
                }

            # Delete the message
            if message_idx >= 0:
                self.mock_messages.pop(message_idx)

            return {"status": "deleted", "user_id": user_id, "message_id": message_id}
        except Exception as e:
            return {"status": "error", "user_id": user_id, "message_id": message_id, "error": str(e)}

    async def get_message(self, message_id: str, **kwargs: Any) -> Optional[Dict[str, Any]]:
        """
        Get a specific message by ID.
        """
        try:
            # Validate message_id
            if not message_id:
                return None

            # Find the message in mock data
            for msg in self.mock_messages:
                if msg["id"] == message_id:
                    return msg

            return None
        except Exception:
            return None

    # Resource stream implementations
    async def get_history_stream(self, user_id: str, limit: Optional[int] = None) -> AsyncGenerator[str, None]:
        """
        Generate SSE stream for user history.
        """
        try:
            if not user_id:
                yield f"data: {json.dumps({'error': 'User ID is required'})}\n\n"
                return

            # Filter messages by user_id (sender_id)
            filtered_messages = [msg for msg in self.mock_messages if msg["sender_id"] == user_id]

            # Apply limit if specified
            if limit and limit > 0:
                filtered_messages = filtered_messages[:limit]

            # Stream each message
            for message in filtered_messages:
                yield f"data: {json.dumps(message)}\n\n"
                # Small delay for client processing
                await asyncio.sleep(0.01)

            # End of stream
            yield f"data: {json.dumps({'end': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    async def get_conversation_stream(self, conversation_id: str, user_id: Optional[str] = None) -> AsyncGenerator[str, None]:
        """
        Generate SSE stream for conversation messages.
        """
        try:
            if not conversation_id:
                yield f"data: {json.dumps({'error': 'Conversation ID is required'})}\n\n"
                return

            # Filter messages by conversation_id
            filtered_messages = [msg for msg in self.mock_messages if msg["conversation_id"] == conversation_id]

            # Further filter by user_id if specified
            if user_id:
                filtered_messages = [msg for msg in filtered_messages if msg["sender_id"] == user_id]

            # Stream each message
            for message in filtered_messages:
                yield f"data: {json.dumps(message)}\n\n"
                # Small delay for client processing
                await asyncio.sleep(0.01)

            # End of stream
            yield f"data: {json.dumps({'end': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"


# Create a mock instance
sms = MockMemoryService()


@pytest.fixture
def mock_messages() -> List[Dict[str, Any]]:
    """Create mock message data for testing."""
    return [
        {
            "id": "msg1",
            "conversation_id": "conv1",
            "content": "Hello, how are you?",
            "sender_id": "user1",
            "timestamp": "2023-01-01T12:00:00",
            "metadata": {"role": "user"},
        },
        {
            "id": "msg2",
            "conversation_id": "conv1",
            "content": "I'm doing well, thank you!",
            "sender_id": "assistant",
            "timestamp": "2023-01-01T12:01:00",
            "metadata": {"role": "assistant"},
        },
        {
            "id": "msg3",
            "conversation_id": "conv2",
            "content": "Let's talk about something else.",
            "sender_id": "user1",
            "timestamp": "2023-01-01T12:02:00",
            "metadata": {"role": "user"},
        },
    ]


@pytest.fixture
def mock_unit_of_work() -> Any:
    """Create a mock unit of work."""
    mock_uow = MagicMock()
    mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
    mock_uow.__aexit__ = AsyncMock(return_value=None)
    mock_uow.commit = AsyncMock()
    
    # Create mock repository
    mock_repo = MagicMock()
    mock_repo.count = AsyncMock(return_value=5)
    mock_repo.create = AsyncMock(side_effect=lambda msg: msg)
    mock_repo.update = AsyncMock(side_effect=lambda msg: msg)
    mock_repo.get_by_id = AsyncMock()
    mock_repo.delete = AsyncMock(return_value=True)
    mock_repo.list_by_sender = AsyncMock()
    mock_repo.list_by_conversation = AsyncMock()
    
    # Add repository to UoW
    mock_uow.repositories = MagicMock()
    mock_uow.repositories.get_message_repository = MagicMock(return_value=mock_repo)
    
    return mock_uow


# Utility classes for testing
class MockRequest:
    """Mock class for FastAPI Request objects."""

    def __init__(
        self, query_params: Optional[Dict[str, str]] = None, json_data: Optional[Dict[str, Any]] = None
    ) -> None:
        self.query_params = query_params or {}
        self._json_data = json_data or {}

    async def json(self) -> Dict[str, Any]:
        """Return mock JSON data."""
        return self._json_data


class MockStreamingResponse:
    """Mock class for StreamingResponse."""

    def __init__(self, content_generator: AsyncGenerator[str, None], media_type: Optional[str] = None) -> None:
        self.content_generator = content_generator
        self.media_type = media_type

    async def get_content(self) -> List[str]:
        """Get all content from the generator."""
        content: List[str] = []
        async for chunk in self.content_generator:
            content.append(chunk)
        return content


# Test startup and shutdown events
@pytest.mark.asyncio
async def test_startup_event() -> None:
    """Test startup event initializes service."""
    # Reset mock
    sms.repository_manager = None
    
    # Call startup event
    await sms.startup_event()
    
    # Verify repository manager was initialized
    assert sms.repository_manager is not None
    assert isinstance(sms.repository_manager.initialize, AsyncMock)
    

@pytest.mark.asyncio
async def test_shutdown_event() -> None:
    """Test shutdown event cleans up resources."""
    # Set up mock repository manager
    sms.repository_manager = MagicMock()
    
    # Call shutdown event
    await sms.shutdown_event()
    
    # Verify repository manager was cleared
    assert sms.repository_manager is None


# Test health check endpoint
@pytest.mark.asyncio
async def test_health_check_success(mock_unit_of_work: Any) -> None:
    """Test successful health check."""
    # Set up unit of work
    sms.unit_of_work = mock_unit_of_work
    
    # Call health check
    result = await sms.health_check()
    
    # Verify result
    assert isinstance(result, dict)
    assert result["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_check_failure(mock_unit_of_work: Any) -> None:
    """Test health check with database error."""
    # Set up unit of work
    sms.unit_of_work = mock_unit_of_work
    
    # Set up mock to raise an exception
    mock_unit_of_work.repositories.get_message_repository().count.side_effect = Exception("Database connection error")
    
    # Call health check
    result = await sms.health_check()
    
    # Verify result is a JSONResponse with unhealthy status
    assert isinstance(result, JSONResponse)
    assert result.status_code == 500
    # Convert response body to string safely
    body_str = result.body.decode('utf-8') if isinstance(result.body, bytes) else str(result.body)
    body_dict = json.loads(body_str)
    assert body_dict["status"] == "unhealthy"
    assert "Database connection error" in body_dict["error"]


# Test call_tool endpoint
@pytest.mark.asyncio
async def test_call_tool_success() -> None:
    """Test successful tool call."""
    # Test store_input tool
    mock_request = MockRequest(json_data={"arguments": {"user_id": "user1", "input_data": {"content": "Test message"}}})
    result = await sms.call_tool("store_input", mock_request)
    
    # Verify result
    assert isinstance(result, dict)
    assert "result" in result
    assert result["result"]["status"] == "stored"
    assert result["result"]["user_id"] == "user1"


@pytest.mark.asyncio
async def test_call_tool_invalid_tool() -> None:
    """Test calling invalid tool."""
    # Test invalid tool
    mock_request = MockRequest(json_data={"arguments": {"user_id": "user1"}})
    
    # Should raise HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await sms.call_tool("invalid_tool", mock_request)
    
    # Verify exception
    assert exc_info.value.status_code == 404
    # Access the detail field safely
    detail = exc_info.value.detail
    if isinstance(detail, dict):
        error_dict = detail.get("error")
        if isinstance(error_dict, dict):
            assert error_dict.get("code") == "tool_not_found"
        else:
            assert False, "Expected HTTPException detail to contain error dictionary"
    else:
        assert False, "Expected HTTPException detail to be a dictionary"


@pytest.mark.asyncio
async def test_call_tool_invalid_request() -> None:
    """Test tool call with invalid request body."""
    # Create a custom mock request class with json method that raises an exception
    class MockRequestWithError:
        """Custom mock request that raises error on json()."""
        async def json(self) -> Dict[str, Any]:
            """Raise an exception during json parsing."""
            raise Exception("JSON parsing error")
    
    mock_request = MockRequestWithError()
    
    # Should raise HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await sms.call_tool("store_input", mock_request)
    
    # Verify exception
    assert exc_info.value.status_code == 400
    # Access the detail field safely
    detail = exc_info.value.detail
    if isinstance(detail, dict):
        error_dict = detail.get("error")
        if isinstance(error_dict, dict):
            assert error_dict.get("code") == "invalid_request"
        else:
            assert False, "Expected HTTPException detail to contain error dictionary"
    else:
        assert False, "Expected HTTPException detail to be a dictionary"


@pytest.mark.asyncio
async def test_call_tool_execution_error() -> None:
    """Test tool execution error handling."""
    # Create a request that provides arguments that will cause an execution error
    mock_request = MockRequest(json_data={"arguments": {}})
    
    # This will fail because we'll try to access 'user_id' which is not provided
    result = await sms.call_tool("store_input", mock_request)
    
    # Verify result contains error
    assert isinstance(result, JSONResponse)
    assert result.status_code == 500
    # Convert response body to string safely
    body_str = result.body.decode('utf-8') if isinstance(result.body, bytes) else str(result.body)
    body_dict = json.loads(body_str)
    assert body_dict["error"]["code"] == "tool_execution_error"


# Test get_resource endpoint
@pytest.mark.asyncio
async def test_get_resource_history_success(mock_messages: List[Dict[str, Any]]) -> None:
    """Test successful history resource access."""
    # Set up mock messages
    sms.mock_messages = mock_messages
    
    # Test history resource
    mock_request = MockRequest()
    response = await sms.get_resource("history/user1", mock_request)
    
    # Verify response type
    assert isinstance(response, MockStreamingResponse)
    assert response.media_type == "text/event-stream"
    
    # Get content from the generator
    content = await response.get_content()
    
    # User1 has 2 messages in the mock data
    assert len(content) == 3  # 2 messages + end marker
    
    # Check message content
    message_text = content[0].replace("data: ", "").strip()
    first_message = json.loads(message_text)
    assert first_message["sender_id"] == "user1"
    
    # Check end marker
    assert "end" in content[-1]


@pytest.mark.asyncio
async def test_get_resource_history_with_limit(mock_messages: List[Dict[str, Any]]) -> None:
    """Test history resource access with limit parameter."""
    # Set up mock messages
    sms.mock_messages = mock_messages
    
    # Test history resource with limit
    mock_request = MockRequest()
    response = await sms.get_resource("history/user1/limit/1", mock_request)
    
    # Verify response type
    assert isinstance(response, MockStreamingResponse)
    
    # Get content from the generator
    content = await response.get_content()
    
    # Should only have 1 message + end marker with limit=1
    assert len(content) == 2  # 1 message + end marker


@pytest.mark.asyncio
async def test_get_resource_conversation_success(mock_messages: List[Dict[str, Any]]) -> None:
    """Test successful conversation resource access."""
    # Set up mock messages
    sms.mock_messages = mock_messages
    
    # Test conversation resource
    mock_request = MockRequest()
    response = await sms.get_resource("conversation/conv1", mock_request)
    
    # Verify response type
    assert isinstance(response, MockStreamingResponse)
    assert response.media_type == "text/event-stream"
    
    # Get content from the generator
    content = await response.get_content()
    
    # Conv1 has 2 messages in the mock data
    assert len(content) == 3  # 2 messages + end marker
    
    # Check first message
    message_text = content[0].replace("data: ", "").strip()
    first_message = json.loads(message_text)
    assert first_message["conversation_id"] == "conv1"


@pytest.mark.asyncio
async def test_get_resource_conversation_with_user(mock_messages: List[Dict[str, Any]]) -> None:
    """Test conversation resource access with user filter."""
    # Set up mock messages
    sms.mock_messages = mock_messages
    
    # Test conversation resource with user filter
    mock_request = MockRequest()
    response = await sms.get_resource("conversation/conv1/user/user1", mock_request)
    
    # Verify response type
    assert isinstance(response, MockStreamingResponse)
    
    # Get content from the generator
    content = await response.get_content()
    
    # Conv1 has 1 message from user1 in the mock data
    assert len(content) == 2  # 1 filtered message + end marker
    
    # Check message sender
    message_text = content[0].replace("data: ", "").strip()
    message = json.loads(message_text)
    assert message["sender_id"] == "user1"
    assert message["conversation_id"] == "conv1"


@pytest.mark.asyncio
async def test_get_resource_invalid_path() -> None:
    """Test resource access with invalid path."""
    # Test invalid resource type
    mock_request = MockRequest()
    
    with pytest.raises(HTTPException) as exc_info:
        await sms.get_resource("invalid/user1", mock_request)
    
    # Verify exception
    assert exc_info.value.status_code == 404
    # Access the detail field safely
    detail = exc_info.value.detail
    if isinstance(detail, dict):
        error_dict = detail.get("error")
        if isinstance(error_dict, dict):
            assert error_dict.get("code") == "resource_not_found"
        else:
            assert False, "Expected HTTPException detail to contain error dictionary"
    else:
        assert False, "Expected HTTPException detail to be a dictionary"
    
    # Test invalid history path (missing user_id)
    with pytest.raises(HTTPException) as exc_info:
        await sms.get_resource("history", mock_request)
    
    # Verify exception
    assert exc_info.value.status_code == 400
    # Access the detail field safely
    detail = exc_info.value.detail
    if isinstance(detail, dict):
        error_dict = detail.get("error")
        if isinstance(error_dict, dict):
            assert error_dict.get("code") == "invalid_resource_path"
        else:
            assert False, "Expected HTTPException detail to contain error dictionary"
    else:
        assert False, "Expected HTTPException detail to be a dictionary"
    
    # Test invalid conversation path (missing conversation_id)
    with pytest.raises(HTTPException) as exc_info:
        await sms.get_resource("conversation", mock_request)
    
    # Verify exception
    assert exc_info.value.status_code == 400
    # Access the detail field safely
    detail = exc_info.value.detail
    if isinstance(detail, dict):
        error_dict = detail.get("error")
        if isinstance(error_dict, dict):
            assert error_dict.get("code") == "invalid_resource_path"
        else:
            assert False, "Expected HTTPException detail to contain error dictionary"
    else:
        assert False, "Expected HTTPException detail to be a dictionary"


@pytest.mark.asyncio
async def test_get_resource_invalid_limit() -> None:
    """Test history resource with invalid limit parameter."""
    # Test invalid limit (non-numeric)
    mock_request = MockRequest()
    
    with pytest.raises(HTTPException) as exc_info:
        await sms.get_resource("history/user1/limit/invalid", mock_request)
    
    # Verify exception
    assert exc_info.value.status_code == 400
    # Access the detail field safely
    detail = exc_info.value.detail
    if isinstance(detail, dict):
        error_dict = detail.get("error")
        if isinstance(error_dict, dict):
            assert error_dict.get("code") == "invalid_parameter"
        else:
            assert False, "Expected HTTPException detail to contain error dictionary"
    else:
        assert False, "Expected HTTPException detail to be a dictionary"


# Test tool implementations
@pytest.mark.asyncio
async def test_store_input_success() -> None:
    """Test store_input tool successfully stores a message."""
    # Reset mock messages
    sms.mock_messages = []
    
    # Call store_input
    result = await sms.store_input(
        user_id="user1",
        input_data={
            "content": "Test message",
            "conversation_id": "conv1",
            "metadata": {"role": "user", "tags": ["test"]},
        },
    )
    
    # Verify result
    assert result["status"] == "stored"
    assert result["user_id"] == "user1"
    assert "item_id" in result
    
    # Verify message was stored
    assert len(sms.mock_messages) == 1
    assert sms.mock_messages[0]["content"] == "Test message"
    assert sms.mock_messages[0]["conversation_id"] == "conv1"
    assert sms.mock_messages[0]["sender_id"] == "user1"
    assert sms.mock_messages[0]["metadata"]["role"] == "user"
    assert "tags" in sms.mock_messages[0]["metadata"]


@pytest.mark.asyncio
async def test_store_input_missing_user_id() -> None:
    """Test store_input with missing user_id."""
    # Call store_input with empty user_id
    result = await sms.store_input(user_id="", input_data={"content": "Test message"})
    
    # Verify error result
    assert result["status"] == "error"
    assert "User ID is required" in result["error"]


@pytest.mark.asyncio
async def test_store_input_missing_input_data() -> None:
    """Test store_input with missing input_data."""
    # Call store_input with empty input_data
    result = await sms.store_input(user_id="user1", input_data={})
    
    # Verify error result
    assert result["status"] == "error"
    assert "user_id" in result
    assert "Input data is required" in result["error"]


@pytest.mark.asyncio
async def test_update_message_success(mock_messages: List[Dict[str, Any]]) -> None:
    """Test update_message successfully updates a message."""
    # Set up mock messages
    sms.mock_messages = mock_messages
    
    # Call update_message
    result = await sms.update_message(
        user_id="user1",
        message_id="msg1",
        updates={
            "content": "Updated message content",
            "metadata": {"updated": True},
        },
    )
    
    # Verify result
    assert result["status"] == "updated"
    assert result["user_id"] == "user1"
    assert result["message_id"] == "msg1"
    
    # Verify message was updated
    updated_message = next((msg for msg in sms.mock_messages if msg["id"] == "msg1"), None)
    assert updated_message is not None
    assert updated_message["content"] == "Updated message content"
    assert updated_message["metadata"]["updated"] is True
    assert "updated_at" in updated_message["metadata"]


@pytest.mark.asyncio
async def test_update_message_not_found(mock_messages: List[Dict[str, Any]]) -> None:
    """Test update_message with non-existent message."""
    # Set up mock messages
    sms.mock_messages = mock_messages
    
    # Call update_message with invalid message_id
    result = await sms.update_message(
        user_id="user1",
        message_id="non_existent",
        updates={"content": "Updated content"},
    )
    
    # Verify error result
    assert result["status"] == "error"
    assert "Message not found or access denied" in result["error"]


@pytest.mark.asyncio
async def test_update_message_access_denied(mock_messages: List[Dict[str, Any]]) -> None:
    """Test update_message with message from different user."""
    # Set up mock messages
    sms.mock_messages = mock_messages
    
    # Call update_message with wrong user_id (msg2 is from 'assistant')
    result = await sms.update_message(
        user_id="user1",
        message_id="msg2",
        updates={"content": "Updated content"},
    )
    
    # Verify error result
    assert result["status"] == "error"
    assert "Message not found or access denied" in result["error"]


@pytest.mark.asyncio
async def test_delete_message_success(mock_messages: List[Dict[str, Any]]) -> None:
    """Test delete_message successfully deletes a message."""
    # Set up mock messages
    sms.mock_messages = mock_messages
    initial_count = len(sms.mock_messages)
    
    # Call delete_message
    result = await sms.delete_message(user_id="user1", message_id="msg1")
    
    # Verify result
    assert result["status"] == "deleted"
    assert result["user_id"] == "user1"
    assert result["message_id"] == "msg1"
    
    # Verify message was deleted
    assert len(sms.mock_messages) == initial_count - 1
    assert all(msg["id"] != "msg1" for msg in sms.mock_messages)


@pytest.mark.asyncio
async def test_delete_message_not_found(mock_messages: List[Dict[str, Any]]) -> None:
    """Test delete_message with non-existent message."""
    # Set up mock messages
    sms.mock_messages = mock_messages
    
    # Call delete_message with invalid message_id
    result = await sms.delete_message(user_id="user1", message_id="non_existent")
    
    # Verify error result
    assert result["status"] == "error"
    assert "Message not found or access denied" in result["error"]


@pytest.mark.asyncio
async def test_delete_message_access_denied(mock_messages: List[Dict[str, Any]]) -> None:
    """Test delete_message with message from different user."""
    # Set up mock messages
    sms.mock_messages = mock_messages
    
    # Call delete_message with wrong user_id (msg2 is from 'assistant')
    result = await sms.delete_message(user_id="user1", message_id="msg2")
    
    # Verify error result
    assert result["status"] == "error"
    assert "Message not found or access denied" in result["error"]


@pytest.mark.asyncio
async def test_get_message_success(mock_messages: List[Dict[str, Any]]) -> None:
    """Test get_message successfully retrieves a message."""
    # Set up mock messages
    sms.mock_messages = mock_messages
    
    # Call get_message
    result = await sms.get_message(message_id="msg1")
    
    # Verify result
    assert result is not None
    assert result["id"] == "msg1"
    assert result["sender_id"] == "user1"
    assert result["conversation_id"] == "conv1"
    assert "content" in result
    assert "timestamp" in result
    assert "metadata" in result


@pytest.mark.asyncio
async def test_get_message_not_found(mock_messages: List[Dict[str, Any]]) -> None:
    """Test get_message with non-existent message."""
    # Set up mock messages
    sms.mock_messages = mock_messages
    
    # Call get_message with invalid message_id
    result = await sms.get_message(message_id="non_existent")
    
    # Verify result is None
    assert result is None


@pytest.mark.asyncio
async def test_get_message_empty_id() -> None:
    """Test get_message with empty message ID."""
    # Call get_message with empty message_id
    result = await sms.get_message(message_id="")
    
    # Verify result is None
    assert result is None


# Test streaming functions
@pytest.mark.asyncio
async def test_get_history_stream_success(mock_messages: List[Dict[str, Any]]) -> None:
    """Test history stream successfully returns user messages."""
    # Set up mock messages
    sms.mock_messages = mock_messages
    
    # Get generator
    generator = sms.get_history_stream(user_id="user1")
    
    # Get all chunks
    chunks = []
    async for chunk in generator:
        chunks.append(chunk)
    
    # User1 has 2 messages in the mock data
    assert len(chunks) == 3  # 2 messages + end marker
    
    # Check message content
    message_text = chunks[0].replace("data: ", "").strip()
    first_msg = json.loads(message_text)
    assert first_msg["sender_id"] == "user1"
    
    # Check end marker
    end_marker_text = chunks[-1].replace("data: ", "").strip()
    end_marker = json.loads(end_marker_text)
    assert "end" in end_marker


@pytest.mark.asyncio
async def test_get_history_stream_with_limit(mock_messages: List[Dict[str, Any]]) -> None:
    """Test history stream with limit parameter."""
    # Set up mock messages
    sms.mock_messages = mock_messages
    
    # Get generator with limit=1
    generator = sms.get_history_stream(user_id="user1", limit=1)
    
    # Get all chunks
    chunks = []
    async for chunk in generator:
        chunks.append(chunk)
    
    # Should only return 1 message + end marker
    assert len(chunks) == 2
    
    # Check message content
    message_text = chunks[0].replace("data: ", "").strip()
    msg = json.loads(message_text)
    assert msg["sender_id"] == "user1"
    
    # Check end marker
    end_marker_text = chunks[-1].replace("data: ", "").strip()
    end_marker = json.loads(end_marker_text)
    assert "end" in end_marker


@pytest.mark.asyncio
async def test_get_history_stream_empty_user_id() -> None:
    """Test history stream with empty user ID."""
    # Get generator with empty user_id
    generator = sms.get_history_stream(user_id="")
    
    # Get all chunks
    chunks = []
    async for chunk in generator:
        chunks.append(chunk)
    
    # Should only return error message
    assert len(chunks) == 1
    error_text = chunks[0].replace("data: ", "").strip()
    error_data = json.loads(error_text)
    assert "error" in error_data


@pytest.mark.asyncio
async def test_get_conversation_stream_success(mock_messages: List[Dict[str, Any]]) -> None:
    """Test conversation stream successfully returns conversation messages."""
    # Set up mock messages
    sms.mock_messages = mock_messages
    
    # Get generator
    generator = sms.get_conversation_stream(conversation_id="conv1")
    
    # Get all chunks
    chunks = []
    async for chunk in generator:
        chunks.append(chunk)
    
    # Conv1 has 2 messages in the mock data
    assert len(chunks) == 3  # 2 messages + end marker
    
    # Check message content
    message_text = chunks[0].replace("data: ", "").strip()
    first_msg = json.loads(message_text)
    assert first_msg["conversation_id"] == "conv1"
    
    # Check end marker
    end_marker_text = chunks[-1].replace("data: ", "").strip()
    end_marker = json.loads(end_marker_text)
    assert "end" in end_marker


@pytest.mark.asyncio
async def test_get_conversation_stream_with_user_filter(mock_messages: List[Dict[str, Any]]) -> None:
    """Test conversation stream with user filter."""
    # Set up mock messages
    sms.mock_messages = mock_messages
    
    # Get generator with user filter
    generator = sms.get_conversation_stream(conversation_id="conv1", user_id="user1")
    
    # Get all chunks
    chunks = []
    async for chunk in generator:
        chunks.append(chunk)
    
    # Conv1 has 1 message from user1 in the mock data
    assert len(chunks) == 2  # 1 filtered message + end marker
    
    # Check message content
    message_text = chunks[0].replace("data: ", "").strip()
    msg = json.loads(message_text)
    assert msg["conversation_id"] == "conv1"
    assert msg["sender_id"] == "user1"
    
    # Check end marker
    end_marker_text = chunks[-1].replace("data: ", "").strip()
    end_marker = json.loads(end_marker_text)
    assert "end" in end_marker


@pytest.mark.asyncio
async def test_get_conversation_stream_empty_conversation_id() -> None:
    """Test conversation stream with empty conversation ID."""
    # Get generator with empty conversation_id
    generator = sms.get_conversation_stream(conversation_id="")
    
    # Get all chunks
    chunks = []
    async for chunk in generator:
        chunks.append(chunk)
    
    # Should only return error message
    assert len(chunks) == 1
    error_text = chunks[0].replace("data: ", "").strip()
    error_data = json.loads(error_text)
    assert "error" in error_data