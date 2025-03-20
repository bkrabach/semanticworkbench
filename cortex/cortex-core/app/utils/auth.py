import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", 24))

# OAuth2 password bearer scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

class TokenData(BaseModel):
    """Token data model."""
    user_id: str
    name: str = ""  # Default empty string if None
    email: str = ""  # Default empty string if None

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
    encoded_jwt: str = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

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
        name = payload.get("name", "")  # Default to empty string if not present
        email = payload.get("email", "")  # Default to empty string if not present

        if user_id is None:
            raise credentials_exception

        token_data = TokenData(user_id=user_id, name=name, email=email)
    except JWTError:
        raise credentials_exception

    return {"user_id": token_data.user_id, "name": token_data.name, "email": token_data.email}