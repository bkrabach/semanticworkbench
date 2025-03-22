# Authentication and Authorization Guide

This document describes the authentication and authorization implementation in Cortex Core.

## Overview

The authentication system in Cortex Core follows the principle of **ruthless simplicity** while providing robust security. It supports two operation modes:

1. **Production Mode**: Uses Auth0 for JWT verification with RS256 signatures and JWKS
2. **Development Mode**: Uses a local secret key for simpler JWT verification with HS256 signatures

## Configuration

The system is configured via environment variables:

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `USE_AUTH0` | Set to "true" to enable Auth0 mode | "false" |
| `AUTH0_DOMAIN` | Your Auth0 tenant domain | "your-auth0-domain.auth0.com" |
| `AUTH0_AUDIENCE` | Your Auth0 API audience | "https://api.example.com" |
| `DEV_SECRET` | Secret key for dev mode | "development_secret_key_do_not_use_in_production" |

## Usage in API Endpoints

All protected endpoints use the `get_current_user` dependency:

```python
from fastapi import Depends
from app.utils.auth import get_current_user

@router.get("/my-endpoint")
async def my_endpoint(current_user: dict = Depends(get_current_user)):
    # Access user info with current_user["id"], current_user["email"], etc.
    return {"message": f"Hello, {current_user['name']}!"}
```

## Authentication Flow

1. **Development Mode**:
   - Client sends credentials to `/auth/login` endpoint
   - Server validates credentials and returns a JWT token
   - Client includes token in Authorization header for subsequent requests

2. **Production Mode**:
   - Client obtains token from Auth0 (not via our API)
   - Client includes Auth0 token in Authorization header for requests
   - Server validates token using Auth0's JWKS

## Testing Authentication

Use the provided test endpoints:

- `POST /auth/login` (Dev mode only): Accepts username/password and returns a token
- `GET /auth/verify`: Requires valid token, returns user information
- `GET /config/user/profile`: Protected endpoint that returns user profile information

## Example Usage

```bash
# In development mode
# 1. Get a token
curl -X POST http://localhost:8000/auth/login \
  -d "username=user@example.com" \
  -d "password=password123"

# Response:
# {"access_token":"eyJ0...","token_type":"bearer"}

# 2. Use token to access protected resources
curl -X GET http://localhost:8000/auth/verify \
  -H "Authorization: Bearer eyJ0..."

# Response:
# {"authenticated":true,"user":{"id":"dev-user-123","name":"Test User","email":"user@example.com"}}
```