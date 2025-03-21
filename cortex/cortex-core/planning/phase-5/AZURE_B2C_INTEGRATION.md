# Azure B2C Integration Guide

## Overview

This document provides comprehensive guidance for integrating Azure B2C authentication into the Cortex Core platform as part of Phase 5 production hardening. Azure B2C provides enterprise-grade identity management that replaces the simplified JWT authentication implemented in earlier phases.

This integration:

- Replaces the custom JWT implementation with Microsoft's enterprise identity solution
- Provides single sign-on capabilities
- Enables advanced user management features
- Supports role-based access control (RBAC)
- Handles token validation with proper key rotation

## Prerequisites

Before beginning implementation, ensure you have:

- An Azure account with administrative access
- Access to Azure Portal (portal.azure.com)
- The Cortex Core Phase 4 codebase
- Python 3.10 or higher
- Basic understanding of OAuth 2.0 and OpenID Connect

## Azure B2C Concepts

### Key Terminology

- **Tenant**: Your Azure B2C directory that contains users and applications
- **Application**: The client or service that authenticates users
- **User Flow**: A predefined authentication journey (registration, login, password reset)
- **Custom Policy**: Advanced user journeys with complete control
- **Identity Provider**: Authentication source (local account, social accounts, etc.)
- **Token**: JWT tokens issued after successful authentication (ID token, access token)
- **Claims**: User information contained in tokens

### Authentication Flows

Azure B2C supports multiple authentication flows:

1. **Authorization Code Flow**: Traditional web applications
2. **Implicit Flow**: Legacy single-page applications
3. **Resource Owner Password Credentials (ROPC)**: API-based authentication
4. **Client Credentials**: Service-to-service authentication

For Cortex Core, we'll implement the Authorization Code Flow with PKCE, as it's the most secure option for web applications.

## Azure B2C Setup

### Creating a B2C Tenant

1. **Create B2C Tenant**:

   - Log in to the Azure Portal
   - Search for "Azure AD B2C"
   - Click "Create an Azure AD B2C Tenant"
   - Fill in the required information:
     - Organization name (e.g., "CortexCore")
     - Initial domain name (e.g., "cortexcoreauth")
     - Country/Region
     - Resource group
   - Click "Review + create", then "Create"

2. **Switch to B2C Tenant**:
   - In the Azure Portal, click on your account in the top right
   - Select your new B2C tenant from the dropdown

### Registering Applications

1. **Register Cortex Core API Application**:

   - In your B2C tenant, go to "App registrations"
   - Click "New registration"
   - Fill in the details:
     - Name: "Cortex Core API"
     - Supported account types: "Accounts in this organizational directory only"
     - Redirect URI: Leave blank initially
   - Click "Register"
   - Note the "Application (client) ID" and "Directory (tenant) ID"

2. **Configure API Permissions**:

   - Go to "API permissions"
   - Click "Add a permission"
   - Select "Microsoft Graph"
   - Select "Application permissions"
   - Add these permissions:
     - `User.Read.All`
     - `Directory.Read.All`
   - Click "Add permissions"
   - Click "Grant admin consent"

3. **Create Client Secret**:

   - Go to "Certificates & secrets"
   - Click "New client secret"
   - Add a description and select expiration
   - Click "Add"
   - **IMPORTANT**: Copy the secret value immediately as it won't be displayed again

4. **Register Web Client Application** (if needed for admin portal):
   - Follow similar steps as the API registration
   - For Redirect URI, add your web client URL (e.g., `https://admin.cortexcore.example.com/auth/callback`)
   - Under "Authentication", check "Access tokens" and "ID tokens"

### Creating User Flows

1. **Create Sign-up/Sign-in User Flow**:

   - In your B2C tenant, go to "User flows"
   - Click "New user flow"
   - Select "Sign up and sign in"
   - Select "Recommended" version
   - Configure user attributes:
     - "Display name" (collect and return)
     - "Email Address" (collect and return)
     - Other attributes as needed
   - Application claims:
     - Include all standard claims
     - Include email and display name
   - Click "Create"

2. **Create Password Reset User Flow** (optional):

   - Similar to above, but select "Password reset"
   - Configure email-based recovery

