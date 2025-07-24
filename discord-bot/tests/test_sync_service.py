"""Tests for the synchronization service."""

import os
import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock, AsyncMock

# Set test environment variables before importing modules
os.environ["DISCORD_BOT_TOKEN"] = "test_token"
os.environ["DISCORD_GUILD_ID"] = "123456789"
os.environ["BACKEND_API_URL"] = "http://localhost:8000"

# Add the parent directory to sys.path to allow imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.sync_service import (
    SynchronizationService,
    SyncEvent,
    SyncEventType,
    ConflictResolutionStrategy
)


@pytest.fixture
def mock_bot():
    """Create a mock Discord bot for testing."""
    mock_bot = MagicMock()
    mock_bot.get_channel.return_value = None
    mock_bot.guilds = []
    return mock_bot


@pytest.fixture
def mock_api_client():
    """Create a mock API client for testing."""
    mock_client = AsyncMock()
    mock_client.connected = True
    mock_client.add_message.return_value = {"id": "msg_123", "status": "created"}
    return mock_client


@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client for testing."""
    mock_client = AsyncMock()
    mock_client.connected = True
    return mock_client


@pytest.fixture
async def sync_service(mock_bot):
    """Create a sync service instance for testing."""
    with patch("utils.sync_service.get_api_client") as mock_get_api:
        with patch("utils.sync_service.get_redis_client") as mock_get_redis:
            mock_get_api.return_value = AsyncMock()
            mock_get_redis.return_value = AsyncMock()
            
            service = SynchronizationService(mock_bot)
            await service.initialize()
            yield service
            await service.shutdown()


@pytest.mark.asyncio
async def test_sync_service_initialization(mock_bot):
    """Test that the sync service initializes correctly."""
    with patch("utils.sync_service.get_api_client") as mock_get_api:
        with patch("utils.sync_service.get_redis_client") as mock_get_redis:
            mock_get_api.return_value = AsyncMock()
            mock_get_redis.return_value = AsyncMock()
            
            service = SynchronizationService(mock_bot)
            await service.initialize()
            
            assert service.bot == mock_bot
            assert service.running is True
            assert len(service.event_handlers) > 0
            
            await service.shutdown()


@pytest.mark.asyncio
async def test_event_emission(sync_service):
    """Test event emission and processing."""
    # Create a test event
    event_data = {
        "id": "ticket_123",
        "title": "Test ticket",
        "discord_channel_id": 123456789
    }
    
    event = SyncEvent(
        event_type=SyncEventType.TICKET_CREATED,
        data=event_data,
        source="discord"
    )
    
    # Emit the event
    await sync_service.emit_event(event)
    
    # Check that event was added to pending events
    assert len(sync_service.pending_events) == 1
    assert sync_service.pending_events[0].event_type == SyncEventType.TICKET_CREATED


@pytest.mark.asyncio
async def test_conflict_detection(sync_service):
    """Test conflict detection between events."""
    # Create two events for the same resource
    event_data = {
        "id": "ticket_123",
        "title": "Test ticket",
        "discord_channel_id": 123456789
    }
    
    event1 = SyncEvent(
        event_type=SyncEventType.TICKET_UPDATED,
        data=event_data,
        source="discord",
        timestamp=time.time()
    )
    
    event2 = SyncEvent(
        event_type=SyncEventType.TICKET_UPDATED,
        data=event_data,
        source="backend",
        timestamp=time.time() + 0.5  # 0.5 seconds later
    )
    
    # Emit first event
    await sync_service.emit_event(event1)
    
    # Check conflict detection for second event
    has_conflict = await sync_service._check_conflict(event2)
    assert has_conflict is True


@pytest.mark.asyncio
async def test_conflict_resolution_timestamp_wins(sync_service):
    """Test conflict resolution with timestamp wins strategy."""
    sync_service.conflict_resolution = ConflictResolutionStrategy.TIMESTAMP_WINS
    
    # Create two events for the same resource
    event_data = {
        "id": "ticket_123",
        "title": "Test ticket",
        "discord_channel_id": 123456789
    }
    
    older_event = SyncEvent(
        event_type=SyncEventType.TICKET_UPDATED,
        data=event_data,
        source="discord",
        timestamp=time.time() - 1.0
    )
    
    newer_event = SyncEvent(
        event_type=SyncEventType.TICKET_UPDATED,
        data=event_data,
        source="backend",
        timestamp=time.time()
    )
    
    # Add older event to recent events
    resource_id = sync_service._get_resource_id(older_event)
    sync_service.recent_events[resource_id] = older_event
    
    # Test conflict resolution
    should_process = await sync_service._resolve_conflict(newer_event)
    assert should_process is True  # Newer event should win


@pytest.mark.asyncio
async def test_conflict_resolution_backend_wins(sync_service):
    """Test conflict resolution with backend wins strategy."""
    sync_service.conflict_resolution = ConflictResolutionStrategy.BACKEND_WINS
    
    # Create events from different sources
    event_data = {
        "id": "ticket_123",
        "title": "Test ticket",
        "discord_channel_id": 123456789
    }
    
    discord_event = SyncEvent(
        event_type=SyncEventType.TICKET_UPDATED,
        data=event_data,
        source="discord"
    )
    
    backend_event = SyncEvent(
        event_type=SyncEventType.TICKET_UPDATED,
        data=event_data,
        source="backend"
    )
    
    # Test resolution for backend event
    should_process_backend = await sync_service._resolve_conflict(backend_event)
    assert should_process_backend is True
    
    # Test resolution for discord event
    should_process_discord = await sync_service._resolve_conflict(discord_event)
    assert should_process_discord is False


@pytest.mark.asyncio
async def test_resource_id_extraction(sync_service):
    """Test resource ID extraction from events."""
    # Test ticket event
    ticket_event = SyncEvent(
        event_type=SyncEventType.TICKET_CREATED,
        data={"id": "ticket_123", "discord_channel_id": 123456789},
        source="discord"
    )
    
    resource_id = sync_service._get_resource_id(ticket_event)
    assert resource_id == "ticket_123"
    
    # Test message event
    message_event = SyncEvent(
        event_type=SyncEventType.MESSAGE_CREATED,
        data={"id": "msg_123", "discord_message_id": 987654321},
        source="discord"
    )
    
    resource_id = sync_service._get_resource_id(message_event)
    assert resource_id == "msg_123"


@pytest.mark.asyncio
async def test_backend_ticket_created_handler(sync_service):
    """Test backend ticket created event handler."""
    # Mock the bot's ticket manager
    mock_ticket_manager = MagicMock()
    mock_ticket_manager.active_tickets = {}
    sync_service.bot.ticket_manager = mock_ticket_manager
    
    # Create event
    ticket_data = {
        "id": "ticket_123",
        "title": "Test ticket",
        "discord_channel_id": 123456789,
        "status": "open"
    }
    
    event = SyncEvent(
        event_type=SyncEventType.TICKET_CREATED,
        data=ticket_data,
        source="backend"
    )
    
    # Handle the event
    await sync_service._handle_backend_ticket_created(event)
    
    # Check that ticket was added to cache
    assert 123456789 in mock_ticket_manager.active_tickets
    assert mock_ticket_manager.active_tickets[123456789] == ticket_data


@pytest.mark.asyncio
async def test_backend_message_created_handler(sync_service):
    """Test backend message created event handler."""
    # Mock the bot components
    mock_ticket_manager = MagicMock()
    mock_ticket_manager.active_tickets = {
        123456789: {"id": "ticket_123", "title": "Test ticket"}
    }
    sync_service.bot.ticket_manager = mock_ticket_manager
    
    mock_channel = AsyncMock()
    sync_service.bot.get_channel.return_value = mock_channel
    
    mock_message_processor = AsyncMock()
    mock_message_processor.format_message.return_value = "**Web Dashboard:** Hello from web"
    sync_service.bot.message_processor = mock_message_processor
    
    # Create event
    message_data = {
        "id": "msg_123",
        "ticket_id": "ticket_123",
        "content": "Hello from web",
        "author_discord_id": 987654321
    }
    
    event = SyncEvent(
        event_type=SyncEventType.MESSAGE_CREATED,
        data=message_data,
        source="backend"
    )
    
    # Handle the event
    await sync_service._handle_backend_message_created(event)
    
    # Check that message was sent to Discord channel
    mock_channel.send.assert_called_once_with("**Web Dashboard:** Hello from web")


@pytest.mark.asyncio
async def test_discord_message_created_handler(sync_service, mock_api_client):
    """Test Discord message created event handler."""
    # Mock the API client
    sync_service.api_client = mock_api_client
    
    # Create event
    message_data = {
        "ticket_id": "ticket_123",
        "discord_message_id": 987654321,
        "author_discord_id": 123456789,
        "content": "Hello from Discord"
    }
    
    event = SyncEvent(
        event_type=SyncEventType.MESSAGE_CREATED,
        data=message_data,
        source="discord"
    )
    
    # Handle the event
    await sync_service._handle_discord_message_created(event)
    
    # Check that message was forwarded to backend
    mock_api_client.add_message.assert_called_once_with("ticket_123", message_data)


@pytest.mark.asyncio
async def test_event_retry_logic(sync_service, mock_api_client):
    """Test event retry logic on failure."""
    # Mock API client to fail initially
    mock_api_client.add_message.side_effect = Exception("API Error")
    sync_service.api_client = mock_api_client
    
    # Create event
    message_data = {
        "ticket_id": "ticket_123",
        "discord_message_id": 987654321,
        "author_discord_id": 123456789,
        "content": "Hello from Discord"
    }
    
    event = SyncEvent(
        event_type=SyncEventType.MESSAGE_CREATED,
        data=message_data,
        source="discord"
    )
    
    # Process the event (should fail and retry)
    await sync_service._process_event(event)
    
    # Check that retry count was incremented
    assert event.retry_count == 1
    
    # Check that event was re-queued
    assert len(sync_service.pending_events) == 1


@pytest.mark.asyncio
async def test_old_events_cleanup(sync_service):
    """Test cleanup of old events from cache."""
    # Add an old event to recent events
    old_event = SyncEvent(
        event_type=SyncEventType.TICKET_UPDATED,
        data={"id": "ticket_123"},
        source="discord",
        timestamp=time.time() - 100  # 100 seconds ago
    )
    
    sync_service.recent_events["ticket_123"] = old_event
    sync_service.event_timeout = 30.0  # 30 seconds timeout
    
    # Run cleanup
    await sync_service._cleanup_old_events()
    
    # Check that old event was removed
    assert "ticket_123" not in sync_service.recent_events


@pytest.mark.asyncio
async def test_event_merge_strategy(sync_service):
    """Test event merging conflict resolution strategy."""
    sync_service.conflict_resolution = ConflictResolutionStrategy.MERGE
    
    # Create two events with different data
    event1 = SyncEvent(
        event_type=SyncEventType.TICKET_UPDATED,
        data={"id": "ticket_123", "title": "Original Title"},
        source="discord"
    )
    
    event2 = SyncEvent(
        event_type=SyncEventType.TICKET_UPDATED,
        data={"id": "ticket_123", "status": "closed"},
        source="backend"
    )
    
    # Test merge
    success = await sync_service._merge_events(event1, event2)
    assert success is True
    
    # Check that data was merged
    expected_data = {"id": "ticket_123", "title": "Original Title", "status": "closed"}
    assert event2.data == expected_data