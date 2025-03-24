"""
Tests for the main FastAPI application.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import app
from app.utils.exceptions import CortexException


class TestMainApp:
    """Tests for the main FastAPI application."""
    
    @pytest.fixture
    def test_client(self):
        """Fixture to provide a test client for the FastAPI app."""
        with TestClient(app) as client:
            yield client
    
    def test_root_endpoint(self, test_client):
        """Test the root endpoint."""
        response = test_client.get("/")
        
        assert response.status_code == 200
        assert response.json() == {"status": "online", "service": "Cortex Core"}
    
    def test_health_endpoint(self, test_client):
        """Test the health check endpoint."""
        # We'll use a simpler test just to verify the endpoint exists and returns 200
        with patch("app.main.app.state") as mock_app_state:
            # Create a separate version of the app for the test to avoid affecting other tests
            from app.main import app as test_app
            from fastapi.testclient import TestClient
            
            # Create a mock response handler for the app state
            mock_app_state.response_handler = None
            
            # Patch the actual health check function to avoid service checks
            with patch("app.backend.cognition_client.CognitionClient.connect") as mock_connect, \
                 patch("app.backend.memory_client.MemoryClient.connect") as mock_mem_connect:
                
                # Set up successful connections
                mock_connect.return_value = (True, None)
                mock_mem_connect.return_value = (True, None)
                
                # Also patch the client sessions
                with patch("app.backend.cognition_client.ClientSession") as mock_cognition_session, \
                     patch("app.backend.memory_client.ClientSession") as mock_memory_session:
                    
                    # Create mock session instances that respond correctly
                    mock_cognition = MagicMock()
                    mock_cognition.list_tools = AsyncMock()
                    mock_cognition.list_tools.return_value = MagicMock(tools=[MagicMock(name="tool1")])
                    
                    mock_memory = MagicMock()
                    mock_memory.initialize = AsyncMock()
                    
                    # Return the mock sessions when requested
                    mock_cognition_session.return_value = mock_cognition
                    mock_memory_session.return_value = mock_memory
                    
                    # Use a fresh client for this test
                    with TestClient(test_app) as client:
                        # Call the health endpoint
                        response = client.get("/health")
                        
                        # Check basic response structure - we only care that it returns 200
                        assert response.status_code == 200
                        data = response.json()
                        assert "status" in data
                        assert "system" in data 
                        assert "services" in data
    
    def test_cortex_exception_handler(self, test_client):
        """Test the custom exception handler for CortexException."""
        # Create a test endpoint that raises a CortexException
        @app.get("/test/cortex-exception")
        async def test_cortex_exception():
            raise CortexException(
                status_code=400,
                error_code="TEST_ERROR",
                message="Test error"
            )
        
        # Call the test endpoint
        response = test_client.get("/test/cortex-exception")
        
        # Check response
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["message"] == "Test error"
        assert data["error"]["code"] == "TEST_ERROR"
        assert "request_id" in data
    
    def test_cortex_exception_handler_string_detail(self, test_client):
        """Test the custom exception handler with string detail."""
        # Create a test endpoint that raises a CortexException with string detail
        @app.get("/test/cortex-exception-string")
        async def test_cortex_exception_string():
            raise CortexException(
                status_code=400,
                error_code="test_error",
                message="Simple error message"
            )
        
        # Call the test endpoint
        response = test_client.get("/test/cortex-exception-string")
        
        # Check response
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["message"] == "Simple error message"
        assert data["error"]["code"] == "test_error"
        assert "request_id" in data
    
    def test_validation_exception_handler(self, test_client):
        """Test the validation exception handler."""
        # Create a test endpoint with validation
        from pydantic import BaseModel
        
        class TestModel(BaseModel):
            name: str
            age: int
        
        @app.post("/test/validation")
        async def test_validation(model: TestModel) -> TestModel:
            return model
        
        # Call the test endpoint with invalid data
        response = test_client.post(
            "/test/validation",
            json={"name": "Test"}  # Missing required field 'age'
        )
        
        # Check response
        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "validation_error"
        assert data["error"]["message"] == "Validation error"
        assert "validation_errors" in data["error"]["details"]
        assert len(data["error"]["details"]["validation_errors"]) > 0
        assert "request_id" in data
    
    @pytest.mark.asyncio
    async def test_lifespan(self):
        """Test the lifespan context manager."""
        # Mock the response handler
        with patch("app.main.create_response_handler") as mock_create_handler, \
             patch("app.main.validate_config", return_value=None) as mock_validate_config:
            
            # Create a mock response handler
            mock_handler = MagicMock()
            mock_handler.stop = AsyncMock()
            mock_create_handler.return_value = mock_handler
            
            # Create a test FastAPI app
            test_app = FastAPI()
            
            # Add our lifespan context manager
            from app.main import lifespan
            test_app.router.lifespan_context = lifespan
            
            # Execute the lifespan context
            async with test_app.router.lifespan_context(test_app):
                # Check that the handler was created and stored
                mock_validate_config.assert_called_once()
                mock_create_handler.assert_called_once()
                assert test_app.state.response_handler == mock_handler
            
            # Check that the handler was cleaned up
            mock_handler.stop.assert_called_once()
            assert test_app.state.response_handler is None
    
    @pytest.mark.asyncio
    async def test_lifespan_with_config_error(self):
        """Test the lifespan context manager with a configuration error."""
        # Mock the response handler and config validation
        with patch("app.main.create_response_handler") as mock_create_handler, \
             patch("app.main.validate_config", return_value="Test config error") as mock_validate_config:
            
            # Create a mock response handler
            mock_handler = MagicMock()
            mock_handler.stop = AsyncMock()
            mock_create_handler.return_value = mock_handler
            
            # Create a test FastAPI app
            test_app = FastAPI()
            
            # Add our lifespan context manager
            from app.main import lifespan
            test_app.router.lifespan_context = lifespan
            
            # Execute the lifespan context
            async with test_app.router.lifespan_context(test_app):
                # Check that validation was called but app still starts
                mock_validate_config.assert_called_once()
                mock_create_handler.assert_called_once()
                assert test_app.state.response_handler == mock_handler
            
            # Check that the handler was cleaned up
            mock_handler.stop.assert_called_once()
    
    def test_router_inclusion(self):
        """Test that all routers are included in the app."""
        # Get all router paths
        routes = [str(getattr(route, "path", "")) for route in app.routes]
        
        # Check all API prefixes are included
        prefixes = [
            "/auth",     # auth router
            "/input",    # input router
            "/output",   # output router
            "/config",   # config router
            "/health",   # health router
            "/manage",   # management router
        ]
        
        # There should be at least one route for each prefix
        for prefix in prefixes:
            matching_routes = [route for route in routes if route.startswith(prefix)]
            assert len(matching_routes) > 0, f"No routes found for prefix: {prefix}"