3. **Create Profile Editing User Flow** (optional):
   - Similar to above, but select "Profile editing"
   - Configure which attributes users can edit

## Implementation Details

### Environment Configuration

Add the following environment variables to your `.env` file:

```
# Azure B2C configuration
B2C_TENANT_ID=yourtenant.onmicrosoft.com
B2C_CLIENT_ID=your-api-application-id
B2C_CLIENT_SECRET=your-api-application-secret
B2C_SIGNIN_POLICY=B2C_1_signupsignin1
B2C_AUTHORITY=https://yourtenant.b2clogin.com/yourtenant.onmicrosoft.com/
B2C_SCOPE=https://yourtenant.onmicrosoft.com/api/user_impersonation
B2C_JWKS_URI=https://yourtenant.b2clogin.com/yourtenant.onmicrosoft.com/discovery/v2.0/keys
B2C_OPENID_CONFIG=https://yourtenant.b2clogin.com/yourtenant.onmicrosoft.com/v2.0/.well-known/openid-configuration
```

Update the configuration module to include these settings:

```python
# app/config.py
from pydantic import BaseSettings

class Settings(BaseSettings):
    # Existing settings...

    # Azure B2C settings
    B2C_TENANT_ID: str
    B2C_CLIENT_ID: str
    B2C_CLIENT_SECRET: str
    B2C_SIGNIN_POLICY: str
    B2C_AUTHORITY: str
    B2C_SCOPE: str
    B2C_JWKS_URI: str
    B2C_OPENID_CONFIG: str

    class Config:
        env_file = ".env"

settings = Settings()
```

### OIDC Configuration and JWK Handling

Create a module to handle OpenID configuration and JSON Web Key (JWK) retrieval:

```python
# app/auth/oidc.py
import httpx
import json
from jose import jwk
from typing import Dict, Any, List, Optional
from app.config import settings

# Cache for OIDC configuration and JWKs
_openid_config = None
_jwks = None

async def get_openid_config() -> Dict[str, Any]:
    """Get OpenID configuration from Azure B2C."""
    global _openid_config

    if _openid_config is None:
        async with httpx.AsyncClient() as client:
            response = await client.get(settings.B2C_OPENID_CONFIG)
            response.raise_for_status()
            _openid_config = response.json()

    return _openid_config

async def get_jwks() -> Dict[str, List[Dict[str, Any]]]:
    """Get JSON Web Key Set from Azure B2C."""
    global _jwks

    if _jwks is None:
        async with httpx.AsyncClient() as client:
            response = await client.get(settings.B2C_JWKS_URI)
            response.raise_for_status()
            _jwks = response.json()

    return _jwks

async def get_key_for_token(token_header: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """
    Get the correct JWK for validating a token based on the key ID in the token header.

    Args:
        token_header: The decoded token header with 'kid' field

    Returns:
        The matching JWK if found, None otherwise
    """
    kid = token_header.get("kid")
    if not kid:
        return None

    jwks = await get_jwks()
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key

    return None
```

### Token Validation

Create a robust token validation module:

```python
# app/auth/validate.py
import time
from typing import Dict, Any, Optional
from jose import jwt, JWTError
from fastapi import HTTPException, status
from app.config import settings
from app.auth.oidc import get_key_for_token

async def decode_and_validate_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT token from Azure B2C.

    Args:
        token: The JWT token to validate

    Returns:
        The decoded token claims if valid

    Raises:
        HTTPException: If token is invalid
    """
    try:
        # Decode the token header without verification to get the kid
        header = jwt.get_unverified_header(token)

        # Get the JWK for this token
        key = await get_key_for_token(header)
        if not key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find appropriate key for token validation",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # Build the public key from JWK
        public_key = jwk.construct(key)

        # Decode and validate the token
        claims = jwt.decode(
            token,
            public_key.to_pem().decode('utf-8'),
            algorithms=["RS256"],
            audience=settings.B2C_CLIENT_ID,
            options={
                "verify_signature": True,
                "verify_aud": True,
                "verify_exp": True,
                "verify_iat": True,
                "require_exp": True,
                "require_iat": True,
            }
        )

        # Additional validations
        issuer = f"{settings.B2C_AUTHORITY}{settings.B2C_SIGNIN_POLICY}/v2.0/"
        if claims.get("iss") != issuer:
            raise JWTError("Invalid token issuer")

        if time.time() > claims.get("exp", 0):
            raise JWTError("Token expired")

        return claims

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )
```

