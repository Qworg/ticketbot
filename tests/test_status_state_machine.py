"""
Unit tests for ticket status state machine functionality.
"""
import pytest
from datetime import datetime
from app.status import (
    TicketStatus, validate_status_transition, get_valid_next_statuses,
    enforce_status_transition, StatusTransitionError, log_status_transition,
    is_open_status, is_closed_status, is_resolved_status, can_be_assigned,
    requires_close_reason, is_terminal_status, get_status_description
)


class TestTicketStatusEnum:
    """Test the TicketStatus enum."""
    
    def test_status_values(self):
        """Test that status enum has correct values."""
        assert TicketStatus.OPEN.value == "open"
        assert TicketStatus.IN_PROGRESS.value == "in_progress"
        assert TicketStatus.RESOLVED.value == "resolved"
        assert TicketStatus.CLOSED.value == "closed"


class TestStatusValidation:
    """Test status transition validation."""
    
    def test_valid_transitions_from_open(self):
        """Test valid transitions from OPEN status."""
        assert validate_status_transition("open", "in_progress") is True
        assert validate_status_transition("open", "closed") is True
        
    def test_invalid_transitions_from_open(self):
        """Test invalid transitions from OPEN status."""
        assert validate_status_transition("open", "resolved") is False
        assert validate_status_transition("open", "open") is False
        
    def test_valid_transitions_from_in_progress(self):
        """Test valid transitions from IN_PROGRESS status."""
        assert validate_status_transition("in_progress", "resolved") is True
        assert validate_status_transition("in_progress", "closed") is True
        assert validate_status_transition("in_progress", "open") is True
        
    def test_invalid_transitions_from_in_progress(self):
        """Test invalid transitions from IN_PROGRESS status."""
        assert validate_status_transition("in_progress", "in_progress") is False
        
    def test_valid_transitions_from_resolved(self):
        """Test valid transitions from RESOLVED status."""
        assert validate_status_transition("resolved", "closed") is True
        assert validate_status_transition("resolved", "in_progress") is True
        
    def test_invalid_transitions_from_resolved(self):
        """Test invalid transitions from RESOLVED status."""
        assert validate_status_transition("resolved", "open") is False
        assert validate_status_transition("resolved", "resolved") is False
        
    def test_no_transitions_from_closed(self):
        """Test that no transitions are allowed from CLOSED status."""
        assert validate_status_transition("closed", "open") is False
        assert validate_status_transition("closed", "in_progress") is False
        assert validate_status_transition("closed", "resolved") is False
        assert validate_status_transition("closed", "closed") is False
        
    def test_case_insensitive_validation(self):
        """Test that validation is case insensitive."""
        assert validate_status_transition("OPEN", "IN_PROGRESS") is True
        assert validate_status_transition("Open", "Closed") is True
        assert validate_status_transition("in_progress", "RESOLVED") is True
        
    def test_invalid_status_values(self):
        """Test validation with invalid status values."""
        assert validate_status_transition("invalid", "open") is False
        assert validate_status_transition("open", "invalid") is False
        assert validate_status_transition("", "open") is False


class TestGetValidNextStatuses:
    """Test getting valid next statuses."""
    
    def test_get_valid_next_statuses_open(self):
        """Test getting valid next statuses from OPEN."""
        next_statuses = get_valid_next_statuses("open")
        assert "in_progress" in next_statuses
        assert "closed" in next_statuses
        assert len(next_statuses) == 2
        
    def test_get_valid_next_statuses_in_progress(self):
        """Test getting valid next statuses from IN_PROGRESS."""
        next_statuses = get_valid_next_statuses("in_progress")
        assert "resolved" in next_statuses
        assert "closed" in next_statuses
        assert "open" in next_statuses
        assert len(next_statuses) == 3
        
    def test_get_valid_next_statuses_resolved(self):
        """Test getting valid next statuses from RESOLVED."""
        next_statuses = get_valid_next_statuses("resolved")
        assert "closed" in next_statuses
        assert "in_progress" in next_statuses
        assert len(next_statuses) == 2
        
    def test_get_valid_next_statuses_closed(self):
        """Test getting valid next statuses from CLOSED."""
        next_statuses = get_valid_next_statuses("closed")
        assert len(next_statuses) == 0
        
    def test_get_valid_next_statuses_invalid(self):
        """Test getting valid next statuses from invalid status."""
        next_statuses = get_valid_next_statuses("invalid")
        assert len(next_statuses) == 0


