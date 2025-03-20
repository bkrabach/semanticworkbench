# Authentication Implementation Guide

## Overview

This document provides a comprehensive guide to the authentication system implemented in Phase 1 of the Cortex Core. It covers JWT token generation, validation, API integration, security considerations, and testing approaches.

The Phase 1 authentication system uses JSON Web Tokens (JWT) for stateless authentication with a simplified user management approach. The system is designed to be secure while maintaining simplicity, with future extensibility for Azure B2C integration in later phases.

## JWT Authentication Flow

```mermaid
sequenceDiagram
    participant Client
    participant AuthAPI as Authentication API
    participant Validator as Token Validator
    participant Protected as Protected Resource

    Client->>AuthAPI: POST /auth/login {email, password}
    AuthAPI->>AuthAPI: Validate credentials
    AuthAPI->>AuthAPI: Generate JWT token
    AuthAPI->>Client: Return token {access_token, token_type, expires_in, claims}

    Client->>Protected: Request with Authorization: Bearer {token}
    Protected->>Validator: Validate token
    Validator->>Validator: Decode and verify token
    Validator->>Validator: Extract user claims
    Validator->>Protected: Return user context
    Protected->>Client: Protected resource response
```

## JWT Token Structure

### Token Format

JSON Web Tokens consist of three parts separated by dots:

1. **Header**: Contains the token type and signing algorithm
2. **Payload**: Contains the claims (data)
3. **Signature**: Used to verify the token

Example JWT token:

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyQGV4YW1wbGUuY29tIiwib2lkIjoiNTUwZTg0MDAtZTI5Yi00MWQ0LWE3MTYtNDQ2NjU1NDQwMDAwIiwibmFtZSI6IlRlc3QgVXNlciIsImVtYWlsIjoidXNlckBleGFtcGxlLmNvbSIsImV4cCI6MTYxNjIzOTAyMiwiaWF0IjoxNjE2MTUyNjIyfQ.8P0xKopBEKoqXMjzwg7aOFN8tRRu4-a5sBTZ9GZ8F8A
```

### Claims Schema

The JWT payload includes standard and custom claims:

#### Standard Claims

| Claim | Description                      | Required |
| ----- | -------------------------------- | -------- |
| `sub` | Subject (typically email)        | Yes      |
| `exp` | Expiration time (Unix timestamp) | Yes      |
| `iat` | Issued at time (Unix timestamp)  | Yes      |

#### Custom Claims

| Claim   | Description                 | Required |
| ------- | --------------------------- | -------- |
| `oid`   | Object ID (user identifier) | Yes      |
| `name`  | User's display name         | Yes      |
| `email` | User's email address        | Yes      |

#### Example Payload (Decoded)

```json
{
  "sub": "user@example.com",
  "oid": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Test User",
  "email": "user@example.com",
  "exp": 1616239022,
  "iat": 1616152622
}
```

## Authentication Implementation

### Key Components

1. **Secret Key Management** - How the signing key is stored and accessed
2. **Token Generation** - Creating and signing JWT tokens
3. **Token Validation** - Verifying token integrity and claims
4. **User Identity** - Extracting and using user information
5. **FastAPI Integration** - Implementing authentication in the API

### Secret Key Management

In Phase 1, the secret key is stored in an environment variable:

```python
# Secret key from environment variable with fallback
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
```

**Security Considerations**:

- Use a strong, randomized secret key in production
- Never hard-code secrets in the source code
- Rotate keys periodically (not implemented in Phase 1)
- Use different keys for different environments

**Best Practices**:

- Generate a secure random key: `openssl rand -hex 32`
- Set the environment variable securely
- Ensure the key is at least 32 bytes (256 bits) for HS256

### Token Generation Implementation

The token generation function creates and signs JWT tokens:

```python
def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: The data to encode in the token
        expires_delta: Optional expiration time override

    Returns:
        JWT token string
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

**Key Aspects**:

1. **Data Copying**: Creates a copy of the input data to avoid modifying the original
2. **Expiration**: Adds an expiration timestamp based on configuration
3. **Encoding**: Uses the python-jose library to create the signed token

### Token Validation Implementation

