"""
Integration tests for Discord bot functionality.
Tests Discord bot integration with backend API and real Discord interactions.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from discord.ext import commands

from bot.ticket_bot import TicketBot
from bot.services.ticket_manager import TicketManager
from bot.services.http_client import HTTPClient
from bot.services.sync_service import SyncService


@pytest.fixture
async def discord_integration_setup():
    """Set up Discord integration test environment."""
    # Mock Discord bot
    mock_bot = MagicMock(spec=commands.Bot)
    mock_bot.user = MagicMock()
    mock_bot.user.id = 987654321
    mock_bot.get_guild = MagicMock()
    mock_bot.get_channel = MagicMock()
    
    # Mock guild and channels
    mock_guild = MagicMock(spec=discord.Guild)
    mock_guild.id = 123456789
    mock_guild.create_text_channel = AsyncMock()
    mock_guild.get_member = MagicMock()
    
    mock_channel = MagicMock(spec=discord.TextChannel)
    mock_channel.id = 555666777
    mock_channel.send = AsyncMock()
    mock_channel.edit = AsyncMock()
    mock_channel.set_permissions = AsyncMock()
    
    mock_bot.get_guild.return_value = mock_guild
    mock_bot.get_channel.return_value = mock_channel
    mock_guild.create_text_channel.return_value = mock_channel
    
    # Mock HTTP client for backend communication
    mock_http_client = MagicMock(spec=HTTPClient)
    mock_http_client.post = AsyncMock()
    mock_http_client.put = AsyncMock()
    mock_http_client.get = AsyncMock()
    
    # Initialize services
    ticket_manager = TicketManager(mock_bot, mock_http_client)
    sync_service = SyncService(mock_bot, mock_http_client)
    
    yield {
        "bot": mock_bot,
        "guild": mock_guild,
        "channel": mock_channel,
        "http_client": mock_http_client,
        "ticket_manager": ticket_manager,
        "sync_service": sync_service
    }


@pytest.mark.asyncio
async def test_discord_ticket_creation_integration(discord_integration_setup):
    """Test complete Discord ticket creation flow with backend integration."""
    setup = discord_integration_setup
    ticket_manager = setup["ticket_manager"]
    http_client = setup["http_client"]
    guild = setup["guild"]
    channel = setup["channel"]
    
    # Mock backend API response for ticket creation
    http_client.post.return_value.status_code = 201
    http_client.post.return_value.json.return_value = {
        "id": "ticket-uuid-123",
        "discord_channel_id": 555666777,
        "title": "Integration Test Ticket",
        "status": "open",
        "creator_discord_id": 111222333
    }
    
    # Mock Discord user
    mock_user = MagicMock(spec=discord.Member)
    mock_user.id = 111222333
    mock_user.display_name = "TestUser"
    mock_user.mention = "<@111222333>"
    
    # Create ticket through Discord
    ticket_data = {
        "title": "Integration Test Ticket",
        "description": "Testing Discord integration",
        "creator": mock_user,
        "guild": guild
    }
    
    result = await ticket_manager.create_ticket(**ticket_data)
    
    # Verify Discord channel was created
    guild.create_text_channel.assert_called_once()
    channel_creation_call = guild.create_text_channel.call_args
    assert "Integration Test Ticket" in channel_creation_call[0][0]
    
    # Verify backend API was called
    http_client.post.assert_called_once()
    api_call = http_client.post.call_args
    assert api_call[0][0] == "/api/tickets"
    
    api_data = api_call[1]["json"]
    assert api_data["title"] == "Integration Test Ticket"
    assert api_data["creator_discord_id"] == 111222333
    assert api_data["discord_channel_id"] == 555666777
    
    # Verify channel permissions were set
    channel.set_permissions.assert_called()
    
    # Verify welcome message was sent
    channel.send.assert_called()
    
    assert result["success"] is True
    assert result["ticket_id"] == "ticket-uuid-123"


@pytest.mark.asyncio
async def test_discord_message_processing_integration(discord_integration_setup):
    """Test Discord message processing and backend synchronization."""
    setup = discord_integration_setup
    sync_service = setup["sync_service"]
    http_client = setup["http_client"]
    channel = setup["channel"]
    
    # Mock backend API response for message creation
    http_client.post.return_value.status_code = 201
    http_client.post.return_value.json.return_value = {
        "id": "message-uuid-456",
        "ticket_id": "ticket-uuid-123",
        "content": "Test message from Discord",
        "author_discord_id": 111222333,
        "created_at": "2024-01-01T12:00:00Z"
    }
    
    # Mock Discord message
    mock_message = MagicMock(spec=discord.Message)
    mock_message.id = 888999000
    mock_message.content = "Test message from Discord"
    mock_message.author.id = 111222333
    mock_message.author.display_name = "TestUser"
    mock_message.channel = channel
    mock_message.channel.id = 555666777
    
    # Process message through Discord bot
    result = await sync_service.process_discord_message(mock_message, "ticket-uuid-123")
    
    # Verify backend API was called
    http_client.post.assert_called_once()
    api_call = http_client.post.call_args
    assert "/api/tickets/ticket-uuid-123/messages" in api_call[0][0]
    
    api_data = api_call[1]["json"]
    assert api_data["content"] == "Test message from Discord"
    assert api_data["author_discord_id"] == 111222333
    assert api_data["discord_message_id"] == 888999000
    
    assert result["success"] is True
    assert result["message_id"] == "message-uuid-456"


@pytest.mark.asyncio
async def test_discord_ticket_assignment_integration(discord_integration_setup):
    """Test Discord ticket assignment with backend synchronization."""
    setup = discord_integration_setup
    ticket_manager = setup["ticket_manager"]
    http_client = setup["http_client"]
    channel = setup["channel"]
    
    # Mock backend API response for ticket update
    http_client.put.return_value.status_code = 200
    http_client.put.return_value.json.return_value = {
        "id": "ticket-uuid-123",
        "assigned_staff_id": 444555666,
        "status": "in_progress",
        "updated_at": "2024-01-01T12:00:00Z"
    }
    
    # Mock staff member
    mock_staff = MagicMock(spec=discord.Member)
    mock_staff.id = 444555666
    mock_staff.display_name = "StaffMember"
    mock_staff.mention = "<@444555666>"
    
    # Assign ticket through Discord
    result = await ticket_manager.assign_ticket("ticket-uuid-123", mock_staff, channel)
    
    # Verify backend API was called
    http_client.put.assert_called_once()
    api_call = http_client.put.call_args
    assert "/api/tickets/ticket-uuid-123" in api_call[0][0]
    
    api_data = api_call[1]["json"]
    assert api_data["assigned_staff_id"] == 444555666
    assert api_data["status"] == "in_progress"
    
    # Verify Discord channel permissions were updated
    channel.set_permissions.assert_called()
    
    # Verify assignment message was sent
    channel.send.assert_called()
    
    assert result["success"] is True


@pytest.mark.asyncio
async def test_discord_ticket_closure_integration(discord_integration_setup):
    """Test Discord ticket closure with backend synchronization."""
    setup = discord_integration_setup
    ticket_manager = setup["ticket_manager"]
    http_client = setup["http_client"]
    channel = setup["channel"]
    
    # Mock backend API responses
    http_client.put.return_value.status_code = 200
    http_client.put.return_value.json.return_value = {
        "id": "ticket-uuid-123",
        "status": "closed",
        "closed_at": "2024-01-01T12:00:00Z"
    }
    
    http_client.get.return_value.status_code = 200
    http_client.get.return_value.json.return_value = {
        "content": "Ticket transcript content...",
        "formatted_content": {"messages": []},
        "created_at": "2024-01-01T12:00:00Z"
    }
    
    # Mock staff member closing ticket
    mock_staff = MagicMock(spec=discord.Member)
    mock_staff.id = 444555666
    mock_staff.display_name = "StaffMember"
    
    # Close ticket through Discord
    result = await ticket_manager.close_ticket("ticket-uuid-123", mock_staff, channel)
    
    # Verify backend API was called to close ticket
    http_client.put.assert_called()
    close_call = http_client.put.call_args
    assert "/api/tickets/ticket-uuid-123" in close_call[0][0]
    
    close_data = close_call[1]["json"]
    assert close_data["status"] == "closed"
    
    # Verify transcript was requested
    http_client.get.assert_called()
    transcript_call = http_client.get.call_args
    assert "/api/tickets/ticket-uuid-123/transcript" in transcript_call[0][0]
    
    # Verify channel was archived (permissions updated)
    channel.set_permissions.assert_called()
    
    # Verify closure message was sent
    channel.send.assert_called()
    
    assert result["success"] is True


@pytest.mark.asyncio
async def test_discord_backend_sync_error_handling(discord_integration_setup):
    """Test error handling during Discord-backend synchronization."""
    setup = discord_integration_setup
    ticket_manager = setup["ticket_manager"]
    http_client = setup["http_client"]
    guild = setup["guild"]
    
    # Mock backend API failure
    http_client.post.return_value.status_code = 500
    http_client.post.return_value.json.return_value = {
        "detail": "Internal server error"
    }
    
    # Mock Discord user
    mock_user = MagicMock(spec=discord.Member)
    mock_user.id = 111222333
    mock_user.display_name = "TestUser"
    
    # Attempt to create ticket with backend failure
    ticket_data = {
        "title": "Error Test Ticket",
        "description": "Testing error handling",
        "creator": mock_user,
        "guild": guild
    }
    
    result = await ticket_manager.create_ticket(**ticket_data)
    
    # Verify error was handled gracefully
    assert result["success"] is False
    assert "error" in result
    
    # Verify Discord channel was still created (graceful degradation)
    guild.create_text_channel.assert_called_once()


@pytest.mark.asyncio
async def test_discord_permission_management_integration(discord_integration_setup):
    """Test Discord permission management integration."""
    setup = discord_integration_setup
    ticket_manager = setup["ticket_manager"]
    channel = setup["channel"]
    guild = setup["guild"]
    
    # Mock users
    mock_creator = MagicMock(spec=discord.Member)
    mock_creator.id = 111222333
    
    mock_staff = MagicMock(spec=discord.Member)
    mock_staff.id = 444555666
    
    guild.get_member.side_effect = lambda user_id: {
        111222333: mock_creator,
        444555666: mock_staff
    }.get(user_id)
    
    # Test permission setup for new ticket
    await ticket_manager.setup_ticket_permissions(
        channel, 
        creator_id=111222333,
        staff_ids=[444555666]
    )
    
    # Verify permissions were set for creator and staff
    assert channel.set_permissions.call_count >= 2
    
    permission_calls = channel.set_permissions.call_args_list
    
    # Check that creator and staff got appropriate permissions
    called_members = [call[0][0] for call in permission_calls if len(call[0]) > 0]
    assert mock_creator in called_members
    assert mock_staff in called_members


@pytest.mark.asyncio
async def test_discord_slash_command_integration(discord_integration_setup):
    """Test Discord slash command integration with backend."""
    setup = discord_integration_setup
    bot = setup["bot"]
    http_client = setup["http_client"]
    
    # Mock interaction
    mock_interaction = MagicMock()
    mock_interaction.user.id = 111222333
    mock_interaction.user.display_name = "TestUser"
    mock_interaction.guild_id = 123456789
    mock_interaction.response.send_message = AsyncMock()
    mock_interaction.followup.send = AsyncMock()
    
    # Mock backend response
    http_client.post.return_value.status_code = 201
    http_client.post.return_value.json.return_value = {
        "id": "ticket-uuid-123",
        "discord_channel_id": 555666777,
        "title": "Slash Command Test",
        "status": "open"
    }
    
    # Create TicketBot instance
    ticket_bot = TicketBot()
    ticket_bot.bot = bot
    ticket_bot.http_client = http_client
    ticket_bot.ticket_manager = setup["ticket_manager"]
    
    # Test /ticket create command
    await ticket_bot.create_ticket_command(
        mock_interaction,
        subject="Slash Command Test",
        description="Testing slash command integration"
    )
    
    # Verify interaction was acknowledged
    mock_interaction.response.send_message.assert_called_once()
    
    # Verify backend API was called
    http_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_discord_event_handling_integration(discord_integration_setup):
    """Test Discord event handling and backend synchronization."""
    setup = discord_integration_setup
    sync_service = setup["sync_service"]
    http_client = setup["http_client"]
    
    # Mock backend event response
    http_client.post.return_value.status_code = 200
    http_client.post.return_value.json.return_value = {"success": True}
    
    # Test message delete event
    mock_message = MagicMock(spec=discord.Message)
    mock_message.id = 888999000
    mock_message.channel.id = 555666777
    
    await sync_service.handle_message_delete(mock_message, "ticket-uuid-123")
    
    # Verify backend was notified of message deletion
    http_client.post.assert_called_once()
    api_call = http_client.post.call_args
    assert "delete" in api_call[0][0] or "remove" in api_call[0][0]
    
    # Test member leave event
    mock_member = MagicMock(spec=discord.Member)
    mock_member.id = 111222333
    
    await sync_service.handle_member_leave(mock_member)
    
    # Verify backend was notified of member leaving
    assert http_client.post.call_count >= 2