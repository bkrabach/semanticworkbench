"""
Test suite for the security manager component
"""

import pytest
from unittest.mock import patch, MagicMock
import json

from app.components.security_manager import (
    SecurityManager,
    get_password_hash,
    verify_password,
    get_current_user_or_none
)
from app.models.domain.user import User
from app.components.tokens import TokenData


def test_get_password_hash():
    """Test password hashing"""
    # Test with a sample password
    password = "test-password"
    hashed = get_password_hash(password)

    # Verify the hash is in the expected format (SHA-256 produces a 64-char hex string)
    assert len(hashed) == 64
    assert all(c in "0123456789abcdef" for c in hashed)

    # Verify that the same password always produces the same hash
    assert get_password_hash(password) == hashed

    # Verify that different passwords produce different hashes
    assert get_password_hash("different-password") != hashed


def test_verify_password():
    """Test password verification"""
    # Test with a correct password
    password = "test-password"
    hashed = get_password_hash(password)

    assert verify_password(password, hashed) is True

    # Test with an incorrect password
    assert verify_password("wrong-password", hashed) is False


class TestSecurityManager:
    """Test suite for the SecurityManager class"""

    @pytest.fixture
    def security_manager(self):
        """Create a SecurityManager instance for testing"""
        # Patch settings to use a predictable key
        test_key = "test-encryption-key-must-be-32-bytes"
        with patch("app.config.settings.security.encryption_key", test_key):
            yield SecurityManager()

    def test_encryption(self, security_manager):
        """
        Test data encryption and decryption with various input types.
        This test verifies that the encryption and decryption functions work correctly for different kinds of data, including:
        - A simple string.
        - A string with special characters.
        - A JSON string representing a dictionary with nested values.
        - A Unicode string containing greetings in multiple languages.
            # Unicode: 你好 ("Hello" in Chinese), こんにちは ("Hello" in Japanese), مرحبا ("Hello" in Arabic)
        The function checks that:
        1. The encrypted output differs from the original input.
        2. Decrypting the encrypted data returns the original input accurately.
        """
        """Test data encryption and decryption"""
        # Test with various types of data
        test_data = [
            "simple string",
            "string with special chars: !@#$%^&*()",
            json.dumps({"key": "value", "nested": {"data": [1, 2, 3]}}),
            "Unicode: 你好, こんにちは, مرحبا"
        ]

        for data in test_data:
            # Encrypt the data
            encrypted = security_manager.encrypt(data)

            # Verify the encrypted data is different from the original
            assert encrypted != data

            # Verify we can decrypt back to the original
            decrypted = security_manager.decrypt(encrypted)
            assert decrypted == data

    def test_encryption_key_derivation(self):
        """Test that the encryption key is correctly derived from settings"""
        # Create two SecurityManager instances with the same key
        with patch("app.config.settings.security.encryption_key", "test-key-1"):
            manager1 = SecurityManager()

        with patch("app.config.settings.security.encryption_key", "test-key-1"):
            manager2 = SecurityManager()

        # Create a third with a different key
        with patch("app.config.settings.security.encryption_key", "test-key-2"):
            manager3 = SecurityManager()

        # Encrypt the same data with all managers
        test_data = "test data"
        encrypted1 = manager1.encrypt(test_data)

        # Verify that manager2 can decrypt data from manager1 (same key)
        assert manager2.decrypt(encrypted1) == test_data

        # Encrypt with manager3
        encrypted3 = manager3.encrypt(test_data)

        # Verify that manager3 produces different ciphertext
        assert encrypted3 != encrypted1

        # Verify that manager1 cannot decrypt data from manager3 (different key)
        with pytest.raises(Exception):
            manager1.decrypt(encrypted3)

    def test_json_handling(self, security_manager):
        """Test JSON serialization and deserialization"""
        # Test with various JSON structures
        test_objects = [
            {"key": "value"},
            {"nested": {"data": [1, 2, 3]}},
            [1, 2, 3, 4],
            {"bool": True, "null": None, "number": 42.5}
        ]

        for obj in test_objects:
            # Convert to JSON string
            json_str = security_manager.stringify_json(obj)

            # Verify it's a valid JSON string
            assert isinstance(json_str, str)

            # Parse it back
            parsed = security_manager.parse_json(json_str)

            # Verify we get the original object back
            assert parsed == obj

    def test_json_error_handling(self, security_manager):
        """Test handling of JSON errors"""
        # Test stringify with non-serializable object
        class NonSerializable:
            pass

        # This should return an empty JSON object without raising an exception
        result = security_manager.stringify_json(NonSerializable())
        assert result == "{}"

        # Test parse with invalid JSON
        result = security_manager.parse_json("invalid json")
        assert result == {}

    @pytest.mark.asyncio
    async def test_check_access(self, security_manager):
        """Test access control checks"""
        # Test default allowed actions for a normal user
        user_id = "test-user"

        # Should be allowed
        assert await security_manager.check_access(user_id, "profile", "read_own_profile") is True
        assert await security_manager.check_access(user_id, "profile", "update_own_profile") is True
        assert await security_manager.check_access(user_id, "workspace", "create_workspace") is True

        # Should not be allowed (not in default allowed actions)
        assert await security_manager.check_access(user_id, "profile", "delete_own_profile") is False

        # Test workspace-specific access
        workspace_id = "test-workspace"
        # All workspace actions are allowed in the MVP implementation
        assert await security_manager.check_access(user_id, f"workspace:{workspace_id}", "read") is True
        assert await security_manager.check_access(user_id, f"workspace:{workspace_id}", "write") is True
        assert await security_manager.check_access(user_id, f"workspace:{workspace_id}", "delete") is True


