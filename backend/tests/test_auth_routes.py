"""
Unit tests for authentication routes.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from backend.routes.auth import router
from backend.models import Staff, StaffRole
from backend.services.auth_service import auth_service


# Create test app
app = FastAPI()
app.include_router(router)
client = TestClient(app)


class TestAuthRoutes:
    """Test cases for authentication routes."""
    
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
    
    @patch('backend.routes.auth.get_db')
    @patch('backend.routes.auth.StaffRepository')
    def test_login_staff_existing_user(self, mock_staff_repo_class, mock_get_db):
        """Test staff login with existing user."""
        # Mock database and repository
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        mock_staff_repo = AsyncMock()
        mock_staff_repo_class.return_value = mock_staff_repo
        mock_staff_repo.get_by_discord_id.return_value = self.test_staff
        
        login_data = {
            "discord_id": 123456789,
            "username": "test_user"
        }
        
        response = client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        
        # Verify repository was called
        mock_staff_repo.get_by_discord_id.assert_called_once_with(123456789)
    
    @patch('backend.routes.auth.get_db')
    @patch('backend.routes.auth.StaffRepository')
    def test_login_staff_new_user(self, mock_staff_repo_class, mock_get_db):
        """Test staff login with new user creation."""
        # Mock database and repository
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        mock_staff_repo = AsyncMock()
        mock_staff_repo_class.return_value = mock_staff_repo
        mock_staff_repo.get_by_discord_id.return_value = None  # User doesn't exist
        mock_staff_repo.create.return_value = self.test_staff
        
        login_data = {
            "discord_id": 123456789,
            "username": "new_user"
        }
        
        response = client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        
        # Verify user creation was called
        mock_staff_repo.create.assert_called_once()
        create_args = mock_staff_repo.create.call_args[0][0]
        assert create_args["discord_id"] == 123456789
        assert create_args["username"] == "new_user"
        assert create_args["role"] == "support"
    
    @patch('backend.routes.auth.get_db')
    @patch('backend.routes.auth.StaffRepository')
    def test_login_staff_inactive_user(self, mock_staff_repo_class, mock_get_db):
        """Test staff login with inactive user."""
        # Mock database and repository
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        inactive_staff = Staff(
            id="123e4567-e89b-12d3-a456-426614174000",
            discord_id=123456789,
            username="inactive_user",
            role=StaffRole.SUPPORT.value,
            permissions={},
            active=False
        )
        
        mock_staff_repo = AsyncMock()
        mock_staff_repo_class.return_value = mock_staff_repo
        mock_staff_repo.get_by_discord_id.return_value = inactive_staff
        
        login_data = {
            "discord_id": 123456789,
            "username": "inactive_user"
        }
        
        response = client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 401
        assert "inactive" in response.json()["detail"].lower()
    
    @patch('backend.routes.auth.get_current_staff')
    def test_get_current_user(self, mock_get_current_staff):
        """Test getting current user information."""
        mock_get_current_staff.return_value = self.test_staff
        
        # Create a valid token
        token = auth_service.create_access_token(self.test_staff)
        headers = {"Authorization": f"Bearer {token.access_token}"}
        
        response = client.get("/api/auth/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["discord_id"] == self.test_staff.discord_id
        assert data["username"] == self.test_staff.username
        assert data["role"] == self.test_staff.role
    
    @patch('backend.routes.auth.get_current_staff')
    def test_create_api_key_admin(self, mock_get_current_staff):
        """Test API key creation by admin user."""
        mock_get_current_staff.return_value = self.admin_staff
        
        # Create a valid admin token
        token = auth_service.create_access_token(self.admin_staff)
        headers = {"Authorization": f"Bearer {token.access_token}"}
        
        api_key_data = {
            "name": "test_api_key",
            "permissions": {
                "view_tickets": True,
                "create_tickets": False
            }
        }
        
        response = client.post("/api/auth/api-keys", json=api_key_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "api_key" in data
        assert data["api_key"].startswith("tb_")
        assert data["name"] == "test_api_key"
        assert data["permissions"] == api_key_data["permissions"]
    
    @patch('backend.routes.auth.get_current_staff')
    def test_create_api_key_non_admin(self, mock_get_current_staff):
        """Test API key creation by non-admin user."""
        mock_get_current_staff.return_value = self.test_staff
        
        # Create a valid non-admin token
        token = auth_service.create_access_token(self.test_staff)
        headers = {"Authorization": f"Bearer {token.access_token}"}
        
        api_key_data = {
            "name": "test_api_key",
            "permissions": {"view_tickets": True}
        }
        
        response = client.post("/api/auth/api-keys", json=api_key_data, headers=headers)
        
        assert response.status_code == 403
        assert "admin" in response.json()["detail"].lower()
    
    @patch('backend.routes.auth.get_current_staff')
    def test_list_api_keys_admin(self, mock_get_current_staff):
        """Test API key listing by admin user."""
        mock_get_current_staff.return_value = self.admin_staff
        
        # Create some test API keys
        auth_service.create_api_key("key1", {"view_tickets": True})
        auth_service.create_api_key("key2", {"create_tickets": True})
        
        # Create a valid admin token
        token = auth_service.create_access_token(self.admin_staff)
        headers = {"Authorization": f"Bearer {token.access_token}"}
        
        response = client.get("/api/auth/api-keys", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        
        # Check that actual API keys are not returned
        for key_info in data:
            assert "api_key" not in key_info
            assert "key_id" in key_info
            assert "name" in key_info
            assert "permissions" in key_info
            assert "active" in key_info
    
    @patch('backend.routes.auth.get_current_staff')
    def test_list_api_keys_non_admin(self, mock_get_current_staff):
        """Test API key listing by non-admin user."""
        mock_get_current_staff.return_value = self.test_staff
        
        # Create a valid non-admin token
        token = auth_service.create_access_token(self.test_staff)
        headers = {"Authorization": f"Bearer {token.access_token}"}
        
        response = client.get("/api/auth/api-keys", headers=headers)
        
        assert response.status_code == 403
        assert "admin" in response.json()["detail"].lower()
    
    @patch('backend.routes.auth.get_current_staff')
    def test_revoke_api_key_admin(self, mock_get_current_staff):
        """Test API key revocation by admin user."""
        mock_get_current_staff.return_value = self.admin_staff
        
        # Create a test API key
        api_key, key_data = auth_service.create_api_key("test_key", {"view_tickets": True})
        
        # Create a valid admin token
        token = auth_service.create_access_token(self.admin_staff)
        headers = {"Authorization": f"Bearer {token.access_token}"}
        
        response = client.delete(f"/api/auth/api-keys/{key_data.key_id}", headers=headers)
        
        assert response.status_code == 200
        assert "revoked" in response.json()["message"].lower()
        
        # Verify key is revoked
        stored_keys = auth_service.list_api_keys()
        assert stored_keys[api_key].active is False
    
    @patch('backend.routes.auth.get_current_staff')
    def test_revoke_api_key_not_found(self, mock_get_current_staff):
        """Test API key revocation with non-existent key."""
        mock_get_current_staff.return_value = self.admin_staff
        
        # Create a valid admin token
        token = auth_service.create_access_token(self.admin_staff)
        headers = {"Authorization": f"Bearer {token.access_token}"}
        
        response = client.delete("/api/auth/api-keys/nonexistent", headers=headers)
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    @patch('backend.routes.auth.get_current_staff')
    def test_verify_token(self, mock_get_current_staff):
        """Test token verification endpoint."""
        mock_get_current_staff.return_value = self.test_staff
        
        # Create a valid token
        token = auth_service.create_access_token(self.test_staff)
        headers = {"Authorization": f"Bearer {token.access_token}"}
        
        response = client.post("/api/auth/verify-token", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["staff_id"] == str(self.test_staff.id)
        assert data["discord_id"] == self.test_staff.discord_id
        assert data["role"] == self.test_staff.role
    
    def test_verify_api_key(self):
        """Test API key verification endpoint."""
        # Create a test API key
        api_key, key_data = auth_service.create_api_key("test_key", {"view_tickets": True})
        headers = {"Authorization": f"Bearer {api_key}"}
        
        response = client.post("/api/auth/verify-api-key", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["key_id"] == key_data.key_id
        assert data["name"] == key_data.name
        assert data["permissions"] == key_data.permissions
    
    def test_unauthorized_access(self):
        """Test accessing protected endpoints without authentication."""
        # Test without any authorization header
        response = client.get("/api/auth/me")
        assert response.status_code == 403  # FastAPI HTTPBearer returns 403 for missing auth
        
        # Test with invalid token
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/auth/me", headers=headers)
        assert response.status_code == 401
    
    def teardown_method(self):
        """Clean up after each test."""
        # Clear API keys
        auth_service._api_keys.clear()