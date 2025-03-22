from datetime import datetime, timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, Form, HTTPException

from app.models import api as api_models
from app.models import domain as domain_models
from app.utils.auth import USE_AUTH0, create_access_token, get_current_user
from app.utils.exceptions import AuthenticationException

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=api_models.LoginResponse)
async def login(username: str = Form(...), password: str = Form(...)):
    """
    Authenticate a user and return a JWT.
    Only available in development mode - disabled in Auth0 production mode.
    """
    # If in Auth0 mode, this endpoint should not be used
    if USE_AUTH0:
        raise HTTPException(status_code=404, detail="Not found")

    # In development mode, verify credentials against our test user
    if username == "user@example.com" and password == "password123":
        # Create a token with standard claims similar to Auth0
        token_data = {
            "sub": "dev-user-123",  # Subject (user ID)
            "name": "Test User",  # User's name
            "email": username,  # User's email
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=1),  # Token expires in 1 hour
        }
        access_token = create_access_token(token_data)
        return api_models.LoginResponse(access_token=access_token, token_type="bearer")
    else:
        raise AuthenticationException("Invalid username or password")


@router.get("/verify")
async def verify_token(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Verify a JWT token and return user information.
    Uses our get_current_user dependency to validate the token.
    """
    # If we're here, the token is valid (otherwise get_current_user would have raised an exception)
    user = domain_models.User(id=current_user["id"], name=current_user["name"], email=current_user["email"])
    return {"authenticated": True, "user": user}