### User Model and Mapping

Ensure the User model can handle B2C claims:

```python
# app/models/user.py
from pydantic import BaseModel, Field
from typing import List, Optional

class User(BaseModel):
    user_id: str = Field(..., description="User ID (from B2C oid claim)")
    name: str = Field(..., description="User display name")
    email: str = Field(..., description="User email address")
    roles: List[str] = Field(default_factory=list, description="User roles for RBAC")

    @classmethod
    def from_b2c_claims(cls, claims: dict) -> "User":
        """
        Create a User instance from B2C token claims.

        Args:
            claims: The claims from a validated B2C token

        Returns:
            A User instance populated with claims data
        """
        return cls(
            user_id=claims.get("oid") or claims.get("sub"),
            name=claims.get("name", ""),
            email=claims.get("emails", [""])[0] if "emails" in claims and claims["emails"] else claims.get("email", ""),
            roles=claims.get("roles", [])
        )
```

### FastAPI Integration

Update the authentication dependency to use Azure B2C:

```python
# app/auth/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2AuthorizationCodeBearer
from app.auth.validate import decode_and_validate_token
from app.models.user import User
from app.config import settings

# OAuth2 scheme using B2C endpoints
oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"{settings.B2C_AUTHORITY}{settings.B2C_SIGNIN_POLICY}/oauth2/v2.0/authorize",
    tokenUrl=f"{settings.B2C_AUTHORITY}{settings.B2C_SIGNIN_POLICY}/oauth2/v2.0/token",
    scopes={settings.B2C_SCOPE: "Access API"}
)

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    Get the current authenticated user from the token.

    Args:
        token: JWT token from request (injected by FastAPI)

    Returns:
        User object with information from token claims

    Raises:
        HTTPException: If token is invalid
    """
    claims = await decode_and_validate_token(token)

    # Create user from claims
    user = User.from_b2c_claims(claims)

    # Verify user has an ID
    if not user.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user identity",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Get the current user and verify they are active.

    In a real implementation, you might check a database or other source
    to verify the user is still active.

    Args:
        current_user: The authenticated user

    Returns:
        The authenticated user if active

    Raises:
        HTTPException: If user is not active
    """
    # This is a placeholder for actual active user validation
    # In a real implementation, you might check a database
    return current_user
```

### Role-Based Access Control (RBAC)

Create a dependency for role-based access control:

```python
# app/auth/rbac.py
from fastapi import Depends, HTTPException, status
from typing import List
from app.models.user import User
from app.auth.dependencies import get_current_active_user

def has_roles(required_roles: List[str]):
    """
    Create a dependency that requires specific roles.

    Args:
        required_roles: List of roles required for access

    Returns:
        A dependency function that validates user roles
    """
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        """
        Check if the current user has any of the required roles.

        Args:
            current_user: The current authenticated user

        Returns:
            The current user if they have required roles

        Raises:
            HTTPException: If user lacks required roles
        """
        # Check if user has any of the required roles
        if not any(role in current_user.roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user

    return role_checker
```

### API Router Integration

Update your API routes to use the new authentication:

```python
# app/api/endpoints/example.py
from fastapi import APIRouter, Depends
from app.models.user import User
from app.auth.dependencies import get_current_active_user
from app.auth.rbac import has_roles

router = APIRouter()

@router.get("/me")
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get current user information."""
    return current_user

@router.get("/admin-only")
async def admin_only(current_user: User = Depends(has_roles(["admin"]))):
    """An endpoint that requires admin role."""
    return {"message": "You have admin access", "user": current_user}
```

### Token Caching

For performance optimization, implement token caching:

