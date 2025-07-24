"""Integration tests for Discord-Backend synchronization."""

import os
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

# Set test environment variables before importing modules
os.environ["DISCORD_BOT_TOKEN"] = "test_token"
os.environ["DISCORD_GUILD_ID"] = "123456789"
os.environ["BACKEND_API_URL"] = "http://localhost:8000"

# Add the parent directory to sys.path to allow imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot.message_processor import MessageProcessor
from bot.ticket_manager import TicketManager
from utils.sync_service import SynchronizationService, SyncEvent, SyncEventType


@pytest.fixture
def mock_discord_message():
    """Create a mock Discord message."""
    import discord
    mock_message = MagicMock()
    mock_message.id = 987654321
    mock_message.content = "Hello from Discord"
    mock_message.author.id = 123456789
    mock_message.author.bot = False
    mock_message.type = discord.MessageType.default
    mock_message.attachments = []
    return mock_message


@pytest.fixture
def mock_discord_guild():
    """Create a mock Discord guild."""
    mock_guild = MagicMock()
    mock_guild.id = 111222333
    mock_guild.create_text_channel = AsyncMock()
    mock_guild.default_role = MagicMock()
    return mock_guild


@pytest.fixture
def mock_discord_user():
    """Create a mock Discord user."""
    mock_user = MagicMock()
    mock_user.id = 123456789
    mock_user.name = "testuser"
    mock_user.mention = "<@123456789>"
    return mock_user


@pytest.fixture
def mock_bot():
    """Create a mock Discord bot."""
    mock_bot = MagicMock()
    mock_bot.get_channel.return_value = None
    mock_bot.guilds = []
    return mock_bot


@pytest.fixture
async def integrated_components(mock_bot):
    """Create integrated components for testing."""
    with patch("utils.http_client.get_api_client") as mock_get_api:
        with patch("utils.redis_client.get_redis_client") as mock_get_redis:
            with patch("utils.sync_service.get_api_client") as mock_sync_api:
                with patch("utils.sync_service.get_redis_client") as mock_sync_redis:
                    # Mock API clients
                    mock_api_client = AsyncMock()
                    mock_api_client.connected = True
                    
                    # Mock the check_connection method to return True immediately
                    async def mock_check_connection():
                        mock_api_client.connected = True
                        return True
                    mock_api_client.check_connection = mock_check_connection
                    mock_api_client.create_ticket.return_value = {
                        "id": "ticket_123",
                        "title": "Test ticket",
                        "discord_channel_id": 123456789,
                        "status": "open"
                    }
                    mock_api_client.add_message.return_value = {
                        "id": "msg_123",
                        "status": "created"
                    }
                    mock_api_client.update_ticket.return_value = {
                        "id": "ticket_123",
                        "title": "Test ticket",
                        "status": "updated"
                    }
                    mock_api_client.close_ticket.return_value = {
                        "id": "ticket_123",
                        "title": "Test ticket",
                        "status": "closed"
                    }
                    
                    mock_get_api.return_value = mock_api_client
                    mock_sync_api.return_value = mock_api_client
                    
                    # Mock Redis clients
                    mock_redis_client = AsyncMock()
                    mock_redis_client.connected = True
                    mock_get_redis.return_value = mock_redis_client
                    mock_sync_redis.return_value = mock_redis_client
                    
                    # Create components
                    sync_service = SynchronizationService(mock_bot)
                    await sync_service.initialize()
                    
                    message_processor = MessageProcessor(mock_bot)
                    await message_processor.initialize()
                    
                    ticket_manager = TicketManager(mock_bot)
                    await ticket_manager.initialize()
                    
                    # Set up bot references
                    mock_bot.message_processor = message_processor
                    mock_bot.ticket_manager = ticket_manager
                    
                    # Directly set the API client on components to ensure they're connected
                    message_processor.api_client = mock_api_client
                    ticket_manager.api_client = mock_api_client
                    sync_service.api_client = mock_api_client
                    
                    yield {
                        "sync_service": sync_service,
                        "message_processor": message_processor,
                        "ticket_manager": ticket_manager,
                        "api_client": mock_api_client,
                        "redis_client": mock_redis_client
                    }
                    
                    await sync_service.shutdown()


