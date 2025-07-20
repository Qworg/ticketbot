"""Tests for ticket service business logic."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from backend.services.ticket_service import TicketService
from backend.database_service import DatabaseService
from backend.schemas import TicketCreate, TicketUpdate
from backend.models import TicketStatus, Priority, StaffRole
from backend.tests.test_database_service import test_engine, test_session, db_service


@pytest.fixture
async def ticket_service(db_service: DatabaseService) -> TicketService:
    """Create ticket service for testing."""
    return TicketService(db_service)


@pytest.fixture
async def sample_staff(db_service: DatabaseService):
    """Create a sample staff member for testing."""
    staff = await db_service.staff.create(
        discord_id=111222333,
        username="test_staff",
        role=StaffRole.SUPPORT.value,
        permissions={"manage_tickets": True}
    )
    await db_service.commit()
    return staff


class TestTicketService:
    """Test ticket service business logic."""
    
    async def test_create_ticket_success(self, ticket_service: TicketService):
        """Test successful ticket creation."""
        ticket_data = TicketCreate(
            title="Test Ticket",
            description="Test description",
            discord_channel_id=123456789,
            creator_discord_id=987654321,
            priority=Priority.HIGH
        )
        
        ticket = await ticket_service.create_ticket(ticket_data, 987654321)
        
        assert ticket.title == "Test Ticket"
        assert ticket.description == "Test description"
        assert ticket.discord_channel_id == 123456789
        assert ticket.creator_discord_id == 987654321
        assert ticket.priority == Priority.HIGH.value
        assert ticket.status == TicketStatus.OPEN.value
    
    async def test_create_ticket_duplicate_channel(self, ticket_service: TicketService):
        """Test creating ticket with duplicate Discord channel ID."""
        ticket_data = TicketCreate(
            title="First Ticket",
            description="First description",
            discord_channel_id=123456789,
            creator_discord_id=987654321
        )
        
        # Create first ticket
        await ticket_service.create_ticket(ticket_data, 987654321)
        
        # Try to create second ticket with same channel ID
        duplicate_data = TicketCreate(
            title="Second Ticket",
            description="Second description",
            discord_channel_id=123456789,
            creator_discord_id=111111111
        )
        
        with pytest.raises(ValueError, match="Ticket already exists for Discord channel"):
            await ticket_service.create_ticket(duplicate_data, 111111111)
    
    async def test_get_ticket(self, ticket_service: TicketService):
        """Test getting a ticket by ID."""
        ticket_data = TicketCreate(
            title="Test Ticket",
            discord_channel_id=123456789,
            creator_discord_id=987654321
        )
        
        created_ticket = await ticket_service.create_ticket(ticket_data, 987654321)
        retrieved_ticket = await ticket_service.get_ticket(created_ticket.id)
        
        assert retrieved_ticket is not None
        assert retrieved_ticket.id == created_ticket.id
        assert retrieved_ticket.title == "Test Ticket"
    
    async def test_get_ticket_by_channel(self, ticket_service: TicketService):
        """Test getting a ticket by Discord channel ID."""
        ticket_data = TicketCreate(
            title="Test Ticket",
            discord_channel_id=123456789,
            creator_discord_id=987654321
        )
        
        created_ticket = await ticket_service.create_ticket(ticket_data, 987654321)
        retrieved_ticket = await ticket_service.get_ticket_by_channel(123456789)
        
        assert retrieved_ticket is not None
        assert retrieved_ticket.id == created_ticket.id
        assert retrieved_ticket.discord_channel_id == 123456789
    
    async def test_update_ticket_success(self, ticket_service: TicketService):
        """Test successful ticket update."""
        ticket_data = TicketCreate(
            title="Original Title",
            discord_channel_id=123456789,
            creator_discord_id=987654321
        )
        
        created_ticket = await ticket_service.create_ticket(ticket_data, 987654321)
        
        update_data = TicketUpdate(
            title="Updated Title",
            description="Updated description",
            priority=Priority.HIGH,
            status=TicketStatus.IN_PROGRESS
        )
        
        updated_ticket = await ticket_service.update_ticket(
            created_ticket.id, update_data, 987654321
        )
        
        assert updated_ticket is not None
        assert updated_ticket.title == "Updated Title"
        assert updated_ticket.description == "Updated description"
        assert updated_ticket.priority == Priority.HIGH.value
        assert updated_ticket.status == TicketStatus.IN_PROGRESS.value
    
    async def test_update_ticket_invalid_status_transition(self, ticket_service: TicketService):
        """Test updating ticket with invalid status transition."""
        ticket_data = TicketCreate(
            title="Test Ticket",
            discord_channel_id=123456789,
            creator_discord_id=987654321
        )
        
        created_ticket = await ticket_service.create_ticket(ticket_data, 987654321)
        
        # Try to transition from OPEN to ARCHIVED (invalid)
        update_data = TicketUpdate(status=TicketStatus.ARCHIVED)
        
        with pytest.raises(ValueError, match="Invalid status transition"):
            await ticket_service.update_ticket(
                created_ticket.id, update_data, 987654321
            )
    
    async def test_assign_ticket_success(self, ticket_service: TicketService, sample_staff):
        """Test successful ticket assignment."""
        ticket_data = TicketCreate(
            title="Test Ticket",
            discord_channel_id=123456789,
            creator_discord_id=987654321
        )
        
        created_ticket = await ticket_service.create_ticket(ticket_data, 987654321)
        
        assigned_ticket = await ticket_service.assign_ticket(
            created_ticket.id, sample_staff.discord_id, 999999999
        )
        
        assert assigned_ticket is not None
        assert assigned_ticket.assigned_staff_id == sample_staff.discord_id
        assert assigned_ticket.status == TicketStatus.IN_PROGRESS.value
    
    async def test_assign_ticket_invalid_staff(self, ticket_service: TicketService):
        """Test assigning ticket to non-existent staff member."""
        ticket_data = TicketCreate(
            title="Test Ticket",
            discord_channel_id=123456789,
            creator_discord_id=987654321
        )
        
        created_ticket = await ticket_service.create_ticket(ticket_data, 987654321)
        
        with pytest.raises(ValueError, match="Staff member .* does not exist"):
            await ticket_service.assign_ticket(
                created_ticket.id, 999999999, 888888888
            )
    
    async def test_unassign_ticket(self, ticket_service: TicketService, sample_staff):
        """Test unassigning a ticket."""
        ticket_data = TicketCreate(
            title="Test Ticket",
            discord_channel_id=123456789,
            creator_discord_id=987654321
        )
        
        created_ticket = await ticket_service.create_ticket(ticket_data, 987654321)
        
        # First assign the ticket
        assigned_ticket = await ticket_service.assign_ticket(
            created_ticket.id, sample_staff.discord_id, 999999999
        )
        assert assigned_ticket.assigned_staff_id == sample_staff.discord_id
        
        # Then unassign it
        unassigned_ticket = await ticket_service.unassign_ticket(
            created_ticket.id, 999999999
        )
        
        assert unassigned_ticket is not None
        assert unassigned_ticket.assigned_staff_id is None
        assert unassigned_ticket.status == TicketStatus.OPEN.value
    
    async def test_close_ticket_success(self, ticket_service: TicketService):
        """Test successful ticket closure."""
        ticket_data = TicketCreate(
            title="Test Ticket",
            discord_channel_id=123456789,
            creator_discord_id=987654321
        )
        
        created_ticket = await ticket_service.create_ticket(ticket_data, 987654321)
        
        closed_ticket = await ticket_service.close_ticket(
            created_ticket.id, 999999999
        )
        
        assert closed_ticket is not None
        assert closed_ticket.status == TicketStatus.CLOSED.value
        assert closed_ticket.closed_at is not None
    
    async def test_close_already_closed_ticket(self, ticket_service: TicketService):
        """Test closing an already closed ticket."""
        ticket_data = TicketCreate(
            title="Test Ticket",
            discord_channel_id=123456789,
            creator_discord_id=987654321
        )
        
        created_ticket = await ticket_service.create_ticket(ticket_data, 987654321)
        
        # Close the ticket first time
        await ticket_service.close_ticket(created_ticket.id, 999999999)
        
        # Try to close it again
        with pytest.raises(ValueError, match="Ticket is already closed"):
            await ticket_service.close_ticket(created_ticket.id, 999999999)
    
    async def test_reopen_ticket_success(self, ticket_service: TicketService):
        """Test successful ticket reopening."""
        ticket_data = TicketCreate(
            title="Test Ticket",
            discord_channel_id=123456789,
            creator_discord_id=987654321
        )
        
        created_ticket = await ticket_service.create_ticket(ticket_data, 987654321)
        
        # Close the ticket first
        closed_ticket = await ticket_service.close_ticket(
            created_ticket.id, 999999999
        )
        assert closed_ticket.status == TicketStatus.CLOSED.value
        
        # Reopen the ticket
        reopened_ticket = await ticket_service.reopen_ticket(
            created_ticket.id, 999999999
        )
        
        assert reopened_ticket is not None
        assert reopened_ticket.status == TicketStatus.OPEN.value
        assert reopened_ticket.closed_at is None
    
    async def test_reopen_non_closed_ticket(self, ticket_service: TicketService):
        """Test reopening a non-closed ticket."""
        ticket_data = TicketCreate(
            title="Test Ticket",
            discord_channel_id=123456789,
            creator_discord_id=987654321
        )
        
        created_ticket = await ticket_service.create_ticket(ticket_data, 987654321)
        
        with pytest.raises(ValueError, match="Only closed tickets can be reopened"):
            await ticket_service.reopen_ticket(created_ticket.id, 999999999)
    
    async def test_archive_ticket_success(self, ticket_service: TicketService):
        """Test successful ticket archiving."""
        ticket_data = TicketCreate(
            title="Test Ticket",
            discord_channel_id=123456789,
            creator_discord_id=987654321
        )
        
        created_ticket = await ticket_service.create_ticket(ticket_data, 987654321)
        
        # Close the ticket first
        closed_ticket = await ticket_service.close_ticket(
            created_ticket.id, 999999999
        )
        assert closed_ticket.status == TicketStatus.CLOSED.value
        
        # Archive the ticket
        archived_ticket = await ticket_service.archive_ticket(
            created_ticket.id, 999999999
        )
        
        assert archived_ticket is not None
        assert archived_ticket.status == TicketStatus.ARCHIVED.value
    
    async def test_archive_non_closed_ticket(self, ticket_service: TicketService):
        """Test archiving a non-closed ticket."""
        ticket_data = TicketCreate(
            title="Test Ticket",
            discord_channel_id=123456789,
            creator_discord_id=987654321
        )
        
        created_ticket = await ticket_service.create_ticket(ticket_data, 987654321)
        
        with pytest.raises(ValueError, match="Only closed tickets can be archived"):
            await ticket_service.archive_ticket(created_ticket.id, 999999999)
    
    async def test_get_user_tickets(self, ticket_service: TicketService):
        """Test getting tickets for a specific user."""
        creator_id = 987654321
        
        # Create multiple tickets for the user
        for i in range(3):
            ticket_data = TicketCreate(
                title=f"User Ticket {i+1}",
                discord_channel_id=123456789 + i,
                creator_discord_id=creator_id
            )
            await ticket_service.create_ticket(ticket_data, creator_id)
        
        # Create a ticket for a different user
        other_ticket_data = TicketCreate(
            title="Other User Ticket",
            discord_channel_id=999999999,
            creator_discord_id=111111111
        )
        await ticket_service.create_ticket(other_ticket_data, 111111111)
        
        # Get tickets for the specific user
        user_tickets = await ticket_service.get_user_tickets(creator_id)
        
        assert len(user_tickets) == 3
        for ticket in user_tickets:
            assert ticket.creator_discord_id == creator_id
    
    async def test_get_staff_tickets(self, ticket_service: TicketService, sample_staff):
        """Test getting tickets assigned to a specific staff member."""
        # Create tickets and assign them to staff
        for i in range(2):
            ticket_data = TicketCreate(
                title=f"Staff Ticket {i+1}",
                discord_channel_id=123456789 + i,
                creator_discord_id=987654321
            )
            created_ticket = await ticket_service.create_ticket(ticket_data, 987654321)
            await ticket_service.assign_ticket(
                created_ticket.id, sample_staff.discord_id, 999999999
            )
        
        # Create an unassigned ticket
        unassigned_data = TicketCreate(
            title="Unassigned Ticket",
            discord_channel_id=999999999,
            creator_discord_id=987654321
        )
        await ticket_service.create_ticket(unassigned_data, 987654321)
        
        # Get tickets for the staff member
        staff_tickets = await ticket_service.get_staff_tickets(sample_staff.discord_id)
        
        assert len(staff_tickets) == 2
        for ticket in staff_tickets:
            assert ticket.assigned_staff_id == sample_staff.discord_id
    
    async def test_search_tickets(self, ticket_service: TicketService):
        """Test searching tickets with various filters."""
        # Create test tickets
        ticket1_data = TicketCreate(
            title="Bug Report",
            description="Found a critical bug",
            discord_channel_id=111111111,
            creator_discord_id=987654321,
            priority=Priority.HIGH
        )
        ticket1 = await ticket_service.create_ticket(ticket1_data, 987654321)
        
        ticket2_data = TicketCreate(
            title="Feature Request",
            description="Need new feature",
            discord_channel_id=222222222,
            creator_discord_id=111111111,
            priority=Priority.LOW
        )
        ticket2 = await ticket_service.create_ticket(ticket2_data, 111111111)
        
        # Search by title
        results = await ticket_service.search_tickets(search_term="Bug")
        assert len(results) == 1
        assert results[0].title == "Bug Report"
        
        # Search by creator
        results = await ticket_service.search_tickets(creator_discord_id=987654321)
        assert len(results) == 1
        assert results[0].creator_discord_id == 987654321
        
        # Search by priority
        results = await ticket_service.search_tickets(priority=Priority.HIGH.value)
        assert len(results) == 1
        assert results[0].priority == Priority.HIGH.value
    
    async def test_get_ticket_statistics(self, ticket_service: TicketService):
        """Test getting ticket statistics."""
        # Create tickets with different statuses
        open_ticket_data = TicketCreate(
            title="Open Ticket",
            discord_channel_id=111111111,
            creator_discord_id=987654321
        )
        open_ticket = await ticket_service.create_ticket(open_ticket_data, 987654321)
        
        closed_ticket_data = TicketCreate(
            title="Closed Ticket",
            discord_channel_id=222222222,
            creator_discord_id=987654321
        )
        closed_ticket = await ticket_service.create_ticket(closed_ticket_data, 987654321)
        await ticket_service.close_ticket(closed_ticket.id, 999999999)
        
        stats = await ticket_service.get_ticket_statistics()
        
        assert stats["total_tickets"] == 2
        assert stats["status_counts"][TicketStatus.OPEN.value] == 1
        assert stats["status_counts"][TicketStatus.CLOSED.value] == 1
    
    async def test_status_transition_validation(self, ticket_service: TicketService):
        """Test status transition validation logic."""
        # Test valid transitions
        assert ticket_service._is_valid_status_transition(
            TicketStatus.OPEN.value, TicketStatus.IN_PROGRESS.value
        )
        assert ticket_service._is_valid_status_transition(
            TicketStatus.CLOSED.value, TicketStatus.OPEN.value
        )
        assert ticket_service._is_valid_status_transition(
            TicketStatus.CLOSED.value, TicketStatus.ARCHIVED.value
        )
        
        # Test invalid transitions
        assert not ticket_service._is_valid_status_transition(
            TicketStatus.OPEN.value, TicketStatus.ARCHIVED.value
        )
        assert not ticket_service._is_valid_status_transition(
            TicketStatus.ARCHIVED.value, TicketStatus.OPEN.value
        )