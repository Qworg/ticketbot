"""
Authentication and authorization middleware for FastAPI.
Provides dependency functions for protecting API endpoints.
"""

from typing import List, Optional, Union, Callable
from functools import wraps

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import Staff
from backend.services.auth_service import auth_service, APIKeyData
from backend.repositories.staff_repository import StaffRepository


security = HTTPBearer()


class AuthenticationError(HTTPException):
    """Custom authentication error."""
    
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


class AuthorizationError(HTTPException):
    """Custom authorization error."""
    
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


async def get_current_staff(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Staff:
    """
    Get the current authenticated staff member from JWT token.
    
    Args:
        credentials: HTTP Bearer token credentials
        db: Database session
        
    Returns:
        Staff object for the authenticated user
        
    Raises:
        AuthenticationError: If authentication fails
    """
    try:
        token_data = auth_service.verify_token(credentials.credentials)
    except HTTPException:
        raise AuthenticationError("Invalid or expired token")
    
    staff_repo = StaffRepository(db)
    staff = await staff_repo.get_by_discord_id(token_data.discord_id)
    
    if staff is None:
        raise AuthenticationError("Staff member not found")
    
    if not staff.active:
        raise AuthenticationError("Staff member is inactive")
    
    return staff


async def get_current_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> APIKeyData:
    """
    Get API key data from Bearer token.
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        APIKeyData object for the authenticated API key
        
    Raises:
        AuthenticationError: If API key authentication fails
    """
    try:
        return auth_service.verify_api_key(credentials.credentials)
    except HTTPException:
        raise AuthenticationError("Invalid or inactive API key")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Union[Staff, APIKeyData]:
    """
    Get current authenticated user (either staff member or API key).
    Tries JWT token first, then API key.
    
    Args:
        credentials: HTTP Bearer token credentials
        db: Database session
        
    Returns:
        Either Staff object or APIKeyData object
        
    Raises:
        AuthenticationError: If both authentication methods fail
    """
    # Try JWT token first
    try:
        return await get_current_staff(credentials, db)
    except AuthenticationError:
        pass
    
    # Try API key
    try:
        return await get_current_api_key(credentials)
    except AuthenticationError:
        pass
    
    raise AuthenticationError("Invalid authentication credentials")


def require_permissions(required_permissions: List[str]):
    """
    Dependency factory for requiring specific permissions.
    
    Args:
        required_permissions: List of required permissions
        
    Returns:
        Dependency function that checks permissions
    """
    async def check_permissions(
        current_user: Union[Staff, APIKeyData] = Depends(get_current_user)
    ) -> Union[Staff, APIKeyData]:
        """
        Check if current user has required permissions.
        
        Args:
            current_user: Current authenticated user
            
        Returns:
            Current user if authorized
            
        Raises:
            AuthorizationError: If user lacks required permissions
        """
        user_permissions = {}
        
        if isinstance(current_user, Staff):
            user_permissions = current_user.permissions
        elif isinstance(current_user, APIKeyData):
            user_permissions = current_user.permissions
        
        # Check if user has all required permissions
        missing_permissions = []
        for permission in required_permissions:
            if not user_permissions.get(permission, False):
                missing_permissions.append(permission)
        
        if missing_permissions:
            raise AuthorizationError(
                f"Missing required permissions: {', '.join(missing_permissions)}"
            )
        
        return current_user
    
    return check_permissions


def require_roles(required_roles: List[str]):
    """
    Dependency factory for requiring specific roles (staff only).
    
    Args:
        required_roles: List of required roles
        
    Returns:
        Dependency function that checks roles
    """
    async def check_roles(
        current_staff: Staff = Depends(get_current_staff)
    ) -> Staff:
        """
        Check if current staff member has required role.
        
        Args:
            current_staff: Current authenticated staff member
            
        Returns:
            Current staff member if authorized
            
        Raises:
            AuthorizationError: If staff member lacks required role
        """
        if current_staff.role not in required_roles:
            raise AuthorizationError(
                f"Required role: {' or '.join(required_roles)}, "
                f"current role: {current_staff.role}"
            )
        
        return current_staff
    
    return check_roles


def require_ticket_access(ticket_id_param: str = "ticket_id"):
    """
    Dependency factory for checking ticket access permissions.
    
    Args:
        ticket_id_param: Name of the path parameter containing ticket ID
        
    Returns:
        Dependency function that checks ticket access
    """
    async def check_ticket_access(
        request: Request,
        current_user: Union[Staff, APIKeyData] = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> Union[Staff, APIKeyData]:
        """
        Check if current user has access to the specified ticket.
        
        Args:
            request: FastAPI request object
            current_user: Current authenticated user
            db: Database session
            
        Returns:
            Current user if authorized
            
        Raises:
            AuthorizationError: If user lacks ticket access
        """
        # Get ticket ID from path parameters
        ticket_id = request.path_params.get(ticket_id_param)
        
        if not ticket_id:
            raise AuthorizationError("Ticket ID not found in request")
        
        # For now, we'll implement basic access control
        # In a full implementation, you'd check if the user is:
        # 1. The ticket creator
        # 2. Assigned to the ticket
        # 3. Has admin/moderator role
        # 4. Has appropriate permissions
        
        if isinstance(current_user, Staff):
            # Staff members with view_tickets permission can access tickets
            if not current_user.permissions.get("view_tickets", False):
                raise AuthorizationError("No permission to view tickets")
        elif isinstance(current_user, APIKeyData):
            # API keys with view_tickets permission can access tickets
            if not current_user.permissions.get("view_tickets", False):
                raise AuthorizationError("API key lacks ticket access permission")
        
        return current_user
    
    return check_ticket_access


# Convenience dependency functions
require_admin = require_roles(["admin"])
require_moderator_or_admin = require_roles(["moderator", "admin"])
require_staff = require_roles(["support", "moderator", "admin"])

require_view_tickets = require_permissions(["view_tickets"])
require_create_tickets = require_permissions(["create_tickets"])
require_update_tickets = require_permissions(["update_tickets"])
require_close_tickets = require_permissions(["close_tickets"])
require_view_transcripts = require_permissions(["view_transcripts"])
require_manage_staff = require_permissions(["manage_staff"])