```python
async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """
    Validate the JWT token and extract user data.

    Args:
        token: JWT token from the request

    Returns:
        User data from the token

    Raises:
        HTTPException: If token is invalid
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("oid")
        name = payload.get("name")
        email = payload.get("email")

        if user_id is None:
            raise credentials_exception

        token_data = TokenData(user_id=user_id, name=name, email=email)
    except JWTError:
        raise credentials_exception

    return {"user_id": token_data.user_id, "name": token_data.name, "email": token_data.email}
```

**Key Aspects**:

1. **Dependency Injection**: Uses FastAPI's dependency system to extract the token
2. **Error Handling**: Uses a specific exception for auth failures
3. **Decoding**: Verifies signature and decodes the token
4. **Claim Validation**: Ensures the required claims are present
5. **Model Validation**: Uses Pydantic for claim validation
6. **User Context**: Returns a standardized user context dictionary

### OAuth2 Scheme Implementation

FastAPI uses an OAuth2PasswordBearer object to extract the token from requests:

```python
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
```

**Key Aspects**:

1. **Extraction Method**: Gets token from Authorization header
2. **tokenUrl**: URL for the token endpoint (used in OpenAPI docs)
3. **Auto-errors**: Automatically raises HTTP 401 if the token is missing

### FastAPI Dependencies Integration

In FastAPI, the authentication is applied using the dependency injection system:

```python
@router.get("/protected-endpoint")
async def protected_endpoint(current_user: dict = Depends(get_current_user)):
    return {"message": "This is protected", "user": current_user}
```

**Key Aspects**:

1. **Dependency Chain**: FastAPI resolves the dependency chain automatically
2. **User Context**: The current_user dict contains user information
3. **Consistent Application**: Can be applied consistently across endpoints

## User Management in Phase 1

For Phase 1, a simple in-memory user store is used for development:

```python
# For development, a simple in-memory user store
# In production, this would use Azure B2C
USERS = {
    "user@example.com": {
        "password": "password123",
        "oid": "550e8400-e29b-41d4-a716-446655440000",
        "name": "Test User",
        "email": "user@example.com"
    }
}
```

**Note**: This is a simplified approach for development. In production (Phase 5), this would be replaced with Azure B2C integration.

### Authentication Endpoints

#### Login Endpoint

```python
@router.post("/login", response_model=LoginResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authenticate a user and return a JWT token.

    Args:
        form_data: OAuth2 password request form

    Returns:
        JWT token and user claims

    Raises:
        HTTPException: If authentication fails
    """
    # This is a simple stub for development
    # In production, this would authenticate via Azure B2C
    user = USERS.get(form_data.username)
    if not user or user["password"] != form_data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create token with user data
    token_data = {
        "sub": form_data.username,
        "oid": user["oid"],
        "name": user["name"],
        "email": user["email"]
    }

    access_token = create_access_token(token_data)

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_HOURS * 3600,  # Convert hours to seconds
        claims={
            "oid": user["oid"],
            "name": user["name"],
            "email": user["email"]
        }
    )
```

#### Token Verification Endpoint

```python
@router.get("/verify")
async def verify_token(current_user: dict = Depends(get_current_user)):
    """
    Verify a JWT token and return the user data.

    Args:
        current_user: The current user from the token

    Returns:
        User data from the token
    """
    return current_user
```

## User Partitioning with JWT

A critical aspect of the system is partitioning all data by user ID to enforce proper security boundaries. The `oid` claim from the JWT token serves as the user identifier throughout the system.

### User ID Extraction

```python
# From the token validator
user_id = payload.get("oid")

# Used in endpoint handlers
@router.get("/user-specific-data")
async def get_user_data(current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    # Use user_id to filter data
```

### Data Filtering Pattern

All data access should be filtered by user ID:

```python
# Example pattern - workspace listing filtered by owner_id
workspaces = [
    workspace for workspace in storage.workspaces.values()
    if workspace["owner_id"] == user_id
]
```

## Security Considerations

### Token Security

1. **Expiration Time**: Tokens expire after 24 hours (configurable)
2. **Token Storage**: Clients should store tokens securely, preferably in HTTP-only cookies
3. **HTTPS**: All token transmission should occur over HTTPS (enforced in production)

### CSRF Protection

In Phase 1, Cross-Site Request Forgery (CSRF) protection is implicit due to:

