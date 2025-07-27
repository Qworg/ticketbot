"""
Integration tests for complete ticket lifecycle.
Tests the full flow from ticket creation to closure across all components.
"""
import asyncio
import pytest
import httpx
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from backend.models import Ticket, Message, Staff
from backend.schemas import TicketCreate, MessageCreate, TicketUpdate
from .test_database_service import TestDatabaseService, get_test_database_service
from .test_redis_service import TestRedisService
from .mock_services import MockTicketService, MockTranscriptService, MockAuthService


@pytest.fixture
async def integration_setup():
    """Set up integration test environment with all services."""
    async with get_test_database_service() as db_service:
        # Initialize services
        redis_service = TestRedisService()
        ticket_service = MockTicketService(db_service, redis_service)
        transcript_service = MockTranscriptService(db_service)
        auth_service = MockAuthService(db_service)
        
        # Create test database tables
        await db_service.create_tables()
        
        # Create test staff member
        staff_data = {
            "discord_id": 123456789,
            "username": "test_staff",
            "role": "admin",
            "permissions": {"can_close_tickets": True, "can_assign_tickets": True}
        }
        staff = await db_service.create_staff(staff_data)
        
        yield {
            "db_service": db_service,
            "redis_service": redis_service,
            "ticket_service": ticket_service,
            "transcript_service": transcript_service,
            "auth_service": auth_service,
            "staff": staff
        }
        
        # Cleanup
        await db_service.cleanup()
        await redis_service.cleanup()


@pytest.mark.asyncio
async def test_complete_ticket_lifecycle(integration_setup):
    """Test complete ticket lifecycle from creation to closure."""
    services = integration_setup
    ticket_service = services["ticket_service"]
    transcript_service = services["transcript_service"]
    staff = services["staff"]
    
    # Step 1: Create ticket
    ticket_data = TicketCreate(
        discord_channel_id=987654321,
        title="Test Integration Ticket",
        description="Testing complete lifecycle",
        creator_discord_id=111222333,
        priority="high"
    )
    
    ticket = await ticket_service.create_ticket(ticket_data)
    assert ticket is not None
    assert ticket.title == "Test Integration Ticket"
    assert ticket.status == "open"
    assert ticket.priority == "high"
    
    # Step 2: Add messages to ticket
    messages = [
        MessageCreate(
            ticket_id=ticket.id,
            author_discord_id=111222333,
            content="Hello, I need help with my account",
            message_type="user_message"
        ),
        MessageCreate(
            ticket_id=ticket.id,
            author_discord_id=staff.discord_id,
            content="Hi! I'll help you with that. Can you provide more details?",
            message_type="staff_message"
        ),
        MessageCreate(
            ticket_id=ticket.id,
            author_discord_id=111222333,
            content="Sure, I can't log into my account since yesterday",
            message_type="user_message"
        )
    ]
    
    created_messages = []
    for msg_data in messages:
        message = await ticket_service.add_message(msg_data)
        created_messages.append(message)
        assert message is not None
        assert message.ticket_id == ticket.id
    
    # Step 3: Assign ticket to staff
    update_data = TicketUpdate(assigned_staff_id=staff.discord_id)
    updated_ticket = await ticket_service.update_ticket(ticket.id, update_data)
    assert updated_ticket.assigned_staff_id == staff.discord_id
    
    # Step 4: Generate transcript
    transcript = await transcript_service.generate_transcript(ticket.id)
    assert transcript is not None
    assert len(transcript.content) > 0
    assert "Hello, I need help with my account" in transcript.content
    assert "Hi! I'll help you with that" in transcript.content
    
    # Step 5: Search transcripts
    search_results = await transcript_service.search_transcripts("account", limit=10)
    assert len(search_results) > 0
    assert any(result.ticket_id == ticket.id for result in search_results)
    
    # Step 6: Close ticket
    close_data = TicketUpdate(status="closed")
    closed_ticket = await ticket_service.update_ticket(ticket.id, close_data)
    assert closed_ticket.status == "closed"
    assert closed_ticket.closed_at is not None
    
    # Step 7: Verify ticket history
    ticket_history = await ticket_service.get_ticket_history(ticket.id)
    assert len(ticket_history) >= 2  # Creation and closure events
    
    # Step 8: Verify final state
    final_ticket = await ticket_service.get_ticket(ticket.id)
    assert final_ticket.status == "closed"
    assert final_ticket.assigned_staff_id == staff.discord_id
    assert len(final_ticket.messages) == 3


