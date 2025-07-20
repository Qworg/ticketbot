"""Tests for database service layer."""

import pytest
import uuid
from datetime import datetime, timedelta
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text

from backend.tests.test_models import Base, Ticket, Message, Transcript, Staff, TicketStatus, MessageType, StaffRole
from backend.database_service import DatabaseService


# Test database URL - using in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"




@pytest.fixture
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Clean up
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = async_sessionmaker(test_engine, expire_on_commit=False)
    
    async with async_session() as session:
        yield session


@pytest.fixture
async def db_service(test_session) -> DatabaseService:
    """Create database service for testing."""
    return DatabaseService(test_session)


@pytest.fixture
async def sample_ticket(db_service: DatabaseService) -> Ticket:
    """Create a sample ticket for testing."""
    ticket = await db_service.tickets.create(
        discord_channel_id=123456789,
        title="Test Ticket",
        description="This is a test ticket",
        creator_discord_id=987654321,
        status=TicketStatus.OPEN.value
    )
    await db_service.commit()
    return ticket


@pytest.fixture
async def sample_staff(db_service: DatabaseService) -> Staff:
    """Create a sample staff member for testing."""
    staff = await db_service.staff.create(
        discord_id=111222333,
        username="test_staff",
        role=StaffRole.SUPPORT.value,
        permissions={"manage_tickets": True}
    )
    await db_service.commit()
    return staff


class TestTicketRepository:
    """Test ticket repository operations."""
    
    async def test_create_ticket(self, db_service: DatabaseService):
        """Test creating a new ticket."""
        ticket = await db_service.tickets.create(
            discord_channel_id=123456789,
            title="Test Ticket",
            description="Test description",
            creator_discord_id=987654321
        )
        
        assert ticket.id is not None
        assert ticket.discord_channel_id == 123456789
        assert ticket.title == "Test Ticket"
        assert ticket.status == TicketStatus.OPEN.value
    
    async def test_get_ticket_by_id(self, db_service: DatabaseService, sample_ticket: Ticket):
        """Test getting a ticket by ID."""
        ticket = await db_service.tickets.get_by_id(sample_ticket.id)
        
        assert ticket is not None
        assert ticket.id == sample_ticket.id
        assert ticket.title == sample_ticket.title
    
    async def test_get_ticket_by_discord_channel_id(self, db_service: DatabaseService, sample_ticket: Ticket):
        """Test getting a ticket by Discord channel ID."""
        ticket = await db_service.tickets.get_by_discord_channel_id(sample_ticket.discord_channel_id)
        
        assert ticket is not None
        assert ticket.id == sample_ticket.id
        assert ticket.discord_channel_id == sample_ticket.discord_channel_id
    
    async def test_update_ticket(self, db_service: DatabaseService, sample_ticket: Ticket):
        """Test updating a ticket."""
        updated_ticket = await db_service.tickets.update(
            sample_ticket.id,
            title="Updated Title",
            status=TicketStatus.IN_PROGRESS.value
        )
        
        assert updated_ticket is not None
        assert updated_ticket.title == "Updated Title"
        assert updated_ticket.status == TicketStatus.IN_PROGRESS.value
    
    async def test_close_ticket(self, db_service: DatabaseService, sample_ticket: Ticket):
        """Test closing a ticket."""
        closed_ticket = await db_service.tickets.close_ticket(sample_ticket.id)
        
        assert closed_ticket is not None
        assert closed_ticket.status == TicketStatus.CLOSED.value
        assert closed_ticket.closed_at is not None
    
    async def test_search_tickets(self, db_service: DatabaseService):
        """Test searching tickets."""
        # Create test tickets
        await db_service.tickets.create(
            discord_channel_id=111111111,
            title="Bug Report",
            description="Found a bug",
            creator_discord_id=123456789
        )
        await db_service.tickets.create(
            discord_channel_id=222222222,
            title="Feature Request",
            description="Need new feature",
            creator_discord_id=123456789
        )
        
        # Search by title
        results = await db_service.tickets.search_tickets(search_term="Bug")
        assert len(results) == 1
        assert results[0].title == "Bug Report"
        
        # Search by creator
        results = await db_service.tickets.search_tickets(creator_discord_id=123456789)
        assert len(results) == 2
    
    async def test_get_ticket_stats(self, db_service: DatabaseService):
        """Test getting ticket statistics."""
        # Create test tickets with different statuses
        await db_service.tickets.create(
            discord_channel_id=111111111,
            title="Open Ticket",
            creator_discord_id=123456789,
            status=TicketStatus.OPEN.value
        )
        await db_service.tickets.create(
            discord_channel_id=222222222,
            title="Closed Ticket",
            creator_discord_id=123456789,
            status=TicketStatus.CLOSED.value
        )
        
        stats = await db_service.tickets.get_ticket_stats()
        
        assert stats["total_tickets"] == 2
        assert stats["status_counts"][TicketStatus.OPEN.value] == 1
        assert stats["status_counts"][TicketStatus.CLOSED.value] == 1