1. Bearer token authentication requiring explicit header setting
2. Frontend frameworks typically handling CSRF protection

For production, additional CSRF protection would be needed if using cookies.

### Secure Headers

Add security headers in production:

```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

# HTTPS redirection
app.add_middleware(HTTPSRedirectMiddleware)

# Trusted hosts
app.add_middleware(
    TrustedHostMiddleware, allowed_hosts=["api.example.com", "www.example.com"]
)
```

### CORS Configuration

In Phase 1, CORS is configured to allow all origins for development:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOW_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

For production, this should be restricted to specific origins.

## Testing Authentication

### Unit Testing Token Generation and Validation

```python
import pytest
import jwt
from datetime import datetime, timedelta
from app.utils.auth import create_access_token, get_current_user
from fastapi import HTTPException
from unittest.mock import AsyncMock

def test_create_access_token():
    """Test JWT token creation."""
    # Test data
    test_data = {
        "sub": "test@example.com",
        "oid": "test-user-123",
        "name": "Test User",
        "email": "test@example.com"
    }

    # Create token
    token = create_access_token(test_data)

    # Decode token
    decoded = jwt.decode(
        token,
        "dev-secret-key-change-in-production",  # Test secret key
        algorithms=["HS256"]
    )

    # Verify data
    assert decoded["sub"] == test_data["sub"]
    assert decoded["oid"] == test_data["oid"]
    assert decoded["name"] == test_data["name"]
    assert "exp" in decoded  # Should have expiration

@pytest.mark.asyncio
async def test_get_current_user_valid():
    """Test getting current user with valid token."""
    # Create valid token
    test_data = {
        "sub": "test@example.com",
        "oid": "test-user-123",
        "name": "Test User",
        "email": "test@example.com"
    }
    token = create_access_token(test_data)

    # Get current user
    user = await get_current_user(token)

    # Verify user data
    assert user["user_id"] == test_data["oid"]
    assert user["name"] == test_data["name"]
    assert user["email"] == test_data["email"]

@pytest.mark.asyncio
async def test_get_current_user_invalid():
    """Test getting current user with invalid token."""
    # Invalid token
    token = "invalid.token.here"

    # Should raise HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token)

    # Verify exception
    assert exc_info.value.status_code == 401
    assert "Invalid authentication credentials" in exc_info.value.detail
```

### Testing Protected Endpoints

```python
from fastapi.testclient import TestClient
from app.main import app
from app.utils.auth import create_access_token

client = TestClient(app)

def get_auth_header(user_id="test-user", name="Test User", email="test@example.com"):
    """Create authentication header with test token."""
    token = create_access_token({
        "sub": email,
        "oid": user_id,
        "name": name,
        "email": email
    })
    return {"Authorization": f"Bearer {token}"}

def test_protected_endpoint():
    """Test a protected endpoint."""
    # Without authentication
    response = client.get("/protected-endpoint")
    assert response.status_code == 401

    # With authentication
    headers = get_auth_header()
    response = client.get("/protected-endpoint", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["user_id"] == "test-user"
```

## Common Authentication Issues and Solutions

### Missing Token

**Issue**: Requests without an Authorization header will receive a 401 error.

**Solution**:

- Ensure all client requests include the Authorization header
- Check for token expiration and refresh as needed
- Provide clear error messages to guide client developers

**Example Client Code (JavaScript)**:

```javascript
const headers = {
  Authorization: `Bearer ${localStorage.getItem("token")}`,
  "Content-Type": "application/json",
};

fetch("/api/endpoint", { headers })
  .then((response) => {
    if (response.status === 401) {
      // Token expired or invalid, redirect to login
      window.location.href = "/login";
    }
    return response.json();
  })
  .then((data) => console.log(data))
  .catch((error) => console.error("Error:", error));
```

### Invalid Token Format

**Issue**: Malformed tokens will be rejected.

**Solution**:

- Use the token exactly as received from the login endpoint
- Don't modify or truncate the token
- Ensure the correct "Bearer " prefix is included

**Example Client Code (Python)**:

```python
import requests

def get_with_auth(url, token):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    return response
```

### Token Expiration

**Issue**: Tokens expire after 24 hours in Phase 1.

**Solution**:

