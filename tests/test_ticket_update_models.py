"""
Integration tests for ticket update functionality using manual endpoint testing.
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from app.schemas import TicketUpdateRequest
from app.status import TicketStatus


class TestTicketUpdateModels:
    """Test the ticket update models and validation."""
    
    def test_ticket_update_request_validation(self):
        """Test validation of ticket update request model."""
        # Valid request with all fields
        valid_request = TicketUpdateRequest(
            status="in_progress",
            category="bug", 
            assigned_to=123456789012345678,
            close_reason=None
        )
        assert valid_request.status == "in_progress"
        assert valid_request.category == "bug"
        assert valid_request.assigned_to == 123456789012345678
        
        # Valid request with only status
        status_only = TicketUpdateRequest(
            status="resolved",
            category=None,
            assigned_to=None,
            close_reason=None
        )
        assert status_only.status == "resolved"
        assert status_only.category is None
        
        # Valid request with all None (should work for partial updates)
        empty_request = TicketUpdateRequest(
            status=None,
            category=None,
            assigned_to=None,
            close_reason=None
        )
        assert empty_request.status is None
        
    def test_close_reason_validation(self):
        """Test close reason validation."""
        # Close reason required for closed status
        with pytest.raises(ValueError, match="close_reason is required"):
            TicketUpdateRequest(
                status="closed",
                category=None,
                assigned_to=None,
                close_reason=None
            )
        
        # Valid close with reason
        valid_close = TicketUpdateRequest(
            status="closed",
            category=None,
            assigned_to=None,
            close_reason="Issue resolved successfully"
        )
        assert valid_close.status == "closed"
        assert valid_close.close_reason == "Issue resolved successfully"
        
        # Close reason too short
        with pytest.raises(ValueError, match="must be at least 3 characters"):
            TicketUpdateRequest(
                status="closed",
                category=None,
                assigned_to=None,
                close_reason="xx"
            )
        
        # Close reason too long
        with pytest.raises(ValueError, match="must be at most 200 characters"):
            TicketUpdateRequest(
                status="closed",
                category=None,
                assigned_to=None,
                close_reason="x" * 201
            )
            
    def test_status_validation(self):
        """Test status validation."""
        # Invalid status
        with pytest.raises(ValueError, match="status must be one of"):
            TicketUpdateRequest(
                status="invalid_status",
                category=None,
                assigned_to=None,
                close_reason=None
            )
        
        # Valid statuses
        for status in ["open", "in_progress", "resolved", "closed"]:
            if status == "closed":
                # Closed requires close reason
                request = TicketUpdateRequest(
                    status=status,
                    category=None,
                    assigned_to=None,
                    close_reason="Valid reason"
                )
            else:
                request = TicketUpdateRequest(
                    status=status,
                    category=None,
                    assigned_to=None,
                    close_reason=None
                )
            assert request.status == status
            
    def test_assigned_to_validation(self):
        """Test assigned_to validation."""
        # Invalid assigned_to (too short)
        with pytest.raises(ValueError, match="valid Discord snowflake"):
            TicketUpdateRequest(
                status=None,
                category=None,
                assigned_to=123,  # Too short
                close_reason=None
            )
        
        # Invalid assigned_to (too long)
        with pytest.raises(ValueError, match="valid Discord snowflake"):
            TicketUpdateRequest(
                status=None,
                category=None,
                assigned_to=12345678901234567890,  # Too long
                close_reason=None
            )
        
        # Invalid assigned_to (negative)
        with pytest.raises(ValueError, match="positive integer"):
            TicketUpdateRequest(
                status=None,
                category=None,
                assigned_to=-123456789012345678,
                close_reason=None
            )
        
        # Valid assigned_to
        valid_request = TicketUpdateRequest(
            status=None,
            category=None,
            assigned_to=123456789012345678,
            close_reason=None
        )
        assert valid_request.assigned_to == 123456789012345678
        
    def test_category_validation(self):
        """Test category validation."""
        # Valid category
        valid_request = TicketUpdateRequest(
            status=None,
            category="support",
            assigned_to=None,
            close_reason=None
        )
        assert valid_request.category == "support"
        
        # Empty category becomes None
        empty_category = TicketUpdateRequest(
            status=None,
            category="   ",  # Whitespace only
            assigned_to=None,
            close_reason=None
        )
        assert empty_category.category is None
        
        # Category too long
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="String should have at most 100 characters"):
            TicketUpdateRequest(
                status=None,
                category="x" * 101,
                assigned_to=None,
                close_reason=None
            )


class TestTicketUpdateFunction:
    """Test the ticket update function in isolation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db = Mock()
        self.test_user_id = 123456789012345678
        
    def test_update_ticket_not_found(self):
        """Test updating non-existent ticket."""
        from app.models.ticket import update_ticket
        
        # Mock db.query to return no ticket
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(ValueError, match="not found"):
            update_ticket(
                db=self.mock_db,
                ticket_id=999,
                user_id=self.test_user_id,
                status="in_progress"
            )
            
    def test_update_ticket_status_change(self):
        """Test updating ticket status."""
        from app.models.ticket import update_ticket
        
        # Mock existing ticket
        mock_ticket = Mock()
        mock_ticket.id = 1
        mock_ticket.status = "open"
        mock_ticket.category = None
        mock_ticket.assigned_to = None
        mock_ticket.close_reason = None
        
        # Mock update_status method
        mock_ticket.update_status = Mock()
        
        # Mock db.query to return the ticket
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_ticket
        
        result = update_ticket(
            db=self.mock_db,
            ticket_id=1,
            user_id=self.test_user_id,
            status="in_progress"
        )
        
        # Verify status update was called
        mock_ticket.update_status.assert_called_once_with(
            new_status="in_progress",
            changed_by=self.test_user_id,
            close_reason=None
        )
        
        # Verify database operations
        self.mock_db.add.assert_called_once_with(mock_ticket)
        self.mock_db.commit.assert_called_once()
        self.mock_db.refresh.assert_called_once_with(mock_ticket)
                
    def test_update_ticket_assignment(self):
        """Test updating ticket assignment."""
        from app.models.ticket import update_ticket
        from app.status import TicketStatus
        
        # Mock existing ticket
        mock_ticket = Mock()
        mock_ticket.id = 1
        mock_ticket.status = TicketStatus.OPEN.value
        mock_ticket.category = None
        mock_ticket.assigned_to = None
        mock_ticket.close_reason = None
        
        # Mock update_status method
        mock_ticket.update_status = Mock()
        
        # Mock db.query to return the ticket
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_ticket
        
        staff_user_id = 987654321098765432
        
        result = update_ticket(
            db=self.mock_db,
            ticket_id=1,
            user_id=self.test_user_id,
            assigned_to=staff_user_id
        )
        
        # Verify assignment was set
        assert mock_ticket.assigned_to == staff_user_id
        
        # Verify auto-transition to in_progress
        mock_ticket.update_status.assert_called_with(
            new_status="in_progress",
            changed_by=self.test_user_id
        )
