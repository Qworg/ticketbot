"""
Unit tests for JWT authentication module.
"""

import os
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.auth import (
    generate_token,
    validate_token,
    extract_claims,
    get_token_expiry,
    is_token_expired,
    JWTError,
    TokenExpiredError,
    TokenInvalidError,
    get_jwt_config
)


class TestJWTTokenGeneration:
    """Test JWT token generation functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        os.environ['JWT_SECRET_KEY'] = 'test-secret-key-for-testing'
    
    def test_generate_token_with_valid_data(self):
        """Test token generation with valid user data."""
        user_data = {
            'user_id': 'test-user-123',
            'discord_id': 123456789,
            'role': 'USER',
            'email': 'test@example.com'
        }
        
        token = generate_token(user_data)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Verify token can be decoded
        claims = extract_claims(token)
        assert claims['user_id'] == 'test-user-123'
        assert claims['discord_id'] == 123456789
        assert claims['role'] == 'USER'
        assert claims['email'] == 'test@example.com'
        assert 'iat' in claims
        assert 'exp' in claims
    
    def test_generate_token_without_email(self):
        """Test token generation without optional email field."""
        user_data = {
            'user_id': 'test-user-456',
            'discord_id': 987654321,
            'role': 'STAFF'
        }
        
        token = generate_token(user_data)
        claims = extract_claims(token)
        
        assert claims['user_id'] == 'test-user-456'
        assert claims['discord_id'] == 987654321
        assert claims['role'] == 'STAFF'
        assert 'email' not in claims
    
    def test_generate_token_missing_required_fields(self):
        """Test token generation fails with missing required fields."""
        # Missing user_id
        with pytest.raises(ValueError, match="Required field 'user_id' missing"):
            generate_token({'discord_id': 123, 'role': 'USER'})
        
        # Missing discord_id
        with pytest.raises(ValueError, match="Required field 'discord_id' missing"):
            generate_token({'user_id': 'test', 'role': 'USER'})
        
        # Missing role
        with pytest.raises(ValueError, match="Required field 'role' missing"):
            generate_token({'user_id': 'test', 'discord_id': 123})
    
    def test_token_expiration_time(self):
        """Test token has correct expiration time (24 hours)."""
        user_data = {
            'user_id': 'test-user',
            'discord_id': 123456,
            'role': 'USER'
        }
        
        before_generation = datetime.now(timezone.utc)
        token = generate_token(user_data)
        after_generation = datetime.now(timezone.utc)
        
        claims = extract_claims(token)
        issued_at = datetime.fromtimestamp(claims['iat'], tz=timezone.utc)
        expires_at = datetime.fromtimestamp(claims['exp'], tz=timezone.utc)
        
        # Check issued_at is within reasonable time window (allow 1 second tolerance)
        assert abs((issued_at - before_generation).total_seconds()) <= 1
        
        # Check expiration is 24 hours after issued_at
        expected_expiry = issued_at + timedelta(hours=24)
        assert abs((expires_at - expected_expiry).total_seconds()) < 5  # Allow 5 second tolerance


class TestJWTTokenValidation:
    """Test JWT token validation functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        os.environ['JWT_SECRET_KEY'] = 'test-secret-key-for-testing'
    
    def test_validate_valid_token(self):
        """Test validation of valid token."""
        user_data = {
            'user_id': 'test-user-789',
            'discord_id': 555666777,
            'role': 'ADMIN',
            'email': 'admin@example.com'
        }
        
        token = generate_token(user_data)
        token_data = validate_token(token)
        
        assert token_data.user_id == 'test-user-789'
        assert token_data.discord_id == 555666777
        assert token_data.role == 'ADMIN'
        assert token_data.email == 'admin@example.com'
        assert isinstance(token_data.issued_at, datetime)
        assert isinstance(token_data.expires_at, datetime)
    
    @patch('app.auth.datetime')
    def test_validate_expired_token(self, mock_datetime):
        """Test validation fails for expired token."""
        # Generate token
        user_data = {
            'user_id': 'test-user',
            'discord_id': 123456,
            'role': 'USER'
        }
        
        # Mock current time to generate token
        mock_now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.fromtimestamp = datetime.fromtimestamp
        
        token = generate_token(user_data)
        
        # Mock time to be after token expiration
        expired_time = mock_now + timedelta(hours=25)  # Token expires after 24 hours
        mock_datetime.now.return_value = expired_time
        
        with pytest.raises(TokenExpiredError, match="Token has expired"):
            validate_token(token)
    
    def test_validate_invalid_signature(self):
        """Test validation fails for token with invalid signature."""
        user_data = {
            'user_id': 'test-user',
            'discord_id': 123456,
            'role': 'USER'
        }
        
        token = generate_token(user_data)
        
        # Tamper with token by changing last character
        tampered_token = token[:-1] + ('a' if token[-1] != 'a' else 'b')
        
        with pytest.raises(TokenInvalidError, match="Invalid token"):
            validate_token(tampered_token)
    
    def test_validate_malformed_token(self):
        """Test validation fails for malformed token."""
        malformed_tokens = [
            "not.a.jwt",
            "",
            "invalid-token-format",
            "header.payload"  # Missing signature
        ]
        
        for token in malformed_tokens:
            with pytest.raises(TokenInvalidError):
                validate_token(token)