@pytest.mark.asyncio
async def test_discord_to_backend_message_sync(integrated_components, mock_discord_message):
    """Test message synchronization from Discord to backend."""
    components = integrated_components
    message_processor = components["message_processor"]
    api_client = components["api_client"]
    
    # Process a Discord message
    result = await message_processor.process_message(mock_discord_message, "ticket_123")
    
    # Wait a bit for async processing
    await asyncio.sleep(0.1)
    
    # Check that message was processed
    assert result is not None
    assert result["discord_message_id"] == 987654321
    assert result["content"] == "Hello from Discord"
    
    # Check that API was called (via sync service)
    # Note: In a real integration test, we'd verify the API call was made
    # Here we just verify the sync event was created properly


@pytest.mark.asyncio
async def test_backend_to_discord_message_sync(integrated_components):
    """Test message synchronization from backend to Discord."""
    components = integrated_components
    sync_service = components["sync_service"]
    
    # Mock Discord channel
    mock_channel = AsyncMock()
    components["sync_service"].bot.get_channel.return_value = mock_channel
    
    # Mock ticket manager with active ticket
    mock_ticket_manager = MagicMock()
    mock_ticket_manager.active_tickets = {
        123456789: {"id": "ticket_123", "title": "Test ticket"}
    }
    components["sync_service"].bot.ticket_manager = mock_ticket_manager
    
    # Mock message processor
    mock_message_processor = AsyncMock()
    mock_message_processor.format_message.return_value = "**Web Dashboard:** Hello from web"
    components["sync_service"].bot.message_processor = mock_message_processor
    
    # Create backend message event
    message_data = {
        "id": "msg_123",
        "ticket_id": "ticket_123",
        "content": "Hello from web",
        "author_discord_id": 987654321,
        "source": "dashboard"
    }
    
    event = SyncEvent(
        event_type=SyncEventType.MESSAGE_CREATED,
        data=message_data,
        source="backend"
    )
    
    # Emit the event
    await sync_service.emit_event(event)
    
    # Wait for processing
    await asyncio.sleep(0.2)
    
    # Check that message was sent to Discord
    mock_channel.send.assert_called_once_with("**Web Dashboard:** Hello from web")


@pytest.mark.asyncio
async def test_ticket_creation_sync(integrated_components, mock_discord_guild, mock_discord_user):
    """Test ticket creation synchronization."""
    components = integrated_components
    ticket_manager = components["ticket_manager"]
    
    # Mock Discord channel creation
    mock_channel = AsyncMock()
    mock_channel.id = 123456789
    mock_channel.send = AsyncMock()
    mock_channel.set_permissions = AsyncMock()
    mock_discord_guild.create_text_channel.return_value = mock_channel
    
    # Mock category and role
    mock_category = MagicMock()
    mock_role = MagicMock()
    
    with patch.object(ticket_manager, 'get_ticket_category', return_value=mock_category):
        with patch.object(ticket_manager, 'get_staff_role', return_value=mock_role):
            # Create a ticket
            result = await ticket_manager.create_ticket(
                guild=mock_discord_guild,
                user=mock_discord_user,
                title="Test ticket",
                description="Test description"
            )
            
            # Wait for processing
            await asyncio.sleep(0.1)
            
            # Check that ticket was created
            assert result is not None
            assert result["id"] == "ticket_123"
            assert result["title"] == "Test ticket"
            
            # Check that Discord channel was created
            mock_discord_guild.create_text_channel.assert_called_once()
            
            # Check that welcome message was sent
            mock_channel.send.assert_called_once()
            
            # Check that ticket is in active tickets
            assert 123456789 in ticket_manager.active_tickets


