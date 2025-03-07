"""
Authentication schemes for Cortex Core
"""

from fastapi.security import OAuth2PasswordBearer

# Standard OAuth2 password bearer token scheme that raises errors for missing tokens
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Optional OAuth2 scheme that allows missing tokens
oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl="/auth/login", auto_error=False)
