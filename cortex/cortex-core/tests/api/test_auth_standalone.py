"""
Test suite for the authentication API endpoints
"""

import pytest
from unittest.mock import patch, MagicMock

from app.services.user_service import UserService
from app.models.domain.user import User
from app.api.auth import get_current_user

@pytest.mark.asyncio
async def test_get_current_user_with_valid_token():
    """Test getting current user with valid token"""
    # Mock dependencies
    token = "test-token"
    from datetime import datetime, timezone
    
    mock_user = User(
        id="test-id",
        email="test@example.com",
        name="Test User",
        roles=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        metadata={},
        password_hash="test-hash"
    )
    
    mock_user_service = MagicMock(spec=UserService)
    mock_user_service.get_user.return_value = mock_user
    
    # Patch token verification
    with patch("app.api.auth.verify_jwt_token", return_value=MagicMock(user_id="test-id")):
        # Call the function
        user = await get_current_user(token=token, user_service=mock_user_service)
        
        # Verify the result
        assert user == mock_user
        mock_user_service.get_user.assert_called_once_with("test-id")