class TestEnforceStatusTransition:
    """Test status transition enforcement."""
    
    def test_enforce_valid_transition(self):
        """Test enforcing a valid transition."""
        result = enforce_status_transition("open", "in_progress")
        assert result == "in_progress"
        
    def test_enforce_invalid_transition(self):
        """Test enforcing an invalid transition raises exception."""
        with pytest.raises(StatusTransitionError) as exc_info:
            enforce_status_transition("open", "resolved")
        
        assert "open" in str(exc_info.value)
        assert "resolved" in str(exc_info.value)
        assert exc_info.value.current_status == "open"
        assert exc_info.value.new_status == "resolved"
        
    def test_enforce_transition_normalizes_case(self):
        """Test that enforcement normalizes status case."""
        result = enforce_status_transition("OPEN", "IN_PROGRESS")
        assert result == "in_progress"


class TestStatusUtilities:
    """Test status utility functions."""
    
    def test_is_open_status(self):
        """Test is_open_status function."""
        assert is_open_status("open") is True
        assert is_open_status("in_progress") is True
        assert is_open_status("resolved") is False
        assert is_open_status("closed") is False
        assert is_open_status("invalid") is False
        
    def test_is_closed_status(self):
        """Test is_closed_status function."""
        assert is_closed_status("closed") is True
        assert is_closed_status("open") is False
        assert is_closed_status("in_progress") is False
        assert is_closed_status("resolved") is False
        assert is_closed_status("invalid") is False
        
    def test_is_resolved_status(self):
        """Test is_resolved_status function."""
        assert is_resolved_status("resolved") is True
        assert is_resolved_status("open") is False
        assert is_resolved_status("in_progress") is False
        assert is_resolved_status("closed") is False
        assert is_resolved_status("invalid") is False
        
    def test_can_be_assigned(self):
        """Test can_be_assigned function."""
        assert can_be_assigned("open") is True
        assert can_be_assigned("in_progress") is True
        assert can_be_assigned("resolved") is False
        assert can_be_assigned("closed") is False
        assert can_be_assigned("invalid") is False
        
    def test_requires_close_reason(self):
        """Test requires_close_reason function."""
        assert requires_close_reason("open", "closed") is True
        assert requires_close_reason("in_progress", "closed") is True
        assert requires_close_reason("resolved", "closed") is True
        assert requires_close_reason("open", "in_progress") is False
        assert requires_close_reason("in_progress", "resolved") is False
        
    def test_is_terminal_status(self):
        """Test is_terminal_status function."""
        assert is_terminal_status("closed") is True
        assert is_terminal_status("open") is False
        assert is_terminal_status("in_progress") is False
        assert is_terminal_status("resolved") is False
        assert is_terminal_status("invalid") is False
        
    def test_get_status_description(self):
        """Test get_status_description function."""
        assert "Open" in get_status_description("open")
        assert "Progress" in get_status_description("in_progress")
        assert "Resolved" in get_status_description("resolved")
        assert "Closed" in get_status_description("closed")
        assert "Invalid" in get_status_description("invalid")


class TestStatusTransitionLog:
    """Test status transition logging."""
    
    def test_log_status_transition(self):
        """Test logging a status transition."""
        log_entry = log_status_transition(
            ticket_id=123,
            previous_status="open",
            new_status="in_progress",
            changed_by=456,
            reason="Staff member claimed ticket"
        )
        
        assert log_entry.ticket_id == 123
        assert log_entry.previous_status == "open"
        assert log_entry.new_status == "in_progress"
        assert log_entry.changed_by == 456
        assert log_entry.reason == "Staff member claimed ticket"
        assert isinstance(log_entry.timestamp, datetime)
        
    def test_log_status_transition_no_reason(self):
        """Test logging a status transition without reason."""
        log_entry = log_status_transition(
            ticket_id=123,
            previous_status="open",
            new_status="closed",
            changed_by=456
        )
        
        assert log_entry.reason is None
        
    def test_status_transition_log_to_dict(self):
        """Test converting status transition log to dictionary."""
        log_entry = log_status_transition(
            ticket_id=123,
            previous_status="open",
            new_status="closed",
            changed_by=456,
            reason="Issue resolved"
        )
        
        log_dict = log_entry.to_dict()
        
        assert log_dict["ticket_id"] == 123
        assert log_dict["previous_status"] == "open"
        assert log_dict["new_status"] == "closed"
        assert log_dict["changed_by"] == 456
        assert log_dict["reason"] == "Issue resolved"
        assert "timestamp" in log_dict


