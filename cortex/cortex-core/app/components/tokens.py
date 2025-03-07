"""
Token management for Cortex Core
Handles JWT token generation, validation, and token data models
"""

from jose import jwt
from typing import Optional, List
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel

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
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
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
        payload = jwt.decode(
            token, settings.security.jwt_secret, algorithms=["HS256"])

        user_id = payload.get("user_id")
        if user_id is None:
            return None

        scopes = payload.get("scopes", [])

        return TokenData(user_id=user_id, scopes=scopes)

    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.JWTError:
        logger.warning("Invalid token")
        return None
