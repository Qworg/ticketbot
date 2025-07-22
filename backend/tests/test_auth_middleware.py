"""
Unit tests for authentication middleware.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import FastAPI, Depends, HTTPException
from fastapi.testclient import TestClient
from fastapi.security import HTTPAuthorizationCredentials

from backend.middleware.auth_middleware import (
    get_current_staff, get_current_api_key, get_current_user,
    require_permissions, require_roles, require_ticket_access,
    AuthenticationError, AuthorizationError,
    require_admin, require_moderator_or_admin, require_staff,
    require_view_tickets, require_create_tickets, require_update_tickets,
    require_close_tickets, require_view_transcripts, require_manage_staff
)
from backend.models import Staff, StaffRole
from backend.services.auth_service import auth_service, APIKeyData


# Helper function to run async functions in tests
async def run_async(coro):
    return await coro


class TestAuthMiddleware:
    """Test cases for authentication middleware."""
    
    def setup_method(self):
        """Set up test fixtures."""
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
        
        self.admin_staff = Staff(
            id="123e4567-e89b-12d3-a456-426614174001",
            discord_id=987654321,
            username="admin_user",
            role=StaffRole.ADMIN.value,
            permissions={
                "view_tickets": True,
                "create_tickets": True,
                "update_tickets": True,
                "close_tickets": True,
                "manage_staff": True
            },
            active=True
        )
        
        self.api_key_data = APIKeyData(
            key_id="test_key_id",
            name="test_api_key",
            permissions={
                "view_tickets": True,
                "create_tickets": False
            },
            active=True
        )
        
        # Create test app with endpoints using the middleware
        self.app = FastAPI()
        
        @self.app.get("/staff-only")
        async def staff_only(staff: Staff = Depends(get_current_staff)):
            return {"staff_id": str(staff.id)}
        
        @self.app.get("/api-key-only")
        async def api_key_only(api_key: APIKeyData = Depends(get_current_api_key)):
            return {"key_id": api_key.key_id}
        
        @self.app.get("/any-auth")
        async def any_auth(user = Depends(get_current_user)):
            if isinstance(user, Staff):
                return {"type": "staff", "id": str(user.id)}
            else:
                return {"type": "api_key", "id": user.key_id}
        
        @self.app.get("/require-view-tickets")
        async def require_view_tickets_endpoint(
            user = Depends(require_permissions(["view_tickets"]))
        ):
            return {"has_permission": True}
        
        @self.app.get("/require-admin")
        async def require_admin_endpoint(staff: Staff = Depends(require_roles(["admin"]))):
            return {"is_admin": True}
        
        @self.app.get("/tickets/{ticket_id}")
        async def ticket_access(
            ticket_id: str,
            user = Depends(require_ticket_access())
        ):
            return {"ticket_id": ticket_id, "access": True}
        
        self.client = TestClient(self.app)
    
    @pytest.mark.asyncio
    @patch('backend.middleware.auth_middleware.auth_service.verify_token')
    @patch('backend.middleware.auth_middleware.StaffRepository')
    async def test_get_current_staff_valid(self, mock_staff_repo_class, mock_verify_token):
        """Test get_current_staff with valid token."""
        # Mock token verification
        token_data = MagicMock()
        token_data.discord_id = 123456789
        mock_verify_token.return_value = token_data
        
        # Mock staff repository
        mock_staff_repo = AsyncMock()
        mock_staff_repo_class.return_value = mock_staff_repo
        mock_staff_repo.get_by_discord_id.return_value = self.test_staff
        
        # Mock database session
        mock_db = MagicMock()
        
        # Create credentials
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", 
            credentials="valid_token"
        )
        
        # Call the dependency
        staff = await get_current_staff(credentials, mock_db)
        
        # Verify results
        assert staff == self.test_staff
        mock_verify_token.assert_called_once_with("valid_token")
        mock_staff_repo.get_by_discord_id.assert_called_once_with(123456789)
    
    @pytest.mark.asyncio
    @patch('backend.middleware.auth_middleware.auth_service.verify_token')
    @patch('backend.middleware.auth_middleware.StaffRepository')
    async def test_get_current_staff_invalid_token(self, mock_staff_repo_class, mock_verify_token):
        """Test get_current_staff with invalid token."""
        # Mock token verification to raise exception
        mock_verify_token.side_effect = HTTPException(
            status_code=401, 
            detail="Invalid token"
        )
        
        # Mock database session
        mock_db = MagicMock()
        
        # Create credentials
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", 
            credentials="invalid_token"
        )
        
        # Call the dependency and expect exception
        with pytest.raises(AuthenticationError) as exc_info:
            await get_current_staff(credentials, mock_db)
        
        assert "Invalid or expired token" in str(exc_info.value.detail)
        mock_verify_token.assert_called_once_with("invalid_token")
        mock_staff_repo_class.assert_not_called()
    
    @pytest.mark.asyncio
    @patch('backend.middleware.auth_middleware.auth_service.verify_token')
    @patch('backend.middleware.auth_middleware.StaffRepository')
    async def test_get_current_staff_not_found(self, mock_staff_repo_class, mock_verify_token):
        """Test get_current_staff with staff not found."""
        # Mock token verification
        token_data = MagicMock()
        token_data.discord_id = 123456789
        mock_verify_token.return_value = token_data
        
        # Mock staff repository to return None
        mock_staff_repo = AsyncMock()
        mock_staff_repo_class.return_value = mock_staff_repo
        mock_staff_repo.get_by_discord_id.return_value = None
        
        # Mock database session
        mock_db = MagicMock()
        
        # Create credentials
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", 
            credentials="valid_token"
        )
        
        # Call the dependency and expect exception
        with pytest.raises(AuthenticationError) as exc_info:
            await get_current_staff(credentials, mock_db)
        
        assert "Staff member not found" in str(exc_info.value.detail)
        mock_verify_token.assert_called_once_with("valid_token")
        mock_staff_repo.get_by_discord_id.assert_called_once_with(123456789)
    
    @pytest.mark.asyncio
    @patch('backend.middleware.auth_middleware.auth_service.verify_token')
    @patch('backend.middleware.auth_middleware.StaffRepository')
    async def test_get_current_staff_inactive(self, mock_staff_repo_class, mock_verify_token):
        """Test get_current_staff with inactive staff."""
        # Mock token verification
        token_data = MagicMock()
        token_data.discord_id = 123456789
        mock_verify_token.return_value = token_data
        
        # Create inactive staff
        inactive_staff = Staff(
            id="123e4567-e89b-12d3-a456-426614174000",
            discord_id=123456789,
            username="inactive_user",
            role=StaffRole.SUPPORT.value,
            permissions={},
            active=False
        )
        
        # Mock staff repository
        mock_staff_repo = AsyncMock()
        mock_staff_repo_class.return_value = mock_staff_repo
        mock_staff_repo.get_by_discord_id.return_value = inactive_staff
        
        # Mock database session
        mock_db = MagicMock()
        
        # Create credentials
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", 
            credentials="valid_token"
        )
        
        # Call the dependency and expect exception
        with pytest.raises(AuthenticationError) as exc_info:
            await get_current_staff(credentials, mock_db)
        
        assert "Staff member is inactive" in str(exc_info.value.detail)
        mock_verify_token.assert_called_once_with("valid_token")
        mock_staff_repo.get_by_discord_id.assert_called_once_with(123456789)
    
    @pytest.mark.asyncio
    @patch('backend.middleware.auth_middleware.auth_service.verify_api_key')
    async def test_get_current_api_key_valid(self, mock_verify_api_key):
        """Test get_current_api_key with valid API key."""
        # Mock API key verification
        mock_verify_api_key.return_value = self.api_key_data
        
        # Create credentials
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", 
            credentials="valid_api_key"
        )
        
        # Call the dependency
        api_key_result = await get_current_api_key(credentials)
        
        # Verify results
        assert api_key_result == self.api_key_data
        mock_verify_api_key.assert_called_once_with("valid_api_key")
    
    @pytest.mark.asyncio
    @patch('backend.middleware.auth_middleware.auth_service.verify_api_key')
    async def test_get_current_api_key_invalid(self, mock_verify_api_key):
        """Test get_current_api_key with invalid API key."""
        # Mock API key verification to raise exception
        mock_verify_api_key.side_effect = HTTPException(
            status_code=401, 
            detail="Invalid API key"
        )
        
        # Create credentials
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", 
            credentials="invalid_api_key"
        )
        
        # Call the dependency and expect exception
        with pytest.raises(AuthenticationError) as exc_info:
            await get_current_api_key(credentials)
        
        assert "Invalid or inactive API key" in str(exc_info.value.detail)
        mock_verify_api_key.assert_called_once_with("invalid_api_key")
    
    @pytest.mark.asyncio
    @patch('backend.middleware.auth_middleware.get_current_staff')
    @patch('backend.middleware.auth_middleware.get_current_api_key')
    async def test_get_current_user_staff(self, mock_get_api_key, mock_get_staff):
        """Test get_current_user with staff token."""
        # Mock staff authentication
        mock_get_staff.return_value = self.test_staff
        
        # Create credentials
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", 
            credentials="valid_token"
        )
        
        # Mock database session
        mock_db = MagicMock()
        
        # Call the dependency
        user_result = await get_current_user(credentials, mock_db)
        
        # Verify results
        assert user_result == self.test_staff
        mock_get_staff.assert_called_once()
        mock_get_api_key.assert_not_called()
    
    @pytest.mark.asyncio
    @patch('backend.middleware.auth_middleware.get_current_staff')
    @patch('backend.middleware.auth_middleware.get_current_api_key')
    async def test_get_current_user_api_key(self, mock_get_api_key, mock_get_staff):
        """Test get_current_user with API key."""
        # Mock staff authentication to fail
        mock_get_staff.side_effect = AuthenticationError("Invalid token")
        
        # Mock API key authentication
        mock_get_api_key.return_value = self.api_key_data
        
        # Create credentials
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", 
            credentials="valid_api_key"
        )
        
        # Mock database session
        mock_db = MagicMock()
        
        # Call the dependency
        user_result = await get_current_user(credentials, mock_db)
        
        # Verify results
        assert user_result == self.api_key_data
        mock_get_staff.assert_called_once()
        mock_get_api_key.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('backend.middleware.auth_middleware.get_current_staff')
    @patch('backend.middleware.auth_middleware.get_current_api_key')
    async def test_get_current_user_both_fail(self, mock_get_api_key, mock_get_staff):
        """Test get_current_user with both authentication methods failing."""
        # Mock both authentication methods to fail
        mock_get_staff.side_effect = AuthenticationError("Invalid token")
        mock_get_api_key.side_effect = AuthenticationError("Invalid API key")
        
        # Create credentials
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", 
            credentials="invalid_credentials"
        )
        
        # Mock database session
        mock_db = MagicMock()
        
        # Call the dependency and expect exception
        with pytest.raises(AuthenticationError) as exc_info:
            await get_current_user(credentials, mock_db)
        
        assert "Invalid authentication credentials" in str(exc_info.value.detail)
        mock_get_staff.assert_called_once()
        mock_get_api_key.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_require_permissions_staff_has_permission(self):
        """Test require_permissions with staff having required permission."""
        # Create dependency
        check_permissions = require_permissions(["view_tickets"])
        
        # Call the dependency with staff having permission
        staff_result = await check_permissions(self.test_staff)
        
        # Verify results
        assert staff_result == self.test_staff
    
    @pytest.mark.asyncio
    async def test_require_permissions_staff_missing_permission(self):
        """Test require_permissions with staff missing required permission."""
        # Create dependency
        check_permissions = require_permissions(["update_tickets"])
        
        # Call the dependency with staff missing permission
        with pytest.raises(AuthorizationError) as exc_info:
            await check_permissions(self.test_staff)
        
        assert "Missing required permissions: update_tickets" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_require_permissions_api_key_has_permission(self):
        """Test require_permissions with API key having required permission."""
        # Create dependency
        check_permissions = require_permissions(["view_tickets"])
        
        # Call the dependency with API key having permission
        api_key_result = await check_permissions(self.api_key_data)
        
        # Verify results
        assert api_key_result == self.api_key_data
    
    @pytest.mark.asyncio
    async def test_require_permissions_api_key_missing_permission(self):
        """Test require_permissions with API key missing required permission."""
        # Create dependency
        check_permissions = require_permissions(["create_tickets"])
        
        # Call the dependency with API key missing permission
        with pytest.raises(AuthorizationError) as exc_info:
            await check_permissions(self.api_key_data)
        
        assert "Missing required permissions: create_tickets" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_require_roles_has_role(self):
        """Test require_roles with staff having required role."""
        # Create dependency
        check_roles = require_roles(["admin"])
        
        # Call the dependency with admin staff
        staff_result = await check_roles(self.admin_staff)
        
        # Verify results
        assert staff_result == self.admin_staff
    
    @pytest.mark.asyncio
    async def test_require_roles_missing_role(self):
        """Test require_roles with staff missing required role."""
        # Create dependency
        check_roles = require_roles(["admin"])
        
        # Call the dependency with non-admin staff
        with pytest.raises(AuthorizationError) as exc_info:
            await check_roles(self.test_staff)
        
        assert "Required role: admin" in str(exc_info.value.detail)
        assert "current role: support" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_require_roles_multiple_roles(self):
        """Test require_roles with multiple allowed roles."""
        # Create dependency
        check_roles = require_roles(["admin", "moderator", "support"])
        
        # Call the dependency with support staff
        staff_result = await check_roles(self.test_staff)
        
        # Verify results
        assert staff_result == self.test_staff
    
    @pytest.mark.asyncio
    @patch('backend.middleware.auth_middleware.get_current_user')
    async def test_require_ticket_access_staff_with_permission(self, mock_get_current_user):
        """Test require_ticket_access with staff having view_tickets permission."""
        # Mock current user
        mock_get_current_user.return_value = self.test_staff
        
        # Create mock request with path parameters
        mock_request = MagicMock()
        mock_request.path_params = {"ticket_id": "test-ticket-id"}
        
        # Mock database session
        mock_db = MagicMock()
        
        # Create dependency
        check_ticket_access = require_ticket_access()
        
        # Call the dependency
        access_result = await check_ticket_access(mock_request, self.test_staff, mock_db)
        
        # Verify results
        assert access_result == self.test_staff
    
    @pytest.mark.asyncio
    @patch('backend.middleware.auth_middleware.get_current_user')
    async def test_require_ticket_access_staff_without_permission(self, mock_get_current_user):
        """Test require_ticket_access with staff missing view_tickets permission."""
        # Create staff without view_tickets permission
        staff_without_permission = Staff(
            id="123e4567-e89b-12d3-a456-426614174002",
            discord_id=111222333,
            username="limited_user",
            role=StaffRole.SUPPORT.value,
            permissions={
                "view_tickets": False,
                "create_tickets": True
            },
            active=True
        )
        
        # Mock current user
        mock_get_current_user.return_value = staff_without_permission
        
        # Create mock request with path parameters
        mock_request = MagicMock()
        mock_request.path_params = {"ticket_id": "test-ticket-id"}
        
        # Mock database session
        mock_db = MagicMock()
        
        # Create dependency
        check_ticket_access = require_ticket_access()
        
        # Call the dependency and expect exception
        with pytest.raises(AuthorizationError) as exc_info:
            await check_ticket_access(mock_request, staff_without_permission, mock_db)
        
        assert "No permission to view tickets" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    @patch('backend.middleware.auth_middleware.get_current_user')
    async def test_require_ticket_access_api_key_with_permission(self, mock_get_current_user):
        """Test require_ticket_access with API key having view_tickets permission."""
        # Mock current user
        mock_get_current_user.return_value = self.api_key_data
        
        # Create mock request with path parameters
        mock_request = MagicMock()
        mock_request.path_params = {"ticket_id": "test-ticket-id"}
        
        # Mock database session
        mock_db = MagicMock()
        
        # Create dependency
        check_ticket_access = require_ticket_access()
        
        # Call the dependency
        access_result = await check_ticket_access(mock_request, self.api_key_data, mock_db)
        
        # Verify results
        assert access_result == self.api_key_data
    
    @pytest.mark.asyncio
    @patch('backend.middleware.auth_middleware.get_current_user')
    async def test_require_ticket_access_api_key_without_permission(self, mock_get_current_user):
        """Test require_ticket_access with API key missing view_tickets permission."""
        # Create API key without view_tickets permission
        api_key_without_permission = APIKeyData(
            key_id="limited_key_id",
            name="limited_api_key",
            permissions={
                "view_tickets": False,
                "create_tickets": True
            },
            active=True
        )
        
        # Mock current user
        mock_get_current_user.return_value = api_key_without_permission
        
        # Create mock request with path parameters
        mock_request = MagicMock()
        mock_request.path_params = {"ticket_id": "test-ticket-id"}
        
        # Mock database session
        mock_db = MagicMock()
        
        # Create dependency
        check_ticket_access = require_ticket_access()
        
        # Call the dependency and expect exception
        with pytest.raises(AuthorizationError) as exc_info:
            await check_ticket_access(mock_request, api_key_without_permission, mock_db)
        
        assert "API key lacks ticket access permission" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    @patch('backend.middleware.auth_middleware.get_current_user')
    async def test_require_ticket_access_missing_ticket_id(self, mock_get_current_user):
        """Test require_ticket_access with missing ticket_id parameter."""
        # Mock current user
        mock_get_current_user.return_value = self.test_staff
        
        # Create mock request with empty path parameters
        mock_request = MagicMock()
        mock_request.path_params = {}
        
        # Mock database session
        mock_db = MagicMock()
        
        # Create dependency
        check_ticket_access = require_ticket_access()
        
        # Call the dependency and expect exception
        with pytest.raises(AuthorizationError) as exc_info:
            await check_ticket_access(mock_request, self.test_staff, mock_db)
        
        assert "Ticket ID not found in request" in str(exc_info.value.detail)
    
    def test_convenience_dependencies(self):
        """Test that convenience dependencies are correctly defined."""
        # Test require_admin
        assert require_admin.__name__ == require_roles(["admin"]).__name__
        
        # Test require_moderator_or_admin
        assert require_moderator_or_admin.__name__ == require_roles(["moderator", "admin"]).__name__
        
        # Test require_staff
        assert require_staff.__name__ == require_roles(["support", "moderator", "admin"]).__name__
        
        # Test require_view_tickets
        assert require_view_tickets.__name__ == require_permissions(["view_tickets"]).__name__
        
        # Test require_create_tickets
        assert require_create_tickets.__name__ == require_permissions(["create_tickets"]).__name__
        
        # Test require_update_tickets
        assert require_update_tickets.__name__ == require_permissions(["update_tickets"]).__name__
        
        # Test require_close_tickets
        assert require_close_tickets.__name__ == require_permissions(["close_tickets"]).__name__
        
        # Test require_view_transcripts
        assert require_view_transcripts.__name__ == require_permissions(["view_transcripts"]).__name__
        
        # Test require_manage_staff
        assert require_manage_staff.__name__ == require_permissions(["manage_staff"]).__name__