```python
# app/auth/cache.py
import time
from typing import Dict, Any, Optional

# Simple in-memory cache for tokens
# In a production environment, consider using Redis or another distributed cache
token_cache: Dict[str, Dict[str, Any]] = {}

def cache_token_claims(token: str, claims: Dict[str, Any]) -> None:
    """
    Cache token claims for faster validation of frequently used tokens.

    Args:
        token: The JWT token
        claims: The decoded claims
    """
    # Only cache if token has an expiration
    if "exp" in claims:
        token_cache[token] = claims

def get_cached_claims(token: str) -> Optional[Dict[str, Any]]:
    """
    Get cached claims for a token if available and not expired.

    Args:
        token: The JWT token

    Returns:
        The cached claims if available and valid, None otherwise
    """
    if token not in token_cache:
        return None

    claims = token_cache[token]

    # Check if token is expired
    if "exp" in claims and time.time() > claims["exp"]:
        # Remove expired token from cache
        del token_cache[token]
        return None

    return claims

def clear_expired_tokens() -> None:
    """Remove all expired tokens from the cache."""
    current_time = time.time()
    expired_tokens = [
        token for token, claims in token_cache.items()
        if "exp" in claims and current_time > claims["exp"]
    ]

    for token in expired_tokens:
        del token_cache[token]
```

Update the token validation to use caching:

```python
# Update in app/auth/validate.py

async def decode_and_validate_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT token from Azure B2C."""
    # Check cache first
    cached_claims = get_cached_claims(token)
    if cached_claims:
        return cached_claims

    # Continue with normal validation if not cached
    try:
        # ... existing validation code ...

        # Cache the valid claims
        cache_token_claims(token, claims)

        return claims

    except JWTError as e:
        # ... existing error handling ...
```

### Scheduled Cache Cleanup

Add a background task to clean up expired tokens:

```python
# app/main.py
import asyncio
from fastapi import FastAPI
from app.auth.cache import clear_expired_tokens

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    # Start background token cache cleanup task
    asyncio.create_task(token_cache_cleanup())

async def token_cache_cleanup():
    """Background task to clean up expired tokens from the cache."""
    while True:
        clear_expired_tokens()
        await asyncio.sleep(300)  # Run every 5 minutes
```

## Authentication Flow Implementation

### Login and Token Acquisition

When a user needs to authenticate, redirect them to the Azure B2C login page:

```python
# app/auth/routes.py
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from app.config import settings

router = APIRouter()

@router.get("/login")
async def login(request: Request):
    """Redirect to Azure B2C login page."""
    # You should implement state parameter for security
    redirect_uri = f"{request.base_url}auth/callback"

    # Build the authorization URL
    auth_url = (
        f"{settings.B2C_AUTHORITY}{settings.B2C_SIGNIN_POLICY}/oauth2/v2.0/authorize"
        f"?client_id={settings.B2C_CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={redirect_uri}"
        f"&response_mode=query"
        f"&scope=openid profile offline_access {settings.B2C_SCOPE}"
    )

    return RedirectResponse(auth_url)

@router.get("/callback")
async def callback(code: str, request: Request):
    """Handle the authorization code callback from B2C."""
    # Exchange code for token
    redirect_uri = f"{request.base_url}auth/callback"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.B2C_AUTHORITY}{settings.B2C_SIGNIN_POLICY}/oauth2/v2.0/token",
            data={
                "grant_type": "authorization_code",
                "client_id": settings.B2C_CLIENT_ID,
                "client_secret": settings.B2C_CLIENT_SECRET,
                "code": code,
                "redirect_uri": redirect_uri,
                "scope": f"openid profile offline_access {settings.B2C_SCOPE}"
            }
        )

        # Handle errors
        if response.status_code != 200:
            return {"error": "Failed to get token", "details": response.text}

        tokens = response.json()

        # In a real app, you would:
        # 1. Store tokens securely (using httpOnly secure cookies or other means)
        # 2. Redirect to your application's main page

        # For now, just return the tokens for demonstration
        return tokens
```

### Token Refresh Implementation

For applications that use refresh tokens:

```python
# app/auth/refresh.py
import httpx
from typing import Dict, Any, Optional
from app.config import settings

async def refresh_token(refresh_token: str) -> Optional[Dict[str, Any]]:
    """
    Refresh an access token using a refresh token.

    Args:
        refresh_token: The refresh token

    Returns:
        A dictionary of new tokens if successful, None otherwise
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.B2C_AUTHORITY}{settings.B2C_SIGNIN_POLICY}/oauth2/v2.0/token",
                data={
                    "grant_type": "refresh_token",
                    "client_id": settings.B2C_CLIENT_ID,
                    "client_secret": settings.B2C_CLIENT_SECRET,
                    "refresh_token": refresh_token,
                    "scope": f"openid profile offline_access {settings.B2C_SCOPE}"
                }
            )

            if response.status_code != 200:
                return None

            return response.json()

    except Exception:
        return None
```

