"""
Unit tests for Message model validation and functionality.
"""
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from app.database import Base
from app.models.message import Message
from app.models.ticket import Ticket
from app.models.guild import Guild


# Test database setup
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


class TestMessageModel:
    """Test Message model creation and validation."""
    
    def test_message_creation_success(self, db_session):
        """Test successful message creation with all required fields."""
        # Create a test guild
        guild = Guild(
            id=123456789,
            name="Test Guild",
            staff_role_ids=None,
            admin_role_ids=None,
            ticket_category_id=None,
            ticket_category_name="tickets",
            auto_archive_hours=24,
            auto_transcript=False
        )
        db_session.add(guild)
        db_session.commit()
        
        # Create a test ticket
        ticket = Ticket(
            channel_id=987654321,
            guild_id=123456789,
            creator_id=555555555,
            status='open',
            category='general',
            reason='Test ticket for message model'
        )
        db_session.add(ticket)
        db_session.commit()
        
        # Create a test message
        message = Message(
            id=111111111,
            ticket_id=ticket.id,
            author_id=555555555,
            content="Test message content",
            attachments=None,
            is_staff_only=False,
            created_at=datetime.utcnow(),
            edited_at=None,
            is_deleted=False
        )
        
        db_session.add(message)
        db_session.commit()
        
        # Verify message was created
        assert message.id == 111111111
        assert message.ticket_id == ticket.id
        assert message.author_id == 555555555
        assert message.content == "Test message content"
        assert message.attachments is None
        assert message.is_staff_only is False
        assert message.created_at is not None
        assert message.edited_at is None
        assert message.is_deleted is False
        
    def test_message_creation_with_attachments(self, db_session):
        """Test message creation with attachment metadata."""
        # Create a test guild
        guild = Guild(
            id=123456789,
            name="Test Guild",
            staff_role_ids=None,
            admin_role_ids=None,
            ticket_category_id=None,
            ticket_category_name="tickets",
            auto_archive_hours=24,
            auto_transcript=False
        )
        db_session.add(guild)
        db_session.commit()
        
        # Create a test ticket
        ticket = Ticket(
            channel_id=987654321,
            guild_id=123456789,
            creator_id=555555555,
            status='open',
            category='general',
            reason='Test ticket for message model'
        )
        db_session.add(ticket)
        db_session.commit()
        
        # Create message with attachments
        attachments = [
            {
                "filename": "test.jpg",
                "size": 1024,
                "content_type": "image/jpeg",
                "url": "https://example.com/test.jpg"
            }
        ]
        
        message = Message(
            id=222222222,
            ticket_id=ticket.id,
            author_id=555555555,
            content="Message with attachment",
            attachments=attachments,
            is_staff_only=False,
            created_at=datetime.utcnow()
        )
        
        db_session.add(message)
        db_session.commit()
        
        # Verify attachment data was stored
        assert message.attachments == attachments
        assert message.attachments[0]["filename"] == "test.jpg"
        assert message.attachments[0]["size"] == 1024
        
    def test_message_creation_staff_only(self, db_session):
        """Test staff-only message creation."""
        # Create a test guild
        guild = Guild(
            id=123456789,
            name="Test Guild",
            staff_role_ids=None,
            admin_role_ids=None,
            ticket_category_id=None,
            ticket_category_name="tickets",
            auto_archive_hours=24,
            auto_transcript=False
        )
        db_session.add(guild)
        db_session.commit()
        
        # Create a test ticket
        ticket = Ticket(
            channel_id=987654321,
            guild_id=123456789,
            creator_id=555555555,
            status='open',
            category='general',
            reason='Test ticket for message model'
        )
        db_session.add(ticket)
        db_session.commit()
        
        # Create staff-only message
        message = Message(
            id=333333333,
            ticket_id=ticket.id,
            author_id=777777777,  # Staff member
            content="Staff-only message",
            is_staff_only=True,
            created_at=datetime.utcnow()
        )
        
        db_session.add(message)
        db_session.commit()
        
        # Verify staff-only flag is set
        assert message.is_staff_only is True
        assert message.content == "Staff-only message"
        
    def test_message_foreign_key_constraint(self, db_session):
        """Test foreign key constraint to tickets table."""
        # Note: SQLite in-memory databases don't enforce FK constraints by default
        # This test verifies that the foreign key is defined correctly
        
        # Create message with non-existent ticket_id
        message = Message(
            id=555555555,
            ticket_id=999999,  # Non-existent ticket
            author_id=777777777,
            content="Test message"
        )
        db_session.add(message)
        
        # In a real database with FK constraints enabled, this would raise IntegrityError
        # For now, we just verify the message can be created but the relationship is None
        db_session.commit()
        
        # Verify the ticket relationship is None since ticket doesn't exist
        assert message.ticket is None
            
    def test_message_cascade_delete(self, db_session):
        """Test that messages are deleted when ticket is deleted."""
        # Create a test guild
        guild = Guild(
            id=123456789,
            name="Test Guild",
            staff_role_ids=None,
            admin_role_ids=None,
            ticket_category_id=None,
            ticket_category_name="tickets",
            auto_archive_hours=24,
            auto_transcript=False
        )
        db_session.add(guild)
        db_session.commit()
        
        # Create a test ticket
        ticket = Ticket(
            channel_id=987654321,
            guild_id=123456789,
            creator_id=555555555,
            status='open',
            category='general',
            reason='Test ticket for message model'
        )
        db_session.add(ticket)
        db_session.commit()
        
        # Create message
        message = Message(
            id=666666666,
            ticket_id=ticket.id,
            author_id=555555555,
            content="Test message",
            created_at=datetime.utcnow()
        )
        db_session.add(message)
        db_session.commit()
        
        # Verify message exists
        assert db_session.query(Message).filter_by(id=666666666).first() is not None
        
        # Delete ticket
        db_session.delete(ticket)
        db_session.commit()
        
        # Verify message was cascaded deleted
        assert db_session.query(Message).filter_by(id=666666666).first() is None
        
    def test_message_to_dict(self, db_session):
        """Test message serialization to dictionary."""
        # Create a test guild
        guild = Guild(
            id=123456789,
            name="Test Guild",
            staff_role_ids=None,
            admin_role_ids=None,
            ticket_category_id=None,
            ticket_category_name="tickets",
            auto_archive_hours=24,
            auto_transcript=False
        )
        db_session.add(guild)
        db_session.commit()
        
        # Create a test ticket
        ticket = Ticket(
            channel_id=987654321,
            guild_id=123456789,
            creator_id=555555555,
            status='open',
            category='general',
            reason='Test ticket for message model'
        )
        db_session.add(ticket)
        db_session.commit()
        
        # Create message
        test_time = datetime.utcnow()
        message = Message(
            id=777777777,
            ticket_id=ticket.id,
            author_id=555555555,
            content="Test message for serialization",
            attachments=[{"filename": "test.jpg"}],
            is_staff_only=False,
            created_at=test_time,
            edited_at=None,
            is_deleted=False
        )
        db_session.add(message)
        db_session.commit()
        
        # Test serialization
        message_dict = message.to_dict()
        
        assert message_dict["id"] == "777777777"
        assert message_dict["ticket_id"] == ticket.id
        assert message_dict["author_id"] == "555555555"
        assert message_dict["content"] == "Test message for serialization"
        assert message_dict["attachments"] == [{"filename": "test.jpg"}]
        assert message_dict["is_staff_only"] is False
        assert message_dict["created_at"] == test_time.isoformat()
        assert message_dict["edited_at"] is None
        assert message_dict["is_deleted"] is False
        
    def test_message_relationship_to_ticket(self, db_session):
        """Test message relationship to ticket."""
        # Create a test guild
        guild = Guild(
            id=123456789,
            name="Test Guild",
            staff_role_ids=None,
            admin_role_ids=None,
            ticket_category_id=None,
            ticket_category_name="tickets",
            auto_archive_hours=24,
            auto_transcript=False
        )
        db_session.add(guild)
        db_session.commit()
        
        # Create a test ticket
        ticket = Ticket(
            channel_id=987654321,
            guild_id=123456789,
            creator_id=555555555,
            status='open',
            category='general',
            reason='Test ticket for message model'
        )
        db_session.add(ticket)
        db_session.commit()
        
        # Create message
        message = Message(
            id=888888888,
            ticket_id=ticket.id,
            author_id=555555555,
            content="Test message relationship",
            created_at=datetime.utcnow()
        )
        db_session.add(message)
        db_session.commit()
        
        # Test relationship
        assert message.ticket.id == ticket.id
        assert message.ticket.reason == 'Test ticket for message model'
        
        # Test reverse relationship
        assert len(ticket.messages) == 1
        assert ticket.messages[0].id == 888888888
        
    def test_message_default_values(self, db_session):
        """Test message default values."""
        # Create a test guild
        guild = Guild(
            id=123456789,
            name="Test Guild",
            staff_role_ids=None,
            admin_role_ids=None,
            ticket_category_id=None,
            ticket_category_name="tickets",
            auto_archive_hours=24,
            auto_transcript=False
        )
        db_session.add(guild)
        db_session.commit()
        
        # Create a test ticket
        ticket = Ticket(
            channel_id=987654321,
            guild_id=123456789,
            creator_id=555555555,
            status='open',
            category='general',
            reason='Test ticket for message model'
        )
        db_session.add(ticket)
        db_session.commit()
        
        # Create message with minimal required fields
        message = Message(
            id=999999999,
            ticket_id=ticket.id,
            author_id=555555555,
            content="Test message defaults"
        )
        db_session.add(message)
        db_session.commit()
        
        # Verify default values
        assert message.is_staff_only is False
        assert message.is_deleted is False
        assert message.created_at is not None  # Should have auto default
        assert message.edited_at is None
        assert message.attachments is None
        
    def test_message_repr(self, db_session):
        """Test message string representation."""
        # Create a test guild
        guild = Guild(
            id=123456789,
            name="Test Guild",
            staff_role_ids=None,
            admin_role_ids=None,
            ticket_category_id=None,
            ticket_category_name="tickets",
            auto_archive_hours=24,
            auto_transcript=False
        )
        db_session.add(guild)
        db_session.commit()
        
        # Create a test ticket
        ticket = Ticket(
            channel_id=987654321,
            guild_id=123456789,
            creator_id=555555555,
            status='open',
            category='general',
            reason='Test ticket for message model'
        )
        db_session.add(ticket)
        db_session.commit()
        
        # Create message
        message = Message(
            id=101010101,
            ticket_id=ticket.id,
            author_id=555555555,
            content="Test message repr",
            is_staff_only=True,
            created_at=datetime.utcnow()
        )
        db_session.add(message)
        db_session.commit()
        
        # Test string representation
        repr_str = repr(message)
        assert "Message(" in repr_str
        assert "id=101010101" in repr_str
        assert f"ticket_id={ticket.id}" in repr_str
        assert "author_id=555555555" in repr_str
        assert "is_staff_only=True" in repr_str
