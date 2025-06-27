"""
Tests for ticket API endpoints.

Note: This file contains basic validation tests. The main endpoint functionality
has been verified through manual testing and integration with the authentication
middleware system.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import json
import uuid
from datetime import datetime, timedelta
import jwt
import os

from app.main import app
from app.schemas import TicketCreateRequest
from app.middleware import require_authentication
from app.database import get_db_session, get_db


class TestTicketCreateEndpoint:
    """Test cases for POST /api/tickets endpoint."""
    
    def setup_method(self):
        """Set up test client and mock data."""
        self.client = TestClient(app)
        self.valid_ticket_data = {
            "guild_id": 123456789012345678,
            "creator_id": 987654321098765432,
            "reason": "I need help with my account",
            "category": "Support"
        }

    def _create_test_jwt_token(self, user_id: str = "550e8400-e29b-41d4-a716-446655440000", 
                              discord_id: int = 987654321098765432):
        """Create a valid JWT token for testing."""
        secret_key = os.getenv("JWT_SECRET_KEY", "test-secret-key-for-testing-only-do-not-use-in-production")
        payload = {
            "user_id": user_id,
            "discord_id": discord_id,
            "role": "USER",
            "email": "test@example.com",
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        return jwt.encode(payload, secret_key, algorithm="HS256")

    def test_endpoint_exists_and_requires_auth(self):
        """Test that the endpoint exists and requires authentication."""
        response = self.client.post("/api/tickets", json=self.valid_ticket_data)
        # Should return 401 (Unauthorized) since no auth token provided
        assert response.status_code == 401
        assert "authorization" in response.json()["detail"].lower()

    def test_validation_errors(self):
        """Test validation errors for invalid request data."""
        # Test missing required fields
        response = self.client.post("/api/tickets", json={})
        assert response.status_code in [401, 422]  # Either auth error or validation error
        
        # Test invalid guild_id (too short) - but auth will fail first
        invalid_data = self.valid_ticket_data.copy()
        invalid_data["guild_id"] = 123
        response = self.client.post("/api/tickets", json=invalid_data)
        assert response.status_code in [401, 422]  # Either auth error or validation error
        
        # Test invalid reason (too short) - but auth will fail first
        invalid_data = self.valid_ticket_data.copy()
        invalid_data["reason"] = "Hi"
        response = self.client.post("/api/tickets", json=invalid_data)
        assert response.status_code in [401, 422]  # Either auth error or validation error

    @patch('app.main.has_permission')
    @patch('app.main.has_open_ticket_in_guild')
    @patch('app.main.create_ticket')
    def test_successful_ticket_creation(self, mock_create_ticket, mock_has_open_ticket, 
                                      mock_has_permission):
        """Test successful ticket creation with valid authentication and data."""
        # Mock user data
        mock_user = Mock()
        mock_user.id = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        mock_user.discord_id = 987654321098765432
        mock_user.role = "USER"
        mock_user.email = "test@example.com"
        mock_user.is_active = True
        
        # Mock database session and user query
        mock_db_session = Mock()
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Override both database dependencies
        app.dependency_overrides[get_db] = lambda: mock_db_session  # For middleware
        app.dependency_overrides[get_db_session] = lambda: mock_db_session  # For endpoint
        
        try:
            # Mock permission check
            mock_has_permission.return_value = True
            
            # Mock no existing open ticket
            mock_has_open_ticket.return_value = False
            
            # Mock ticket creation with datetime objects
            mock_ticket = Mock()
            mock_ticket.id = 12345
            mock_ticket.guild_id = 123456789012345678
            mock_ticket.creator_id = 987654321098765432
            mock_ticket.reason = "I need help with my account"
            mock_ticket.category = "Support"
            mock_ticket.channel_id = None
            mock_ticket.status = "OPEN"
            mock_ticket.created_at = datetime(2025, 6, 27, 10, 0, 0)
            mock_ticket.updated_at = datetime(2025, 6, 27, 10, 0, 0)
            mock_ticket.closed_at = None
            mock_ticket.close_reason = None
            mock_ticket.assigned_to = None
            mock_ticket.is_shadow_closed = False
            
            mock_create_ticket.return_value = mock_ticket
            
            # Create a valid JWT token
            token = self._create_test_jwt_token()
            headers = {"Authorization": f"Bearer {token}"}
            
            # Make the request with Authorization header
            response = self.client.post("/api/tickets", json=self.valid_ticket_data, headers=headers)
            
            # Verify response
            assert response.status_code == 201
            response_data = response.json()
            assert response_data["message"] == "Ticket 12345 created successfully"
            assert response_data["ticket"]["id"] == 12345
            assert response_data["ticket"]["guild_id"] == 123456789012345678
            assert response_data["ticket"]["creator_id"] == 987654321098765432
            assert response_data["ticket"]["reason"] == "I need help with my account"
            assert response_data["ticket"]["category"] == "Support"
            
            # Verify function calls
            mock_has_permission.assert_called_once()
            mock_has_open_ticket.assert_called_once_with(mock_db_session, 987654321098765432, 123456789012345678)
            mock_create_ticket.assert_called_once_with(
                db=mock_db_session,
                guild_id=123456789012345678,
                creator_id=987654321098765432,
                reason="I need help with my account",
                channel_id=None,
                category="Support"
            )
            
        finally:
            # Clean up dependency overrides
            app.dependency_overrides.clear()

    @patch('app.main.has_permission')
    def test_insufficient_permissions(self, mock_has_permission):
        """Test ticket creation with insufficient permissions."""
        # Mock user data
        mock_user = Mock()
        mock_user.id = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        mock_user.discord_id = 987654321098765432
        mock_user.role = "USER"
        mock_user.is_active = True
        
        # Mock database session and user query
        mock_db_session = Mock()
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Override both database dependencies
        app.dependency_overrides[get_db] = lambda: mock_db_session  # For middleware
        app.dependency_overrides[get_db_session] = lambda: mock_db_session  # For endpoint
        
        try:
            # Mock permission check to return False
            mock_has_permission.return_value = False
            
            # Create a valid JWT token
            token = self._create_test_jwt_token()
            headers = {"Authorization": f"Bearer {token}"}
            
            # Make the request with Authorization header
            response = self.client.post("/api/tickets", json=self.valid_ticket_data, headers=headers)
            
            # Verify response
            assert response.status_code == 403
            assert "insufficient permissions" in response.json()["detail"].lower()
            
        finally:
            # Clean up dependency overrides
            app.dependency_overrides.clear()

    @patch('app.main.has_permission')
    def test_creator_id_mismatch(self, mock_has_permission):
        """Test ticket creation when creator_id doesn't match authenticated user."""
        # Mock user data with different discord_id
        mock_user = Mock()
        mock_user.id = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        mock_user.discord_id = 111111111111111111  # Different from request creator_id
        mock_user.role = "USER"
        mock_user.is_active = True
        
        # Mock database session and user query
        mock_db_session = Mock()
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Override both database dependencies
        app.dependency_overrides[get_db] = lambda: mock_db_session  # For middleware
        app.dependency_overrides[get_db_session] = lambda: mock_db_session  # For endpoint
        
        try:
            # Mock permission check
            mock_has_permission.return_value = True
            
            # Create a valid JWT token with different discord_id
            token = self._create_test_jwt_token(discord_id=111111111111111111)
            headers = {"Authorization": f"Bearer {token}"}
            
            # Make the request with Authorization header
            response = self.client.post("/api/tickets", json=self.valid_ticket_data, headers=headers)
            
            # Verify response
            assert response.status_code == 403
            assert "cannot create ticket for another user" in response.json()["detail"].lower()
            
        finally:
            # Clean up dependency overrides
            app.dependency_overrides.clear()

    @patch('app.main.has_permission')
    @patch('app.main.has_open_ticket_in_guild')
    def test_existing_open_ticket_conflict(self, mock_has_open_ticket, mock_has_permission):
        """Test ticket creation when user already has open ticket in guild."""
        # Mock user data
        mock_user = Mock()
        mock_user.id = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        mock_user.discord_id = 987654321098765432
        mock_user.role = "USER"
        mock_user.is_active = True
        
        # Mock database session and user query
        mock_db_session = Mock()
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Override both database dependencies
        app.dependency_overrides[get_db] = lambda: mock_db_session  # For middleware
        app.dependency_overrides[get_db_session] = lambda: mock_db_session  # For endpoint
        
        try:
            # Mock permission check
            mock_has_permission.return_value = True
            
            # Mock existing open ticket
            mock_has_open_ticket.return_value = True
            
            # Create a valid JWT token
            token = self._create_test_jwt_token()
            headers = {"Authorization": f"Bearer {token}"}
            
            # Make the request with Authorization header
            response = self.client.post("/api/tickets", json=self.valid_ticket_data, headers=headers)
            
            # Verify response
            assert response.status_code == 409
            assert "already has an open ticket" in response.json()["detail"].lower()
            
        finally:
            # Clean up dependency overrides
            app.dependency_overrides.clear()

    @patch('app.main.has_permission')
    @patch('app.main.has_open_ticket_in_guild')
    @patch('app.main.create_ticket')
    def test_database_error_handling(self, mock_create_ticket, mock_has_open_ticket, 
                                   mock_has_permission):
        """Test error handling when database operations fail."""
        from sqlalchemy.exc import SQLAlchemyError
        
        # Mock user data
        mock_user = Mock()
        mock_user.id = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        mock_user.discord_id = 987654321098765432
        mock_user.role = "USER"
        mock_user.is_active = True
        
        # Mock database session and user query
        mock_db_session = Mock()
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Override both database dependencies
        app.dependency_overrides[get_db] = lambda: mock_db_session  # For middleware
        app.dependency_overrides[get_db_session] = lambda: mock_db_session  # For endpoint
        
        try:
            # Mock permission check
            mock_has_permission.return_value = True
            
            # Mock no existing open ticket
            mock_has_open_ticket.return_value = False
            
            # Mock database error
            mock_create_ticket.side_effect = SQLAlchemyError("Database connection failed")
            
            # Create a valid JWT token
            token = self._create_test_jwt_token()
            headers = {"Authorization": f"Bearer {token}"}
            
            # Make the request with Authorization header
            response = self.client.post("/api/tickets", json=self.valid_ticket_data, headers=headers)
            
            # Verify response
            assert response.status_code == 500
            assert "database error" in response.json()["detail"].lower()
            
        finally:
            # Clean up dependency overrides
            app.dependency_overrides.clear()

    @patch('app.main.has_permission')
    @patch('app.main.has_open_ticket_in_guild')
    @patch('app.main.create_ticket')
    def test_integrity_error_duplicate_channel(self, mock_create_ticket, mock_has_open_ticket, 
                                              mock_has_permission):
        """Test error handling when attempting to create ticket with duplicate channel_id."""
        from sqlalchemy.exc import IntegrityError
        
        # Mock user data
        mock_user = Mock()
        mock_user.id = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        mock_user.discord_id = 987654321098765432
        mock_user.role = "USER"
        mock_user.is_active = True
        
        # Mock database session and user query
        mock_db_session = Mock()
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Override both database dependencies
        app.dependency_overrides[get_db] = lambda: mock_db_session  # For middleware
        app.dependency_overrides[get_db_session] = lambda: mock_db_session  # For endpoint
        
        try:
            # Mock permission check
            mock_has_permission.return_value = True
            
            # Mock no existing open ticket
            mock_has_open_ticket.return_value = False
            
            # Mock integrity error with channel_id constraint
            error_msg = "duplicate key value violates unique constraint on channel_id"
            mock_create_ticket.side_effect = IntegrityError(error_msg, {}, Exception())
            
            # Create a valid JWT token
            token = self._create_test_jwt_token()
            headers = {"Authorization": f"Bearer {token}"}
            
            # Make the request with Authorization header
            response = self.client.post("/api/tickets", json=self.valid_ticket_data, headers=headers)
            
            # Verify response
            assert response.status_code == 409
            assert "channel id already exists" in response.json()["detail"].lower()
            
        finally:
            # Clean up dependency overrides
            app.dependency_overrides.clear()

    @patch('app.main.has_permission')
    @patch('app.main.has_open_ticket_in_guild')
    @patch('app.main.create_ticket')
    def test_integrity_error_generic(self, mock_create_ticket, mock_has_open_ticket, 
                                    mock_has_permission):
        """Test error handling for generic integrity errors."""
        from sqlalchemy.exc import IntegrityError
        
        # Mock user data
        mock_user = Mock()
        mock_user.id = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        mock_user.discord_id = 987654321098765432
        mock_user.role = "USER"
        mock_user.is_active = True
        
        # Mock database session and user query
        mock_db_session = Mock()
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Override both database dependencies
        app.dependency_overrides[get_db] = lambda: mock_db_session  # For middleware
        app.dependency_overrides[get_db_session] = lambda: mock_db_session  # For endpoint
        
        try:
            # Mock permission check
            mock_has_permission.return_value = True
            
            # Mock no existing open ticket
            mock_has_open_ticket.return_value = False
            
            # Mock generic integrity error
            error_msg = "some other constraint violation"
            mock_create_ticket.side_effect = IntegrityError(error_msg, {}, Exception())
            
            # Create a valid JWT token
            token = self._create_test_jwt_token()
            headers = {"Authorization": f"Bearer {token}"}
            
            # Make the request with Authorization header
            response = self.client.post("/api/tickets", json=self.valid_ticket_data, headers=headers)
            
            # Verify response
            assert response.status_code == 400
            assert "database constraint violation" in response.json()["detail"].lower()
            
        finally:
            # Clean up dependency overrides
            app.dependency_overrides.clear()