class TestMessageRepository:
    """Test message repository operations."""
    
    async def test_create_message(self, db_service: DatabaseService, sample_ticket: Ticket):
        """Test creating a new message."""
        message = await db_service.messages.create(
            ticket_id=sample_ticket.id,
            discord_message_id=987654321,
            author_discord_id=123456789,
            content="Test message content",
            message_type=MessageType.USER_MESSAGE.value
        )
        
        assert message.id is not None
        assert message.ticket_id == sample_ticket.id
        assert message.content == "Test message content"
        assert message.message_type == MessageType.USER_MESSAGE.value
    
    async def test_get_messages_by_ticket(self, db_service: DatabaseService, sample_ticket: Ticket):
        """Test getting messages for a ticket."""
        # Create test messages
        await db_service.messages.create(
            ticket_id=sample_ticket.id,
            author_discord_id=123456789,
            content="First message"
        )
        await db_service.messages.create(
            ticket_id=sample_ticket.id,
            author_discord_id=123456789,
            content="Second message"
        )
        
        messages = await db_service.messages.get_by_ticket_id(sample_ticket.id)
        
        assert len(messages) == 2
        assert messages[0].content == "First message"
        assert messages[1].content == "Second message"
    
    async def test_search_messages(self, db_service: DatabaseService, sample_ticket: Ticket):
        """Test searching messages."""
        await db_service.messages.create(
            ticket_id=sample_ticket.id,
            author_discord_id=123456789,
            content="This is a test message"
        )
        await db_service.messages.create(
            ticket_id=sample_ticket.id,
            author_discord_id=123456789,
            content="Another message"
        )
        
        results = await db_service.messages.search_messages("test")
        assert len(results) == 1
        assert "test" in results[0].content.lower()
    
    async def test_get_message_stats(self, db_service: DatabaseService, sample_ticket: Ticket):
        """Test getting message statistics for a ticket."""
        # Create test messages
        await db_service.messages.create(
            ticket_id=sample_ticket.id,
            author_discord_id=123456789,
            content="User message",
            message_type=MessageType.USER_MESSAGE.value
        )
        await db_service.messages.create(
            ticket_id=sample_ticket.id,
            author_discord_id=111222333,
            content="Staff message",
            message_type=MessageType.STAFF_MESSAGE.value
        )
        
        stats = await db_service.messages.get_message_stats_by_ticket(sample_ticket.id)
        
        assert stats["total_messages"] == 2
        assert stats["type_counts"][MessageType.USER_MESSAGE.value] == 1
        assert stats["type_counts"][MessageType.STAFF_MESSAGE.value] == 1
        assert stats["unique_authors"] == 2


class TestTranscriptRepository:
    """Test transcript repository operations."""
    
    async def test_create_transcript_with_share_token(self, db_service: DatabaseService, sample_ticket: Ticket):
        """Test creating a transcript with share token."""
        transcript = await db_service.transcripts.create_with_share_token(
            ticket_id=sample_ticket.id,
            content="Transcript content"
        )
        
        assert transcript.id is not None
        assert transcript.ticket_id == sample_ticket.id
        assert transcript.content == "Transcript content"
        assert transcript.share_token is not None
        assert len(transcript.share_token) == 32
    
    async def test_get_transcript_by_ticket_id(self, db_service: DatabaseService, sample_ticket: Ticket):
        """Test getting transcript by ticket ID."""
        created_transcript = await db_service.transcripts.create_with_share_token(
            ticket_id=sample_ticket.id,
            content="Test transcript"
        )
        
        transcript = await db_service.transcripts.get_by_ticket_id(sample_ticket.id)
        
        assert transcript is not None
        assert transcript.id == created_transcript.id
        assert transcript.content == "Test transcript"
    
    async def test_get_transcript_by_share_token(self, db_service: DatabaseService, sample_ticket: Ticket):
        """Test getting transcript by share token."""
        created_transcript = await db_service.transcripts.create_with_share_token(
            ticket_id=sample_ticket.id,
            content="Shared transcript"
        )
        
        transcript = await db_service.transcripts.get_by_share_token(created_transcript.share_token)
        
        assert transcript is not None
        assert transcript.id == created_transcript.id
        assert transcript.share_token == created_transcript.share_token
    
    async def test_search_transcripts(self, db_service: DatabaseService, sample_ticket: Ticket):
        """Test searching transcripts."""
        await db_service.transcripts.create_with_share_token(
            ticket_id=sample_ticket.id,
            content="This transcript contains important information"
        )
        
        results = await db_service.transcripts.search_transcripts("important")
        
        assert len(results) == 1
        assert "important" in results[0].content
    
    async def test_update_transcript_content(self, db_service: DatabaseService, sample_ticket: Ticket):
        """Test updating transcript content."""
        transcript = await db_service.transcripts.create_with_share_token(
            ticket_id=sample_ticket.id,
            content="Original content"
        )
        
        updated_transcript = await db_service.transcripts.update_content(
            sample_ticket.id,
            "Updated content"
        )
        
        assert updated_transcript is not None
        assert updated_transcript.content == "Updated content"
        assert updated_transcript.id == transcript.id


