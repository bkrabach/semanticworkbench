"""
Test suite for token generation and validation
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone
from jose import jwt

from app.components.tokens import TokenData, generate_jwt_token, verify_jwt_token


@pytest.fixture
def token_data():
    """Create sample token data"""
    return TokenData(
        user_id="test-user-id",
        scopes=["read", "write"]
    )


@pytest.fixture
def test_settings():
    """Mock app settings"""
    mock_settings = MagicMock()
    mock_settings.security.jwt_secret = "test-secret-key"
    mock_settings.security.token_expiry_seconds = 3600  # 1 hour
    return mock_settings


def test_generate_jwt_token(token_data, test_settings):
    """Test generation of JWT tokens"""
    # Patch settings
    with patch("app.components.tokens.settings", test_settings):
        # Generate token with default expiry
        token = generate_jwt_token(token_data)
        
        # Decode the token to verify its contents
        payload = jwt.decode(token, test_settings.security.jwt_secret, algorithms=["HS256"])
        
        # Verify the payload contains the expected data
        assert payload["user_id"] == token_data.user_id
        assert payload["scopes"] == token_data.scopes
        assert "exp" in payload
        
        # Verify expiration is set to approximately 1 hour in the future
        now = datetime.now(timezone.utc).timestamp()
        assert abs(payload["exp"] - (now + 3600)) < 5  # Within 5 seconds
        
        # Generate token with custom expiry
        custom_expire = timedelta(minutes=30)
        token = generate_jwt_token(token_data, expires_delta=custom_expire)
        
        # Decode and verify expiration
        payload = jwt.decode(token, test_settings.security.jwt_secret, algorithms=["HS256"])
        assert abs(payload["exp"] - (now + 1800)) < 5  # Within 5 seconds


def test_verify_jwt_token_valid(token_data, test_settings):
    """Test verification of valid JWT tokens"""
    # Patch settings
    with patch("app.components.tokens.settings", test_settings):
        # Generate a valid token
        token = generate_jwt_token(token_data)
        
        # Verify the token
        result = verify_jwt_token(token)
        
        # Check the result
        assert result is not None
        assert result.user_id == token_data.user_id
        assert result.scopes == token_data.scopes


def test_verify_jwt_token_invalid_signature(token_data, test_settings):
    """Test verification of tokens with invalid signatures"""
    # Patch settings
    with patch("app.components.tokens.settings", test_settings):
        # Generate a valid token
        token = generate_jwt_token(token_data)
        
        # Tamper with the token (replace the signature)
        parts = token.split(".")
        tampered_token = f"{parts[0]}.{parts[1]}.invalid-signature"
        
        # Verify the token
        result = verify_jwt_token(tampered_token)
        
        # Check the result (should be None for invalid token)
        assert result is None


def test_verify_jwt_token_expired(token_data, test_settings):
    """Test verification of expired tokens"""
    # Patch settings
    with patch("app.components.tokens.settings", test_settings):
        # Create token data with expiration in the past
        to_encode = token_data.model_dump()
        expire = datetime.now(timezone.utc) - timedelta(hours=1)  # 1 hour in the past
        to_encode.update({"exp": expire})
        
        # Create the token
        expired_token = jwt.encode(to_encode, test_settings.security.jwt_secret, algorithm="HS256")
        
        # Verify the token
        result = verify_jwt_token(expired_token)
        
        # Check the result (should be None for expired token)
        assert result is None


def test_verify_jwt_token_missing_user_id(test_settings):
    """Test verification of tokens with missing user_id"""
    # Patch settings
    with patch("app.components.tokens.settings", test_settings):
        # Create token data without user_id
        to_encode = {
            "scopes": ["read", "write"],
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        
        # Create the token
        invalid_token = jwt.encode(to_encode, test_settings.security.jwt_secret, algorithm="HS256")
        
        # Verify the token
        result = verify_jwt_token(invalid_token)
        
        # Check the result (should be None for token without user_id)
        assert result is None


def test_token_expiration_behavior(token_data, test_settings):
    """Test token expiration behavior"""
    # This test is more reliable without actual sleeping
    # Create an expired token directly
    with patch("app.components.tokens.settings", test_settings):
        # Create token data with expiration in the past
        to_encode = token_data.model_dump()
        expire = datetime.now(timezone.utc) - timedelta(seconds=1)  # Expired 1 second ago
        to_encode.update({"exp": expire})
        
        # Create the token
        expired_token = jwt.encode(to_encode, test_settings.security.jwt_secret, algorithm="HS256")
        
        # Verify the token is recognized as expired
        result = verify_jwt_token(expired_token)
        assert result is None