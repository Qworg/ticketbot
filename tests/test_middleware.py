"""
Unit tests for authentication middleware.
Tests JWT token extraction, validation, and user authentication flow.
"""

import pytest
import uuid
import os
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials

# Set JWT secret for testing
os.environ['JWT_SECRET_KEY'] = 'test-secret-key-for-testing-only'

from app.middleware import (
    get_current_user, 
    get_optional_user, 
    require_authentication,
    get_user_from_cookie,
    AuthenticationMiddleware,
    PUBLIC_ENDPOINTS
)
from app.auth import TokenData, TokenExpiredError, TokenInvalidError
from app.models.user import User
from datetime import datetime, timezone


class TestAuthenticationMiddleware:
    """Test suite for authentication middleware functions."""
    
    @pytest.fixture
    def mock_request(self):
        """Create mock FastAPI request."""
        request = Mock(spec=Request)
        request.url.path = "/api/test"
        request.client.host = "127.0.0.1"
        request.headers = {"user-agent": "test-client"}
        return request
    
    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        db = Mock()
        return db
    
    @pytest.fixture
    def mock_user(self):
        """Create mock user object."""
        user = Mock(spec=User)
        user.id = uuid.uuid4()
        user.discord_id = 123456789
        user.role = "USER"
        user.email = "test@example.com"
        user.is_active = True
        return user
    
    @pytest.fixture
    def mock_token_data(self):
        """Create mock token data."""
        return TokenData(
            user_id=str(uuid.uuid4()),
            discord_id=123456789,
            role="USER",
            email="test@example.com",
            issued_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc)
        )
    
    @pytest.fixture
    def mock_credentials(self):
        """Create mock HTTP authorization credentials."""
        return HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="valid.jwt.token"
        )
    
    def test_public_endpoint_bypass(self, mock_request, mock_db_session):
        """Test that public endpoints bypass authentication."""
        mock_request.url.path = "/"
        
        result = get_current_user(mock_request, None, mock_db_session)
        
        assert result == {"is_authenticated": False}
    
    @patch('app.middleware.validate_token')
    def test_missing_authorization_header(self, mock_validate, mock_request, mock_db_session):
        """Test authentication failure with missing authorization header."""
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(mock_request, None, mock_db_session)
        
        assert exc_info.value.status_code == 401
        assert "Authorization header required" in exc_info.value.detail
    
    @patch('app.middleware.validate_token')
    def test_valid_token_authentication(self, mock_validate, mock_request, mock_db_session, 
                                      mock_credentials, mock_token_data, mock_user):
        """Test successful authentication with valid token."""
        # Setup mocks
        mock_validate.return_value = mock_token_data
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
        
        result = get_current_user(mock_request, mock_credentials, mock_db_session)
        
        assert result["is_authenticated"] is True
        assert result["user_id"] == mock_token_data.user_id
        assert result["user"] == mock_user
        assert result["role"] == "USER"
        assert result["discord_id"] == mock_user.discord_id
        
        # Verify token validation was called
        mock_validate.assert_called_once_with("valid.jwt.token")
    
    @patch('app.middleware.validate_token')
    def test_expired_token_rejection(self, mock_validate, mock_request, mock_db_session, mock_credentials):
        """Test authentication failure with expired token."""
        mock_validate.side_effect = TokenExpiredError("Token has expired")
        
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(mock_request, mock_credentials, mock_db_session)
        
        assert exc_info.value.status_code == 401
        assert "Token has expired" in exc_info.value.detail
    
    @patch('app.middleware.validate_token')
    def test_invalid_token_rejection(self, mock_validate, mock_request, mock_db_session, mock_credentials):
        """Test authentication failure with malformed token."""
        mock_validate.side_effect = TokenInvalidError("Invalid token signature")
        
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(mock_request, mock_credentials, mock_db_session)
        
        assert exc_info.value.status_code == 401
        assert "Invalid or malformed token" in exc_info.value.detail
    
    @patch('app.middleware.validate_token')
    def test_user_not_found_in_database(self, mock_validate, mock_request, mock_db_session, 
                                       mock_credentials, mock_token_data):
        """Test authentication failure when user not found in database."""
        mock_validate.return_value = mock_token_data
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(mock_request, mock_credentials, mock_db_session)
        
        assert exc_info.value.status_code == 401
        assert "User not found" in exc_info.value.detail
    
    @patch('app.middleware.validate_token')
    def test_inactive_user_rejection(self, mock_validate, mock_request, mock_db_session, 
                                   mock_credentials, mock_token_data, mock_user):
        """Test authentication failure for inactive user account."""
        mock_user.is_active = False
        mock_validate.return_value = mock_token_data
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
        
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(mock_request, mock_credentials, mock_db_session)
        
        assert exc_info.value.status_code == 401
        assert "User account is inactive" in exc_info.value.detail
    
    @patch('app.middleware.get_current_user')
    def test_optional_user_success(self, mock_get_current, mock_request, mock_db_session, mock_credentials):
        """Test optional authentication with valid user."""
        mock_get_current.return_value = {"is_authenticated": True, "user_id": "123"}
        
        result = get_optional_user(mock_request, mock_credentials, mock_db_session)
        
        assert result == {"is_authenticated": True, "user_id": "123"}
    
    @patch('app.middleware.get_current_user')
    def test_optional_user_failure(self, mock_get_current, mock_request, mock_db_session, mock_credentials):
        """Test optional authentication with invalid credentials."""
        mock_get_current.side_effect = HTTPException(status_code=401)
        
        result = get_optional_user(mock_request, mock_credentials, mock_db_session)
        
        assert result is None
    
    @patch('app.middleware.validate_token')
    def test_cookie_authentication_success(self, mock_validate, mock_request, mock_db_session, 
                                         mock_token_data, mock_user):
        """Test successful authentication via HTTP cookie."""
        mock_request.cookies = {"auth_token": "valid.jwt.token"}
        mock_validate.return_value = mock_token_data
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
        
        result = get_user_from_cookie(mock_request, mock_db_session)
        
        assert result is not None
        assert result["is_authenticated"] is True
        assert result["user"] == mock_user
    
    def test_cookie_authentication_no_cookie(self, mock_request, mock_db_session):
        """Test cookie authentication with no auth cookie."""
        mock_request.cookies = {}
        
        result = get_user_from_cookie(mock_request, mock_db_session)
        
        assert result is None
    
    @patch('app.middleware.redis_client')
    def test_rate_limiting_check(self, mock_redis):
        """Test rate limiting functionality."""
        middleware = AuthenticationMiddleware()
        
        # Test normal case (under limit)
        mock_redis.get.return_value = "5"
        result = middleware._check_rate_limit("127.0.0.1")
        assert result is True
        
        # Test rate limit exceeded
        mock_redis.get.return_value = "15"
        result = middleware._check_rate_limit("127.0.0.1")
        assert result is False
    
    @patch('app.middleware.redis_client')
    def test_rate_limiting_increment(self, mock_redis):
        """Test rate limiting increment functionality."""
        middleware = AuthenticationMiddleware()
        
        # Test increment existing counter
        mock_redis.get.return_value = "3"
        middleware._increment_failed_attempts("127.0.0.1")
        mock_redis.incr.assert_called_once()
        
        # Test set new counter
        mock_redis.get.return_value = None
        mock_redis.incr.reset_mock()
        middleware._increment_failed_attempts("127.0.0.1")
        mock_redis.setex.assert_called_once()
    
    @patch('app.middleware.redis_client', None)
    def test_rate_limiting_redis_unavailable(self):
        """Test rate limiting when Redis is unavailable."""
        middleware = AuthenticationMiddleware()
        
        # Should return True (allow) when Redis is unavailable
        result = middleware._check_rate_limit("127.0.0.1")
        assert result is True
        
        # Should not raise exception when incrementing
        middleware._increment_failed_attempts("127.0.0.1")  # Should not raise
    
    def test_public_endpoints_list(self):
        """Test that public endpoints are properly defined."""
        assert "/" in PUBLIC_ENDPOINTS
        assert "/health" in PUBLIC_ENDPOINTS
        assert "/auth/discord/login" in PUBLIC_ENDPOINTS
        assert "/auth/discord/callback" in PUBLIC_ENDPOINTS
    
    def test_require_authentication_dependency(self):
        """Test the require_authentication dependency factory."""
        dependency = require_authentication()
        
        # Test with authenticated user
        user_info = {"is_authenticated": True, "user_id": "123"}
        result = dependency(user_info)
        assert result == user_info
        
        # Test with unauthenticated user
        user_info = {"is_authenticated": False}
        with pytest.raises(HTTPException) as exc_info:
            dependency(user_info)
        assert exc_info.value.status_code == 401