@pytest.mark.asyncio
async def test_get_current_user_or_none_valid_token():
    """Test getting user from valid token without raising exceptions"""
    # Mock dependencies
    mock_user_service = MagicMock()
    mock_user = MagicMock(spec=User)
    mock_user.id = "test-user-id"

    # Configure mock user service to return our test user
    mock_user_service.get_user.return_value = mock_user

    # Create a valid token
    token_data = TokenData(user_id=mock_user.id)

    # Patch verify_jwt_token to return our token data
    with patch("app.components.security_manager.verify_jwt_token", return_value=token_data):
        # Call the function
        user = await get_current_user_or_none(token="valid-token", user_service=mock_user_service)

        # Verify we got the expected user
        assert user is not None
        assert user is mock_user
        
        # Verify user service was called with correct user_id
        mock_user_service.get_user.assert_called_once_with(mock_user.id)

        # Access the id property safely and compare using string equality
        user_id = user.id
        expected_id = "test-user-id"
        assert str(user_id) == expected_id


@pytest.mark.asyncio
async def test_get_current_user_or_none_invalid_token():
    """Test behavior with invalid token"""
    # Mock dependencies
    mock_user_service = MagicMock()

    # Patch verify_jwt_token to return None (invalid token)
    with patch("app.components.security_manager.verify_jwt_token", return_value=None):
        # Call the function
        user = await get_current_user_or_none(token="invalid-token", user_service=mock_user_service)

        # Verify we got None
        assert user is None
        
        # Verify user service was not called
        mock_user_service.get_user.assert_not_called()


@pytest.mark.asyncio
async def test_get_current_user_or_none_exception():
    """Test handling of exceptions during token verification"""
    # Mock dependencies
    mock_user_service = MagicMock()

    # Patch verify_jwt_token to raise an exception
    with patch("app.components.security_manager.verify_jwt_token", side_effect=Exception("Test error")):
        # Call the function
        user = await get_current_user_or_none(token="error-token", user_service=mock_user_service)

        # Verify we got None
        assert user is None
        
        # Verify user service was not called
        mock_user_service.get_user.assert_not_called()


@pytest.mark.asyncio
async def test_get_current_user_or_none_no_token():
    """Test behavior when no token is provided"""
    # Mock dependencies
    mock_user_service = MagicMock()

    # Call the function without a token
    user = await get_current_user_or_none(token=None, user_service=mock_user_service)

    # Verify we got None
    assert user is None
    
    # Verify user service was not called
    mock_user_service.get_user.assert_not_called()