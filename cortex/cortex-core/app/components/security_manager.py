"""
Security Manager component for Cortex Core
Handles authentication, authorization, and encryption
"""

import json
import hashlib
from typing import Optional, Any
from cryptography.fernet import Fernet
import base64
from fastapi import Depends
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.database.models import User
from app.components.tokens import verify_jwt_token
from app.components.auth_schemes import oauth2_scheme_optional

from app.config import settings
from app.utils.logger import logger


def get_password_hash(password: str) -> str:
    """
    Hash a password

    Args:
        password: Plain text password

    Returns:
        Password hash
    """
    # In production, use a more secure hashing algorithm like bcrypt
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password

    Returns:
        True if password matches, False otherwise
    """
    return get_password_hash(plain_password) == hashed_password


async def get_current_user_or_none(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user from token but don't raise exception if token is invalid

    Args:
        token: JWT token (optional)
        db: Database session

    Returns:
        User object if token is valid, None otherwise
    """
    if not token:
        return None

    try:
        token_data = verify_jwt_token(token)
        if not token_data:
            return None

        user = db.query(User).filter(User.id == token_data.user_id).first()
        return user
    except Exception:
        return None


class SecurityManager:
    """Security Manager implementation"""

    def __init__(self):
        # Derive encryption key from the provided key
        key_bytes = hashlib.sha256(
            settings.security.encryption_key.encode()).digest()
        self.fernet = Fernet(base64.urlsafe_b64encode(key_bytes))

    def encrypt(self, data: str) -> str:
        """
        Encrypt sensitive data

        Args:
            data: The data to encrypt

        Returns:
            The encrypted data
        """
        try:
            # Encrypt the data
            encoded = data.encode()
            encrypted = self.fernet.encrypt(encoded)
            # Convert bytes to string and return
            result = encrypted.decode('utf-8')
            return result  # type: ignore
        except Exception as e:
            logger.error(f"Encryption failed: {str(e)}")
            raise

    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt sensitive data

        Args:
            encrypted_data: The data to decrypt

        Returns:
            The decrypted data
        """
        try:
            # Decode the encrypted data
            encoded = encrypted_data.encode()
            decrypted = self.fernet.decrypt(encoded)
            # Convert bytes to string and return
            result = decrypted.decode('utf-8')
            return result  # type: ignore
        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            raise

    def stringify_json(self, data: Any) -> str:
        """
        Convert object to JSON string

        Args:
            data: The data to convert

        Returns:
            JSON string
        """
        try:
            result = json.dumps(data)
            return str(result) if result is not None else "{}"
        except Exception as e:
            logger.error(f"JSON stringify failed: {str(e)}")
            return "{}"

    def parse_json(self, json_str: str) -> Any:
        """
        Parse JSON string to object

        Args:
            json_str: The JSON string to parse

        Returns:
            Parsed object
        """
        try:
            return json.loads(json_str)
        except Exception as e:
            logger.error(f"JSON parse failed: {str(e)}")
            return {}

    async def check_access(self, user_id: str, resource: str, action: str) -> bool:
        """
        Check if a user has access to a resource

        Args:
            user_id: The user ID
            resource: The resource being accessed
            action: The action being performed

        Returns:
            True if access is allowed
        """
        # TODO: Implement proper access control
        # This is a simplified version for the MVP

        # Check workspace-specific access
        if resource.startswith("workspace:"):
            return await self._check_workspace_access(
                user_id, resource.split(":")[1], action
            )

        # Default permissions for basic user actions
        default_allowed_actions = [
            "read_own_profile",
            "update_own_profile",
            "create_workspace",
            "list_own_workspaces",
        ]

        return action in default_allowed_actions

    async def _check_workspace_access(
        self, user_id: str, workspace_id: str, action: str
    ) -> bool:
        """
        Check access to a specific workspace

        Args:
            user_id: The user ID
            workspace_id: The workspace ID
            action: The action being performed

        Returns:
            True if access is allowed
        """
        # TODO: Implement proper workspace access control
        # For MVP, assume user has access to their own workspaces
        return True
