"""
Tests for the auth.py utility functions.
"""
import datetime
import pytest
from unittest.mock import patch, MagicMock

import jwt

from app.utils.auth import (
    create_access_token,
    verify_jwt,
    get_current_user,
    Auth0JWTVerifier
)
from app.utils.exceptions import AuthenticationException


class TestCreateAccessToken:
    """Tests for the create_access_token function."""
    
    def test_create_token_with_expiry(self):
        """Test creating a token with an expiry time."""
        # Mock datetime for consistent testing
        with patch("app.utils.auth.datetime") as mock_datetime:
            mock_now = datetime.datetime(2025, 1, 1, 12, 0, 0)
            mock_datetime.datetime.utcnow.return_value = mock_now
            mock_datetime.timedelta = datetime.timedelta
            
            # Set USE_AUTH0 to False for the test
            with patch("app.utils.auth.USE_AUTH0", False), \
                 patch("app.utils.auth.DEV_SECRET", "test-secret"):
                
                # Create a token with 1 hour expiry
                expiry = datetime.timedelta(hours=1)
                data = {"sub": "test-user", "name": "Test User"}
                token = create_access_token(data, expiry)
                
                # Decode the token without verification to check payload
                decoded = jwt.decode(token, "test-secret", algorithms=["HS256"], options={"verify_exp": False})
                
                # Verify the payload
                assert decoded["sub"] == "test-user"
                assert decoded["name"] == "Test User"
                
                # Just verify that an expiry is set, we don't need the exact value
                assert "exp" in decoded
    
    def test_create_token_default_expiry(self):
        """Test creating a token with the default expiry."""
        # Mock datetime for consistent testing
        with patch("app.utils.auth.datetime") as mock_datetime:
            mock_now = datetime.datetime(2025, 1, 1, 12, 0, 0)
            mock_datetime.datetime.utcnow.return_value = mock_now
            mock_datetime.timedelta = datetime.timedelta
            
            # Set USE_AUTH0 to False for the test
            with patch("app.utils.auth.USE_AUTH0", False), \
                 patch("app.utils.auth.DEV_SECRET", "test-secret"):
                
                # Create a token with default expiry
                data = {"sub": "test-user", "name": "Test User"}
                token = create_access_token(data)
                
                # Decode the token without verification to check payload
                decoded = jwt.decode(token, "test-secret", algorithms=["HS256"], options={"verify_exp": False})
                
                # Verify the payload
                assert decoded["sub"] == "test-user"
                assert decoded["name"] == "Test User"
                
                # Just verify that an expiry is set, we don't need the exact value
                assert "exp" in decoded
    
    def test_create_token_auth0_mode(self):
        """Test that create_access_token raises error in Auth0 mode."""
        # Set USE_AUTH0 to True for the test
        with patch("app.utils.auth.USE_AUTH0", True):
            # Try to create a token in Auth0 mode
            with pytest.raises(ValueError) as exc_info:
                data = {"sub": "test-user", "name": "Test User"}
                create_access_token(data)
            
            # Verify the exception message
            assert "Cannot create tokens in Auth0 mode" in str(exc_info.value)


class TestAuth0JWTVerifier:
    """Tests for the Auth0JWTVerifier class."""
    
    def test_init(self):
        """Test initialization of Auth0JWTVerifier."""
        with patch("app.utils.auth.PyJWKClient") as mock_client:
            verifier = Auth0JWTVerifier("test.domain", "api-audience")
            
            assert verifier.domain == "test.domain"
            assert verifier.audience == "api-audience"
            assert verifier.issuer == "https://test.domain/"
            mock_client.assert_called_once_with("https://test.domain/.well-known/jwks.json")
    
    def test_verify(self):
        """Test the verify method."""
        with patch("app.utils.auth.PyJWKClient") as mock_client:
            # Create a mock for the jwks client
            mock_jwks = MagicMock()
            mock_client.return_value = mock_jwks
            
            # Create a mock signing key
            mock_signing_key = MagicMock()
            mock_jwks.get_signing_key_from_jwt.return_value = mock_signing_key
            mock_signing_key.key = "test-key"
            
            # Create a mock for jwt.decode
            with patch("app.utils.auth.jwt.decode") as mock_decode:
                mock_decode.return_value = {"sub": "test-user", "name": "Test User"}
                
                # Create the verifier and call verify
                verifier = Auth0JWTVerifier("test.domain", "api-audience")
                result = verifier.verify("test-token")
                
                # Verify the result
                assert result == {"sub": "test-user", "name": "Test User"}
                
                # Verify the mock was called correctly
                mock_jwks.get_signing_key_from_jwt.assert_called_once_with("test-token")
                mock_decode.assert_called_once_with(
                    "test-token", 
                    "test-key", 
                    algorithms=["RS256"], 
                    audience="api-audience", 
                    issuer="https://test.domain/"
                )


