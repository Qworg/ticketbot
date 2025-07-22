"""
Authentication routes for Discord Ticket Bot API.
Handles staff authentication and API key management.
"""

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import Staff
from backend.schemas import Staff as StaffSchema
from backend.services.auth_service import auth_service, Token, TokenData, APIKeyData
from backend.repositories.staff_repository import StaffRepository


class StaffLogin(BaseModel):
    """Staff login request model."""
    discord_id: int
    username: str


class APIKeyCreate(BaseModel):
    """API key creation request model."""
    name: str
    permissions: Dict[str, bool]


class APIKeyResponse(BaseModel):
    """API key creation response model."""
    api_key: str
    key_id: str
    name: str
    permissions: Dict[str, bool]


class APIKeyList(BaseModel):
    """API key list response model."""
    key_id: str
    name: str
    permissions: Dict[str, bool]
    active: bool


router = APIRouter(prefix="/api/auth", tags=["authentication"])
security = HTTPBearer()


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
        HTTPException: If authentication fails
    """
    token_data = auth_service.verify_token(credentials.credentials)
    
    staff_repo = StaffRepository(db)
    staff = await staff_repo.get_by_discord_id(token_data.discord_id)
    
    if staff is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Staff member not found"
        )
    
    if not staff.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Staff member is inactive"
        )
    
    return staff


async def get_api_key_data(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> APIKeyData:
    """
    Get API key data from Bearer token.
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        APIKeyData object for the authenticated API key
        
    Raises:
        HTTPException: If API key authentication fails
    """
    return auth_service.verify_api_key(credentials.credentials)


@router.post("/login", response_model=Token)
async def login_staff(
    login_data: StaffLogin,
    db: Session = Depends(get_db)
):
    """
    Authenticate a staff member and return a JWT token.
    
    Args:
        login_data: Staff login credentials
        db: Database session
        
    Returns:
        JWT token for authenticated staff member
        
    Raises:
        HTTPException: If authentication fails
    """
    staff_repo = StaffRepository(db)
    staff = await staff_repo.get_by_discord_id(login_data.discord_id)
    
    if not staff:
        # Create new staff member if they don't exist
        staff_data = {
            "discord_id": login_data.discord_id,
            "username": login_data.username,
            "role": "support",  # Default role
            "permissions": {
                "view_tickets": True,
                "create_tickets": True,
                "update_tickets": False,
                "close_tickets": False,
                "view_transcripts": True,
                "manage_staff": False
            },
            "active": True
        }
        staff = await staff_repo.create(staff_data)
    
    if not staff.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Staff member is inactive"
        )
    
    # Update username if it has changed
    if staff.username != login_data.username:
        await staff_repo.update(staff.id, {"username": login_data.username})
        staff.username = login_data.username
    
    return auth_service.create_access_token(staff)


@router.get("/me", response_model=StaffSchema)
async def get_current_user(
    current_staff: Staff = Depends(get_current_staff)
):
    """
    Get information about the currently authenticated staff member.
    
    Args:
        current_staff: Current authenticated staff member
        
    Returns:
        Staff information
    """
    return current_staff


@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    api_key_data: APIKeyCreate,
    current_staff: Staff = Depends(get_current_staff)
):
    """
    Create a new API key for external system authentication.
    Only admin staff members can create API keys.
    
    Args:
        api_key_data: API key creation data
        current_staff: Current authenticated staff member
        
    Returns:
        Created API key information
        
    Raises:
        HTTPException: If user doesn't have permission to create API keys
    """
    if current_staff.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin staff members can create API keys"
        )
    
    api_key, key_data = auth_service.create_api_key(
        api_key_data.name,
        api_key_data.permissions
    )
    
    return APIKeyResponse(
        api_key=api_key,
        key_id=key_data.key_id,
        name=key_data.name,
        permissions=key_data.permissions
    )


@router.get("/api-keys", response_model=List[APIKeyList])
async def list_api_keys(
    current_staff: Staff = Depends(get_current_staff)
):
    """
    List all API keys. Only admin staff members can list API keys.
    
    Args:
        current_staff: Current authenticated staff member
        
    Returns:
        List of API key information (without the actual keys)
        
    Raises:
        HTTPException: If user doesn't have permission to list API keys
    """
    if current_staff.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin staff members can list API keys"
        )
    
    api_keys = auth_service.list_api_keys()
    
    return [
        APIKeyList(
            key_id=key_data.key_id,
            name=key_data.name,
            permissions=key_data.permissions,
            active=key_data.active
        )
        for key_data in api_keys.values()
    ]


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_staff: Staff = Depends(get_current_staff)
):
    """
    Revoke an API key by key ID. Only admin staff members can revoke API keys.
    
    Args:
        key_id: ID of the API key to revoke
        current_staff: Current authenticated staff member
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If user doesn't have permission or key not found
    """
    if current_staff.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin staff members can revoke API keys"
        )
    
    # Find the API key by key_id
    api_keys = auth_service.list_api_keys()
    api_key_to_revoke = None
    
    for api_key, key_data in api_keys.items():
        if key_data.key_id == key_id:
            api_key_to_revoke = api_key
            break
    
    if not api_key_to_revoke:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    success = auth_service.revoke_api_key(api_key_to_revoke)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    return {"message": "API key revoked successfully"}


@router.post("/verify-token")
async def verify_token(
    current_staff: Staff = Depends(get_current_staff)
):
    """
    Verify that the current token is valid.
    
    Args:
        current_staff: Current authenticated staff member
        
    Returns:
        Token verification status
    """
    return {
        "valid": True,
        "staff_id": str(current_staff.id),
        "discord_id": current_staff.discord_id,
        "role": current_staff.role
    }


@router.post("/verify-api-key")
async def verify_api_key(
    api_key_data: APIKeyData = Depends(get_api_key_data)
):
    """
    Verify that the current API key is valid.
    
    Args:
        api_key_data: Current API key data
        
    Returns:
        API key verification status
    """
    return {
        "valid": True,
        "key_id": api_key_data.key_id,
        "name": api_key_data.name,
        "permissions": api_key_data.permissions
    }