## Testing Azure B2C Integration

### Unit Testing

Create unit tests for token validation:

```python
# tests/auth/test_validate.py
import pytest
from unittest.mock import patch, AsyncMock
from jose import jwt
from datetime import datetime, timedelta
from app.auth.validate import decode_and_validate_token
from fastapi import HTTPException

# Create a mock JWT for testing
def create_mock_token(
    user_id: str = "test-user-123",
    name: str = "Test User",
    email: str = "test@example.com",
    expired: bool = False,
    wrong_issuer: bool = False,
    wrong_audience: bool = False
):
    """Create a mock JWT token for testing."""
    now = datetime.utcnow()
    claims = {
        "oid": user_id,
        "name": name,
        "emails": [email],
        "iss": "https://yourtenant.b2clogin.com/yourtenant.onmicrosoft.com/B2C_1_signupsignin1/v2.0/",
        "aud": "your-api-application-id",
        "iat": now.timestamp(),
        "exp": (now - timedelta(hours=1) if expired else now + timedelta(hours=1)).timestamp()
    }

    if wrong_issuer:
        claims["iss"] = "https://wrong-issuer.com"

    if wrong_audience:
        claims["aud"] = "wrong-audience"

    # For testing, we use a dummy key - in real validation this would fail
    # but we mock the validation in tests
    return jwt.encode(claims, "test-key", algorithm="HS256")

@pytest.mark.asyncio
async def test_valid_token():
    """Test validation with a valid token."""
    token = create_mock_token()

    # Mock dependencies
    with patch("app.auth.validate.get_key_for_token", new_callable=AsyncMock) as mock_get_key:
        mock_get_key.return_value = {"kty": "RSA", "n": "test", "e": "AQAB"}

        with patch("jose.jwt.decode") as mock_decode:
            # Return the decoded claims directly
            mock_decode.return_value = {
                "oid": "test-user-123",
                "name": "Test User",
                "emails": ["test@example.com"],
                "exp": (datetime.utcnow() + timedelta(hours=1)).timestamp()
            }

            # Call function
            claims = await decode_and_validate_token(token)

            # Assert
            assert claims["oid"] == "test-user-123"
            assert claims["name"] == "Test User"
            assert claims["emails"][0] == "test@example.com"

@pytest.mark.asyncio
async def test_expired_token():
    """Test validation with an expired token."""
    token = create_mock_token(expired=True)

    # Mock dependencies
    with patch("app.auth.validate.get_key_for_token", new_callable=AsyncMock) as mock_get_key:
        mock_get_key.return_value = {"kty": "RSA", "n": "test", "e": "AQAB"}

        with patch("jose.jwt.decode") as mock_decode:
            # Simulate JWT error for expired token
            mock_decode.side_effect = jwt.JWTError("Token expired")

            # Call function - should raise HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await decode_and_validate_token(token)

            # Assert
            assert exc_info.value.status_code == 401
            assert "Token expired" in exc_info.value.detail
```

### Integration Testing

Create an integration test for the authentication flow:

