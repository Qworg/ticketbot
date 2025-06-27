"""
Unit tests for the Ticket model.
Tests ticket creation, validation, and model methods.
"""
import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from app.models.ticket import Ticket
from app.database import get_db_session


class TestTicketModel:
    """Test cases for the Ticket model."""

    def test_ticket_creation(self):
        """Test basic ticket creation with required fields."""
        ticket = Ticket(
            channel_id=123456789012345678,
            guild_id=987654321098765432,
            creator_id=111222333444555666,
            reason="Test ticket for bug report"
        )
        
        assert ticket.channel_id == 123456789012345678
        assert ticket.guild_id == 987654321098765432
        assert ticket.creator_id == 111222333444555666
        assert ticket.reason == "Test ticket for bug report"
        assert ticket.status == "open"  # Default status
        assert ticket.assigned_to is None  # Default unassigned
        assert ticket.is_shadow_closed is False  # Default not shadow closed

    def test_ticket_with_all_fields(self):
        """Test ticket creation with all optional fields."""
        ticket = Ticket(
            channel_id=123456789012345678,
            guild_id=987654321098765432,
            creator_id=111222333444555666,
            assigned_to=777888999000111222,
            status="in_progress",
            category="bug_report",
            reason="Critical bug in user authentication",
            close_reason="Fixed in version 1.2.3",
            is_shadow_closed=True
        )
        
        assert ticket.assigned_to == 777888999000111222
        assert ticket.status == "in_progress"
        assert ticket.category == "bug_report"
        assert ticket.close_reason == "Fixed in version 1.2.3"
        assert ticket.is_shadow_closed is True

    def test_ticket_repr(self):
        """Test string representation of ticket."""
        ticket = Ticket(
            channel_id=123456789012345678,
            guild_id=987654321098765432,
            creator_id=111222333444555666,
            reason="Test ticket",
            status="open"
        )
        
        expected = "<Ticket(id=None, channel_id=123456789012345678, status='open', creator_id=111222333444555666)>"
        assert repr(ticket) == expected

    def test_is_open_method(self):
        """Test is_open method for different statuses."""
        # Test open status
        ticket_open = Ticket(
            channel_id=123456789012345678,
            guild_id=987654321098765432,
            creator_id=111222333444555666,
            reason="Test ticket",
            status="open"
        )
        assert ticket_open.is_open() is True
        
        # Test in_progress status
        ticket_in_progress = Ticket(
            channel_id=123456789012345679,
            guild_id=987654321098765432,
            creator_id=111222333444555666,
            reason="Test ticket",
            status="in_progress"
        )
        assert ticket_in_progress.is_open() is True
        
        # Test closed status
        ticket_closed = Ticket(
            channel_id=123456789012345680,
            guild_id=987654321098765432,
            creator_id=111222333444555666,
            reason="Test ticket",
            status="closed"
        )
        assert ticket_closed.is_open() is False

    def test_is_closed_method(self):
        """Test is_closed method for different statuses."""
        # Test closed status
        ticket_closed = Ticket(
            channel_id=123456789012345678,
            guild_id=987654321098765432,
            creator_id=111222333444555666,
            reason="Test ticket",
            status="closed"
        )
        assert ticket_closed.is_closed() is True
        
        # Test open status
        ticket_open = Ticket(
            channel_id=123456789012345679,
            guild_id=987654321098765432,
            creator_id=111222333444555666,
            reason="Test ticket",
            status="open"
        )
        assert ticket_open.is_closed() is False

    def test_can_be_assigned_method(self):
        """Test can_be_assigned method for different statuses."""
        # Test open ticket
        ticket_open = Ticket(
            channel_id=123456789012345678,
            guild_id=987654321098765432,
            creator_id=111222333444555666,
            reason="Test ticket",
            status="open"
        )
        assert ticket_open.can_be_assigned() is True
        
        # Test in_progress ticket
        ticket_in_progress = Ticket(
            channel_id=123456789012345679,
            guild_id=987654321098765432,
            creator_id=111222333444555666,
            reason="Test ticket",
            status="in_progress"
        )
        assert ticket_in_progress.can_be_assigned() is True
        
        # Test closed ticket
        ticket_closed = Ticket(
            channel_id=123456789012345680,
            guild_id=987654321098765432,
            creator_id=111222333444555666,
            reason="Test ticket",
            status="closed"
        )
        assert ticket_closed.can_be_assigned() is False

    def test_to_dict_method(self):
        """Test to_dict method conversion."""
        # Create a ticket instance
        ticket = Ticket(
            channel_id=123456789012345678,
            guild_id=987654321098765432,
            creator_id=111222333444555666,
            assigned_to=777888999000111222,
            status="in_progress",
            category="bug_report",
            reason="Test ticket reason",
            close_reason="Test close reason",
            is_shadow_closed=False
        )
        
        # Convert to dict
        ticket_dict = ticket.to_dict()
        
        # Verify required fields
        assert ticket_dict['channel_id'] == 123456789012345678
        assert ticket_dict['guild_id'] == 987654321098765432
        assert ticket_dict['creator_id'] == 111222333444555666
        assert ticket_dict['assigned_to'] == 777888999000111222
        assert ticket_dict['status'] == "in_progress"
        assert ticket_dict['category'] == "bug_report"
        assert ticket_dict['reason'] == "Test ticket reason"
        assert ticket_dict['close_reason'] == "Test close reason"
        assert ticket_dict['is_shadow_closed'] is False
        
        # Check that dict contains all expected keys
        expected_keys = {
            'id', 'channel_id', 'guild_id', 'creator_id', 'assigned_to',
            'status', 'category', 'reason', 'created_at', 'updated_at',
            'closed_at', 'close_reason', 'is_shadow_closed'
        }
        assert set(ticket_dict.keys()) == expected_keys


