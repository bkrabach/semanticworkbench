"""
Session Manager Component

This module implements a session manager that handles user sessions, authentication,
and session state. It provides functionality for creating, retrieving, and managing
user sessions.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Union, Any

from fastapi import HTTPException, status
from pydantic import BaseModel, Field

from app.cache.redis import redis_cache
from app.config import settings
from app.utils.logger import get_contextual_logger

# Configure logger
logger = get_contextual_logger("components.session_manager")


class SessionState(BaseModel):
    """Model representing the state of a user session"""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: Optional[uuid.UUID] = None
    authenticated: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    active: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)
    last_activity_timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "550e8400-e29b-41d4-a716-446655440001",
                "authenticated": True,
                "created_at": "2025-03-06T15:30:45.123456",
                "updated_at": "2025-03-06T15:30:45.123456",
                "expires_at": "2025-03-06T16:30:45.123456",
                "active": True,
                "metadata": {"client_info": "web", "ip_address": "127.0.0.1"},
                "last_activity_timestamp": "2025-03-06T15:30:45.123456",
            }
        }


class SessionManager:
    """
    Session Manager for handling user sessions

    This class provides functionality for creating, retrieving, and managing
    user sessions, including authentication and session state.
    """

    SESSION_CACHE_PREFIX = "session:"
    SESSION_CACHE_TTL = 24 * 3600  # 24 hours in seconds
    SESSION_CLEANUP_INTERVAL = 3600  # 1 hour in seconds

    def __init__(self):
        """Initialize the session manager"""
        self.sessions: Dict[uuid.UUID, SessionState] = {}
        logger.info("Session manager initialized")

        # Start session cleanup task
        asyncio.create_task(self._cleanup_expired_sessions())

    async def create_session(
        self,
        user_id: Optional[uuid.UUID] = None,
        authenticated: bool = False,
        expires_in: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SessionState:
        """
        Create a new user session

        Args:
            user_id: Optional user ID for authenticated sessions
            authenticated: Whether the session is authenticated
            expires_in: Optional expiration time in seconds
            metadata: Optional metadata for the session

        Returns:
            New session state
        """
        try:
            # Create a new session ID
            session_id = uuid.uuid4()

            # Calculate expiration time
            expires_at = None
            if expires_in is not None:
                expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

            # Create session state
            session = SessionState(
                id=session_id,
                user_id=user_id,
                authenticated=authenticated,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                expires_at=expires_at,
                active=True,
                metadata=metadata or {},
                last_activity_timestamp=datetime.utcnow(),
            )

            # Store session in memory
            self.sessions[session_id] = session

            # Cache session
            await self._cache_session(session)

            logger.info(f"Created new session: {session_id}")
            return session

        except Exception as e:
            logger.error(f"Failed to create session: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create session: {str(e)}",
            )

    async def get_session(self, session_id: uuid.UUID) -> Optional[SessionState]:
        """
        Get a session by ID

        Args:
            session_id: The session ID

        Returns:
            Session state or None if not found
        """
        try:
            # Try to get from memory first
            session = self.sessions.get(session_id)

            # If not in memory, try to get from cache
            if session is None:
                cached_session = await redis_cache.get(
                    key=self._get_cache_key(session_id)
                )

                if cached_session:
                    session = SessionState(**cached_session)

                    # Store in memory for future access
                    self.sessions[session_id] = session

            if session is None:
                logger.warning(f"Session not found: {session_id}")
                return None

            # Check if session is expired
            if session.expires_at and session.expires_at < datetime.utcnow():
                logger.info(f"Session expired: {session_id}")
                await self.invalidate_session(session_id)
                return None

            # Update last activity timestamp
            session.last_activity_timestamp = datetime.utcnow()
            session.updated_at = datetime.utcnow()

            # Update cache
            await self._cache_session(session)

            return session

        except Exception as e:
            logger.error(f"Failed to get session: {str(e)}", exc_info=True)
            return None

    async def update_session(
        self,
        session_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
        authenticated: Optional[bool] = None,
        metadata: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None,
        active: Optional[bool] = None,
    ) -> Optional[SessionState]:
        """
        Update a session

        Args:
            session_id: The session ID
            user_id: Optional new user ID
            authenticated: Optional new authentication status
            metadata: Optional new metadata
            expires_at: Optional new expiration time
            active: Optional new active status

        Returns:
            Updated session state or None if not found
        """
        try:
            # Get current session
            session = await self.get_session(session_id)
            if session is None:
                logger.warning(f"Session not found for update: {session_id}")
                return None

            # Update session fields
            if user_id is not None:
                session.user_id = user_id

            if authenticated is not None:
                session.authenticated = authenticated

            if metadata is not None:
                session.metadata = metadata

            if expires_at is not None:
                session.expires_at = expires_at

            if active is not None:
                session.active = active

            # Update timestamps
            session.updated_at = datetime.utcnow()
            session.last_activity_timestamp = datetime.utcnow()

            # Store updated session
            self.sessions[session_id] = session

            # Update cache
            await self._cache_session(session)

            logger.info(f"Updated session: {session_id}")
            return session

        except Exception as e:
            logger.error(f"Failed to update session: {str(e)}", exc_info=True)
            return None

    async def invalidate_session(self, session_id: uuid.UUID) -> bool:
        """
        Invalidate a session

        Args:
            session_id: The session ID

        Returns:
            True if session was invalidated, False otherwise
        """
        try:
            # Get current session
            session = self.sessions.get(session_id)

            if session is None:
                cached_session = await redis_cache.get(
                    key=self._get_cache_key(session_id)
                )

                if cached_session:
                    session = SessionState(**cached_session)

            if session is None:
                logger.warning(f"Session not found for invalidation: {session_id}")
                return False

            # Mark session as inactive
            session.active = False
            session.updated_at = datetime.utcnow()

            # Remove from memory
            if session_id in self.sessions:
                del self.sessions[session_id]

            # Remove from cache
            await redis_cache.delete(key=self._get_cache_key(session_id))

            logger.info(f"Invalidated session: {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to invalidate session: {str(e)}", exc_info=True)
            return False

    async def get_user_sessions(self, user_id: uuid.UUID) -> List[SessionState]:
        """
        Get all active sessions for a user

        Args:
            user_id: The user ID

        Returns:
            List of active sessions for the user
        """
        try:
            # Filter sessions by user ID
            user_sessions = [
                session
                for session in self.sessions.values()
                if session.user_id == user_id and session.active
            ]

            # Check for expired sessions
            valid_sessions = []
            for session in user_sessions:
                if session.expires_at and session.expires_at < datetime.utcnow():
                    # Invalidate expired session
                    await self.invalidate_session(session.id)
                else:
                    valid_sessions.append(session)

            return valid_sessions

        except Exception as e:
            logger.error(f"Failed to get user sessions: {str(e)}", exc_info=True)
            return []

    def _get_cache_key(self, session_id: uuid.UUID) -> str:
        """
        Get the cache key for a session

        Args:
            session_id: The session ID

        Returns:
            Cache key for the session
        """
        return f"{self.SESSION_CACHE_PREFIX}{session_id}"

    async def _cache_session(self, session: SessionState) -> None:
        """
        Cache a session for fast access

        Args:
            session: The session to cache
        """
        cache_key = self._get_cache_key(session.id)

        ttl = None
        if session.expires_at:
            # Calculate TTL in seconds
            delta = session.expires_at - datetime.utcnow()
            ttl = max(1, int(delta.total_seconds()))
        else:
            ttl = self.SESSION_CACHE_TTL

        await redis_cache.set(
            key=cache_key,
            value=session.dict(),
            ttl=ttl,
        )

    async def _cleanup_expired_sessions(self) -> None:
        """
        Periodic task to clean up expired sessions
        """
        while True:
            try:
                logger.debug("Running session cleanup task")

                current_time = datetime.utcnow()
                expired_session_ids = []

                # Find expired sessions
                for session_id, session in self.sessions.items():
                    if (session.expires_at and session.expires_at < current_time) or (
                        not session.active
                    ):
                        expired_session_ids.append(session_id)

                # Invalidate expired sessions
                for session_id in expired_session_ids:
                    await self.invalidate_session(session_id)

                if expired_session_ids:
                    logger.info(
                        f"Cleaned up {len(expired_session_ids)} expired sessions"
                    )

            except Exception as e:
                logger.error(f"Error in session cleanup task: {str(e)}", exc_info=True)

            # Wait for next cleanup interval
            await asyncio.sleep(self.SESSION_CLEANUP_INTERVAL)


# Global instance
session_manager = None


def initialize_session_manager() -> SessionManager:
    """
    Initialize the global session manager instance

    Returns:
        The initialized session manager
    """
    global session_manager
    if session_manager is None:
        session_manager = SessionManager()
    return session_manager


# Export public symbols
__all__ = [
    "SessionState",
    "SessionManager",
    "session_manager",
    "initialize_session_manager",
]