```python
# tests/auth/test_integration.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app
from app.models.user import User
from tests.auth.test_validate import create_mock_token

client = TestClient(app)

def test_protected_endpoint():
    """Test authentication on a protected endpoint."""
    # Create a valid token
    token = create_mock_token()

    # Mock token validation
    with patch("app.auth.dependencies.decode_and_validate_token", new_callable=AsyncMock) as mock_validate:
        # Return valid claims
        mock_validate.return_value = {
            "oid": "test-user-123",
            "name": "Test User",
            "emails": ["test@example.com"],
            "roles": ["user"]
        }

        # Test endpoint
        response = client.get(
            "/api/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test-user-123"
        assert data["name"] == "Test User"
        assert data["email"] == "test@example.com"

def test_admin_endpoint_with_correct_role():
    """Test role-based access control with admin role."""
    # Create a valid token
    token = create_mock_token()

    # Mock token validation
    with patch("app.auth.dependencies.decode_and_validate_token", new_callable=AsyncMock) as mock_validate:
        # Return valid claims with admin role
        mock_validate.return_value = {
            "oid": "test-user-123",
            "name": "Test User",
            "emails": ["test@example.com"],
            "roles": ["admin"]
        }

        # Test endpoint
        response = client.get(
            "/api/admin-only",
            headers={"Authorization": f"Bearer {token}"}
        )

        # Assert
        assert response.status_code == 200

def test_admin_endpoint_without_role():
    """Test role-based access control without admin role."""
    # Create a valid token
    token = create_mock_token()

    # Mock token validation
    with patch("app.auth.dependencies.decode_and_validate_token", new_callable=AsyncMock) as mock_validate:
        # Return valid claims without admin role
        mock_validate.return_value = {
            "oid": "test-user-123",
            "name": "Test User",
            "emails": ["test@example.com"],
            "roles": ["user"]
        }

        # Test endpoint
        response = client.get(
            "/api/admin-only",
            headers={"Authorization": f"Bearer {token}"}
        )

        # Assert
        assert response.status_code == 403
```

## Local Development Setup

For local development, create a configuration file that points to your development B2C tenant:

```python
# app/config/local.py
"""
Local development configuration.
This file is gitignored and contains local development settings.
"""

# Azure B2C configuration for local development
B2C_TENANT_ID = "yourtenant.onmicrosoft.com"
B2C_CLIENT_ID = "your-local-application-id"
B2C_CLIENT_SECRET = "your-local-application-secret"
B2C_SIGNIN_POLICY = "B2C_1_signupsignin1"
B2C_AUTHORITY = "https://yourtenant.b2clogin.com/yourtenant.onmicrosoft.com/"
B2C_SCOPE = "https://yourtenant.onmicrosoft.com/api/user_impersonation"
B2C_JWKS_URI = "https://yourtenant.b2clogin.com/yourtenant.onmicrosoft.com/discovery/v2.0/keys"
B2C_OPENID_CONFIG = "https://yourtenant.b2clogin.com/yourtenant.onmicrosoft.com/v2.0/.well-known/openid-configuration"
```

### Testing with B2C Locally

For local testing, create a simple script to obtain a token:

```python
# scripts/get_b2c_token.py
import os
import webbrowser
import http.server
import socketserver
import urllib.parse
import requests
import threading
import json
from datetime import datetime

# B2C Configuration - update with your values
B2C_TENANT = "yourtenant.onmicrosoft.com"
B2C_CLIENT_ID = "your-client-id"
B2C_CLIENT_SECRET = "your-client-secret"
B2C_POLICY = "B2C_1_signupsignin1"
REDIRECT_URI = "http://localhost:8000/callback"

# Global variables
auth_code = None
server_closed = threading.Event()

class TokenHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        global auth_code

        if self.path.startswith('/callback'):
            # Parse the query string
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)

            if 'code' in params:
                auth_code = params['code'][0]

                # Send response to browser
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'Authentication successful! You can close this window.')

                # Signal to close the server
                server_closed.set()
            else:
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'Authentication failed! No code parameter found.')
        else:
            self.send_response(404)
            self.end_headers()

def get_token():
    global auth_code

    # Build the authorization URL
    auth_url = (
        f"https://{B2C_TENANT}.b2clogin.com/{B2C_TENANT}/{B2C_POLICY}/oauth2/v2.0/authorize"
        f"?client_id={B2C_CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_mode=query"
        f"&scope=openid profile offline_access"
    )

    print(f"Opening browser to: {auth_url}")
    webbrowser.open(auth_url)

    # Start a local server to receive the callback
    with socketserver.TCPServer(("", 8000), TokenHandler) as httpd:
        print("Waiting for callback at http://localhost:8000/callback")

        # Wait until callback received or timeout
        while not server_closed.is_set():
            httpd.handle_request()

    if not auth_code:
        print("Failed to get authorization code")
        return

    # Exchange code for token
    token_url = f"https://{B2C_TENANT}.b2clogin.com/{B2C_TENANT}/{B2C_POLICY}/oauth2/v2.0/token"
    token_data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "client_id": B2C_CLIENT_ID,
        "client_secret": B2C_CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI
    }

    response = requests.post(token_url, data=token_data)

    if response.status_code != 200:
        print(f"Error getting token: {response.text}")
        return

    tokens = response.json()

    # Extract JWT and expiration
    access_token = tokens["access_token"]
    id_token = tokens["id_token"]
    expires_in = tokens["expires_in"]

    print("\nAccess Token:")
    print(access_token)
    print(f"\nExpires in: {expires_in} seconds")
    print(f"Expiration: {datetime.now().timestamp() + expires_in}")

    # Save to a file for convenience
    with open("b2c_token.json", "w") as f:
        json.dump(tokens, f, indent=2)

    print("\nTokens saved to b2c_token.json")
    print("\nUse this command to include the token in a request:")
    print(f'curl -H "Authorization: Bearer {access_token}" http://localhost:8000/api/me')

if __name__ == "__main__":
    get_token()
```

