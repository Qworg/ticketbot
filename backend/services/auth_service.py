"""
Authentication service for Discord Ticket Bot.
Handles JWT token generation, validation, and API key authentication.
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from backend.models import Staff, StaffRole


class TokenData(BaseModel):
    """Token data model for JWT payload."""
    discord_id: Optional[int] = None
    staff_id: Optional[str] = None
    role: Optional[str] = None
    permissions: Optional[Dict[str, bool]] = None


class Token(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str
    expires_in: int


class APIKeyData(BaseModel):
    """API key data model."""
    key_id: str
    name: str
    permissions: Dict[str, bool]
    active: bool


class AuthService:
    """Authentication service for handling JWT tokens and API keys."""
    
    def __init__(self):
        """Initialize the authentication service."""
        self.secret_key = os.getenv("JWT_SECRET_KEY", self._generate_secret_key())
        self.algorithm = "HS256"
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # In-memory API key storage (in production, this should be in database)
        self._api_keys: Dict[str, APIKeyData] = {}
    
    def _generate_secret_key(self) -> str:
        """Generate a random secret key if not provided."""
        return secrets.token_urlsafe(32)
    
    def create_access_token(
        self, 
        staff: Staff, 
        expires_delta: Optional[timedelta] = None
    ) -> Token:
        """
        Create a JWT access token for a staff member.
        
        Args:
            staff: Staff member object
            expires_delta: Optional custom expiration time
            
        Returns:
            Token object with access token and metadata
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode = {
            "sub": str(staff.discord_id),
            "staff_id": str(staff.id),
            "role": staff.role,
            "permissions": staff.permissions,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access_token"
        }
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        
        return Token(
            access_token=encoded_jwt,
            token_type="bearer",
            expires_in=self.access_token_expire_minutes * 60
        )
    
    def verify_token(self, token: str) -> TokenData:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            TokenData object with decoded token information
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            discord_id: str = payload.get("sub")
            
            if discord_id is None:
                raise credentials_exception
                
            token_data = TokenData(
                discord_id=int(discord_id),
                staff_id=payload.get("staff_id"),
                role=payload.get("role"),
                permissions=payload.get("permissions", {})
            )
            
            return token_data
            
        except JWTError:
            raise credentials_exception
        except ValueError:
            raise credentials_exception
    
    def create_api_key(
        self, 
        name: str, 
        permissions: Dict[str, bool]
    ) -> tuple[str, APIKeyData]:
        """
        Create a new API key for external system authentication.
        
        Args:
            name: Human-readable name for the API key
            permissions: Dictionary of permissions for this API key
            
        Returns:
            Tuple of (api_key_string, APIKeyData)
        """
        key_id = secrets.token_urlsafe(16)
        api_key = f"tb_{key_id}_{secrets.token_urlsafe(32)}"
        
        api_key_data = APIKeyData(
            key_id=key_id,
            name=name,
            permissions=permissions,
            active=True
        )
        
        self._api_keys[api_key] = api_key_data
        
        return api_key, api_key_data
    
    def verify_api_key(self, api_key: str) -> APIKeyData:
        """
        Verify an API key and return its data.
        
        Args:
            api_key: API key string
            
        Returns:
            APIKeyData object with key information
            
        Raises:
            HTTPException: If API key is invalid or inactive
        """
        if not api_key or not api_key.startswith("tb_"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key format"
            )
        
        api_key_data = self._api_keys.get(api_key)
        
        if not api_key_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        
        if not api_key_data.active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key is inactive"
            )
        
        return api_key_data
    
    def revoke_api_key(self, api_key: str) -> bool:
        """
        Revoke an API key by marking it as inactive.
        
        Args:
            api_key: API key string to revoke
            
        Returns:
            True if key was revoked, False if key not found
        """
        api_key_data = self._api_keys.get(api_key)
        
        if api_key_data:
            api_key_data.active = False
            return True
        
        return False
    
    def list_api_keys(self) -> Dict[str, APIKeyData]:
        """
        List all API keys (for admin purposes).
        
        Returns:
            Dictionary of API keys and their data
        """
        return self._api_keys.copy()
    
    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
        """
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            plain_password: Plain text password
            hashed_password: Hashed password to verify against
            
        Returns:
            True if password matches, False otherwise
        """
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def check_permission(
        self, 
        user_permissions: Dict[str, bool], 
        required_permission: str
    ) -> bool:
        """
        Check if user has a specific permission.
        
        Args:
            user_permissions: User's permission dictionary
            required_permission: Permission to check for
            
        Returns:
            True if user has permission, False otherwise
        """
        return user_permissions.get(required_permission, False)
    
    def check_role_permission(
        self, 
        user_role: str, 
        required_roles: list[str]
    ) -> bool:
        """
        Check if user's role is in the list of required roles.
        
        Args:
            user_role: User's role
            required_roles: List of roles that have access
            
        Returns:
            True if user's role is authorized, False otherwise
        """
        return user_role in required_roles


# Global authentication service instance
auth_service = AuthService()