- Handle 401 responses by redirecting to login
- Store the token expiration time and proactively refresh
- Implement retry logic for expired tokens

**Example Expiration Check (JavaScript)**:

```javascript
// When receiving the token
const tokenData = JSON.parse(atob(token.split(".")[1]));
const expirationTime = tokenData.exp * 1000; // Convert to milliseconds

// Before using the token
if (Date.now() >= expirationTime) {
  // Token expired, get a new one
  redirectToLogin();
}
```

## Future Azure B2C Integration (Phase 5)

In Phase 5, the authentication system will be extended to use Azure B2C. This section provides a preview of how that will work, for context.

### Azure B2C Configuration

```python
# Azure B2C Configuration (Future)
B2C_TENANT_ID = os.getenv("B2C_TENANT_ID")
B2C_CLIENT_ID = os.getenv("B2C_CLIENT_ID")
B2C_POLICY = os.getenv("B2C_POLICY")
B2C_AUTHORITY = f"https://{B2C_TENANT_ID}.b2clogin.com/{B2C_TENANT_ID}.onmicrosoft.com/{B2C_POLICY}"
```

### Token Validation with Azure B2C

```python
# Future implementation (Phase 5)
import msal

async def validate_b2c_token(token: str) -> Dict[str, Any]:
    """Validate an Azure B2C token."""
    # This is a simplification - actual implementation will vary
    app = msal.ConfidentialClientApplication(
        B2C_CLIENT_ID,
        authority=B2C_AUTHORITY
    )

    # Validate the token
    claims = app.verify_token(token)

    if not claims:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    return claims
```

### Login Flow with Azure B2C

In Phase 5, the login endpoint will be replaced with a redirect to Azure B2C:

```python
@router.get("/login")
async def login_redirect():
    """Redirect to Azure B2C login page."""
    return RedirectResponse(
        f"{B2C_AUTHORITY}/oauth2/v2.0/authorize?client_id={B2C_CLIENT_ID}&response_type=token&redirect_uri={REDIRECT_URI}&scope=openid%20profile"
    )
```

## Client Integration Guide

### Authentication Flow for Clients

1. **Login**:

   - POST to `/auth/login` with username/password
   - Receive JWT token in response

2. **Using the Token**:

   - Include token in all requests as `Authorization: Bearer {token}`
   - Handle 401 responses (unauthorized) by redirecting to login

3. **Token Verification**:
   - Optional: Verify token by calling `/auth/verify`
   - Extract user information from token payload

### Example Client Code

#### Login (JavaScript)

```javascript
async function login(email, password) {
  const response = await fetch("/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: new URLSearchParams({
      username: email,
      password: password,
    }),
  });

  if (!response.ok) {
    throw new Error("Login failed");
  }

  const data = await response.json();

  // Store token in localStorage (or more securely in memory for SPAs)
  localStorage.setItem("token", data.access_token);
  localStorage.setItem("token_expiry", Date.now() + data.expires_in * 1000);

  return data;
}
```

#### Protected Request (JavaScript)

```javascript
async function fetchProtectedResource(url) {
  // Check if token exists and is not expired
  const token = localStorage.getItem("token");
  const expiry = localStorage.getItem("token_expiry");

  if (!token || !expiry || Date.now() > parseInt(expiry)) {
    // Redirect to login if token is missing or expired
    window.location.href = "/login";
    return;
  }

  const response = await fetch(url, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (response.status === 401) {
    // Token is invalid or expired
    localStorage.removeItem("token");
    localStorage.removeItem("token_expiry");
    window.location.href = "/login";
    return;
  }

  return response.json();
}
```

## Conclusion

The Phase 1 authentication system implements a solid foundation for secure client authentication using JWT tokens. The system is designed to be simple yet secure, with a clear path for future integration with Azure B2C in Phase 5.

Key takeaways:

1. **JWT-Based Authentication**: Stateless authentication using JSON Web Tokens
2. **User Partitioning**: All data is properly partitioned by user ID
3. **FastAPI Integration**: Clean integration with FastAPI's dependency system
4. **Testing Approach**: Comprehensive testing strategy for authentication
5. **Future Extensibility**: Clear path to Azure B2C integration in Phase 5

By following the guidelines in this document, you can implement a secure authentication system that properly isolates user data and provides a solid foundation for future enhancements.