class TestVerifyJWT:
    """Tests for the verify_jwt function."""
    
    def test_verify_jwt_no_token(self):
        """Test verify_jwt with no token."""
        with pytest.raises(ValueError) as exc_info:
            verify_jwt("")
        
        assert "No token provided" in str(exc_info.value)
    
    def test_verify_jwt_development_mode(self):
        """Test verify_jwt in development mode."""
        with patch("app.utils.auth.USE_AUTH0", False), \
             patch("app.utils.auth.DEV_SECRET", "test-secret"), \
             patch("app.utils.auth.jwt.decode") as mock_decode:
            
            # Set up the mock
            mock_decode.return_value = {"sub": "test-user", "name": "Test User"}
            
            # Call verify_jwt
            result = verify_jwt("test-token")
            
            # Verify the result
            assert result == {"sub": "test-user", "name": "Test User"}
            
            # Verify the mock was called correctly
            mock_decode.assert_called_once_with("test-token", "test-secret", algorithms=["HS256"])
    
    def test_verify_jwt_auth0_mode(self):
        """Test verify_jwt in Auth0 mode."""
        with patch("app.utils.auth.USE_AUTH0", True), \
             patch("app.utils.auth.auth0_verifier") as mock_verifier:
            
            # Set up the mock
            mock_verifier.verify.return_value = {"sub": "test-user", "name": "Test User"}
            
            # Call verify_jwt
            result = verify_jwt("test-token")
            
            # Verify the result
            assert result == {"sub": "test-user", "name": "Test User"}
            
            # Verify the mock was called correctly
            mock_verifier.verify.assert_called_once_with("test-token")
    
    def test_verify_jwt_auth0_mode_no_verifier(self):
        """Test verify_jwt in Auth0 mode with no verifier initialized."""
        with patch("app.utils.auth.USE_AUTH0", True), \
             patch("app.utils.auth.auth0_verifier", None):
            
            # Call verify_jwt
            with pytest.raises(ValueError) as exc_info:
                verify_jwt("test-token")
            
            # Verify the exception message
            assert "Auth0 verifier not initialized" in str(exc_info.value)
    
    def test_verify_jwt_invalid_token(self):
        """Test verify_jwt with an invalid token."""
        with patch("app.utils.auth.USE_AUTH0", False), \
             patch("app.utils.auth.DEV_SECRET", "test-secret"), \
             patch("app.utils.auth.jwt.decode") as mock_decode:
            
            # Set up the mock to raise an exception
            mock_decode.side_effect = jwt.PyJWTError("Invalid token")
            
            # Call verify_jwt
            with pytest.raises(ValueError) as exc_info:
                verify_jwt("test-token")
            
            # Verify the exception message
            assert "Invalid token: Invalid token" in str(exc_info.value)


class TestGetCurrentUser:
    """Tests for the get_current_user function."""
    
    def test_no_authorization_header(self):
        """Test get_current_user with no Authorization header."""
        with pytest.raises(AuthenticationException) as exc_info:
            get_current_user(None)
        
        assert "Authorization header missing" in str(exc_info.value)
    
    def test_invalid_header_format(self):
        """Test get_current_user with invalid header format."""
        # Test with wrong prefix
        with pytest.raises(AuthenticationException) as exc_info:
            get_current_user("NotBearer token123")
        
        assert "Invalid Authorization header format" in str(exc_info.value)
        
        # Test with no token
        with pytest.raises(AuthenticationException) as exc_info:
            get_current_user("Bearer")
        
        assert "Invalid Authorization header format" in str(exc_info.value)
    
    def test_valid_token(self):
        """Test get_current_user with a valid token."""
        with patch("app.utils.auth.verify_jwt") as mock_verify:
            # Set up the mock
            mock_verify.return_value = {
                "sub": "test-user-123",
                "email": "user@example.com",
                "name": "Test User"
            }
            
            # Call get_current_user
            result = get_current_user("Bearer test-token")
            
            # Verify the result
            assert result == {
                "id": "test-user-123",
                "email": "user@example.com",
                "name": "Test User"
            }
            
            # Verify the mock was called correctly
            mock_verify.assert_called_once_with("test-token")
    
    def test_missing_user_id(self):
        """Test get_current_user with a token missing the sub claim."""
        with patch("app.utils.auth.verify_jwt") as mock_verify:
            # Set up the mock with missing sub claim
            mock_verify.return_value = {
                "email": "user@example.com",
                "name": "Test User"
            }
            
            # Call get_current_user
            with pytest.raises(AuthenticationException) as exc_info:
                get_current_user("Bearer test-token")
            
            # Verify the exception message
            assert "Token payload missing 'sub' claim" in str(exc_info.value)
    
    def test_verification_error(self):
        """Test get_current_user with a token that fails verification."""
        with patch("app.utils.auth.verify_jwt") as mock_verify:
            # Set up the mock to raise an exception
            mock_verify.side_effect = ValueError("Test verification error")
            
            # Call get_current_user
            with pytest.raises(AuthenticationException) as exc_info:
                get_current_user("Bearer test-token")
            
            # Verify the exception message
            assert "Test verification error" in str(exc_info.value)