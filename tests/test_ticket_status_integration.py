"""
Unit tests for ticket model status state machine integration.
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.ticket import Ticket, create_ticket
from app.status import TicketStatus, StatusTransitionError


class TestTicketStatusMethods:
    """Test ticket model status-related methods."""
    
    def test_is_open_with_open_status(self):
        """Test is_open method with open status."""
        ticket = Ticket(status="open")
        assert ticket.is_open() is True
        
    def test_is_open_with_in_progress_status(self):
        """Test is_open method with in_progress status."""
        ticket = Ticket(status="in_progress")
        assert ticket.is_open() is True
        
    def test_is_open_with_closed_status(self):
        """Test is_open method with closed status."""
        ticket = Ticket(status="closed")
        assert ticket.is_open() is False
        
    def test_is_closed_with_closed_status(self):
        """Test is_closed method with closed status."""
        ticket = Ticket(status="closed")
        assert ticket.is_closed() is True
        
    def test_is_closed_with_open_status(self):
        """Test is_closed method with open status."""
        ticket = Ticket(status="open")
        assert ticket.is_closed() is False
        
    def test_can_be_assigned_with_open_status(self):
        """Test can_be_assigned method with open status."""
        ticket = Ticket(status="open")
        assert ticket.can_be_assigned() is True
        
    def test_can_be_assigned_with_in_progress_status(self):
        """Test can_be_assigned method with in_progress status."""
        ticket = Ticket(status="in_progress")
        assert ticket.can_be_assigned() is True
        
    def test_can_be_assigned_with_closed_status(self):
        """Test can_be_assigned method with closed status."""
        ticket = Ticket(status="closed")
        assert ticket.can_be_assigned() is False
        
    def test_validate_status_transition_valid(self):
        """Test validate_status_transition with valid transition."""
        ticket = Ticket(status="open")
        assert ticket.validate_status_transition("in_progress") is True
        
    def test_validate_status_transition_invalid(self):
        """Test validate_status_transition with invalid transition."""
        ticket = Ticket(status="open")
        assert ticket.validate_status_transition("resolved") is False


class TestTicketStatusUpdate:
    """Test ticket status update functionality."""
    
    def test_update_status_valid_transition(self):
        """Test updating status with valid transition."""
        ticket = Ticket(id=1, status="open")
        result = ticket.update_status("in_progress", changed_by=123)
        
        assert result is True
        assert str(ticket.status) == "in_progress"
        
    def test_update_status_invalid_transition(self):
        """Test updating status with invalid transition raises exception."""
        ticket = Ticket(id=1, status="open")
        
        with pytest.raises(StatusTransitionError):
            ticket.update_status("resolved", changed_by=123)
            
    def test_update_status_to_closed_with_reason(self):
        """Test updating status to closed with close reason."""
        # Create ticket with a creator_id that matches the user making the change
        ticket = Ticket(id=1, status="open", creator_id=123)
        close_reason = "Issue resolved by user"
        
        # Use USER role since the creator is closing their own ticket
        result = ticket.update_status("closed", changed_by=123, user_role="USER", close_reason=close_reason)
        
        assert result is True
        assert str(ticket.status) == "closed"
        assert str(ticket.close_reason) == close_reason
        assert ticket.closed_at is not None
        assert isinstance(ticket.closed_at, datetime)
        
    def test_update_status_to_closed_without_reason(self):
        """Test updating status to closed without close reason raises exception."""
        # Create ticket with creator_id that matches the user making the change
        ticket = Ticket(id=1, status="open", creator_id=123)
        
        # The test should raise TicketClosureError because close_reason is missing
        from app.status import TicketClosureError
        with pytest.raises(TicketClosureError) as exc_info:
            ticket.update_status("closed", changed_by=123, user_role="USER")
            
        assert "Close reason is required" in str(exc_info.value)
        
    @patch('app.models.ticket.log_status_transition')
    def test_update_status_logs_transition(self, mock_log_transition):
        """Test that status update logs the transition."""
        ticket = Ticket(id=1, status="open")
        
        ticket.update_status("in_progress", changed_by=123)
        
        mock_log_transition.assert_called_once_with(
            ticket_id=1,
            previous_status="open",
            new_status="in_progress",
            changed_by=123,
            reason=None
        )
        
    def test_update_status_with_database_session(self):
        """Test updating status with database session."""
        # Mock database session
        mock_session = MagicMock(spec=Session)
        
        ticket = Ticket(id=1, status="open")
        result = ticket.update_status("in_progress", changed_by=123, db_session=mock_session)
        
        assert result is True
        assert str(ticket.status) == "in_progress"
        
        # Verify database operations
        mock_session.add.assert_called_once_with(ticket)
        mock_session.commit.assert_called_once()
        
    def test_update_status_database_error_rollback(self):
        """Test that database errors trigger rollback."""
        from sqlalchemy.exc import SQLAlchemyError
        
        # Mock database session that raises exception on commit
        mock_session = MagicMock(spec=Session)
        mock_session.commit.side_effect = SQLAlchemyError("Database error")
        
        ticket = Ticket(id=1, status="open")
        
        with pytest.raises(SQLAlchemyError):
            ticket.update_status("in_progress", changed_by=123, db_session=mock_session)
            
        # Verify rollback was called
        mock_session.rollback.assert_called_once()


class TestCreateTicketWithStatus:
    """Test ticket creation with proper status initialization."""
    
    def test_create_ticket_sets_open_status(self):
        """Test that create_ticket sets status to open."""
        # Mock database session
        mock_session = MagicMock(spec=Session)
        
        ticket = create_ticket(
            db=mock_session,
            guild_id=123456789012345678,
            creator_id=987654321098765432,
            reason="Test ticket creation"
        )
        
        assert str(ticket.status) == TicketStatus.OPEN.value
        
    def test_ticket_initialization_default_status(self):
        """Test that Ticket initialization sets default status."""
        ticket = Ticket(
            guild_id=123456789012345678,
            creator_id=987654321098765432,
            reason="Test ticket"
        )
        
        assert str(ticket.status) == "open"
        assert ticket.is_shadow_closed is False


class TestTicketToDict:
    """Test ticket dictionary conversion includes status."""
    
    def test_to_dict_includes_status(self):
        """Test that to_dict method includes status field."""
        ticket = Ticket(
            id=1,
            guild_id=123456789012345678,
            creator_id=987654321098765432,
            reason="Test ticket",
            status="in_progress"
        )
        
        ticket_dict = ticket.to_dict()
        
        assert "status" in ticket_dict
        assert ticket_dict["status"] == "in_progress"
        
    def test_to_dict_includes_all_status_related_fields(self):
        """Test that to_dict includes all status-related fields."""
        now = datetime.utcnow()
        ticket = Ticket(
            id=1,
            guild_id=123456789012345678,
            creator_id=987654321098765432,
            reason="Test ticket",
            status="closed",
            closed_at=now,
            close_reason="Resolved by staff",
            is_shadow_closed=False
        )
        
        ticket_dict = ticket.to_dict()
        
        assert ticket_dict["status"] == "closed"
        assert ticket_dict["close_reason"] == "Resolved by staff"
        assert ticket_dict["is_shadow_closed"] is False
        assert "closed_at" in ticket_dict