class TestJWTHelperFunctions:
    """Test JWT helper functions."""
    
    def setup_method(self):
        """Set up test environment."""
        os.environ['JWT_SECRET_KEY'] = 'test-secret-key-for-testing'
    
    def test_extract_claims(self):
        """Test extracting claims from token without validation."""
        user_data = {
            'user_id': 'claim-test-user',
            'discord_id': 999888777,
            'role': 'STAFF'
        }
        
        token = generate_token(user_data)
        claims = extract_claims(token)
        
        assert claims['user_id'] == 'claim-test-user'
        assert claims['discord_id'] == 999888777
        assert claims['role'] == 'STAFF'
        assert 'iat' in claims
        assert 'exp' in claims
    
    def test_get_token_expiry(self):
        """Test getting expiration time from token."""
        user_data = {
            'user_id': 'expiry-test-user',
            'discord_id': 111222333,
            'role': 'USER'
        }
        
        before_generation = datetime.now(timezone.utc)
        token = generate_token(user_data)
        
        expiry = get_token_expiry(token)
        expected_expiry = before_generation + timedelta(hours=24)
        
        # Allow 10 second tolerance for test execution time
        assert abs((expiry - expected_expiry).total_seconds()) < 10
    
    def test_is_token_expired_false(self):
        """Test is_token_expired returns False for valid token."""
        user_data = {
            'user_id': 'fresh-token-user',
            'discord_id': 444555666,
            'role': 'USER'
        }
        
        token = generate_token(user_data)
        assert not is_token_expired(token)
    
    @patch('app.auth.datetime')
    def test_is_token_expired_true(self, mock_datetime):
        """Test is_token_expired returns True for expired token."""
        user_data = {
            'user_id': 'expired-token-user',
            'discord_id': 777888999,
            'role': 'USER'
        }
        
        # Generate token at specific time
        mock_now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.fromtimestamp = datetime.fromtimestamp
        
        token = generate_token(user_data)
        
        # Check expiration after token has expired
        expired_time = mock_now + timedelta(hours=25)
        mock_datetime.now.return_value = expired_time
        
        assert is_token_expired(token)
    
    def test_is_token_expired_malformed(self):
        """Test is_token_expired returns True for malformed token."""
        assert is_token_expired("invalid-token")
        assert is_token_expired("")
        assert is_token_expired("not.a.jwt")


class TestJWTConfigError:
    """Test JWT configuration error handling."""
    
    def test_jwt_config_missing_secret_key(self):
        """Test JWT config raises error when secret key is missing."""
        # Remove JWT_SECRET_KEY from environment
        if 'JWT_SECRET_KEY' in os.environ:
            del os.environ['JWT_SECRET_KEY']
        
        with pytest.raises(ValueError, match="JWT_SECRET_KEY environment variable is required"):
            from app.auth import JWTConfig
            JWTConfig()
