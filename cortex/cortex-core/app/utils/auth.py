import datetime
import logging
from typing import Any, Dict, Optional

import jwt
from fastapi import Header
from jwt.jwks_client import PyJWKClient

from app.core.config import USE_AUTH0, AUTH0_DOMAIN, AUTH0_AUDIENCE, DEV_SECRET
from app.utils.exceptions import AuthenticationException

# Set up logger
logger = logging.getLogger(__name__)

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
        logger.warning("Token verification failed: No token provided")
        raise ValueError("No token provided")

    try:
        if USE_AUTH0:
            # Production mode: verify with Auth0 JWKS
            if auth0_verifier is None:
                logger.error("Auth0 verifier not initialized but USE_AUTH0 is True")
                raise ValueError("Auth0 verifier not initialized")
                
            logger.debug("Verifying token with Auth0 JWKS")
            payload = auth0_verifier.verify(token)
            logger.debug(f"Auth0 token verified successfully for subject: {payload.get('sub')}")
            return payload
        else:
            # Development mode: verify with local secret
            logger.debug("Verifying development token with local secret")
            decoded_token = jwt.decode(token, DEV_SECRET, algorithms=["HS256"])
            # Explicitly cast to ensure typing is correct
            logger.debug(f"Development token verified successfully for subject: {decoded_token.get('sub')}")
            return dict(decoded_token)
    except jwt.PyJWTError as e:
        logger.warning(f"Token verification failed: {str(e)}")
        # Always raise exceptions for invalid tokens
        raise ValueError(f"Invalid token: {str(e)}")


def get_current_user(
    authorization: Optional[str] = Header(None), 
    token: Optional[str] = None
) -> Dict[str, Any]:
    """
    FastAPI dependency function to extract and validate the user from JWT token.
    Supports both header-based and query parameter-based authentication.

    Usage:
        @app.get("/protected")
        async def protected_route(current_user: dict = Depends(get_current_user)):
            return {"message": f"Hello, {current_user['name']}!"}

    Args:
        authorization: The Authorization header value (Bearer token)
        token: Token from query parameter (alternative to Authorization header)

    Raises AuthenticationException if token is invalid or missing.
    """
    # Check for token from query parameter first, then header
    jwt_token = None
    
    # If token is in query parameter, use it directly
    if token:
        jwt_token = token
        logger.debug("Using token from query parameter")
    # Otherwise try to extract from Authorization header
    elif authorization:
        # Check if it has the correct format (Bearer token)
        parts = authorization.split()
        if parts[0].lower() != "bearer" or len(parts) != 2:
            logger.warning("Authentication failed: Invalid Authorization header format")
            raise AuthenticationException("Invalid Authorization header format")
        jwt_token = parts[1]
        logger.debug("Using token from Authorization header")
    else:
        logger.warning("Authentication failed: No token provided (missing both Authorization header and token parameter)")
        raise AuthenticationException("No authentication token provided")
    
    try:
        # Verify the token using our helper function
        logger.debug("Attempting to verify JWT token")
        payload = verify_jwt(jwt_token)

        # Extract user info from token claims
        user = {"id": payload.get("sub"), "email": payload.get("email"), "name": payload.get("name", "Anonymous User")}

        # Ensure we have a user ID
        if not user["id"]:
            logger.warning("Authentication failed: Token payload missing 'sub' claim")
            raise AuthenticationException("Token payload missing 'sub' claim")

        logger.debug(f"User authenticated successfully: {user['id']}")
        return user
    except (ValueError, jwt.PyJWTError) as e:
        logger.warning(f"Authentication failed: {str(e)}")
        raise AuthenticationException(str(e))
