"""
Tests for web client integration with the Cortex Core API
"""

import json
from app.models.api.response.user import LoginResponse, UserInfoResponse

def test_login_response_format_matches_web_client_expectations():
    """
    Test that the LoginResponse model matches what the web client expects
    
    This tests the contract between the API and web client without requiring
    actual HTTP requests or database connections.
    """
    # Create a sample login response
    user_info = UserInfoResponse(
        id="test-id", 
        email="test@example.com",
        name="Test User",
        roles=["user"]
    )
    
    login_response = LoginResponse(
        access_token="sample-token",
        token_type="bearer",
        user=user_info
    )
    
    # Convert to JSON (this is what the client would receive)
    response_json = json.loads(login_response.model_dump_json())
    
    # Check that the fields match what the web client expects
    assert "access_token" in response_json  # Not "token"
    assert "user" in response_json
    assert isinstance(response_json["user"], dict)
    assert "id" in response_json["user"]  # Not "user_id"
    assert "email" in response_json["user"]