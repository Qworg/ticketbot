"""
Tests for ticket update functionality.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import Mock, patch
from datetime import datetime

from app.main import app
from app.middleware import require_authentication
from app.models.ticket import create_ticket, get_ticket_by_id
from app.models.user import create_user
from app.status import TicketStatus
from app.permissions import Permission


class TestTicketUpdate:
    """Test cases for ticket update endpoint."""
    
    def setup_method(self):
        """Set up test client and mock data."""
        self.client = TestClient(app)
        self.mock_db = Mock(spec=Session)
        self.mock_user = Mock()
        self.mock_user.id = "550e8400-e29b-41d4-a716-446655440000"
        self.mock_user.discord_id = 123456789012345678
        self.mock_user.role = "STAFF"
        self.mock_user.email = "test@example.com"
        
    @patch('app.main.require_authentication')
    @patch('app.main.get_db_session')
    @patch('app.main.get_ticket_by_id')
    @patch('app.main.update_ticket')
    @patch('app.main.has_permission')
    def test_update_ticket_status_success(
        self, mock_has_permission, mock_update_ticket, mock_get_ticket, 
        mock_get_db, mock_auth
    ):
        """Test successful ticket status update."""
        # Setup dependency override
        def auth_override():
            return {
                "user": self.mock_user,
                "discord_id": self.mock_user.discord_id,
                "is_authenticated": True
            }
        
        app.dependency_overrides[require_authentication] = auth_override
        
        try:
            # Setup other mocks
            mock_get_db.return_value = self.mock_db
            mock_has_permission.return_value = True
            
            # Mock existing ticket
            mock_ticket = Mock()
            mock_ticket.id = 1
            mock_ticket.creator_id = 987654321098765432
            mock_ticket.status = TicketStatus.OPEN.value
            mock_get_ticket.return_value = mock_ticket
            
            # Mock updated ticket
            mock_updated_ticket = Mock()
            mock_updated_ticket.id = 1
            mock_updated_ticket.channel_id = None
            mock_updated_ticket.guild_id = 111111111111111111
            mock_updated_ticket.creator_id = 987654321098765432
            mock_updated_ticket.assigned_to = None
            mock_updated_ticket.status = TicketStatus.IN_PROGRESS.value
            mock_updated_ticket.category = None
            mock_updated_ticket.reason = "Test ticket"
            mock_updated_ticket.created_at = datetime.utcnow()
            mock_updated_ticket.updated_at = datetime.utcnow()
            mock_updated_ticket.closed_at = None
            mock_updated_ticket.close_reason = None
            mock_updated_ticket.is_shadow_closed = False
            mock_update_ticket.return_value = mock_updated_ticket
            
            # Make request
            response = self.client.patch(
                "/api/tickets/1",
                json={"status": "in_progress"}
            )
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "updated successfully" in data["message"]
            assert data["ticket"]["status"] == "in_progress"
            assert "status updated" in " ".join(data["changes_made"])
            
            # Verify function calls
            mock_get_ticket.assert_called_once_with(self.mock_db, 1)
            mock_update_ticket.assert_called_once()
        finally:
            # Cleanup
            app.dependency_overrides.clear()
        
    @patch('app.main.require_authentication')
    @patch('app.main.get_db_session')
    @patch('app.main.get_ticket_by_id')
    @patch('app.main.has_permission')
    def test_update_ticket_invalid_transition(
        self, mock_has_permission, mock_get_ticket, mock_get_db, mock_auth
    ):
        """Test invalid status transition."""
        # Setup mocks
        mock_auth.return_value = {
            "user": self.mock_user,
            "discord_id": self.mock_user.discord_id,
            "is_authenticated": True
        }
        mock_get_db.return_value = self.mock_db
        mock_has_permission.return_value = True
        
        # Mock existing closed ticket
        mock_ticket = Mock()
        mock_ticket.id = 1
        mock_ticket.creator_id = 987654321098765432
        mock_ticket.status = TicketStatus.CLOSED.value
        mock_get_ticket.return_value = mock_ticket
        
        # Make request (trying to reopen closed ticket)
        response = self.client.patch(
            "/api/tickets/1",
            json={"status": "open"}
        )
        
        # Assertions
        assert response.status_code == 400
        data = response.json()
        assert "Invalid status transition" in data["detail"]
        
    @patch('app.main.require_authentication')
    @patch('app.main.get_db_session')
    @patch('app.main.get_ticket_by_id')
    @patch('app.main.has_permission')
    def test_update_ticket_insufficient_permissions(
        self, mock_has_permission, mock_get_ticket, mock_get_db, mock_auth
    ):
        """Test update with insufficient permissions."""
        # Setup mocks - user without permissions
        mock_user_no_perms = Mock()
        mock_user_no_perms.id = "550e8400-e29b-41d4-a716-446655440001"
        mock_user_no_perms.discord_id = 999999999999999999
        mock_user_no_perms.role = "USER"
        mock_user_no_perms.email = "user@example.com"
        
        mock_auth.return_value = {
            "user": mock_user_no_perms,
            "discord_id": mock_user_no_perms.discord_id,
            "is_authenticated": True
        }
        mock_get_db.return_value = self.mock_db
        mock_has_permission.return_value = False
        
        # Mock existing ticket not owned by user
        mock_ticket = Mock()
        mock_ticket.id = 1
        mock_ticket.creator_id = 987654321098765432  # Different from requesting user
        mock_ticket.status = TicketStatus.OPEN.value
        mock_get_ticket.return_value = mock_ticket
        
        # Make request
        response = self.client.patch(
            "/api/tickets/1",
            json={"status": "in_progress"}
        )
        
        # Assertions
        assert response.status_code == 403
        data = response.json()
        assert "Insufficient permissions" in data["detail"]
        
    @patch('app.main.require_authentication')
    @patch('app.main.get_db_session')
    @patch('app.main.get_ticket_by_id')
    @patch('app.main.update_ticket')
    @patch('app.main.has_permission')
    def test_update_ticket_multiple_fields(
        self, mock_has_permission, mock_update_ticket, mock_get_ticket, 
        mock_get_db, mock_auth
    ):
        """Test updating multiple ticket fields."""
        # Setup mocks
        mock_auth.return_value = {
            "user": self.mock_user,
            "discord_id": self.mock_user.discord_id,
            "is_authenticated": True
        }
        mock_get_db.return_value = self.mock_db
        mock_has_permission.return_value = True
        
        # Mock existing ticket
        mock_ticket = Mock()
        mock_ticket.id = 1
        mock_ticket.creator_id = 987654321098765432
        mock_ticket.status = TicketStatus.OPEN.value
        mock_get_ticket.return_value = mock_ticket
        
        # Mock updated ticket
        mock_updated_ticket = Mock()
        mock_updated_ticket.id = 1
        mock_updated_ticket.channel_id = None
        mock_updated_ticket.guild_id = 111111111111111111
        mock_updated_ticket.creator_id = 987654321098765432
        mock_updated_ticket.assigned_to = self.mock_user.discord_id
        mock_updated_ticket.status = TicketStatus.IN_PROGRESS.value
        mock_updated_ticket.category = "bug"
        mock_updated_ticket.reason = "Test ticket"
        mock_updated_ticket.created_at = datetime.utcnow()
        mock_updated_ticket.updated_at = datetime.utcnow()
        mock_updated_ticket.closed_at = None
        mock_updated_ticket.close_reason = None
        mock_updated_ticket.is_shadow_closed = False
        mock_update_ticket.return_value = mock_updated_ticket
        
        # Make request
        response = self.client.patch(
            "/api/tickets/1",
            json={
                "status": "in_progress",
                "category": "bug",
                "assigned_to": self.mock_user.discord_id
            }
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["changes_made"]) >= 2  # Should have multiple changes
        
    @patch('app.main.require_authentication')
    @patch('app.main.get_db_session')
    @patch('app.main.get_ticket_by_id')
    def test_update_ticket_not_found(self, mock_get_ticket, mock_get_db, mock_auth):
        """Test updating non-existent ticket."""
        # Setup mocks
        mock_auth.return_value = {
            "user": self.mock_user,
            "discord_id": self.mock_user.discord_id,
            "is_authenticated": True
        }
        mock_get_db.return_value = self.mock_db
        mock_get_ticket.return_value = None
        
        # Make request
        response = self.client.patch(
            "/api/tickets/999",
            json={"status": "in_progress"}
        )
        
        # Assertions
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
        
    @patch('app.main.require_authentication')
    @patch('app.main.get_db_session')
    def test_update_ticket_invalid_id(self, mock_get_db, mock_auth):
        """Test updating with invalid ticket ID."""
        # Setup mocks
        mock_auth.return_value = {
            "user": self.mock_user,
            "discord_id": self.mock_user.discord_id,
            "is_authenticated": True
        }
        mock_get_db.return_value = self.mock_db
        
        # Make request with invalid ID
        response = self.client.patch(
            "/api/tickets/0",
            json={"status": "in_progress"}
        )
        
        # Assertions
        assert response.status_code == 400
        data = response.json()
        assert "Invalid ticket ID" in data["detail"]
        
    @patch('app.main.require_authentication')
    @patch('app.main.get_db_session')
    @patch('app.main.get_ticket_by_id')
    @patch('app.main.has_permission')
    def test_update_ticket_no_changes(
        self, mock_has_permission, mock_get_ticket, mock_get_db, mock_auth
    ):
        """Test update request with no changes."""
        # Setup mocks
        mock_auth.return_value = {
            "user": self.mock_user,
            "discord_id": self.mock_user.discord_id,
            "is_authenticated": True
        }
        mock_get_db.return_value = self.mock_db
        mock_has_permission.return_value = True
        
        # Mock existing ticket
        mock_ticket = Mock()
        mock_ticket.id = 1
        mock_ticket.creator_id = 987654321098765432
        mock_ticket.status = TicketStatus.OPEN.value
        mock_get_ticket.return_value = mock_ticket
        
        # Make request with empty body
        response = self.client.patch("/api/tickets/1", json={})
        
        # Assertions
        assert response.status_code == 400
        data = response.json()
        assert "No updates provided" in data["detail"]
        
    @patch('app.main.require_authentication')
    @patch('app.main.get_db_session')
    @patch('app.main.get_ticket_by_id')
    @patch('app.main.update_ticket')
    @patch('app.main.has_permission')
    def test_update_ticket_close_with_reason(
        self, mock_has_permission, mock_update_ticket, mock_get_ticket, 
        mock_get_db, mock_auth
    ):
        """Test closing ticket with required close reason."""
        # Setup mocks
        mock_auth.return_value = {
            "user": self.mock_user,
            "discord_id": self.mock_user.discord_id,
            "is_authenticated": True
        }
        mock_get_db.return_value = self.mock_db
        mock_has_permission.return_value = True
        
        # Mock existing ticket
        mock_ticket = Mock()
        mock_ticket.id = 1
        mock_ticket.creator_id = 987654321098765432
        mock_ticket.status = TicketStatus.RESOLVED.value
        mock_get_ticket.return_value = mock_ticket
        
        # Mock updated ticket
        mock_updated_ticket = Mock()
        mock_updated_ticket.id = 1
        mock_updated_ticket.channel_id = None
        mock_updated_ticket.guild_id = 111111111111111111
        mock_updated_ticket.creator_id = 987654321098765432
        mock_updated_ticket.assigned_to = None
        mock_updated_ticket.status = TicketStatus.CLOSED.value
        mock_updated_ticket.category = None
        mock_updated_ticket.reason = "Test ticket"
        mock_updated_ticket.created_at = datetime.utcnow()
        mock_updated_ticket.updated_at = datetime.utcnow()
        mock_updated_ticket.closed_at = datetime.utcnow()
        mock_updated_ticket.close_reason = "Issue resolved"
        mock_updated_ticket.is_shadow_closed = False
        mock_update_ticket.return_value = mock_updated_ticket
        
        # Make request
        response = self.client.patch(
            "/api/tickets/1",
            json={
                "status": "closed",
                "close_reason": "Issue resolved"
            }
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["ticket"]["status"] == "closed"
        
    def test_ticket_update_request_validation(self):
        """Test validation of ticket update request model."""
        from app.schemas import TicketUpdateRequest
        
        # Valid request
        valid_request = TicketUpdateRequest(
            status="in_progress",
            category="bug",
            assigned_to=123456789012345678,
            close_reason=None
        )
        assert valid_request.status == "in_progress"
        assert valid_request.category == "bug"
        assert valid_request.assigned_to == 123456789012345678
        
        # Test close reason required for closed status
        with pytest.raises(ValueError, match="close_reason is required"):
            TicketUpdateRequest(status="closed", category=None, assigned_to=None, close_reason=None)
        
        # Test invalid status
        with pytest.raises(ValueError, match="status must be one of"):
            TicketUpdateRequest(status="invalid_status", category=None, assigned_to=None, close_reason=None)
        
        # Test invalid assigned_to format
        with pytest.raises(ValueError, match="valid Discord snowflake"):
            TicketUpdateRequest(status=None, category=None, assigned_to=123, close_reason=None)  # Too short
