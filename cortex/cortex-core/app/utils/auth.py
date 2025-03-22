import datetime
import os
from typing import Any, Dict, Optional

import jwt
from fastapi import Header
from jwt.jwks_client import PyJWKClient

from app.utils.exceptions import AuthenticationException

# Configuration settings
USE_AUTH0 = os.getenv("USE_AUTH0", "false").lower() == "true"
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN", "your-auth0-domain.auth0.com")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE", "https://api.example.com")
DEV_SECRET = os.getenv("DEV_SECRET", "development_secret_key_do_not_use_in_production")

# Initialize JWKS client if in Auth0 mode
jwks_client = None
if USE_AUTH0:
    jwks_url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
    jwks_client = PyJWKClient(jwks_url)


class Auth0JWTVerifier:
    """Simple helper for verifying Auth0 JWT tokens using JWKS."""

    def __init__(self, domain: str, audience: str):
        """Initialize with Auth0 domain and API audience."""
        self.domain = domain
        self.audience = audience
        self.issuer = f"https://{domain}/"
        jwks_url = f"https://{domain}/.well-known/jwks.json"
        self.jwks_client = PyJWKClient(jwks_url)

    def verify(self, token: str) -> Dict[str, Any]:
        """
        Verify the token signature and claims, return payload if valid.
        Raises exception if token is invalid.
        """
        # Get the public key for this token
        signing_key = self.jwks_client.get_signing_key_from_jwt(token).key

        # Decode and verify the token
        payload = jwt.decode(token, signing_key, algorithms=["RS256"], audience=self.audience, issuer=self.issuer)
        # Explicitly cast to ensure typing is correct
        return dict(payload)


# Instantiate the verifier if in Auth0 mode
auth0_verifier = Auth0JWTVerifier(AUTH0_DOMAIN, AUTH0_AUDIENCE) if USE_AUTH0 else None


def create_access_token(data: Dict[str, Any], expires_delta: Optional[datetime.timedelta] = None) -> str:
    """
    Create a JWT access token with the provided data and expiration delta.
    For development testing purposes only.
    """
    if USE_AUTH0:
        raise ValueError("Cannot create tokens in Auth0 mode - use Auth0 to obtain tokens")

    to_encode = data.copy()

    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        # Default to 15 minutes
        expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=15)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, DEV_SECRET, algorithm="HS256")

    # PyJWT > 2.0.0 returns string, < 2.0.0 returns bytes
    if isinstance(encoded_jwt, bytes):
        return encoded_jwt.decode("utf-8")
    return encoded_jwt


def verify_jwt(token: str) -> Dict[str, Any]:
    """
    Verify a JWT and return the decoded token claims.
    Uses Auth0 JWT verification in production mode,
    and local verification with secret key in development mode.

    Raises ValueError or jwt.PyJWTError if token is invalid.
    """
    if not token:
        raise ValueError("No token provided")

    try:
        if USE_AUTH0:
            # Production mode: verify with Auth0 JWKS
            if auth0_verifier is None:
                raise ValueError("Auth0 verifier not initialized")
            return auth0_verifier.verify(token)
        else:
            # Development mode: verify with local secret
            decoded_token = jwt.decode(token, DEV_SECRET, algorithms=["HS256"])
            # Explicitly cast to ensure typing is correct
            return dict(decoded_token)
    except jwt.PyJWTError as e:
        # Always raise exceptions for invalid tokens
        raise ValueError(f"Invalid token: {str(e)}")


def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """
    FastAPI dependency function to extract and validate the user from JWT token.

    Usage:
        @app.get("/protected")
        async def protected_route(current_user: dict = Depends(get_current_user)):
            return {"message": f"Hello, {current_user['name']}!"}

    Raises AuthenticationException if token is invalid or missing.
    """
    # Check if Authorization header is present
    if not authorization:
        raise AuthenticationException("Authorization header missing")

    # Check if it has the correct format (Bearer token)
    parts = authorization.split()
    if parts[0].lower() != "bearer" or len(parts) != 2:
        raise AuthenticationException("Invalid Authorization header format")

    token = parts[1]

    try:
        # Verify the token using our helper function
        payload = verify_jwt(token)

        # Extract user info from token claims
        user = {"id": payload.get("sub"), "email": payload.get("email"), "name": payload.get("name", "Anonymous User")}

        # Ensure we have a user ID
        if not user["id"]:
            raise AuthenticationException("Token payload missing 'sub' claim")

        return user
    except (ValueError, jwt.PyJWTError) as e:
        raise AuthenticationException(str(e))