@pytest.mark.asyncio
async def test_concurrent_ticket_operations(integration_setup):
    """Test concurrent operations on tickets to ensure data consistency."""
    services = integration_setup
    ticket_service = services["ticket_service"]
    staff = services["staff"]
    
    # Create a ticket
    ticket_data = TicketCreate(
        discord_channel_id=987654322,
        title="Concurrent Test Ticket",
        description="Testing concurrent operations",
        creator_discord_id=111222334
    )
    
    ticket = await ticket_service.create_ticket(ticket_data)
    
    # Define concurrent operations
    async def add_message(content: str):
        msg_data = MessageCreate(
            ticket_id=ticket.id,
            author_discord_id=staff.discord_id,
            content=content,
            message_type="staff_message"
        )
        return await ticket_service.add_message(msg_data)
    
    async def update_ticket_status():
        update_data = TicketUpdate(status="in_progress")
        return await ticket_service.update_ticket(ticket.id, update_data)
    
    async def assign_ticket():
        update_data = TicketUpdate(assigned_staff_id=staff.discord_id)
        return await ticket_service.update_ticket(ticket.id, update_data)
    
    # Run concurrent operations
    results = await asyncio.gather(
        add_message("Message 1"),
        add_message("Message 2"),
        update_ticket_status(),
        assign_ticket(),
        add_message("Message 3"),
        return_exceptions=True
    )
    
    # Verify no exceptions occurred
    for result in results:
        assert not isinstance(result, Exception), f"Concurrent operation failed: {result}"
    
    # Verify final state consistency
    final_ticket = await ticket_service.get_ticket(ticket.id)
    assert len(final_ticket.messages) == 3
    assert final_ticket.assigned_staff_id == staff.discord_id
    # Status could be either "in_progress" or original based on operation order


@pytest.mark.asyncio
async def test_ticket_permissions_integration(integration_setup):
    """Test ticket permission management across the system."""
    services = integration_setup
    ticket_service = services["ticket_service"]
    auth_service = services["auth_service"]
    db_service = services["db_service"]
    
    # Create different staff members with different permissions
    admin_staff = await db_service.create_staff({
        "discord_id": 123456790,
        "username": "admin_staff",
        "role": "admin",
        "permissions": {"can_close_tickets": True, "can_assign_tickets": True, "can_view_all_tickets": True}
    })
    
    regular_staff = await db_service.create_staff({
        "discord_id": 123456791,
        "username": "regular_staff",
        "role": "support",
        "permissions": {"can_close_tickets": False, "can_assign_tickets": False, "can_view_all_tickets": False}
    })
    
    # Create ticket
    ticket_data = TicketCreate(
        discord_channel_id=987654323,
        title="Permission Test Ticket",
        description="Testing permissions",
        creator_discord_id=111222335
    )
    
    ticket = await ticket_service.create_ticket(ticket_data)
    
    # Test admin permissions
    admin_can_view = await auth_service.can_access_ticket(admin_staff.discord_id, ticket.id)
    assert admin_can_view is True
    
    admin_can_close = await auth_service.has_permission(admin_staff.discord_id, "can_close_tickets")
    assert admin_can_close is True
    
    # Test regular staff permissions
    regular_can_view = await auth_service.can_access_ticket(regular_staff.discord_id, ticket.id)
    # Should be False initially since not assigned
    assert regular_can_view is False
    
    regular_can_close = await auth_service.has_permission(regular_staff.discord_id, "can_close_tickets")
    assert regular_can_close is False
    
    # Assign ticket to regular staff
    update_data = TicketUpdate(assigned_staff_id=regular_staff.discord_id)
    await ticket_service.update_ticket(ticket.id, update_data)
    
    # Now regular staff should be able to view
    regular_can_view_after_assign = await auth_service.can_access_ticket(regular_staff.discord_id, ticket.id)
    assert regular_can_view_after_assign is True


@pytest.mark.asyncio
async def test_error_recovery_integration(integration_setup):
    """Test system behavior during error conditions and recovery."""
    services = integration_setup
    ticket_service = services["ticket_service"]
    db_service = services["db_service"]
    
    # Test database connection failure recovery
    with patch.object(db_service, 'execute_query', side_effect=Exception("Database connection lost")):
        with pytest.raises(Exception):
            await ticket_service.create_ticket(TicketCreate(
                discord_channel_id=987654324,
                title="Error Test Ticket",
                description="Testing error recovery",
                creator_discord_id=111222336
            ))
    
    # Verify system recovers after database is back
    ticket_data = TicketCreate(
        discord_channel_id=987654325,
        title="Recovery Test Ticket",
        description="Testing recovery",
        creator_discord_id=111222337
    )
    
    ticket = await ticket_service.create_ticket(ticket_data)
    assert ticket is not None
    assert ticket.title == "Recovery Test Ticket"


@pytest.mark.asyncio
async def test_real_time_synchronization_integration(integration_setup):
    """Test real-time synchronization between components."""
    services = integration_setup
    ticket_service = services["ticket_service"]
    redis_service = services["redis_service"]
    
    # Set up event listeners
    received_events = []
    
    async def event_handler(channel, message):
        received_events.append({"channel": channel, "message": message})
    
    # Subscribe to ticket events
    await redis_service.subscribe("ticket_events", event_handler)
    
    # Create ticket (should trigger event)
    ticket_data = TicketCreate(
        discord_channel_id=987654326,
        title="Sync Test Ticket",
        description="Testing synchronization",
        creator_discord_id=111222338
    )
    
    ticket = await ticket_service.create_ticket(ticket_data)
    
    # Add message (should trigger event)
    msg_data = MessageCreate(
        ticket_id=ticket.id,
        author_discord_id=111222338,
        content="Test message for sync",
        message_type="user_message"
    )
    
    await ticket_service.add_message(msg_data)
    
    # Wait for events to be processed
    await asyncio.sleep(0.1)
    
    # Verify events were received
    assert len(received_events) >= 2  # ticket_created and message_added events
    
    event_types = [event["message"].get("type") for event in received_events]
    assert "ticket_created" in event_types
    assert "message_added" in event_types