"""
Integration tests for authentication middleware with protected endpoints.
Tests complete authentication flow with FastAPI endpoints.
"""

import pytest
import uuid
from fastapi import FastAPI, Depends, HTTPException
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from app.middleware import get_current_user, require_authentication
from app.auth import generate_token, TokenData
from app.models.user import User


# Create test FastAPI app with protected endpoints
test_app = FastAPI()


@test_app.get("/public")
async def public_endpoint():
    """Public endpoint that doesn't require authentication."""
    return {"message": "public"}


@test_app.get("/protected")
async def protected_endpoint(user_info=Depends(require_authentication())):
    """Protected endpoint that requires authentication."""
    return {"message": "protected", "user_id": user_info["user_id"]}


@test_app.get("/user-info")
async def user_info_endpoint(user_info=Depends(get_current_user)):
    """Endpoint that uses the authentication middleware directly."""
    return {"authenticated": user_info.get("is_authenticated", False)}


class TestAuthenticationIntegration:
    """Integration tests for authentication middleware with FastAPI."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(test_app)
    
    @pytest.fixture
    def mock_user(self):
        """Create mock user for testing."""
        user = Mock(spec=User)
        user.id = uuid.uuid4()
        user.discord_id = 123456789
        user.role = "USER"
        user.email = "test@example.com"
        user.is_active = True
        return user
    
    @pytest.fixture
    def valid_token(self, mock_user):
        """Generate valid JWT token for testing."""
        user_data = {
            'user_id': str(mock_user.id),
            'discord_id': mock_user.discord_id,
            'role': mock_user.role,
            'email': mock_user.email
        }
        return generate_token(user_data)
    
    def test_public_endpoint_no_auth(self, client):
        """Test public endpoint access without authentication."""
        response = client.get("/public")
        assert response.status_code == 200
        assert response.json() == {"message": "public"}
    
    @patch('app.middleware.get_current_user')
    def test_protected_endpoint_no_auth(self, mock_get_current, client):
        """Test protected endpoint access without authentication."""
        mock_get_current.return_value = {"is_authenticated": False}
        
        response = client.get("/protected")
        assert response.status_code == 401
        assert "Authentication required" in response.json()["detail"]
    
    @patch('app.database.get_db')
    @patch('app.middleware.validate_token')
    def test_protected_endpoint_with_valid_auth(self, mock_validate, mock_get_db, client, valid_token, mock_user):
        """Test protected endpoint access with valid authentication."""
        # Setup mocks
        token_data = TokenData(
            user_id=str(mock_user.id),
            discord_id=mock_user.discord_id,
            role=mock_user.role,
            email=mock_user.email,
            issued_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc)
        )
        mock_validate.return_value = token_data
        
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        mock_get_db.return_value = mock_db
        
        headers = {"Authorization": f"Bearer {valid_token}"}
        response = client.get("/protected", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "protected"
        assert data["user_id"] == str(mock_user.id)
    
    @patch('app.database.get_db')
    @patch('app.middleware.validate_token')
    def test_protected_endpoint_with_invalid_token(self, mock_validate, mock_get_db, client):
        """Test protected endpoint access with invalid token."""
        from app.auth import TokenInvalidError
        mock_validate.side_effect = TokenInvalidError("Invalid token")
        
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        headers = {"Authorization": "Bearer invalid.token.here"}
        response = client.get("/protected", headers=headers)
        
        assert response.status_code == 401
        assert "Invalid or malformed token" in response.json()["detail"]
    
    @patch('app.database.get_db')
    @patch('app.middleware.validate_token')
    def test_protected_endpoint_with_expired_token(self, mock_validate, mock_get_db, client):
        """Test protected endpoint access with expired token."""
        from app.auth import TokenExpiredError
        mock_validate.side_effect = TokenExpiredError("Token has expired")
        
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        headers = {"Authorization": "Bearer expired.token.here"}
        response = client.get("/protected", headers=headers)
        
        assert response.status_code == 401
        assert "Token has expired" in response.json()["detail"]
    
    def test_missing_authorization_header(self, client):
        """Test protected endpoint access without Authorization header."""
        response = client.get("/protected")
        assert response.status_code == 401
        assert "Authorization header required" in response.json()["detail"]
    
    @patch('app.database.get_db')
    @patch('app.middleware.validate_token')
    def test_user_not_found_in_database(self, mock_validate, mock_get_db, client, valid_token, mock_user):
        """Test authentication failure when user not found in database."""
        token_data = TokenData(
            user_id=str(mock_user.id),
            discord_id=mock_user.discord_id,
            role=mock_user.role,
            email=mock_user.email,
            issued_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc)
        )
        mock_validate.return_value = token_data
        
        # User not found in database
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_get_db.return_value = mock_db
        
        headers = {"Authorization": f"Bearer {valid_token}"}
        response = client.get("/protected", headers=headers)
        
        assert response.status_code == 401
        assert "User not found" in response.json()["detail"]
    
    @patch('app.middleware.redis_client')
    @patch('app.database.get_db')
    def test_rate_limiting_integration(self, mock_get_db, mock_redis, client):
        """Test rate limiting integration with protected endpoints."""
        # Simulate rate limit exceeded
        mock_redis.get.return_value = "15"  # Over the limit
        
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        headers = {"Authorization": "Bearer some.token.here"}
        response = client.get("/protected", headers=headers)
        
        assert response.status_code == 429
        assert "Too many failed authentication attempts" in response.json()["detail"]
    
    @patch('app.database.get_db')
    @patch('app.middleware.validate_token')
    def test_user_info_endpoint_authenticated(self, mock_validate, mock_get_db, client, valid_token, mock_user):
        """Test user info endpoint with authenticated user."""
        token_data = TokenData(
            user_id=str(mock_user.id),
            discord_id=mock_user.discord_id,
            role=mock_user.role,
            email=mock_user.email,
            issued_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc)
        )
        mock_validate.return_value = token_data
        
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        mock_get_db.return_value = mock_db
        
        headers = {"Authorization": f"Bearer {valid_token}"}
        response = client.get("/user-info", headers=headers)
        
        assert response.status_code == 200
        assert response.json()["authenticated"] is True
    
    def test_user_info_endpoint_unauthenticated(self, client):
        """Test user info endpoint without authentication."""
        response = client.get("/user-info")
        
        assert response.status_code == 401
        assert "Authorization header required" in response.json()["detail"]
    
    @patch('app.database.get_db')
    @patch('app.middleware.validate_token')
    def test_multiple_requests_same_token(self, mock_validate, mock_get_db, client, valid_token, mock_user):
        """Test multiple requests with the same valid token."""
        token_data = TokenData(
            user_id=str(mock_user.id),
            discord_id=mock_user.discord_id,
            role=mock_user.role,
            email=mock_user.email,
            issued_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc)
        )
        mock_validate.return_value = token_data
        
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        mock_get_db.return_value = mock_db
        
        headers = {"Authorization": f"Bearer {valid_token}"}
        
        # First request
        response1 = client.get("/protected", headers=headers)
        assert response1.status_code == 200
        
        # Second request with same token
        response2 = client.get("/protected", headers=headers)
        assert response2.status_code == 200
        
        # Verify token was validated for both requests
        assert mock_validate.call_count == 2
    
    @patch('app.database.get_db')
    def test_malformed_authorization_header(self, mock_get_db, client):
        """Test request with malformed Authorization header."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        # Missing Bearer prefix
        headers = {"Authorization": "invalid-format-token"}
        response = client.get("/protected", headers=headers)
        
        assert response.status_code == 401