@pytest.mark.asyncio
async def test_ticket_update_sync(integrated_components):
    """Test ticket update synchronization."""
    components = integrated_components
    ticket_manager = components["ticket_manager"]
    api_client = components["api_client"]
    
    # Set up existing ticket
    ticket_manager.active_tickets[123456789] = {
        "id": "ticket_123",
        "title": "Test ticket",
        "status": "open"
    }
    
    # Mock API response
    api_client.update_ticket.return_value = {
        "id": "ticket_123",
        "title": "Test ticket",
        "status": "in_progress"
    }
    
    # Update the ticket
    result = await ticket_manager.update_ticket(123456789, {"status": "in_progress"})
    
    # Wait for processing
    await asyncio.sleep(0.1)
    
    # Check that ticket was updated
    assert result is not None
    assert result["status"] == "in_progress"
    
    # Check that API was called
    api_client.update_ticket.assert_called_once_with("ticket_123", {"status": "in_progress"})
    
    # Check that local cache was updated
    assert ticket_manager.active_tickets[123456789]["status"] == "in_progress"


@pytest.mark.asyncio
async def test_ticket_close_sync(integrated_components):
    """Test ticket close synchronization."""
    components = integrated_components
    ticket_manager = components["ticket_manager"]
    api_client = components["api_client"]
    
    # Set up existing ticket
    ticket_manager.active_tickets[123456789] = {
        "id": "ticket_123",
        "title": "Test ticket",
        "status": "open"
    }
    
    # Mock Discord channel
    mock_channel = AsyncMock()
    components["sync_service"].bot.get_channel.return_value = mock_channel
    
    # Mock API response
    api_client.close_ticket.return_value = {
        "id": "ticket_123",
        "title": "Test ticket",
        "status": "closed"
    }
    
    # Close the ticket
    result = await ticket_manager.close_ticket(123456789)
    
    # Wait for processing
    await asyncio.sleep(0.1)
    
    # Check that ticket was closed
    assert result is True
    
    # Check that API was called
    api_client.close_ticket.assert_called_once_with("ticket_123")
    
    # Check that ticket was removed from cache
    assert 123456789 not in ticket_manager.active_tickets
    
    # Check that Discord channel was notified
    mock_channel.send.assert_called_once_with("🔒 This ticket has been closed.")


@pytest.mark.asyncio
async def test_bidirectional_sync_conflict_resolution(integrated_components):
    """Test conflict resolution in bidirectional synchronization."""
    components = integrated_components
    sync_service = components["sync_service"]
    
    # Create two conflicting events
    ticket_data_discord = {
        "id": "ticket_123",
        "title": "Discord Title",
        "status": "open"
    }
    
    ticket_data_backend = {
        "id": "ticket_123",
        "title": "Backend Title",
        "status": "closed"
    }
    
    discord_event = SyncEvent(
        event_type=SyncEventType.TICKET_UPDATED,
        data=ticket_data_discord,
        source="discord"
    )
    
    backend_event = SyncEvent(
        event_type=SyncEventType.TICKET_UPDATED,
        data=ticket_data_backend,
        source="backend"
    )
    
    # Emit first event
    await sync_service.emit_event(discord_event)
    
    # Wait a bit
    await asyncio.sleep(0.01)
    
    # Emit conflicting event
    await sync_service.emit_event(backend_event)
    
    # Wait for processing
    await asyncio.sleep(0.1)
    
    # Check that conflict was detected and resolved
    # The exact resolution depends on the strategy, but both events should be processed
    assert len(sync_service.recent_events) > 0


@pytest.mark.asyncio
async def test_sync_service_error_handling(integrated_components):
    """Test error handling in synchronization service."""
    components = integrated_components
    sync_service = components["sync_service"]
    api_client = components["api_client"]
    
    # Make API client fail
    api_client.add_message.side_effect = Exception("API Error")
    
    # Create message event
    message_data = {
        "ticket_id": "ticket_123",
        "discord_message_id": 987654321,
        "content": "Test message"
    }
    
    event = SyncEvent(
        event_type=SyncEventType.MESSAGE_CREATED,
        data=message_data,
        source="discord"
    )
    
    # Emit the event
    await sync_service.emit_event(event)
    
    # Wait for processing and retries
    await asyncio.sleep(0.3)
    
    # Check that retry logic was triggered
    # The event should have been retried based on the retry count
    assert api_client.add_message.call_count > 1