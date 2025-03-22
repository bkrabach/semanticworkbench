from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health_check():
    """Test that the health check endpoint returns the expected response."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()

    # Check the structure of the response
    assert "status" in data
    assert "timestamp" in data
    assert "version" in data
    assert "services" in data

    # Check the services are included
    assert "cognition" in data["services"]
    assert "memory" in data["services"]

    # Check the services have status
    assert "status" in data["services"]["cognition"]
    assert "status" in data["services"]["memory"]


def test_health_ping():
    """Test that the ping endpoint returns a simple response."""
    response = client.get("/health/ping")
    assert response.status_code == 200
    assert "ping" in response.json()
    assert response.json()["ping"] == "pong"
    assert "timestamp" in response.json()
