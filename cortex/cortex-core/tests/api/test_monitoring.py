"""
Test suite for the monitoring API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app
from app.components.event_system import EventSystem


@pytest.fixture
def test_client():
    """Create a FastAPI test client"""
    return TestClient(app)


class AsyncMockWithStats(AsyncMock):
    """Mock event system with predefined stats"""
    
    async def get_stats(self):
        """Return predefined stats"""
        return {
            "events_published": 100,
            "events_delivered": 95,
            "subscriber_count": 5,
            "event_types": {
                "test.event": 50,
                "other.event": 30,
                "system.event": 20
            },
            "errors": 2,
            "uptime_seconds": 3600,
            "events_per_second": 0.028
        }


def test_get_event_stats(test_client):
    """Test the event stats endpoint"""
    # Create a mock with preconfigured stats response
    mock_system = AsyncMockWithStats(spec=EventSystem)
    
    # Patch the event system function
    with patch("app.api.monitoring.get_event_system", return_value=mock_system):
        # Make the request
        response = test_client.get("/monitoring/events/stats")
        
        # Verify the response
        assert response.status_code == 200
        data = response.json()
        
        # Check that we have the expected keys in the response
        assert "events_published" in data
        assert "events_delivered" in data
        assert "subscriber_count" in data
        assert "event_types" in data
        assert "errors" in data
        assert "uptime_seconds" in data
        assert "events_per_second" in data