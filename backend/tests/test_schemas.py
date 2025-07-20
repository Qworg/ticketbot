"""
Unit tests for Pydantic models in the Discord Ticket Bot system.
"""

import uuid
import pytest
from datetime import datetime
from pydantic import ValidationError

from schemas import (
    TicketBase, TicketCreate, TicketUpdate, Ticket,
    MessageBase, MessageCreate, Message,
    TranscriptBase, TranscriptCreate, TranscriptUpdate, Transcript,
    StaffBase, StaffCreate, StaffUpdate, Staff,
    TicketStatus, Priority, MessageType, StaffRole
)


class TestTicketModels:
    """Test cases for Ticket-related Pydantic models."""
    
    def test_ticket_base_valid(self):
        """Test that a valid TicketBase model can be created."""
        ticket = TicketBase(
            title="Test Ticket",
            description="This is a test ticket",
            priority=Priority.HIGH
        )
        assert ticket.title == "Test Ticket"
        assert ticket.description == "This is a test ticket"
        assert ticket.priority == Priority.HIGH
    
    def test_ticket_base_default_priority(self):
        """Test that TicketBase uses the default priority if not provided."""
        ticket = TicketBase(title="Test Ticket")
        assert ticket.priority == Priority.MEDIUM
    
    def test_ticket_base_empty_title(self):
        """Test that TicketBase raises an error for an empty title."""
        with pytest.raises(ValidationError):
            TicketBase(title="")
    
    def test_ticket_base_whitespace_title(self):
        """Test that TicketBase raises an error for a whitespace-only title."""
        with pytest.raises(ValidationError):
            TicketBase(title="   ")
    
    def test_ticket_create_valid(self):
        """Test that a valid TicketCreate model can be created."""
        ticket = TicketCreate(
            title="Test Ticket",
            description="This is a test ticket",
            priority=Priority.HIGH,
            creator_discord_id=123456789012345678,
            discord_channel_id=234567890123456789
        )
        assert ticket.title == "Test Ticket"
        assert ticket.creator_discord_id == 123456789012345678
        assert ticket.discord_channel_id == 234567890123456789
    
    def test_ticket_create_invalid_discord_id(self):
        """Test that TicketCreate raises an error for an invalid Discord ID."""
        with pytest.raises(ValidationError):
            TicketCreate(
                title="Test Ticket",
                creator_discord_id=-1,  # Invalid negative ID
                discord_channel_id=234567890123456789
            )
    
    def test_ticket_update_valid(self):
        """Test that a valid TicketUpdate model can be created."""
        ticket = TicketUpdate(
            title="Updated Title",
            status=TicketStatus.IN_PROGRESS,
            assigned_staff_id=123456789012345678
        )
        assert ticket.title == "Updated Title"
        assert ticket.status == TicketStatus.IN_PROGRESS
        assert ticket.assigned_staff_id == 123456789012345678
    
    def test_ticket_update_empty(self):
        """Test that TicketUpdate raises an error when no fields are provided."""
        with pytest.raises(ValidationError):
            TicketUpdate()
    
    def test_ticket_full_model(self):
        """Test that a complete Ticket model can be created."""
        ticket_id = uuid.uuid4()
        now = datetime.now()
        
        ticket = Ticket(
            id=ticket_id,
            title="Test Ticket",
            description="This is a test ticket",
            priority=Priority.HIGH,
            status=TicketStatus.OPEN,
            creator_discord_id=123456789012345678,
            discord_channel_id=234567890123456789,
            created_at=now,
            updated_at=now
        )
        
        assert ticket.id == ticket_id
        assert ticket.title == "Test Ticket"
        assert ticket.status == TicketStatus.OPEN
        assert ticket.created_at == now
        assert ticket.closed_at is None


class TestMessageModels:
    """Test cases for Message-related Pydantic models."""
    
    def test_message_base_valid(self):
        """Test that a valid MessageBase model can be created."""
        message = MessageBase(
            content="This is a test message",
            message_type=MessageType.USER_MESSAGE
        )
        assert message.content == "This is a test message"
        assert message.message_type == MessageType.USER_MESSAGE
    
    def test_message_base_default_type(self):
        """Test that MessageBase uses the default message type if not provided."""
        message = MessageBase(content="This is a test message")
        assert message.message_type == MessageType.USER_MESSAGE
    
    def test_message_base_empty_content(self):
        """Test that MessageBase raises an error for empty content."""
        with pytest.raises(ValidationError):
            MessageBase(content="")
    
    def test_message_base_whitespace_content(self):
        """Test that MessageBase raises an error for whitespace-only content."""
        with pytest.raises(ValidationError):
            MessageBase(content="   ")
    
    def test_message_create_valid(self):
        """Test that a valid MessageCreate model can be created."""
        ticket_id = uuid.uuid4()
        
        message = MessageCreate(
            content="This is a test message",
            message_type=MessageType.STAFF_MESSAGE,
            ticket_id=ticket_id,
            author_discord_id=123456789012345678,
            discord_message_id=234567890123456789
        )
        
        assert message.content == "This is a test message"
        assert message.message_type == MessageType.STAFF_MESSAGE
        assert message.ticket_id == ticket_id
        assert message.author_discord_id == 123456789012345678
        assert message.discord_message_id == 234567890123456789
    
    def test_message_create_invalid_author_id(self):
        """Test that MessageCreate raises an error for an invalid author ID."""
        with pytest.raises(ValidationError):
            MessageCreate(
                content="This is a test message",
                ticket_id=uuid.uuid4(),
                author_discord_id=-1  # Invalid negative ID
            )
    
    def test_message_full_model(self):
        """Test that a complete Message model can be created."""
        message_id = uuid.uuid4()
        ticket_id = uuid.uuid4()
        now = datetime.now()
        
        message = Message(
            id=message_id,
            content="This is a test message",
            message_type=MessageType.SYSTEM_MESSAGE,
            ticket_id=ticket_id,
            author_discord_id=123456789012345678,
            discord_message_id=234567890123456789,
            created_at=now
        )
        
        assert message.id == message_id
        assert message.content == "This is a test message"
        assert message.message_type == MessageType.SYSTEM_MESSAGE
        assert message.ticket_id == ticket_id
        assert message.created_at == now