class TestStatusTransitionError:
    """Test StatusTransitionError exception."""
    
    def test_status_transition_error_default_message(self):
        """Test StatusTransitionError with default message."""
        error = StatusTransitionError("open", "resolved")
        assert "open" in str(error)
        assert "resolved" in str(error)
        assert error.current_status == "open"
        assert error.new_status == "resolved"
        
    def test_status_transition_error_custom_message(self):
        """Test StatusTransitionError with custom message."""
        custom_message = "Custom error message"
        error = StatusTransitionError("open", "resolved", custom_message)
        assert str(error) == custom_message
        assert error.current_status == "open"
        assert error.new_status == "resolved"


class TestTicketClosureValidation:
    """Test ticket closure validation functionality."""
    
    def test_validate_close_reason_valid(self):
        """Test valid close reasons."""
        from app.status import validate_close_reason
        
        # Valid reasons
        validate_close_reason("Fixed the issue")
        validate_close_reason("User requested closure")
        validate_close_reason("No response from user")
        validate_close_reason("   Valid reason with spaces   ")  # Should handle trimming
        
    def test_validate_close_reason_invalid(self):
        """Test invalid close reasons."""
        from app.status import validate_close_reason
        
        # Empty or None
        with pytest.raises(ValueError, match="Close reason is required"):
            validate_close_reason(None)
        
        with pytest.raises(ValueError, match="Close reason is required"):
            validate_close_reason("")
        
        with pytest.raises(ValueError, match="Close reason is required"):
            validate_close_reason("   ")  # After trimming, becomes empty
        
        # Too short
        with pytest.raises(ValueError, match="at least 3 characters"):
            validate_close_reason("Hi")
        
        # Too long
        long_reason = "x" * 201
        with pytest.raises(ValueError, match="cannot exceed 200 characters"):
            validate_close_reason(long_reason)
    
    def test_validate_ticket_closure_permission_admin(self):
        """Test admin can close any ticket."""
        from app.status import validate_ticket_closure_permission
        
        # Mock ticket
        class MockTicket:
            def __init__(self, creator_id=12345, assigned_to=None):
                self.creator_id = creator_id
                self.assigned_to = assigned_to
        
        # Admin can close any ticket
        ticket = MockTicket(creator_id=12345, assigned_to=67890)
        assert validate_ticket_closure_permission(ticket, 99999, "ADMIN") is True
    
    def test_validate_ticket_closure_permission_staff(self):
        """Test staff can close assigned tickets."""
        from app.status import validate_ticket_closure_permission
        
        class MockTicket:
            def __init__(self, creator_id=12345, assigned_to=None):
                self.creator_id = creator_id
                self.assigned_to = assigned_to
        
        # Staff can close tickets assigned to them
        ticket = MockTicket(creator_id=12345, assigned_to=67890)
        assert validate_ticket_closure_permission(ticket, 67890, "STAFF") is True
        
        # Staff with MANAGE_TICKETS can close any ticket (current implementation allows all staff)
        ticket = MockTicket(creator_id=12345, assigned_to=11111)
        assert validate_ticket_closure_permission(ticket, 67890, "STAFF") is True
    
    def test_validate_ticket_closure_permission_user(self):
        """Test users can only close their own tickets."""
        from app.status import validate_ticket_closure_permission
        
        class MockTicket:
            def __init__(self, creator_id=12345, assigned_to=None):
                self.creator_id = creator_id
                self.assigned_to = assigned_to
        
        # User can close their own ticket
        ticket = MockTicket(creator_id=12345)
        assert validate_ticket_closure_permission(ticket, 12345, "USER") is True
        
        # User cannot close others' tickets
        ticket = MockTicket(creator_id=67890)
        assert validate_ticket_closure_permission(ticket, 12345, "USER") is False
    
    def test_check_ticket_dependencies_no_issues(self):
        """Test dependency checking with no issues."""
        from app.status import check_ticket_dependencies
        
        class MockTicket:
            def __init__(self, status="open"):
                self.status = status
        
        ticket = MockTicket(status="open")
        issues = check_ticket_dependencies(ticket)
        assert issues == []
    
    def test_check_ticket_dependencies_already_closed(self):
        """Test dependency checking for already closed ticket."""
        from app.status import check_ticket_dependencies
        
        class MockTicket:
            def __init__(self, status="closed"):
                self.status = status
        
        ticket = MockTicket(status="closed")
        issues = check_ticket_dependencies(ticket)
        assert "already closed" in issues[0]
    
    def test_validate_ticket_closure_success(self):
        """Test successful ticket closure validation."""
        from app.status import validate_ticket_closure
        
        class MockTicket:
            def __init__(self):
                self.id = 123
                self.creator_id = 12345
                self.status = "open"
        
        ticket = MockTicket()
        # Should not raise any exception
        validate_ticket_closure(
            ticket=ticket,
            user_id=12345,
            user_role="USER",
            close_reason="Valid closure reason"
        )
    
    def test_validate_ticket_closure_invalid_reason(self):
        """Test ticket closure validation with invalid reason."""
        from app.status import validate_ticket_closure, TicketClosureError
        
        class MockTicket:
            def __init__(self):
                self.id = 123
                self.creator_id = 12345
                self.status = "open"
        
        ticket = MockTicket()
        with pytest.raises(TicketClosureError, match="Close reason is required"):
            validate_ticket_closure(
                ticket=ticket,
                user_id=12345,
                user_role="USER",
                close_reason=None
            )
    
    def test_validate_ticket_closure_no_permission(self):
        """Test ticket closure validation without permission."""
        from app.status import validate_ticket_closure, TicketClosureError
        
        class MockTicket:
            def __init__(self):
                self.id = 123
                self.creator_id = 12345
                self.status = "open"
        
        ticket = MockTicket()
        with pytest.raises(TicketClosureError, match="do not have permission"):
            validate_ticket_closure(
                ticket=ticket,
                user_id=67890,  # Different user
                user_role="USER",
                close_reason="Valid reason"
            )
    
    def test_validate_ticket_closure_already_closed(self):
        """Test ticket closure validation for already closed ticket."""
        from app.status import validate_ticket_closure, TicketClosureError
        
        class MockTicket:
            def __init__(self):
                self.id = 123
                self.creator_id = 12345
                self.status = "closed"
        
        ticket = MockTicket()
        with pytest.raises(TicketClosureError, match="already closed"):
            validate_ticket_closure(
                ticket=ticket,
                user_id=12345,
                user_role="USER",
                close_reason="Valid reason"
            )
    
    def test_create_closure_audit_entry(self):
        """Test creation of closure audit log entry."""
        from app.status import create_closure_audit_entry
        from datetime import datetime
        
        closed_at = datetime(2023, 6, 15, 10, 30, 0)
        entry = create_closure_audit_entry(
            ticket_id=123,
            user_id=12345,
            close_reason="Issue resolved",
            closed_at=closed_at
        )
        
        assert entry["action"] == "ticket_closed"
        assert entry["ticket_id"] == 123
        assert entry["user_id"] == 12345
        assert entry["timestamp"] == "2023-06-15T10:30:00"
        assert entry["details"]["close_reason"] == "Issue resolved"
        assert entry["details"]["closed_by"] == 12345


class TestTicketClosureError:
    """Test TicketClosureError exception."""
    
    def test_ticket_closure_error_creation(self):
        """Test TicketClosureError creation and message."""
        from app.status import TicketClosureError
        
        error = TicketClosureError(123, "Cannot close ticket")
        assert error.ticket_id == 123
        assert error.message == "Cannot close ticket"
        assert "Ticket 123: Cannot close ticket" in str(error)
    
    def test_ticket_closure_error_inheritance(self):
        """Test TicketClosureError inherits from Exception."""
        from app.status import TicketClosureError
        
        error = TicketClosureError(123, "Test message")
        assert isinstance(error, Exception)
