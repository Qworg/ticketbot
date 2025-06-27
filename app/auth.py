"""
JWT Authentication module for Discord Ticket Bot.

This module provides JWT token generation, validation, and utility functions
for handling user authentication and authorization.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
import jwt
from pydantic import BaseModel


class JWTConfig:
    """JWT Configuration settings."""
    
    def __init__(self):
        secret_key = os.getenv("JWT_SECRET_KEY")
        if not secret_key:
            raise ValueError("JWT_SECRET_KEY environment variable is required")
        
        self.secret_key: str = secret_key
        self.algorithm = "HS256"
        self.token_expiration_hours = 24


class TokenData(BaseModel):
    """Data structure for JWT token claims."""
    user_id: str
    discord_id: int
    role: str
    email: Optional[str] = None
    issued_at: datetime
    expires_at: datetime


class JWTError(Exception):
    """Base exception for JWT-related errors."""
    pass


class TokenExpiredError(JWTError):
    """Raised when a JWT token has expired."""
    pass


class TokenInvalidError(JWTError):
    """Raised when a JWT token is malformed or has invalid signature."""
    pass


# Global JWT configuration instance - initialized on first use
_jwt_config = None


def get_jwt_config() -> JWTConfig:
    """Get or create JWT configuration instance."""
    global _jwt_config
    if _jwt_config is None:
        _jwt_config = JWTConfig()
    return _jwt_config


def generate_token(user_data: Dict[str, Any]) -> str:
    """
    Generate a JWT token for authenticated user.
    
    Args:
        user_data: Dictionary containing user information with keys:
                  - user_id: User UUID string
                  - discord_id: Discord user ID integer
                  - role: User role string
                  - email: User email (optional)
    
    Returns:
        JWT token string
        
    Raises:
        ValueError: If required user_data fields are missing
        JWTError: If token generation fails
    """
    # Validate required fields
    required_fields = ['user_id', 'discord_id', 'role']
    for field in required_fields:
        if field not in user_data:
            raise ValueError(f"Required field '{field}' missing from user_data")
    
    try:
        # Calculate timestamps
        now = datetime.now(timezone.utc)
        config = get_jwt_config()
        expires_at = now + timedelta(hours=config.token_expiration_hours)
        
        # Build JWT payload
        payload = {
            'user_id': str(user_data['user_id']),
            'discord_id': int(user_data['discord_id']),
            'role': str(user_data['role']),
            'iat': now,  # issued at
            'exp': expires_at,  # expires at
        }
        
        # Add optional email if provided
        if user_data.get('email'):
            payload['email'] = str(user_data['email'])
        
        # Generate token
        token = jwt.encode(payload, config.secret_key, algorithm=config.algorithm)
        return token
        
    except Exception as e:
        raise JWTError(f"Failed to generate token: {str(e)}")


def validate_token(token: str) -> TokenData:
    """
    Validate JWT token signature and expiration.
    
    Args:
        token: JWT token string
        
    Returns:
        TokenData object with extracted claims
        
    Raises:
        TokenExpiredError: If token has expired
        TokenInvalidError: If token is malformed or has invalid signature
    """
    try:
        # Decode and validate token
        config = get_jwt_config()
        payload = jwt.decode(
            token, 
            config.secret_key, 
            algorithms=[config.algorithm]
        )
        
        # Extract claims and create TokenData
        token_data = TokenData(
            user_id=payload['user_id'],
            discord_id=payload['discord_id'],
            role=payload['role'],
            email=payload.get('email'),
            issued_at=datetime.fromtimestamp(payload['iat'], tz=timezone.utc),
            expires_at=datetime.fromtimestamp(payload['exp'], tz=timezone.utc)
        )
        
        return token_data
        
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise TokenInvalidError(f"Invalid token: {str(e)}")
    except (KeyError, ValueError) as e:
        raise TokenInvalidError(f"Malformed token payload: {str(e)}")


def extract_claims(token: str) -> Dict[str, Any]:
    """
    Extract claims from a valid JWT token without validation.
    
    Args:
        token: JWT token string
        
    Returns:
        Dictionary of token claims
        
    Note:
        This function does not validate the token signature or expiration.
        Use validate_token() for secure token validation.
    """
    try:
        # Decode without verification (for extracting claims only)
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload
    except Exception as e:
        raise TokenInvalidError(f"Failed to extract claims: {str(e)}")


def get_token_expiry(token: str) -> datetime:
    """
    Get expiration time from JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Expiration datetime
    """
    claims = extract_claims(token)
    return datetime.fromtimestamp(claims['exp'], tz=timezone.utc)


def is_token_expired(token: str) -> bool:
    """
    Check if JWT token is expired without full validation.
    
    Args:
        token: JWT token string
        
    Returns:
        True if token is expired, False otherwise
    """
    try:
        expiry = get_token_expiry(token)
        return datetime.now(timezone.utc) > expiry
    except Exception:
        return True  # Treat malformed tokens as expired
