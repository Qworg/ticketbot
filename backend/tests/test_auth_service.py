"""
Unit tests for the authentication service.
"""

import os
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from fastapi import HTTPException
from jose import jwt

from backend.services.auth_service import AuthService, TokenData, APIKeyData
from backend.models import Staff, StaffRole


class TestAuthService:
    """Test cases for AuthService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.auth_service = AuthService()
        
        # Create a test staff member
        self.test_staff = Staff(
            id="123e4567-e89b-12d3-a456-426614174000",
            discord_id=123456789,
            username="test_user",
            role=StaffRole.SUPPORT.value,
            permissions={
                "view_tickets": True,
                "create_tickets": True,
                "update_tickets": False,
                "close_tickets": False
            },
            active=True
        )
    
    def test_create_access_token(self):
        """Test JWT token creation."""
        token = self.auth_service.create_access_token(self.test_staff)
        
        assert token.access_token is not None
        assert token.token_type == "bearer"
        assert token.expires_in == self.auth_service.access_token_expire_minutes * 60
        
        # Verify token can be decoded
        payload = jwt.decode(
            token.access_token, 
            self.auth_service.secret_key, 
            algorithms=[self.auth_service.algorithm]
        )
        
        assert payload["sub"] == str(self.test_staff.discord_id)
        assert payload["staff_id"] == str(self.test_staff.id)
        assert payload["role"] == self.test_staff.role
        assert payload["permissions"] == self.test_staff.permissions
        assert payload["type"] == "access_token"
    
    def test_create_access_token_with_custom_expiry(self):
        """Test JWT token creation with custom expiry."""
        custom_expiry = timedelta(minutes=60)
        token = self.auth_service.create_access_token(
            self.test_staff, 
            expires_delta=custom_expiry
        )
        
        payload = jwt.decode(
            token.access_token, 
            self.auth_service.secret_key, 
            algorithms=[self.auth_service.algorithm]
        )
        
        # Check that expiry is approximately 60 minutes from now
        exp_time = datetime.utcfromtimestamp(payload["exp"])
        expected_time = datetime.utcnow() + custom_expiry
        
        # Allow 1 minute tolerance for test execution time
        assert abs((exp_time - expected_time).total_seconds()) < 60
    
    def test_verify_token_valid(self):
        """Test token verification with valid token."""
        token = self.auth_service.create_access_token(self.test_staff)
        token_data = self.auth_service.verify_token(token.access_token)
        
        assert token_data.discord_id == self.test_staff.discord_id
        assert token_data.staff_id == str(self.test_staff.id)
        assert token_data.role == self.test_staff.role
        assert token_data.permissions == self.test_staff.permissions
    
    def test_verify_token_invalid(self):
        """Test token verification with invalid token."""
        with pytest.raises(HTTPException) as exc_info:
            self.auth_service.verify_token("invalid_token")
        
        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in exc_info.value.detail
    
    def test_verify_token_expired(self):
        """Test token verification with expired token."""
        # Create token with past expiry
        past_time = datetime.utcnow() - timedelta(minutes=1)
        expired_payload = {
            "sub": str(self.test_staff.discord_id),
            "staff_id": str(self.test_staff.id),
            "role": self.test_staff.role,
            "permissions": self.test_staff.permissions,
            "exp": past_time,
            "iat": datetime.utcnow() - timedelta(minutes=2),
            "type": "access_token"
        }
        
        expired_token = jwt.encode(
            expired_payload, 
            self.auth_service.secret_key, 
            algorithm=self.auth_service.algorithm
        )
        
        with pytest.raises(HTTPException) as exc_info:
            self.auth_service.verify_token(expired_token)
        
        assert exc_info.value.status_code == 401
    
    def test_create_api_key(self):
        """Test API key creation."""
        permissions = {"view_tickets": True, "create_tickets": False}
        api_key, key_data = self.auth_service.create_api_key("test_key", permissions)
        
        assert api_key.startswith("tb_")
        assert key_data.name == "test_key"
        assert key_data.permissions == permissions
        assert key_data.active is True
        assert len(key_data.key_id) > 0
        
        # Verify key is stored
        stored_keys = self.auth_service.list_api_keys()
        assert api_key in stored_keys
        assert stored_keys[api_key] == key_data
    
    def test_verify_api_key_valid(self):
        """Test API key verification with valid key."""
        permissions = {"view_tickets": True}
        api_key, expected_data = self.auth_service.create_api_key("test_key", permissions)
        
        key_data = self.auth_service.verify_api_key(api_key)
        
        assert key_data.key_id == expected_data.key_id
        assert key_data.name == expected_data.name
        assert key_data.permissions == expected_data.permissions
        assert key_data.active is True
    
    def test_verify_api_key_invalid_format(self):
        """Test API key verification with invalid format."""
        with pytest.raises(HTTPException) as exc_info:
            self.auth_service.verify_api_key("invalid_key")
        
        assert exc_info.value.status_code == 401
        assert "Invalid API key format" in exc_info.value.detail
    
    def test_verify_api_key_not_found(self):
        """Test API key verification with non-existent key."""
        with pytest.raises(HTTPException) as exc_info:
            self.auth_service.verify_api_key("tb_nonexistent_key")
        
        assert exc_info.value.status_code == 401
        assert "Invalid API key" in exc_info.value.detail
    
    def test_verify_api_key_inactive(self):
        """Test API key verification with inactive key."""
        permissions = {"view_tickets": True}
        api_key, _ = self.auth_service.create_api_key("test_key", permissions)
        
        # Revoke the key
        self.auth_service.revoke_api_key(api_key)
        
        with pytest.raises(HTTPException) as exc_info:
            self.auth_service.verify_api_key(api_key)
        
        assert exc_info.value.status_code == 401
        assert "API key is inactive" in exc_info.value.detail
    
    def test_revoke_api_key(self):
        """Test API key revocation."""
        permissions = {"view_tickets": True}
        api_key, _ = self.auth_service.create_api_key("test_key", permissions)
        
        # Verify key is active
        key_data = self.auth_service.verify_api_key(api_key)
        assert key_data.active is True
        
        # Revoke key
        success = self.auth_service.revoke_api_key(api_key)
        assert success is True
        
        # Verify key is inactive
        stored_keys = self.auth_service.list_api_keys()
        assert stored_keys[api_key].active is False
    
    def test_revoke_api_key_not_found(self):
        """Test API key revocation with non-existent key."""
        success = self.auth_service.revoke_api_key("nonexistent_key")
        assert success is False
    
    def test_list_api_keys(self):
        """Test API key listing."""
        # Initially empty
        keys = self.auth_service.list_api_keys()
        assert len(keys) == 0
        
        # Create some keys
        permissions1 = {"view_tickets": True}
        permissions2 = {"create_tickets": True}
        
        api_key1, _ = self.auth_service.create_api_key("key1", permissions1)
        api_key2, _ = self.auth_service.create_api_key("key2", permissions2)
        
        keys = self.auth_service.list_api_keys()
        assert len(keys) == 2
        assert api_key1 in keys
        assert api_key2 in keys
    
    def test_hash_password(self):
        """Test password hashing."""
        password = "test_password"
        hashed = self.auth_service.hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")  # bcrypt hash format
    
    def test_verify_password(self):
        """Test password verification."""
        password = "test_password"
        hashed = self.auth_service.hash_password(password)
        
        # Correct password
        assert self.auth_service.verify_password(password, hashed) is True
        
        # Incorrect password
        assert self.auth_service.verify_password("wrong_password", hashed) is False
    
    def test_check_permission(self):
        """Test permission checking."""
        permissions = {
            "view_tickets": True,
            "create_tickets": False,
            "admin": True
        }
        
        assert self.auth_service.check_permission(permissions, "view_tickets") is True
        assert self.auth_service.check_permission(permissions, "create_tickets") is False
        assert self.auth_service.check_permission(permissions, "admin") is True
        assert self.auth_service.check_permission(permissions, "nonexistent") is False
    
    def test_check_role_permission(self):
        """Test role-based permission checking."""
        user_role = "moderator"
        
        # User has required role
        assert self.auth_service.check_role_permission(
            user_role, ["admin", "moderator"]
        ) is True
        
        # User doesn't have required role
        assert self.auth_service.check_role_permission(
            user_role, ["admin"]
        ) is False
        
        # Empty required roles
        assert self.auth_service.check_role_permission(
            user_role, []
        ) is False
    
    @patch.dict(os.environ, {"JWT_SECRET_KEY": "test_secret_key"})
    def test_custom_secret_key(self):
        """Test using custom secret key from environment."""
        auth_service = AuthService()
        assert auth_service.secret_key == "test_secret_key"
    
    @patch.dict(os.environ, {"ACCESS_TOKEN_EXPIRE_MINUTES": "60"})
    def test_custom_token_expiry(self):
        """Test using custom token expiry from environment."""
        auth_service = AuthService()
        assert auth_service.access_token_expire_minutes == 60
    
    def test_generate_secret_key(self):
        """Test secret key generation."""
        key1 = self.auth_service._generate_secret_key()
        key2 = self.auth_service._generate_secret_key()
        
        assert len(key1) > 0
        assert len(key2) > 0
        assert key1 != key2  # Should be random