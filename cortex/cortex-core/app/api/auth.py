from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from ..core.exceptions import InvalidCredentialsException
from ..models.api.response import LoginResponse
from ..utils.auth import ACCESS_TOKEN_EXPIRE_HOURS, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

# For development, a simple in-memory user store
# In production, this would use Azure B2C
#
# Authentication Flow:
# 1. Users authenticate against this static dictionary via the login endpoint
# 2. Once authenticated, a JWT token is generated with the user information
# 3. This token is used for subsequent requests
# 4. The system expects these users to exist in the database for foreign key constraints
# 5. The ensure_test_users_exist() function in main.py synchronizes these users to the database
#
# This two-part approach (in-memory auth + database records) is a development
# simplification. In production, a proper Azure B2C integration would handle
# user authentication and database synchronization.
USERS = {
    "user@example.com": {
        "password": "password123",
        "oid": "550e8400-e29b-41d4-a716-446655440000",
        "name": "Test User",
        "email": "user@example.com",
    }
}


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
        raise InvalidCredentialsException(
            message="Invalid email or password", details={"headers": {"WWW-Authenticate": "Bearer"}}
        )

    # Create token with user data
    token_data = {"sub": form_data.username, "oid": user["oid"], "name": user["name"], "email": user["email"]}

    access_token = create_access_token(token_data)

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_HOURS * 3600,  # Convert hours to seconds
        claims={"oid": user["oid"], "name": user["name"], "email": user["email"]},
    )


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
