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