class TestTranscriptModels:
    """Test cases for Transcript-related Pydantic models."""
    
    def test_transcript_base_valid(self):
        """Test that a valid TranscriptBase model can be created."""
        transcript = TranscriptBase(
            content="This is a test transcript",
            formatted_content={"messages": [{"content": "Test message"}]}
        )
        assert transcript.content == "This is a test transcript"
        assert transcript.formatted_content["messages"][0]["content"] == "Test message"
    
    def test_transcript_base_no_formatted_content(self):
        """Test that TranscriptBase can be created without formatted content."""
        transcript = TranscriptBase(content="This is a test transcript")
        assert transcript.content == "This is a test transcript"
        assert transcript.formatted_content is None
    
    def test_transcript_create_valid(self):
        """Test that a valid TranscriptCreate model can be created."""
        ticket_id = uuid.uuid4()
        
        transcript = TranscriptCreate(
            content="This is a test transcript",
            ticket_id=ticket_id
        )
        
        assert transcript.content == "This is a test transcript"
        assert transcript.ticket_id == ticket_id
    
    def test_transcript_update_valid(self):
        """Test that a valid TranscriptUpdate model can be created."""
        transcript = TranscriptUpdate(
            content="Updated transcript content",
            share_token="test-share-token"
        )
        
        assert transcript.content == "Updated transcript content"
        assert transcript.share_token == "test-share-token"
    
    def test_transcript_update_empty(self):
        """Test that TranscriptUpdate can be created with no fields."""
        transcript = TranscriptUpdate()
        assert transcript.content is None
        assert transcript.formatted_content is None
        assert transcript.share_token is None
    
    def test_transcript_full_model(self):
        """Test that a complete Transcript model can be created."""
        transcript_id = uuid.uuid4()
        ticket_id = uuid.uuid4()
        now = datetime.now()
        
        transcript = Transcript(
            id=transcript_id,
            ticket_id=ticket_id,
            content="This is a test transcript",
            formatted_content={"messages": [{"content": "Test message"}]},
            share_token="test-share-token",
            created_at=now,
            updated_at=now
        )
        
        assert transcript.id == transcript_id
        assert transcript.ticket_id == ticket_id
        assert transcript.content == "This is a test transcript"
        assert transcript.share_token == "test-share-token"
        assert transcript.created_at == now
        assert transcript.updated_at == now


class TestStaffModels:
    """Test cases for Staff-related Pydantic models."""
    
    def test_staff_base_valid(self):
        """Test that a valid StaffBase model can be created."""
        staff = StaffBase(
            discord_id=123456789012345678,
            username="test_user",
            role=StaffRole.ADMIN,
            permissions={"manage_tickets": True, "manage_staff": True},
            active=True
        )
        
        assert staff.discord_id == 123456789012345678
        assert staff.username == "test_user"
        assert staff.role == StaffRole.ADMIN
        assert staff.permissions["manage_tickets"] is True
        assert staff.active is True
    
    def test_staff_base_default_values(self):
        """Test that StaffBase uses default values if not provided."""
        staff = StaffBase(
            discord_id=123456789012345678,
            username="test_user"
        )
        
        assert staff.role == StaffRole.SUPPORT
        assert staff.permissions == {}
        assert staff.active is True
    
    def test_staff_base_invalid_discord_id(self):
        """Test that StaffBase raises an error for an invalid Discord ID."""
        with pytest.raises(ValidationError):
            StaffBase(
                discord_id=-1,  # Invalid negative ID
                username="test_user"
            )
    
    def test_staff_base_empty_username(self):
        """Test that StaffBase raises an error for an empty username."""
        with pytest.raises(ValidationError):
            StaffBase(
                discord_id=123456789012345678,
                username=""
            )
    
    def test_staff_create_valid(self):
        """Test that a valid StaffCreate model can be created."""
        staff = StaffCreate(
            discord_id=123456789012345678,
            username="test_user",
            role=StaffRole.MODERATOR
        )
        
        assert staff.discord_id == 123456789012345678
        assert staff.username == "test_user"
        assert staff.role == StaffRole.MODERATOR
    
    def test_staff_update_valid(self):
        """Test that a valid StaffUpdate model can be created."""
        staff = StaffUpdate(
            username="updated_user",
            role=StaffRole.ADMIN,
            active=False
        )
        
        assert staff.username == "updated_user"
        assert staff.role == StaffRole.ADMIN
        assert staff.active is False
    
    def test_staff_update_empty(self):
        """Test that StaffUpdate can be created with no fields."""
        staff = StaffUpdate()
        assert staff.username is None
        assert staff.role is None
        assert staff.permissions is None
        assert staff.active is None
    
    def test_staff_full_model(self):
        """Test that a complete Staff model can be created."""
        staff_id = uuid.uuid4()
        now = datetime.now()
        
        staff = Staff(
            id=staff_id,
            discord_id=123456789012345678,
            username="test_user",
            role=StaffRole.ADMIN,
            permissions={"manage_tickets": True, "manage_staff": True},
            active=True,
            created_at=now
        )
        
        assert staff.id == staff_id
        assert staff.discord_id == 123456789012345678
        assert staff.username == "test_user"
        assert staff.role == StaffRole.ADMIN
        assert staff.created_at == now