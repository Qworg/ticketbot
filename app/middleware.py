"""
Authentication middleware for FastAPI endpoints.
Handles JWT token extraction, validation, and user authentication.
"""

import time
import logging
from typing import Optional, Set, Dict, Any
from fastapi import HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import uuid

from app.database import get_db
from app.auth import validate_token, TokenExpiredError, TokenInvalidError
from app.models.user import User
from app.cache import redis_client

logger = logging.getLogger(__name__)

# HTTP Bearer security scheme
security = HTTPBearer(auto_error=False)

# Public endpoints that bypass authentication
PUBLIC_ENDPOINTS: Set[str] = {
    "/",
    "/health",
    "/docs",
    "/openapi.json",
    "/auth/discord/login",
    "/auth/discord/callback",
    "/auth/logout"
}

# Rate limiting for failed authentication attempts
RATE_LIMIT_WINDOW = 300  # 5 minutes in seconds
MAX_FAILED_ATTEMPTS = 10


class AuthenticationMiddleware:
    """Authentication middleware for handling JWT tokens and user verification."""
    
    def __init__(self):
        self.redis_client = redis_client
    
    def _is_public_endpoint(self, path: str) -> bool:
        """Check if endpoint is public and bypasses authentication."""
        return path in PUBLIC_ENDPOINTS or path.startswith("/docs") or path.startswith("/static")
    
    def _get_rate_limit_key(self, client_ip: str) -> str:
        """Generate Redis key for rate limiting."""
        return f"auth_failures:{client_ip}"
    
    def _check_rate_limit(self, client_ip: str) -> bool:
        """Check if client IP has exceeded rate limit for failed attempts."""
        if not self.redis_client:
            return True  # Skip rate limiting if Redis unavailable
        
        try:
            key = self._get_rate_limit_key(client_ip)
            current_attempts = self.redis_client.get(key)
            if current_attempts is not None and isinstance(current_attempts, str):
                if int(current_attempts) >= MAX_FAILED_ATTEMPTS:
                    return False
            return True
        except Exception as e:
            logger.warning(f"Rate limit check failed: {e}")
            return True  # Allow on Redis failures
    
    def _increment_failed_attempts(self, client_ip: str):
        """Increment failed authentication attempts for client IP."""
        if not self.redis_client:
            return  # Skip if Redis unavailable
        
        try:
            key = self._get_rate_limit_key(client_ip)
            current = self.redis_client.get(key)
            if current is not None and isinstance(current, str):
                self.redis_client.incr(key)
            else:
                self.redis_client.setex(key, RATE_LIMIT_WINDOW, 1)
        except Exception as e:
            logger.warning(f"Failed to increment rate limit: {e}")
    
    def _log_auth_failure(self, client_ip: str, reason: str, user_agent: Optional[str] = None):
        """Log authentication failure for security monitoring."""
        logger.warning(
            f"Authentication failure - IP: {client_ip}, Reason: {reason}, "
            f"User-Agent: {user_agent or 'Unknown'}"
        )


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    FastAPI dependency for JWT token extraction and user authentication.
    
    Args:
        request: FastAPI request object
        credentials: JWT token from Authorization header (Bearer scheme)
        db: Database session
        
    Returns:
        dict: User information if authenticated
        
    Raises:
        HTTPException: 401 if unauthorized, 403 if forbidden
    """
    middleware = AuthenticationMiddleware()
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent")
    
    # Check if endpoint is public
    if middleware._is_public_endpoint(request.url.path):
        return {"is_authenticated": False}
    
    # Check rate limiting
    if not middleware._check_rate_limit(client_ip):
        middleware._log_auth_failure(client_ip, "Rate limit exceeded", user_agent)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed authentication attempts. Please try again later."
        )
    
    # Check for missing authorization header
    if not credentials:
        middleware._log_auth_failure(client_ip, "Missing authorization header", user_agent)
        middleware._increment_failed_attempts(client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    try:
        # Validate JWT token signature and expiration
        token_data = validate_token(credentials.credentials)
        
        if not token_data.user_id:
            middleware._log_auth_failure(client_ip, "Invalid token: missing user_id", user_agent)
            middleware._increment_failed_attempts(client_ip)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user_id"
            )
        
        # Query database to verify user still exists and is active
        user = db.query(User).filter(User.id == uuid.UUID(token_data.user_id)).first()
        if not user:
            middleware._log_auth_failure(client_ip, "User not found in database", user_agent)
            middleware._increment_failed_attempts(client_ip)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Check if user account is active (assuming we have an is_active field)
        if hasattr(user, 'is_active') and not user.is_active:
            middleware._log_auth_failure(client_ip, "User account inactive", user_agent)
            middleware._increment_failed_attempts(client_ip)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive"
            )
        
        # Return user information for downstream handlers
        return {
            "is_authenticated": True,
            "user_id": token_data.user_id,
            "user": user,
            "role": str(user.role),
            "discord_id": user.discord_id,
            "token_data": token_data
        }
        
    except TokenExpiredError:
        middleware._log_auth_failure(client_ip, "Token expired", user_agent)
        middleware._increment_failed_attempts(client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    except TokenInvalidError as e:
        middleware._log_auth_failure(client_ip, f"Invalid token: {str(e)}", user_agent)
        middleware._increment_failed_attempts(client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or malformed token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    except HTTPException:
        # Re-raise HTTPExceptions (including user not found, inactive user, etc.)
        raise
    
    except Exception as e:
        middleware._log_auth_failure(client_ip, f"Authentication error: {str(e)}", user_agent)
        middleware._increment_failed_attempts(client_ip)
        logger.error(f"Authentication failed for {client_ip}: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[Dict[str, Any]]:
    """
    Optional authentication dependency that doesn't raise exceptions.
    
    Returns:
        User information if authenticated, None otherwise
    """
    try:
        user_info = get_current_user(request, credentials, db)
        return user_info if user_info.get("is_authenticated") else None
    except HTTPException:
        return None


def require_authentication():
    """
    Dependency that requires valid authentication.
    
    Returns:
        FastAPI dependency function
    """
    def auth_dependency(user_info: Dict[str, Any] = Depends(get_current_user)):
        if not user_info.get("is_authenticated"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        return user_info
    
    return auth_dependency


def get_user_from_cookie(request: Request, db: Session = Depends(get_db)) -> Optional[Dict[str, Any]]:
    """
    Extract user from HTTP-only cookie for web dashboard.
    
    Args:
        request: FastAPI request object
        db: Database session
        
    Returns:
        User information if authenticated via cookie, None otherwise
    """
    try:
        # Get token from cookie
        token = request.cookies.get("auth_token")
        if not token:
            return None
        
        # Validate token
        token_data = validate_token(token)
        
        # Get user from database
        user = db.query(User).filter(User.id == uuid.UUID(token_data.user_id)).first()
        if not user:
            return None
        
        return {
            "is_authenticated": True,
            "user_id": token_data.user_id,
            "user": user,
            "role": str(user.role),
            "discord_id": user.discord_id,
            "token_data": token_data
        }
        
    except Exception as e:
        logger.debug(f"Cookie authentication failed: {e}")
        return None
