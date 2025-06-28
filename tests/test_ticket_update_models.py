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
        with pytest.raises(ValueError, match="must be at most 100 characters"):
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
        
    @patch('app.models.ticket.get_ticket_by_id')
    def test_update_ticket_not_found(self, mock_get_ticket):
        """Test updating non-existent ticket."""
        from app.models.ticket import update_ticket
        
        mock_get_ticket.return_value = None
        
        with pytest.raises(ValueError, match="not found"):
            update_ticket(
                db=self.mock_db,
                ticket_id=999,
                user_id=self.test_user_id,
                status="in_progress"
            )
            
    @patch('app.models.ticket.get_ticket_by_id') 
    def test_update_ticket_status_change(self, mock_get_ticket):
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
        
        # Mock getattr calls
        def mock_getattr(obj, attr, default=None):
            if attr == 'status':
                return 'open'
            elif attr == 'category':
                return None
            elif attr == 'assigned_to':
                return None
            elif attr == 'close_reason':
                return None
            return default
            
        mock_get_ticket.return_value = mock_ticket
        
        with patch('builtins.getattr', side_effect=mock_getattr):
            with patch('builtins.setattr') as mock_setattr:
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
                
    @patch('app.models.ticket.get_ticket_by_id')
    def test_update_ticket_assignment(self, mock_get_ticket):
        """Test updating ticket assignment."""
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
        
        # Mock getattr calls
        def mock_getattr(obj, attr, default=None):
            if attr == 'status':
                return 'open'
            elif attr == 'category':
                return None
            elif attr == 'assigned_to':
                return None
            elif attr == 'close_reason':
                return None
            return default
            
        mock_get_ticket.return_value = mock_ticket
        
        staff_user_id = 987654321098765432
        
        with patch('builtins.getattr', side_effect=mock_getattr):
            with patch('builtins.setattr') as mock_setattr:
                result = update_ticket(
                    db=self.mock_db,
                    ticket_id=1,
                    user_id=self.test_user_id,
                    assigned_to=staff_user_id
                )
                
                # Verify assignment was set
                mock_setattr.assert_any_call(mock_ticket, 'assigned_to', staff_user_id)
                
                # Verify auto-transition to in_progress
                mock_ticket.update_status.assert_called_with(
                    new_status="in_progress",
                    changed_by=self.test_user_id
                )
