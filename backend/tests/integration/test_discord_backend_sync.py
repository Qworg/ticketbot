"""
Integration tests for Discord-backend synchronization.
Tests bidirectional synchronization between Discord bot and backend API.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
import json

from backend.schemas import TicketCreate, MessageCreate, TicketUpdate
from .test_database_service import TestDatabaseService, get_test_database_service
from .test_redis_service import TestRedisService
from .mock_services import MockTicketService


@pytest.fixture
async def sync_integration_setup():
    """Set up synchronization integration test environment."""
    async with get_test_database_service() as db_service:
        # Initialize backend services
        redis_service = TestRedisService()
        ticket_service = MockTicketService(db_service, redis_service)
        
        # Create test database tables
        await db_service.create_tables()
        
        # Create test staff
        staff_data = {
            "discord_id": 123456789,
            "username": "sync_test_staff",
            "role": "admin",
            "permissions": {"can_close_tickets": True, "can_assign_tickets": True}
        }
        staff = await db_service.create_staff(staff_data)
        
        # Mock Discord bot components
        mock_discord_bot = MagicMock()
        mock_discord_bot.create_ticket_channel = AsyncMock()
        mock_discord_bot.send_message = AsyncMock()
        mock_discord_bot.update_channel_permissions = AsyncMock()
        mock_discord_bot.archive_channel = AsyncMock()
        
        # Mock HTTP client for Discord bot
        mock_http_client = MagicMock()
        mock_http_client.post = AsyncMock()
        mock_http_client.put = AsyncMock()
        mock_http_client.get = AsyncMock()
        
        yield {
            "db_service": db_service,
            "redis_service": redis_service,
            "ticket_service": ticket_service,
            "staff": staff,
            "mock_discord_bot": mock_discord_bot,
            "mock_http_client": mock_http_client
        }
        
        # Cleanup
        await db_service.cleanup()
        await redis_service.cleanup()


@pytest.mark.asyncio
async def test_discord_to_backend_ticket_creation_sync(sync_integration_setup):
    """Test ticket creation synchronization from Discord to backend."""
    setup = sync_integration_setup
    ticket_service = setup["ticket_service"]
    redis_service = setup["redis_service"]
    mock_discord_bot = setup["mock_discord_bot"]
    
    # Set up event listeners
    sync_events = []
    
    async def event_handler(channel, message):
        sync_events.append({"channel": channel, "message": json.loads(message)})
    
    await redis_service.subscribe("discord_events", event_handler)
    
    # Simulate Discord ticket creation
    discord_ticket_data = {
        "type": "ticket_created",
        "data": {
            "discord_channel_id": 987654321,
            "title": "Discord Sync Test",
            "description": "Testing Discord to backend sync",
            "creator_discord_id": 111222333,
            "creator_username": "test_user"
        }
    }
    
    # Publish Discord event
    await redis_service.publish("discord_events", json.dumps(discord_ticket_data))
    
    # Wait for event processing
    await asyncio.sleep(0.1)
    
    # Verify event was received
    assert len(sync_events) >= 1
    received_event = sync_events[0]["message"]
    assert received_event["type"] == "ticket_created"
    assert received_event["data"]["discord_channel_id"] == 987654321
    
    # Simulate backend processing the Discord event
    ticket_data = TicketCreate(
        discord_channel_id=received_event["data"]["discord_channel_id"],
        title=received_event["data"]["title"],
        description=received_event["data"]["description"],
        creator_discord_id=received_event["data"]["creator_discord_id"]
    )
    
    ticket = await ticket_service.create_ticket(ticket_data)
    assert ticket is not None
    assert ticket.discord_channel_id == 987654321
    assert ticket.title == "Discord Sync Test"


@pytest.mark.asyncio
async def test_backend_to_discord_ticket_update_sync(sync_integration_setup):
    """Test ticket update synchronization from backend to Discord."""
    setup = sync_integration_setup
    ticket_service = setup["ticket_service"]
    redis_service = setup["redis_service"]
    mock_discord_bot = setup["mock_discord_bot"]
    staff = setup["staff"]
    
    # Create ticket in backend
    ticket_data = TicketCreate(
        discord_channel_id=987654322,
        title="Backend Sync Test",
        description="Testing backend to Discord sync",
        creator_discord_id=111222334
    )
    
    ticket = await ticket_service.create_ticket(ticket_data)
    
    # Set up Discord event listeners
    discord_events = []
    
    async def discord_event_handler(channel, message):
        discord_events.append({"channel": channel, "message": json.loads(message)})
    
    await redis_service.subscribe("backend_events", discord_event_handler)
    
    # Update ticket in backend (should trigger Discord sync)
    update_data = TicketUpdate(
        status="in_progress",
        assigned_staff_id=staff.discord_id
    )
    
    updated_ticket = await ticket_service.update_ticket(ticket.id, update_data)
    
    # Wait for event processing
    await asyncio.sleep(0.1)
    
    # Verify Discord received the update event
    assert len(discord_events) >= 1
    update_event = discord_events[-1]["message"]
    assert update_event["type"] == "ticket_updated"
    assert update_event["data"]["ticket_id"] == str(ticket.id)
    assert update_event["data"]["status"] == "in_progress"
    assert update_event["data"]["assigned_staff_id"] == staff.discord_id


@pytest.mark.asyncio
async def test_bidirectional_message_synchronization(sync_integration_setup):
    """Test bidirectional message synchronization between Discord and backend."""
    setup = sync_integration_setup
    ticket_service = setup["ticket_service"]
    redis_service = setup["redis_service"]
    
    # Create ticket
    ticket_data = TicketCreate(
        discord_channel_id=987654323,
        title="Message Sync Test",
        description="Testing message synchronization",
        creator_discord_id=111222335
    )
    
    ticket = await ticket_service.create_ticket(ticket_data)
    
    # Set up event listeners for both directions
    discord_events = []
    backend_events = []
    
    async def discord_event_handler(channel, message):
        discord_events.append({"channel": channel, "message": json.loads(message)})
    
    async def backend_event_handler(channel, message):
        backend_events.append({"channel": channel, "message": json.loads(message)})
    
    await redis_service.subscribe("backend_events", discord_event_handler)
    await redis_service.subscribe("discord_events", backend_event_handler)
    
    # Test 1: Discord message to backend
    discord_message_event = {
        "type": "message_created",
        "data": {
            "ticket_id": str(ticket.id),
            "discord_message_id": 555666777,
            "author_discord_id": 111222335,
            "content": "Message from Discord",
            "message_type": "user_message"
        }
    }
    
    await redis_service.publish("discord_events", json.dumps(discord_message_event))
    await asyncio.sleep(0.1)
    
    # Simulate backend processing Discord message
    message_data = MessageCreate(
        ticket_id=ticket.id,
        discord_message_id=555666777,
        author_discord_id=111222335,
        content="Message from Discord",
        message_type="user_message"
    )
    
    backend_message = await ticket_service.add_message(message_data)
    assert backend_message.content == "Message from Discord"
    
    # Test 2: Backend message to Discord
    backend_message_data = MessageCreate(
        ticket_id=ticket.id,
        author_discord_id=setup["staff"].discord_id,
        content="Response from backend",
        message_type="staff_message"
    )
    
    staff_message = await ticket_service.add_message(backend_message_data)
    await asyncio.sleep(0.1)
    
    # Verify Discord received the backend message event
    assert len(discord_events) >= 1
    message_event = discord_events[-1]["message"]
    assert message_event["type"] == "message_added"
    assert message_event["data"]["content"] == "Response from backend"


@pytest.mark.asyncio
async def test_conflict_resolution_during_sync(sync_integration_setup):
    """Test conflict resolution when simultaneous updates occur."""
    setup = sync_integration_setup
    ticket_service = setup["ticket_service"]
    redis_service = setup["redis_service"]
    staff = setup["staff"]
    
    # Create ticket
    ticket_data = TicketCreate(
        discord_channel_id=987654324,
        title="Conflict Test",
        description="Testing conflict resolution",
        creator_discord_id=111222336
    )
    
    ticket = await ticket_service.create_ticket(ticket_data)
    
    # Simulate simultaneous updates from Discord and backend
    async def discord_update():
        # Simulate Discord updating ticket status
        discord_update_event = {
            "type": "ticket_updated",
            "data": {
                "ticket_id": str(ticket.id),
                "status": "closed",
                "updated_by": "discord_user",
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        await redis_service.publish("discord_events", json.dumps(discord_update_event))
        
        # Simulate backend processing Discord update
        update_data = TicketUpdate(status="closed")
        return await ticket_service.update_ticket(ticket.id, update_data)
    
    async def backend_update():
        # Simulate backend updating ticket assignment
        update_data = TicketUpdate(assigned_staff_id=staff.discord_id)
        return await ticket_service.update_ticket(ticket.id, update_data)
    
    # Run simultaneous updates
    results = await asyncio.gather(
        discord_update(),
        backend_update(),
        return_exceptions=True
    )
    
    # Verify no exceptions occurred (conflict resolution handled gracefully)
    for result in results:
        assert not isinstance(result, Exception), f"Conflict resolution failed: {result}"
    
    # Verify final state is consistent
    final_ticket = await ticket_service.get_ticket(ticket.id)
    assert final_ticket.status == "closed"  # Discord update
    assert final_ticket.assigned_staff_id == staff.discord_id  # Backend update


@pytest.mark.asyncio
async def test_sync_failure_recovery(sync_integration_setup):
    """Test synchronization failure recovery mechanisms."""
    setup = sync_integration_setup
    ticket_service = setup["ticket_service"]
    redis_service = setup["redis_service"]
    
    # Create ticket
    ticket_data = TicketCreate(
        discord_channel_id=987654325,
        title="Sync Failure Test",
        description="Testing sync failure recovery",
        creator_discord_id=111222337
    )
    
    ticket = await ticket_service.create_ticket(ticket_data)
    
    # Simulate Redis connection failure
    with patch.object(redis_service, 'publish', side_effect=Exception("Redis connection lost")):
        # Try to add message (sync should fail but operation should succeed)
        message_data = MessageCreate(
            ticket_id=ticket.id,
            author_discord_id=111222337,
            content="Message during Redis failure",
            message_type="user_message"
        )
        
        # Should not raise exception despite sync failure
        message = await ticket_service.add_message(message_data)
        assert message is not None
        assert message.content == "Message during Redis failure"
    
    # Verify system recovers after Redis is back
    recovery_message_data = MessageCreate(
        ticket_id=ticket.id,
        author_discord_id=111222337,
        content="Message after recovery",
        message_type="user_message"
    )
    
    recovery_message = await ticket_service.add_message(recovery_message_data)
    assert recovery_message is not None
    assert recovery_message.content == "Message after recovery"


@pytest.mark.asyncio
async def test_discord_permission_sync(sync_integration_setup):
    """Test Discord permission synchronization with backend changes."""
    setup = sync_integration_setup
    ticket_service = setup["ticket_service"]
    redis_service = setup["redis_service"]
    mock_discord_bot = setup["mock_discord_bot"]
    staff = setup["staff"]
    
    # Create ticket
    ticket_data = TicketCreate(
        discord_channel_id=987654326,
        title="Permission Sync Test",
        description="Testing permission synchronization",
        creator_discord_id=111222338
    )
    
    ticket = await ticket_service.create_ticket(ticket_data)
    
    # Set up Discord permission event listener
    permission_events = []
    
    async def permission_event_handler(channel, message):
        permission_events.append({"channel": channel, "message": json.loads(message)})
    
    await redis_service.subscribe("permission_events", permission_event_handler)
    
    # Assign ticket to staff (should trigger permission update)
    update_data = TicketUpdate(assigned_staff_id=staff.discord_id)
    await ticket_service.update_ticket(ticket.id, update_data)
    
    # Wait for event processing
    await asyncio.sleep(0.1)
    
    # Verify permission update event was sent
    assert len(permission_events) >= 1
    permission_event = permission_events[-1]["message"]
    assert permission_event["type"] == "permission_update"
    assert permission_event["data"]["ticket_id"] == str(ticket.id)
    assert permission_event["data"]["assigned_staff_id"] == staff.discord_id
    
    # Close ticket (should trigger permission removal)
    close_data = TicketUpdate(status="closed")
    await ticket_service.update_ticket(ticket.id, close_data)
    
    await asyncio.sleep(0.1)
    
    # Verify permission removal event was sent
    assert len(permission_events) >= 2
    close_permission_event = permission_events[-1]["message"]
    assert close_permission_event["type"] == "permission_update"
    assert close_permission_event["data"]["status"] == "closed"


@pytest.mark.asyncio
async def test_webhook_integration_sync(sync_integration_setup):
    """Test webhook integration for external system synchronization."""
    setup = sync_integration_setup
    ticket_service = setup["ticket_service"]
    redis_service = setup["redis_service"]
    mock_http_client = setup["mock_http_client"]
    
    # Set up webhook event listener
    webhook_events = []
    
    async def webhook_event_handler(channel, message):
        webhook_events.append({"channel": channel, "message": json.loads(message)})
        
        # Simulate webhook delivery
        event_data = json.loads(message)
        mock_http_client.post.return_value.status_code = 200
        mock_http_client.post.return_value.json.return_value = {"success": True}
    
    await redis_service.subscribe("webhook_events", webhook_event_handler)
    
    # Create ticket (should trigger webhook)
    ticket_data = TicketCreate(
        discord_channel_id=987654327,
        title="Webhook Sync Test",
        description="Testing webhook synchronization",
        creator_discord_id=111222339
    )
    
    ticket = await ticket_service.create_ticket(ticket_data)
    
    # Simulate webhook event publishing
    webhook_data = {
        "type": "ticket.created",
        "data": {
            "ticket_id": str(ticket.id),
            "title": ticket.title,
            "status": ticket.status,
            "created_at": ticket.created_at.isoformat()
        }
    }
    
    await redis_service.publish("webhook_events", json.dumps(webhook_data))
    await asyncio.sleep(0.1)
    
    # Verify webhook event was processed
    assert len(webhook_events) >= 1
    webhook_event = webhook_events[0]["message"]
    assert webhook_event["type"] == "ticket.created"
    assert webhook_event["data"]["ticket_id"] == str(ticket.id)


@pytest.mark.asyncio
async def test_real_time_dashboard_sync(sync_integration_setup):
    """Test real-time dashboard synchronization with backend changes."""
    setup = sync_integration_setup
    ticket_service = setup["ticket_service"]
    redis_service = setup["redis_service"]
    
    # Set up dashboard event listener
    dashboard_events = []
    
    async def dashboard_event_handler(channel, message):
        dashboard_events.append({"channel": channel, "message": json.loads(message)})
    
    await redis_service.subscribe("dashboard_events", dashboard_event_handler)
    
    # Create ticket
    ticket_data = TicketCreate(
        discord_channel_id=987654328,
        title="Dashboard Sync Test",
        description="Testing dashboard synchronization",
        creator_discord_id=111222340
    )
    
    ticket = await ticket_service.create_ticket(ticket_data)
    
    # Add message
    message_data = MessageCreate(
        ticket_id=ticket.id,
        author_discord_id=111222340,
        content="Real-time sync test message",
        message_type="user_message"
    )
    
    await ticket_service.add_message(message_data)
    
    # Wait for events
    await asyncio.sleep(0.1)
    
    # Verify dashboard received real-time updates
    assert len(dashboard_events) >= 2  # ticket_created and message_added
    
    event_types = [event["message"]["type"] for event in dashboard_events]
    assert "ticket_created" in event_types
    assert "message_added" in event_types
    
    # Verify event data
    ticket_event = next(event for event in dashboard_events if event["message"]["type"] == "ticket_created")
    assert ticket_event["message"]["data"]["ticket_id"] == str(ticket.id)
    
    message_event = next(event for event in dashboard_events if event["message"]["type"] == "message_added")
    assert message_event["message"]["data"]["content"] == "Real-time sync test message"