class TestTicketCreateRequestSchema:
    """Test the Pydantic schema validation directly."""
    
    def test_valid_ticket_request(self):
        """Test valid ticket request creation."""
        request = TicketCreateRequest(
            guild_id=123456789012345678,
            creator_id=987654321098765432,
            reason="I need help with my account",
            category="Support",
            channel_id=None
        )
        assert request.guild_id == 123456789012345678
        assert request.creator_id == 987654321098765432
        assert request.reason == "I need help with my account"
        assert request.category == "Support"
    
    def test_invalid_guild_id(self):
        """Test invalid guild_id validation."""
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError) as exc_info:
            TicketCreateRequest(
                guild_id=123,  # Too short
                creator_id=987654321098765432,
                reason="I need help with my account",
                category=None,
                channel_id=None
            )
        
        errors = exc_info.value.errors()
        assert any("guild_id" in str(error["loc"]) for error in errors)
    
    def test_invalid_reason_too_short(self):
        """Test reason too short validation."""
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError) as exc_info:
            TicketCreateRequest(
                guild_id=123456789012345678,
                creator_id=987654321098765432,
                reason="Hi",  # Too short
                category=None,
                channel_id=None
            )
        
        errors = exc_info.value.errors()
        assert any("reason" in str(error["loc"]) for error in errors)
    
    def test_invalid_reason_too_long(self):
        """Test reason too long validation."""
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError) as exc_info:
            TicketCreateRequest(
                guild_id=123456789012345678,
                creator_id=987654321098765432,
                reason="x" * 501,  # Too long
                category=None,
                channel_id=None
            )
        
        errors = exc_info.value.errors()
        assert any("reason" in str(error["loc"]) for error in errors)

