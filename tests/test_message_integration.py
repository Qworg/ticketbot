"""
Integration tests for message database saving functionality.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.message import Message
from app.models.ticket import Ticket
from app.models.guild import Guild
from app.services.message_service import (
    save_discord_message,
    update_message_content,
    soft_delete_message,
    get_ticket_by_channel,
    is_user_staff,
    extract_attachment_metadata
)


class TestMessageDatabaseIntegration:
    """Integration tests for message database operations."""
    
    @pytest.fixture(autouse=True)
    def setup_database(self):
        """Set up in-memory database for testing."""
        # Create in-memory SQLite database
        self.engine = create_engine('sqlite:///:memory:', echo=False)
        Base.metadata.create_all(self.engine)
        
        # Create session factory
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        # Create test guild
        self.guild = Guild(
            id=123456789,
            name="Test Guild",
            staff_role_ids=[987654321],
            admin_role_ids=[987654322],
            ticket_category_id=111111111,
            created_at=datetime.utcnow()
        )
        self.session.add(self.guild)
        
        # Create test ticket
        self.ticket = Ticket(
            id=1,
            channel_id=222222222,
            guild_id=123456789,
            creator_id=333333333,
            assigned_to=None,
            status='open',
            category='general',
            reason='Test ticket',
            created_at=datetime.utcnow()
        )
        self.session.add(self.ticket)
        
        self.session.commit()
        
        yield
        
        # Cleanup
        self.session.close()
    
    def test_save_discord_message_success(self):
        """Test successful Discord message saving."""
        message_id = 444444444
        content = "Test message content"
        attachments = [{"filename": "test.jpg", "size": 1024, "content_type": "image/jpeg"}]
        
        # Save message
        saved_message = save_discord_message(
            db=self.session,
            message_id=message_id,
            ticket_id=self.ticket.id,
            author_id=333333333,
            content=content,
            attachments=attachments,
            is_staff_only=False,
            created_at=datetime.utcnow()
        )
        
        # Verify message was saved
        assert saved_message is not None
        assert saved_message.id == message_id
        assert saved_message.content == content
        assert saved_message.attachments == attachments
        assert saved_message.is_staff_only == False
        assert saved_message.is_deleted == False
        
        # Verify in database
        db_message = self.session.query(Message).filter(Message.id == message_id).first()
        assert db_message is not None
        assert db_message.content == content
    
    def test_save_discord_message_duplicate(self):
        """Test saving duplicate message returns existing message."""
        message_id = 555555555
        content = "Original content"
        
        # Save first message
        first_message = save_discord_message(
            db=self.session,
            message_id=message_id,
            ticket_id=self.ticket.id,
            author_id=333333333,
            content=content,
            is_staff_only=False
        )
        
        # Try to save duplicate
        duplicate_message = save_discord_message(
            db=self.session,
            message_id=message_id,
            ticket_id=self.ticket.id,
            author_id=333333333,
            content="Different content",
            is_staff_only=True
        )
        
        # Should return existing message
        assert duplicate_message.id == first_message.id
        assert duplicate_message.content == content  # Original content preserved
        assert duplicate_message.is_staff_only == False  # Original flag preserved
    
    def test_update_message_content_success(self):
        """Test successful message content update."""
        message_id = 666666666
        original_content = "Original content"
        updated_content = "Updated content"
        
        # Save original message
        save_discord_message(
            db=self.session,
            message_id=message_id,
            ticket_id=self.ticket.id,
            author_id=333333333,
            content=original_content,
            is_staff_only=False
        )
        
        # Update message content
        edit_time = datetime.utcnow()
        success = update_message_content(
            db=self.session,
            message_id=message_id,
            new_content=updated_content,
            edited_at=edit_time
        )
        
        # Verify update was successful
        assert success == True
        
        # Verify in database
        db_message = self.session.query(Message).filter(Message.id == message_id).first()
        assert db_message.content == updated_content
        assert db_message.edited_at == edit_time
    
    def test_update_message_content_not_found(self):
        """Test updating non-existent message returns False."""
        success = update_message_content(
            db=self.session,
            message_id=999999999,
            new_content="New content"
        )
        
        assert success == False
    
    def test_soft_delete_message_success(self):
        """Test successful message soft deletion."""
        message_id = 777777777
        
        # Save message
        save_discord_message(
            db=self.session,
            message_id=message_id,
            ticket_id=self.ticket.id,
            author_id=333333333,
            content="Message to delete",
            is_staff_only=False
        )
        
        # Soft delete message
        success = soft_delete_message(
            db=self.session,
            message_id=message_id
        )
        
        # Verify deletion was successful
        assert success == True
        
        # Verify message is marked as deleted but still exists
        db_message = self.session.query(Message).filter(Message.id == message_id).first()
        assert db_message is not None
        assert db_message.is_deleted == True
        assert db_message.content == "Message to delete"  # Content preserved
    
    def test_soft_delete_message_not_found(self):
        """Test soft deleting non-existent message returns False."""
        success = soft_delete_message(
            db=self.session,
            message_id=888888888
        )
        
        assert success == False
    
    def test_get_ticket_by_channel_success(self):
        """Test successful ticket retrieval by channel ID."""
        ticket = get_ticket_by_channel(
            db=self.session,
            channel_id=self.ticket.channel_id
        )
        
        assert ticket is not None
        assert ticket.id == self.ticket.id
        assert ticket.channel_id == self.ticket.channel_id
    
    def test_get_ticket_by_channel_not_found(self):
        """Test ticket retrieval for non-existent channel returns None."""
        ticket = get_ticket_by_channel(
            db=self.session,
            channel_id=999999999
        )
        
        assert ticket is None
    
    def test_is_user_staff_with_staff_role(self):
        """Test staff check with user having staff role."""
        user_roles = [987654321, 123456789]  # Includes staff role
        
        is_staff = is_user_staff(
            db=self.session,
            user_id=333333333,
            guild_id=self.guild.id,
            user_roles=user_roles
        )
        
        assert is_staff == True
    
    def test_is_user_staff_with_admin_role(self):
        """Test staff check with user having admin role."""
        user_roles = [987654322, 123456789]  # Includes admin role
        
        is_staff = is_user_staff(
            db=self.session,
            user_id=333333333,
            guild_id=self.guild.id,
            user_roles=user_roles
        )
        
        assert is_staff == True
    
    def test_is_user_staff_no_staff_role(self):
        """Test staff check with user having no staff roles."""
        user_roles = [123456789, 987654320]  # No staff roles
        
        is_staff = is_user_staff(
            db=self.session,
            user_id=333333333,
            guild_id=self.guild.id,
            user_roles=user_roles
        )
        
        assert is_staff == False
    
    def test_extract_attachment_metadata(self):
        """Test attachment metadata extraction."""
        # Mock Discord attachment objects
        mock_attachment1 = Mock()
        mock_attachment1.filename = "image.jpg"
        mock_attachment1.size = 1024
        mock_attachment1.content_type = "image/jpeg"
        mock_attachment1.url = "https://example.com/image.jpg"
        mock_attachment1.proxy_url = "https://proxy.example.com/image.jpg"
        mock_attachment1.width = 800
        mock_attachment1.height = 600
        
        attachments = [mock_attachment1]
        
        # Extract metadata
        metadata = extract_attachment_metadata(attachments)
        
        # Verify metadata
        assert len(metadata) == 1
        
        # Check attachment
        assert metadata[0]["filename"] == "image.jpg"
        assert metadata[0]["size"] == 1024
        assert metadata[0]["content_type"] == "image/jpeg"
        assert metadata[0]["url"] == "https://example.com/image.jpg"
        # Note: Mock objects will return Mock for proxy_url, width, height
        # This is acceptable for testing the basic functionality
    
    def test_extract_attachment_metadata_empty(self):
        """Test attachment metadata extraction with empty list."""
        metadata = extract_attachment_metadata([])
        assert metadata == []
    
    def test_extract_attachment_metadata_error(self):
        """Test attachment metadata extraction with error."""
        # Create an object that will raise an exception during iteration
        class BadAttachment:
            @property
            def filename(self):
                raise Exception("Attachment error")
        
        attachments = [BadAttachment()]
        
        # Should not raise exception and return empty list due to error handling
        metadata = extract_attachment_metadata(attachments)
        assert metadata == []
    
    def test_message_database_cascade_delete(self):
        """Test that messages are deleted when ticket is deleted."""
        # Save a message
        message_id = 111111111
        save_discord_message(
            db=self.session,
            message_id=message_id,
            ticket_id=self.ticket.id,
            author_id=333333333,
            content="Test message",
            is_staff_only=False
        )
        
        # Verify message exists
        db_message = self.session.query(Message).filter(Message.id == message_id).first()
        assert db_message is not None
        
        # Delete ticket
        self.session.delete(self.ticket)
        self.session.commit()
        
        # Verify message was cascaded deleted
        db_message = self.session.query(Message).filter(Message.id == message_id).first()
        assert db_message is None
