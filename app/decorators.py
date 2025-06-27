"""
Permission decorators for FastAPI endpoints.
Provides role-based access control for API endpoints.
"""
from functools import wraps
from typing import Optional, List, Union
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import uuid
import logging

from app.database import get_db
from app.permissions import Permission, Role, has_permission, check_role_hierarchy
from app.cache import get_user_permissions_cached
from app.auth import validate_token

logger = logging.getLogger(__name__)

security = HTTPBearer()


class PermissionDependency:
    """
    FastAPI dependency for checking user permissions.
    """
    
    def __init__(
        self, 
        required_permissions: Optional[List[Permission]] = None,
        required_role: Optional[Role] = None,
        guild_id_param: Optional[str] = None
    ):
        """
        Initialize permission dependency.
        
        Args:
            required_permissions: List of permissions user must have
            required_role: Minimum role required (uses hierarchy)
            guild_id_param: Parameter name to extract guild_id from request
        """
        self.required_permissions = required_permissions or []
        self.required_role = required_role
        self.guild_id_param = guild_id_param
    
    def __call__(
        self,
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: Session = Depends(get_db)
    ):
        """
        Check user permissions.
        
        Args:
            credentials: JWT token from Authorization header
            db: Database session
            
        Returns:
            dict: User information if authorized
            
        Raises:
            HTTPException: 401 if unauthorized, 403 if forbidden
        """
        try:
            # Verify JWT token and get user
            token_data = validate_token(credentials.credentials)
            user_id = token_data.user_id
            
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: missing user_id"
                )
            
            # Get user from database to verify existence
            from app.models.user import User
            user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            
            # Check role hierarchy if required
            if self.required_role:
                if not check_role_hierarchy(str(user.role), self.required_role.value):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Insufficient role. Required: {self.required_role.value}"
                    )
            
            # Check permissions if required
            if self.required_permissions:
                # Determine guild context
                guild_id = None
                if self.guild_id_param:
                    # TODO: Extract guild_id from request context
                    # This would need to be implemented based on FastAPI request handling
                    pass
                
                # Get user permissions (with caching)
                user_permissions = get_user_permissions_cached(db, user_id, guild_id)
                
                # Check if user has all required permissions
                missing_permissions = [
                    perm for perm in self.required_permissions 
                    if perm not in user_permissions
                ]
                
                if missing_permissions:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Missing permissions: {[p.value for p in missing_permissions]}"
                    )
            
            return {
                "user_id": user_id,
                "user": user,
                "role": str(user.role),
                "discord_id": user.discord_id
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Permission check failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed"
            )


def require_permissions(*permissions: Permission):
    """
    Decorator factory for requiring specific permissions.
    
    Args:
        *permissions: Required permissions
        
    Returns:
        FastAPI dependency
    """
    return PermissionDependency(required_permissions=list(permissions))


def require_role(role: Role):
    """
    Decorator factory for requiring minimum role.
    
    Args:
        role: Minimum required role
        
    Returns:
        FastAPI dependency
    """
    return PermissionDependency(required_role=role)


def require_admin():
    """
    Decorator for admin-only endpoints.
    
    Returns:
        FastAPI dependency
    """
    return PermissionDependency(required_role=Role.ADMIN)


def require_staff():
    """
    Decorator for staff+ endpoints.
    
    Returns:
        FastAPI dependency
    """
    return PermissionDependency(required_role=Role.STAFF)


def require_authenticated():
    """
    Basic authentication requirement (any valid user).
    
    Returns:
        FastAPI dependency
    """
    return PermissionDependency()


# Example usage decorators for common permission combinations
def require_ticket_management():
    """Require ticket management permissions."""
    return require_permissions(Permission.MANAGE_TICKETS)


def require_analytics_access():
    """Require analytics view permissions."""
    return require_permissions(Permission.VIEW_ANALYTICS)


def require_admin_settings():
    """Require admin settings permissions."""
    return require_permissions(Permission.ADMIN_SETTINGS)