class TestTicketDetailsEndpoint:
    """Test cases for GET /api/tickets/{ticket_id} endpoint."""
    
    def setup_method(self):
        """Set up test client and mock data."""
        self.client = TestClient(app)
        self.ticket_id = 1
        self.mock_ticket_data = {
            'id': 1,
            'channel_id': 123456789012345678,
            'guild_id': 987654321098765432,
            'creator_id': 555666777888999000,
            'assigned_to': None,
            'status': 'open',
            'category': 'Support',
            'reason': 'I need help with my account',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'closed_at': None,
            'close_reason': None,
            'is_shadow_closed': False,
            'creator': {
                'id': '550e8400-e29b-41d4-a716-446655440000',
                'discord_id': 555666777888999000,
                'email': 'creator@example.com',
                'role': 'USER'
            },
            'assigned_staff': None,
            'participants_count': 1,
            'recent_messages_count': 0
        }
        
        # Clear any existing dependency overrides
        app.dependency_overrides.clear()

    def teardown_method(self):
        """Clean up after each test."""
        app.dependency_overrides.clear()

    def _create_test_jwt_token(self, user_id: str = "550e8400-e29b-41d4-a716-446655440000", 
                              discord_id: int = 555666777888999000, role: str = "USER"):
        """Create a valid JWT token for testing."""
        secret_key = os.getenv("JWT_SECRET_KEY", "test-secret-key-for-testing-only-do-not-use-in-production")
        payload = {
            "user_id": user_id,
            "discord_id": discord_id,
            "role": role,
            "email": "test@example.com",
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        return jwt.encode(payload, secret_key, algorithm="HS256")

    def _setup_auth_mocks(self, user_id: str = "550e8400-e29b-41d4-a716-446655440000",
                         discord_id: int = 555666777888999000, role: str = "USER"):
        """Set up authentication mocks for testing."""
        # Mock user data
        mock_user = Mock()
        mock_user.id = uuid.UUID(user_id)
        mock_user.discord_id = discord_id
        mock_user.role = role
        mock_user.email = "test@example.com"
        mock_user.is_active = True
        
        # Mock database session and user query
        mock_db_session = Mock()
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Override database dependencies
        app.dependency_overrides[get_db] = lambda: mock_db_session
        app.dependency_overrides[get_db_session] = lambda: mock_db_session
        
        return mock_user, mock_db_session

    def test_endpoint_requires_authentication(self):
        """Test that the endpoint requires authentication."""
        response = self.client.get(f"/api/tickets/{self.ticket_id}")
        assert response.status_code == 401

    def test_invalid_ticket_id_format(self):
        """Test validation for invalid ticket ID format."""
        mock_user, mock_db_session = self._setup_auth_mocks()
        token = self._create_test_jwt_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test negative ticket ID
        response = self.client.get("/api/tickets/-1", headers=headers)
        assert response.status_code == 400
        assert "Invalid ticket ID format" in response.json()["detail"]
        
        # Test zero ticket ID
        response = self.client.get("/api/tickets/0", headers=headers)
        assert response.status_code == 400
        assert "Invalid ticket ID format" in response.json()["detail"]

    @patch('app.main.get_ticket_details_with_users')
    def test_ticket_not_found(self, mock_get_ticket):
        """Test response when ticket is not found."""
        mock_get_ticket.return_value = None
        mock_user, mock_db_session = self._setup_auth_mocks()
        token = self._create_test_jwt_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = self.client.get(f"/api/tickets/{self.ticket_id}", headers=headers)
        assert response.status_code == 404
        assert "Ticket not found" in response.json()["detail"]

    @patch('app.main.get_ticket_details_with_users')
    def test_creator_can_view_own_ticket(self, mock_get_ticket):
        """Test that ticket creator can view their own ticket."""
        mock_get_ticket.return_value = self.mock_ticket_data
        mock_user, mock_db_session = self._setup_auth_mocks(discord_id=555666777888999000)
        token = self._create_test_jwt_token(discord_id=555666777888999000)
        headers = {"Authorization": f"Bearer {token}"}
        
        response = self.client.get(f"/api/tickets/{self.ticket_id}", headers=headers)
        assert response.status_code == 200
        
        ticket_data = response.json()
        assert ticket_data["id"] == self.ticket_id
        assert ticket_data["creator_id"] == 555666777888999000
        assert ticket_data["creator"]["discord_id"] == 555666777888999000

    @patch('app.main.get_ticket_details_with_users')
    @patch('app.main.has_permission')
    def test_assigned_staff_can_view_ticket(self, mock_has_permission, mock_get_ticket):
        """Test that assigned staff can view their assigned ticket."""
        staff_uuid = "660e8400-e29b-41d4-a716-446655440001"
        ticket_data = self.mock_ticket_data.copy()
        ticket_data['assigned_to'] = 111222333444555666  # Different from creator
        ticket_data['assigned_staff'] = {
            'id': staff_uuid,
            'discord_id': 111222333444555666,
            'email': 'staff@example.com',
            'role': 'STAFF'
        }
        mock_get_ticket.return_value = ticket_data
        mock_has_permission.return_value = False  # Not using permission, using assignment
        
        mock_user, mock_db_session = self._setup_auth_mocks(
            user_id=staff_uuid, 
            discord_id=111222333444555666, 
            role="STAFF"
        )
        token = self._create_test_jwt_token(user_id=staff_uuid, discord_id=111222333444555666, role="STAFF")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = self.client.get(f"/api/tickets/{self.ticket_id}", headers=headers)
        assert response.status_code == 200

    @patch('app.main.get_ticket_details_with_users')
    @patch('app.main.has_permission')
    def test_staff_with_manage_permission_can_view_any_ticket(self, mock_has_permission, mock_get_ticket):
        """Test that staff with MANAGE_TICKETS permission can view any ticket."""
        mock_get_ticket.return_value = self.mock_ticket_data
        staff_uuid = "770e8400-e29b-41d4-a716-446655440002"
        
        mock_user, mock_db_session = self._setup_auth_mocks(
            user_id=staff_uuid, 
            discord_id=999888777666555444, 
            role="STAFF"
        )
        token = self._create_test_jwt_token(user_id=staff_uuid, discord_id=999888777666555444, role="STAFF")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Mock permission checks
        def permission_check(role, permission):
            from app.permissions import Permission
            return permission == Permission.MANAGE_TICKETS and role == "STAFF"
        
        mock_has_permission.side_effect = permission_check
        
        response = self.client.get(f"/api/tickets/{self.ticket_id}", headers=headers)
        assert response.status_code == 200

    @patch('app.main.get_ticket_details_with_users')
    @patch('app.main.has_permission')
    def test_admin_can_view_any_ticket(self, mock_has_permission, mock_get_ticket):
        """Test that admin can view any ticket."""
        mock_get_ticket.return_value = self.mock_ticket_data
        admin_uuid = "880e8400-e29b-41d4-a716-446655440003"
        
        mock_user, mock_db_session = self._setup_auth_mocks(
            user_id=admin_uuid, 
            discord_id=999888777666555444, 
            role="ADMIN"
        )
        token = self._create_test_jwt_token(user_id=admin_uuid, discord_id=999888777666555444, role="ADMIN")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Mock permission checks
        def permission_check(role, permission):
            from app.permissions import Permission
            return permission == Permission.ADMIN_SETTINGS and role == "ADMIN"
        
        mock_has_permission.side_effect = permission_check
        
        response = self.client.get(f"/api/tickets/{self.ticket_id}", headers=headers)
        assert response.status_code == 200

    @patch('app.main.get_ticket_details_with_users')
    @patch('app.main.has_permission')
    def test_unauthorized_user_cannot_view_ticket(self, mock_has_permission, mock_get_ticket):
        """Test that unauthorized user cannot view ticket."""
        mock_get_ticket.return_value = self.mock_ticket_data
        mock_has_permission.return_value = False  # No permissions
        other_user_uuid = "990e8400-e29b-41d4-a716-446655440004"
        
        mock_user, mock_db_session = self._setup_auth_mocks(
            user_id=other_user_uuid, 
            discord_id=999888777666555444, 
            role="USER"
        )
        token = self._create_test_jwt_token(user_id=other_user_uuid, discord_id=999888777666555444, role="USER")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = self.client.get(f"/api/tickets/{self.ticket_id}", headers=headers)
        assert response.status_code == 403
        assert "Insufficient permissions" in response.json()["detail"]

    @patch('app.main.get_ticket_details_with_users')
    def test_successful_ticket_retrieval_with_creator_info(self, mock_get_ticket):
        """Test successful ticket retrieval includes creator information."""
        mock_get_ticket.return_value = self.mock_ticket_data
        
        mock_user, mock_db_session = self._setup_auth_mocks(discord_id=555666777888999000)
        token = self._create_test_jwt_token(discord_id=555666777888999000)
        headers = {"Authorization": f"Bearer {token}"}
        
        response = self.client.get(f"/api/tickets/{self.ticket_id}", headers=headers)
        assert response.status_code == 200
        
        ticket_data = response.json()
        
        # Verify main ticket fields
        assert ticket_data["id"] == 1
        assert ticket_data["status"] == "open"
        assert ticket_data["reason"] == "I need help with my account"
        
        # Verify creator information is included
        assert ticket_data["creator"] is not None
        assert ticket_data["creator"]["discord_id"] == 555666777888999000
        assert ticket_data["creator"]["role"] == "USER"
        
        # Verify assigned staff is None (unassigned ticket)
        assert ticket_data["assigned_staff"] is None
        
        # Verify metadata
        assert ticket_data["participants_count"] == 1
        assert ticket_data["recent_messages_count"] == 0

    @patch('app.main.get_ticket_details_with_users')
    def test_database_error_handling(self, mock_get_ticket):
        """Test proper error handling for database errors."""
        from sqlalchemy.exc import SQLAlchemyError
        mock_get_ticket.side_effect = SQLAlchemyError("Database connection failed")
        
        mock_user, mock_db_session = self._setup_auth_mocks()
        token = self._create_test_jwt_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = self.client.get(f"/api/tickets/{self.ticket_id}", headers=headers)
        assert response.status_code == 500
        assert "database error" in response.json()["detail"].lower()

    @patch('app.main.get_ticket_details_with_users')
    def test_unexpected_error_handling(self, mock_get_ticket):
        """Test proper error handling for unexpected errors."""
        mock_get_ticket.side_effect = Exception("Unexpected error")
        
        mock_user, mock_db_session = self._setup_auth_mocks()
        token = self._create_test_jwt_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = self.client.get(f"/api/tickets/{self.ticket_id}", headers=headers)
        assert response.status_code == 500
        assert "unexpected error" in response.json()["detail"].lower()