class TestTicketDatabaseValidation:
    """Test cases for ticket database validation and constraints."""
    
    @pytest.fixture
    def db_session(self):
        """Create a database session for testing."""
        session = get_db_session()
        yield session
        session.close()

    def test_ticket_database_creation(self, db_session):
        """Test creating a ticket in the database."""
        ticket = Ticket(
            channel_id=123456789012345678,
            guild_id=987654321098765432,
            creator_id=111222333444555666,
            reason="Database test ticket"
        )
        
        db_session.add(ticket)
        db_session.commit()
        
        # Verify ticket was created
        assert ticket.id is not None
        assert ticket.created_at is not None
        assert ticket.updated_at is not None
        
        # Clean up
        db_session.delete(ticket)
        db_session.commit()

    def test_unique_channel_id_constraint(self, db_session):
        """Test that channel_id must be unique."""
        channel_id = 123456789012345678
        
        # Create first ticket
        ticket1 = Ticket(
            channel_id=channel_id,
            guild_id=987654321098765432,
            creator_id=111222333444555666,
            reason="First ticket"
        )
        db_session.add(ticket1)
        db_session.commit()
        
        # Try to create second ticket with same channel_id
        ticket2 = Ticket(
            channel_id=channel_id,  # Same channel_id
            guild_id=987654321098765433,
            creator_id=111222333444555667,
            reason="Second ticket"
        )
        db_session.add(ticket2)
        
        # Should raise IntegrityError due to unique constraint
        with pytest.raises(IntegrityError):
            db_session.commit()
        
        # Clean up
        db_session.rollback()
        db_session.delete(ticket1)
        db_session.commit()

    def test_required_fields_validation(self, db_session):
        """Test that required fields cannot be null."""
        # Test missing channel_id
        with pytest.raises(IntegrityError):
            ticket = Ticket(
                guild_id=987654321098765432,
                creator_id=111222333444555666,
                reason="Test ticket"
            )
            db_session.add(ticket)
            db_session.commit()
        
        db_session.rollback()
        
        # Test missing guild_id
        with pytest.raises(IntegrityError):
            ticket = Ticket(
                channel_id=123456789012345678,
                creator_id=111222333444555666,
                reason="Test ticket"
            )
            db_session.add(ticket)
            db_session.commit()
        
        db_session.rollback()
        
        # Test missing creator_id
        with pytest.raises(IntegrityError):
            ticket = Ticket(
                channel_id=123456789012345678,
                guild_id=987654321098765432,
                reason="Test ticket"
            )
            db_session.add(ticket)
            db_session.commit()
        
        db_session.rollback()
        
        # Test missing reason
        with pytest.raises(IntegrityError):
            ticket = Ticket(
                channel_id=123456789012345678,
                guild_id=987654321098765432,
                creator_id=111222333444555666
            )
            db_session.add(ticket)
            db_session.commit()
        
        db_session.rollback()

    def test_ticket_query_operations(self, db_session):
        """Test basic query operations on tickets."""
        # Create test tickets
        ticket1 = Ticket(
            channel_id=123456789012345678,
            guild_id=987654321098765432,
            creator_id=111222333444555666,
            status="open",
            reason="First test ticket"
        )
        ticket2 = Ticket(
            channel_id=123456789012345679,
            guild_id=987654321098765432,
            creator_id=111222333444555667,
            status="closed",
            reason="Second test ticket"
        )
        
        db_session.add_all([ticket1, ticket2])
        db_session.commit()
        
        try:
            # Test query by guild_id
            guild_tickets = db_session.query(Ticket).filter_by(guild_id=987654321098765432).all()
            assert len(guild_tickets) == 2
            
            # Test query by status
            open_tickets = db_session.query(Ticket).filter_by(status="open").all()
            assert len(open_tickets) >= 1
            assert ticket1 in open_tickets
            
            # Test query by creator_id
            user_tickets = db_session.query(Ticket).filter_by(creator_id=111222333444555666).all()
            assert len(user_tickets) >= 1
            assert ticket1 in user_tickets
            
        finally:
            # Clean up
            db_session.delete(ticket1)
            db_session.delete(ticket2)
            db_session.commit()
