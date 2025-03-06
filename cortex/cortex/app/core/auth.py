import logging
from typing import Dict, List, Any, Optional, Union, Callable
import asyncio
import json
from datetime import datetime, timedelta
import uuid
import time
from functools import lru_cache
import re
import os
import base64
import secrets
from jose import jwt, JWTError

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, ValidationError

from app.core.config import get_settings
from app.core.router import message_router
from app.models.schemas import User, Session, LoginAccount, AccountType, AADAccount

# Setup logging
logger = logging.getLogger(__name__)
settings = get_settings()

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/token")

# Try to import MSAL for AAD authentication
try:
    import msal
    MSAL_AVAILABLE = True
except ImportError:
    logger.warning("MSAL not available, Azure AD authentication will be limited")
    MSAL_AVAILABLE = False

class UserSessionManager:
    """
    Manager for user authentication and session tracking.
    
    This class is responsible for:
    - Handling user authentication
    - Managing session creation and validation
    - Ensuring data partitioning between users
    - Supporting multiple authentication methods
    - Linking multiple accounts to a single user
    """
    
    def __init__(self):
        """Initialize the User Session Manager."""
        # Users
        # Key: user_id, Value: User
        self.users: Dict[str, User] = {}
        
        # Accounts
        # Key: account_id, Value: LoginAccount
        self.accounts: Dict[str, LoginAccount] = {}
        
        # Account lookup by external ID
        # Key: (account_type, external_id), Value: account_id
        self.account_lookup: Dict[tuple, str] = {}
        
        # Sessions
        # Key: session_id (token), Value: Session
        self.sessions: Dict[str, Session] = {}
        
        # Session expiration (in minutes)
        self.session_expiration = settings.session_expiration if hasattr(settings, 'session_expiration') else 60 * 24  # 24 hours
        
        # JWT settings
        self.jwt_secret = settings.jwt_secret if hasattr(settings, 'jwt_secret') else secrets.token_hex(32)
        self.jwt_algorithm = "HS256"
        self.jwt_expiration = settings.jwt_expiration if hasattr(settings, 'jwt_expiration') else 60 * 24  # 24 hours
        
        # AAD settings
        self.aad_client_id = settings.aad_client_id if hasattr(settings, 'aad_client_id') else None
        self.aad_tenant_id = settings.aad_tenant_id if hasattr(settings, 'aad_tenant_id') else None
        self.aad_client_secret = settings.aad_client_secret if hasattr(settings, 'aad_client_secret') else None
        
        # Background tasks
        self.tasks: List[asyncio.Task] = []
        
        # Register with router for events
        message_router.register_component("user_session_manager", self)
        
        # Start background tasks
        self._start_background_tasks()
        
        logger.info("UserSessionManager initialized")
    
    def _start_background_tasks(self):
        """Start background tasks."""
        # Start session cleanup task
        cleanup_task = asyncio.create_task(self._session_cleanup_task())
        self.tasks.append(cleanup_task)
        
        logger.debug("Started background tasks")
    
    async def _session_cleanup_task(self):
        """Task to clean up expired sessions."""
        try:
            while True:
                # Wait for interval
                await asyncio.sleep(60 * 10)  # Check every 10 minutes
                
                # Get current time
                now = datetime.utcnow()
                
                # Find expired sessions
                expired_sessions = []
                
                for session_id, session in list(self.sessions.items()):
                    # Calculate expiration time
                    expiration = session.last_active + timedelta(minutes=self.session_expiration)
                    
                    # Check if expired
                    if now > expiration:
                        expired_sessions.append(session_id)
                
                # Remove expired sessions
                for session_id in expired_sessions:
                    logger.debug(f"Removing expired session: {session_id}")
                    await self.remove_session(session_id)
                
        except asyncio.CancelledError:
            logger.debug("Session cleanup task cancelled")
        
        except Exception as e:
            logger.error(f"Error in session cleanup task: {str(e)}")
    
    async def authenticate_user(
        self,
        account_type: AccountType,
        credentials: Dict[str, Any]
    ) -> Optional[str]:
        """
        Authenticate a user and create a session.
        
        Args:
            account_type: Type of authentication
            credentials: Authentication credentials
            
        Returns:
            Session token if successful
        """
        # Handle different authentication methods
        account_id = None
        
        if account_type == AccountType.AAD:
            # Authenticate with Azure AD
            account_id = await self._authenticate_aad(credentials)
        
        elif account_type == AccountType.LOCAL:
            # Authenticate with local account
            account_id = await self._authenticate_local(credentials)
        
        elif account_type == AccountType.MSA:
            # Authenticate with Microsoft Account (consumer)
            account_id = await self._authenticate_msa(credentials)
        
        elif account_type == AccountType.OAUTH:
            # Authenticate with generic OAuth provider
            account_id = await self._authenticate_oauth(credentials)
        
        else:
            logger.error(f"Unsupported account type: {account_type}")
            return None
        
        # Check if authentication succeeded
        if not account_id:
            logger.error(f"Authentication failed for {account_type}")
            return None
        
        # Get account
        account = self.accounts.get(account_id)
        
        if not account:
            logger.error(f"Account not found after authentication: {account_id}")
            return None
        
        # Get or create user
        user_id = await self._get_user_for_account(account_id)
        
        if not user_id:
            logger.error(f"User not found for account: {account_id}")
            return None
        
        # Create session
        session_token = await self.create_session(user_id)
        
        return session_token
    
    async def _authenticate_aad(
        self,
        credentials: Dict[str, Any]
    ) -> Optional[str]:
        """
        Authenticate with Azure AD.
        
        Args:
            credentials: AAD credentials
            
        Returns:
            Account ID if successful
        """
        # Check if MSAL is available
        if not MSAL_AVAILABLE:
            logger.error("MSAL not available for AAD authentication")
            return None
        
        # Check if AAD client ID is configured
        if not self.aad_client_id or not self.aad_tenant_id:
            logger.error("AAD client ID or tenant ID not configured")
            return None
        
        try:
            # Extract token from credentials
            token = credentials.get('token')
            
            if not token:
                logger.error("No token provided for AAD authentication")
                return None
            
            # For a complete implementation, we would validate the token here
            # For the PoC, we'll extract claims without full validation
            
            # Parse token
            try:
                # Split the token and get the payload
                token_parts = token.split('.')
                
                if len(token_parts) != 3:
                    logger.error("Invalid token format")
                    return None
                
                # Decode the payload
                payload = token_parts[1]
                
                # Add padding if needed
                padding = len(payload) % 4
                if padding:
                    payload += '=' * (4 - padding)
                
                # Decode the payload
                decoded_payload = base64.b64decode(payload)
                claims = json.loads(decoded_payload)
                
                # Extract claims
                object_id = claims.get('oid')
                tenant_id = claims.get('tid')
                email = claims.get('email') or claims.get('upn')
                name = claims.get('name')
                
                # Validate tenant ID
                if tenant_id != self.aad_tenant_id:
                    logger.error(f"Token tenant ID ({tenant_id}) does not match configured tenant ID ({self.aad_tenant_id})")
                    return None
                
                # Check if we already have an account for this object ID
                account_key = (str(AccountType.AAD), object_id)
                
                if account_key in self.account_lookup:
                    # Return existing account
                    return self.account_lookup[account_key]
                
                # Create new account
                account_id = str(uuid.uuid4())
                
                account = AADAccount(
                    id=account_id,
                    type=AccountType.AAD,
                    object_id=object_id,
                    tenant_id=tenant_id,
                    email=email,
                    display_name=name,
                    is_primary=True
                )
                
                # Add to accounts
                self.accounts[account_id] = account
                
                # Add to lookup
                self.account_lookup[account_key] = account_id
                
                logger.info(f"Created AAD account: {account_id} for {email or object_id}")
                
                return account_id
                
            except Exception as e:
                logger.error(f"Error parsing AAD token: {str(e)}")
                return None
            
        except Exception as e:
            logger.error(f"Error authenticating with AAD: {str(e)}")
            return None
    
    async def _authenticate_local(
        self,
        credentials: Dict[str, Any]
    ) -> Optional[str]:
        """
        Authenticate with local account.
        
        Args:
            credentials: Local credentials
            
        Returns:
            Account ID if successful
        """
        # For the PoC, we'll implement a simple username/password authentication
        try:
            # Extract credentials
            username = credentials.get('username')
            password = credentials.get('password')
            
            if not username or not password:
                logger.error("Missing username or password for local authentication")
                return None
            
            # In a real implementation, we would validate against a database
            # For the PoC, we'll accept any credentials for testing
            # In production, use proper password hashing and verification
            
            # For demo purposes, only accept a hardcoded test account
            if username != "test" or password != "test":
                logger.error(f"Invalid local credentials for {username}")
                return None
            
            # Check if we already have an account for this username
            account_key = (str(AccountType.LOCAL), username)
            
            if account_key in self.account_lookup:
                # Return existing account
                return self.account_lookup[account_key]
            
            # Create new account
            account_id = str(uuid.uuid4())
            
            account = LoginAccount(
                id=account_id,
                type=AccountType.LOCAL,
                is_primary=True,
                metadata={
                    "username": username,
                    "display_name": username
                }
            )
            
            # Add to accounts
            self.accounts[account_id] = account
            
            # Add to lookup
            self.account_lookup[account_key] = account_id
            
            logger.info(f"Created local account: {account_id} for {username}")
            
            return account_id
            
        except Exception as e:
            logger.error(f"Error authenticating local account: {str(e)}")
            return None
    
    async def _authenticate_msa(
        self,
        credentials: Dict[str, Any]
    ) -> Optional[str]:
        """
        Authenticate with Microsoft Account (consumer).
        
        Args:
            credentials: MSA credentials
            
        Returns:
            Account ID if successful
        """
        # Not implemented in the PoC
        logger.warning("MSA authentication not implemented in PoC")
        return None
    
    async def _authenticate_oauth(
        self,
        credentials: Dict[str, Any]
    ) -> Optional[str]:
        """
        Authenticate with generic OAuth provider.
        
        Args:
            credentials: OAuth credentials
            
        Returns:
            Account ID if successful
        """
        # Not implemented in the PoC
        logger.warning("OAuth authentication not implemented in PoC")
        return None
    
    async def _get_user_for_account(
        self,
        account_id: str
    ) -> Optional[str]:
        """
        Get the user ID for an account.
        
        Args:
            account_id: Account ID
            
        Returns:
            User ID if found or created
        """
        # Check if account exists
        if account_id not in self.accounts:
            logger.error(f"Account not found: {account_id}")
            return None
        
        # Get account
        account = self.accounts[account_id]
        
        # Check if any user has this account
        for user_id, user in self.users.items():
            for user_account in user.accounts:
                if user_account.id == account_id:
                    # Update primary account if needed
                    if account.is_primary and user.primary_account_id != account_id:
                        user.primary_account_id = account_id
                    
                    return user_id
        
        # No user found, create new user
        user_id = str(uuid.uuid4())
        
        # Determine user name from account
        user_name = None
        
        if account.type == AccountType.AAD and isinstance(account, AADAccount):
            user_name = account.display_name or account.email or f"User-{user_id[:8]}"
        else:
            # Try to get from metadata
            user_name = account.metadata.get("display_name", f"User-{user_id[:8]}")
        
        # Create user
        user = User(
            id=user_id,
            name=user_name,
            accounts=[account],
            primary_account_id=account_id
        )
        
        # Add to users
        self.users[user_id] = user
        
        logger.info(f"Created user: {user_id} for account {account_id}")
        
        return user_id
    
    async def create_session(
        self,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new session for a user.
        
        Args:
            user_id: User ID
            metadata: Optional session metadata
            
        Returns:
            Session token
        """
        # Check if user exists
        if user_id not in self.users:
            raise ValueError(f"User not found: {user_id}")
        
        # Create session
        session_id = str(uuid.uuid4())
        
        session = Session(
            id=session_id,
            user_id=user_id,
            metadata=metadata or {}
        )
        
        # Create JWT token
        token_data = {
            "sub": user_id,
            "sid": session_id,
            "exp": datetime.utcnow() + timedelta(minutes=self.jwt_expiration)
        }
        
        token = jwt.encode(token_data, self.jwt_secret, algorithm=self.jwt_algorithm)
        
        # Add to sessions
        self.sessions[token] = session
        
        logger.info(f"Created session: {session_id} for user {user_id}")
        
        return token
    
    async def validate_session(
        self,
        token: str
    ) -> Optional[str]:
        """
        Validate a session token.
        
        Args:
            token: Session token
            
        Returns:
            User ID if session is valid
        """
        # Check if token exists
        if token not in self.sessions:
            logger.warning(f"Session token not found")
            return None
        
        # Get session
        session = self.sessions[token]
        
        # Check if session is expired
        now = datetime.utcnow()
        expiration = session.last_active + timedelta(minutes=self.session_expiration)
        
        if now > expiration:
            # Remove expired session
            await self.remove_session(token)
            logger.warning(f"Session expired: {session.id}")
            return None
        
        # Update last active time
        session.last_active = now
        
        # Check if user exists
        if session.user_id not in self.users:
            # Remove invalid session
            await self.remove_session(token)
            logger.error(f"User not found for session: {session.id}")
            return None
        
        return session.user_id
    
    async def remove_session(
        self,
        token: str
    ) -> bool:
        """
        Remove a session.
        
        Args:
            token: Session token
            
        Returns:
            True if removed successfully
        """
        # Check if token exists
        if token not in self.sessions:
            logger.warning(f"Session token not found for removal")
            return False
        
        # Get session
        session = self.sessions[token]
        
        # Remove session
        del self.sessions[token]
        
        logger.info(f"Removed session: {session.id}")
        
        return True
    
    async def get_user(
        self,
        user_id: str
    ) -> Optional[User]:
        """
        Get a user.
        
        Args:
            user_id: User ID
            
        Returns:
            User if found
        """
        return self.users.get(user_id)
    
    async def add_account_to_user(
        self,
        user_id: str,
        account: LoginAccount
    ) -> bool:
        """
        Add an account to a user.
        
        Args:
            user_id: User ID
            account: Login account
            
        Returns:
            True if added successfully
        """
        # Check if user exists
        if user_id not in self.users:
            logger.error(f"User not found: {user_id}")
            return False
        
        # Get user
        user = self.users[user_id]
        
        # Check if account already exists
        for existing_account in user.accounts:
            if existing_account.id == account.id:
                logger.warning(f"Account already associated with user: {account.id}")
                return False
        
        # Add account
        user.accounts.append(account)
        
        # Set as primary if requested
        if account.is_primary:
            user.primary_account_id = account.id
        
        # Add to accounts if not already there
        if account.id not in self.accounts:
            self.accounts[account.id] = account
            
            # Add to lookup
            # For AAD accounts, use object_id as external_id
            if account.type == AccountType.AAD and isinstance(account, AADAccount):
                self.account_lookup[(str(account.type), account.object_id)] = account.id
            elif account.type == AccountType.LOCAL:
                # Use username from metadata
                username = account.metadata.get("username")
                if username:
                    self.account_lookup[(str(account.type), username)] = account.id
        
        logger.info(f"Added account {account.id} to user {user_id}")
        
        return True
    
    async def create_token(
        self,
        form_data: OAuth2PasswordRequestForm
    ) -> Dict[str, str]:
        """
        Create a token from username/password.
        
        Args:
            form_data: OAuth2 form data
            
        Returns:
            Token response
        """
        # Authenticate with local account
        credentials = {
            "username": form_data.username,
            "password": form_data.password
        }
        
        # Authenticate
        token = await self.authenticate_user(AccountType.LOCAL, credentials)
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Return token
        return {
            "access_token": token,
            "token_type": "bearer"
        }
    
    async def get_current_user(
        self,
        token: str = Depends(oauth2_scheme)
    ) -> User:
        """
        Get the current user from a token.
        
        Args:
            token: Bearer token
            
        Returns:
            User
        """
        # Validate session
        user_id = await self.validate_session(token)
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Get user
        user = await self.get_user(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        return user
    
    async def get_session_count(self) -> int:
        """
        Get the number of active sessions.
        
        Returns:
            Number of active sessions
        """
        return len(self.sessions)
    
    async def get_user_count(self) -> int:
        """
        Get the number of users.
        
        Returns:
            Number of users
        """
        return len(self.users)
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            # Cancel tasks
            for task in self.tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for tasks to complete
            if self.tasks:
                await asyncio.gather(*self.tasks, return_exceptions=True)
            
            # Clear data
            self.users.clear()
            self.accounts.clear()
            self.account_lookup.clear()
            self.sessions.clear()
            
            logger.info("UserSessionManager cleaned up")
            
        except Exception as e:
            logger.error(f"Error in cleanup: {str(e)}")

# Create a global instance for use throughout the application
user_session_manager = UserSessionManager()

# Dependency for getting current user
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    Get the current user from a token.
    
    Args:
        token: Bearer token
        
    Returns:
        User
    """
    return await user_session_manager.get_current_user(token)

# Reusable dependency for user ID
async def get_current_user_id(user: User = Depends(get_current_user)) -> str:
    """
    Get the current user ID.
    
    Args:
        user: Current user
        
    Returns:
        User ID
    """
    return user.id