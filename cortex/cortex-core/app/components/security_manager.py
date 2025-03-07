"""
Security Manager component for Cortex Core
Handles authentication, authorization, and encryption
"""

import json
import jwt
from typing import Optional, Dict, List, Any, Union
from datetime import datetime, timedelta
import secrets
import hashlib
from pydantic import BaseModel
from cryptography.fernet import Fernet
import base64

from app.config import settings
from app.utils.logger import logger


class TokenData(BaseModel):
    """JWT token data"""

    user_id: str
    scopes: List[str] = []


def generate_jwt_token(
    data: TokenData, expires_delta: Optional[timedelta] = None
) -> str:
    """
    Generate a JWT token

    Args:
        data: Token data
        expires_delta: Token expiry time

    Returns:
        JWT token
    """
    to_encode = data.model_dump()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            seconds=settings.security.token_expiry_seconds
        )

    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, settings.security.jwt_secret, algorithm="HS256")


def verify_jwt_token(token: str) -> Optional[TokenData]:
    """
    Verify a JWT token

    Args:
        token: JWT token

    Returns:
        Token data if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, settings.security.jwt_secret, algorithms=["HS256"])

        user_id = payload.get("user_id")
        if user_id is None:
            return None

        scopes = payload.get("scopes", [])

        return TokenData(user_id=user_id, scopes=scopes)

    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.InvalidTokenError:
        logger.warning("Invalid token")
        return None


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


class SecurityManager:
    """Security Manager implementation"""

    def __init__(self):
        # Derive encryption key from the provided key
        key_bytes = hashlib.sha256(settings.security.encryption_key.encode()).digest()
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
            return self.fernet.encrypt(data.encode()).decode()
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
            return self.fernet.decrypt(encrypted_data.encode()).decode()
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
            return json.dumps(data)
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