## Common Issues and Troubleshooting

### Token Validation Issues

1. **Missing Key ID (kid)**:

   - The JWT token header is missing the `kid` field
   - Solution: Ensure you're using the correct token from B2C

2. **Key Not Found**:

   - Unable to find the key with matching `kid` in JWKS
   - Solution: Refresh the JWKS cache or check if you're using the correct JWKS URI

3. **Incorrect Issuer**:

   - The token's `iss` claim doesn't match the expected issuer
   - Solution: Verify the B2C policy and tenant name in your configuration

4. **Expired Token**:
   - The token's `exp` claim indicates it has expired
   - Solution: Get a new token or implement refresh token flow

### Integration Issues

1. **CORS Problems**:

   - B2C login page not loading in browser due to CORS
   - Solution: Add your redirect URI to the allowed origins in B2C application settings

2. **Redirect URI Mismatch**:

   - Error during authentication flow about invalid redirect URI
   - Solution: Ensure the redirect URI in your code exactly matches the one registered in Azure B2C

3. **Missing Claims**:

   - Expected claims like roles or email are missing in the token
   - Solution: Check B2C policy settings to ensure these claims are included

4. **Rate Limiting**:
   - Too many requests to B2C or token validation fails due to rate limiting
   - Solution: Implement caching for JWKS and token validation

## Security Considerations

### Token Handling

1. **Never Store Tokens in LocalStorage**:

   - Vulnerable to XSS attacks
   - Use HttpOnly cookies or in-memory storage instead

2. **Implement Token Refresh**:

   - Shorter-lived access tokens (1 hour) with refresh tokens
   - Securely store refresh tokens

3. **Validate All Token Fields**:
   - Audience (`aud`)
   - Issuer (`iss`)
   - Expiration time (`exp`)
   - Issued at time (`iat`)

### HTTPS and Secure Headers

1. **Force HTTPS**:

   - All B2C communication must be over HTTPS
   - Implement HSTS header

2. **Secure Cookies**:

   - When storing tokens in cookies:
     - HttpOnly
     - Secure
     - SameSite=Lax

3. **Content Security Policy**:
   - Implement CSP header to prevent XSS
   - Explicitly allow B2C domains

### B2C Security Settings

1. **Password Complexity**:

   - Enforce strong password requirements in B2C policies

2. **MFA (Multi-Factor Authentication)**:

   - Enable for sensitive operations or admin accounts

3. **Login Attempt Limits**:

   - Prevent brute force attacks with login attempt limits

4. **IP Restrictions**:
   - For admin applications, consider IP restrictions

## Next Steps

After implementing Azure B2C authentication:

1. **Migrate Users**: If you have existing users, implement a migration strategy
2. **Custom UI**: Customize the B2C login pages for your brand
3. **Enhanced Security**: Consider implementing MFA and other security features
4. **Identity Governance**: Implement user lifecycle management
5. **Monitoring**: Set up monitoring and alerting for authentication failures

## References

- [Azure B2C Documentation](https://docs.microsoft.com/en-us/azure/active-directory-b2c/)
- [OAuth 2.0 & OpenID Connect](https://docs.microsoft.com/en-us/azure/active-directory-b2c/openid-connect)
- [JWT Validation Best Practices](https://auth0.com/blog/a-look-at-the-latest-draft-for-jwt-bcp/)
- [FastAPI OAuth2 with JWT](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