class TestStaffRepository:
    """Test staff repository operations."""
    
    async def test_create_staff(self, db_service: DatabaseService):
        """Test creating a new staff member."""
        staff = await db_service.staff.create(
            discord_id=123456789,
            username="test_user",
            role=StaffRole.SUPPORT.value,
            permissions={"manage_tickets": True}
        )
        
        assert staff.id is not None
        assert staff.discord_id == 123456789
        assert staff.username == "test_user"
        assert staff.role == StaffRole.SUPPORT.value
        assert staff.permissions["manage_tickets"] is True
    
    async def test_get_staff_by_discord_id(self, db_service: DatabaseService, sample_staff: Staff):
        """Test getting staff by Discord ID."""
        staff = await db_service.staff.get_by_discord_id(sample_staff.discord_id)
        
        assert staff is not None
        assert staff.id == sample_staff.id
        assert staff.discord_id == sample_staff.discord_id
    
    async def test_get_staff_by_role(self, db_service: DatabaseService):
        """Test getting staff by role."""
        await db_service.staff.create(
            discord_id=111111111,
            username="admin_user",
            role=StaffRole.ADMIN.value
        )
        await db_service.staff.create(
            discord_id=222222222,
            username="support_user",
            role=StaffRole.SUPPORT.value
        )
        
        admins = await db_service.staff.get_by_role(StaffRole.ADMIN)
        support = await db_service.staff.get_by_role(StaffRole.SUPPORT)
        
        assert len(admins) == 1
        assert len(support) == 1
        assert admins[0].role == StaffRole.ADMIN.value
        assert support[0].role == StaffRole.SUPPORT.value
    
    async def test_is_staff_member(self, db_service: DatabaseService, sample_staff: Staff):
        """Test checking if user is staff member."""
        is_staff = await db_service.staff.is_staff_member(sample_staff.discord_id)
        is_not_staff = await db_service.staff.is_staff_member(999999999)
        
        assert is_staff is True
        assert is_not_staff is False
    
    async def test_has_permission(self, db_service: DatabaseService, sample_staff: Staff):
        """Test checking staff permissions."""
        has_permission = await db_service.staff.has_permission(
            sample_staff.discord_id, 
            "manage_tickets"
        )
        no_permission = await db_service.staff.has_permission(
            sample_staff.discord_id, 
            "admin_access"
        )
        
        assert has_permission is True
        assert no_permission is False
    
    async def test_update_permissions(self, db_service: DatabaseService, sample_staff: Staff):
        """Test updating staff permissions."""
        updated_staff = await db_service.staff.update_permissions(
            sample_staff.id,
            {"admin_access": True, "manage_tickets": False}
        )
        
        assert updated_staff is not None
        assert updated_staff.permissions["admin_access"] is True
        assert updated_staff.permissions["manage_tickets"] is False
    
    async def test_deactivate_staff(self, db_service: DatabaseService, sample_staff: Staff):
        """Test deactivating staff member."""
        deactivated_staff = await db_service.staff.deactivate_staff(sample_staff.id)
        
        assert deactivated_staff is not None
        assert deactivated_staff.active is False


class TestDatabaseService:
    """Test database service integration."""
    
    async def test_repository_access(self, db_service: DatabaseService):
        """Test accessing repositories through database service."""
        assert db_service.tickets is not None
        assert db_service.messages is not None
        assert db_service.transcripts is not None
        assert db_service.staff is not None
        
        # Test that repositories are cached
        assert db_service.tickets is db_service.tickets
    
    async def test_transaction_management(self, db_service: DatabaseService):
        """Test transaction management."""
        # Create a ticket
        ticket = await db_service.tickets.create(
            discord_channel_id=123456789,
            title="Transaction Test",
            creator_discord_id=987654321
        )
        
        # Flush to get the ID but don't commit
        await db_service.flush()
        assert ticket.id is not None
        
        # Rollback the transaction
        await db_service.rollback()
        
        # Ticket should not exist after rollback
        found_ticket = await db_service.tickets.get_by_id(ticket.id)
        assert found_ticket is None