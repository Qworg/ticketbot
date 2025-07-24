"""Tests for bot initialization."""

import os
import pytest
import asyncio
import datetime
from unittest.mock import patch, MagicMock, AsyncMock

import discord
from discord.ext import commands

# Add the parent directory to sys.path to allow imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from discord_bot.bot.ticket_bot import TicketBot
from discord_bot.config.settings import BotConfig


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    return BotConfig(
        token="test_token",
        guild_id=123456789,
        api_url="http://localhost:8000",
        api_key="test_api_key",
        redis_url="redis://localhost:6379",
        command_prefix="!",
        ticket_category_id=987654321,
        staff_role_id=123123123,
        log_level="INFO"
    )


@pytest.mark.asyncio
async def test_bot_initialization():
    """Test that the bot initializes correctly."""
    with patch("discord_bot.bot.ticket_bot.config", create=True) as mock_config:
        # Configure the mock
        mock_config.token = "test_token"
        mock_config.command_prefix = "!"
        
        # Create the bot
        bot = TicketBot()
        
        # Check that the bot was initialized correctly
        assert bot.command_prefix == "!"
        assert bot.description == "Discord Ticket Bot for support ticket management"
        assert bot.intents.message_content is True
        assert bot.intents.members is True
        assert bot.intents.guilds is True
        assert bot.is_ready is False
        assert bot.synced is False
        assert bot.health_status["status"] == "starting"
        assert bot.health_status["version"] == "0.1.0"
        assert bot.health_status["python_version"] == sys.version.split()[0]
        assert bot.health_status["discord_version"] == discord.__version__


@pytest.mark.asyncio
async def test_bot_setup_hook():
    """Test the setup_hook method."""
    with patch("discord_bot.bot.ticket_bot.config", create=True) as mock_config:
        # Configure the mock
        mock_config.token = "test_token"
        mock_config.command_prefix = "!"
        
        # Create the bot
        bot = TicketBot()
        
        # Mock the manager initialize methods
        bot.message_processor.initialize = AsyncMock()
        bot.ticket_manager.initialize = AsyncMock()
        
        # Mock the load_extensions method
        bot.load_extensions = AsyncMock()
        
        # Call the setup_hook method
        await bot.setup_hook()
        
        # Check that the methods were called correctly
        bot.message_processor.initialize.assert_called_once()
        bot.ticket_manager.initialize.assert_called_once()
        bot.load_extensions.assert_called_once()
        
        # Check that the startup time was set
        assert bot.startup_time is not None


@pytest.mark.asyncio
async def test_bot_sync_commands():
    """Test that the bot syncs commands correctly."""
    with patch("discord_bot.bot.ticket_bot.config", create=True) as mock_config:
        # Configure the mock
        mock_config.token = "test_token"
        mock_config.command_prefix = "!"
        mock_config.guild_id = 123456789
        
        # Create the bot
        bot = TicketBot()
        
        # Mock the tree.sync method
        bot.tree.sync = AsyncMock()
        
        # Mock the tree.copy_global_to method
        bot.tree.copy_global_to = MagicMock()
        
        # Call the sync_commands method
        await bot.sync_commands()
        
        # Check that the methods were called correctly
        bot.tree.copy_global_to.assert_called_once()
        bot.tree.sync.assert_called_once()
        assert bot.synced is True
        assert bot.health_status["commands_synced"] is True


@pytest.mark.asyncio
async def test_bot_sync_commands_global():
    """Test that the bot syncs commands globally when no guild ID is provided."""
    with patch("discord_bot.bot.ticket_bot.config", create=True) as mock_config:
        # Configure the mock
        mock_config.token = "test_token"
        mock_config.command_prefix = "!"
        mock_config.guild_id = None  # No guild ID
        
        # Create the bot
        bot = TicketBot()
        
        # Mock the tree.sync method
        bot.tree.sync = AsyncMock()
        
        # Mock the tree.copy_global_to method
        bot.tree.copy_global_to = MagicMock()
        
        # Call the sync_commands method
        await bot.sync_commands()
        
        # Check that the methods were called correctly
        bot.tree.copy_global_to.assert_not_called()
        bot.tree.sync.assert_called_once()
        assert bot.synced is True
        assert bot.health_status["commands_synced"] is True


@pytest.mark.asyncio
async def test_bot_sync_commands_error():
    """Test that the bot handles sync command errors correctly."""
    with patch("discord_bot.bot.ticket_bot.config", create=True) as mock_config:
        # Configure the mock
        mock_config.token = "test_token"
        mock_config.command_prefix = "!"
        mock_config.guild_id = 123456789
        
        # Create the bot
        bot = TicketBot()
        
        # Mock the tree.sync method to raise an exception
        bot.tree.sync = AsyncMock(side_effect=discord.HTTPException(MagicMock(), "Test error"))
        
        # Mock the tree.copy_global_to method
        bot.tree.copy_global_to = MagicMock()
        
        # Call the sync_commands method
        await bot.sync_commands()
        
        # Check that the methods were called correctly
        bot.tree.copy_global_to.assert_called_once()
        bot.tree.sync.assert_called_once()
        assert bot.synced is False
        assert bot.health_status["commands_synced"] is False


@pytest.mark.asyncio
async def test_bot_on_ready():
    """Test the on_ready event handler."""
    with patch("discord_bot.bot.ticket_bot.config", create=True) as mock_config:
        # Configure the mock
        mock_config.token = "test_token"
        mock_config.command_prefix = "!"
        
        # Create the bot
        bot = TicketBot()
        
        # Mock the sync_commands method
        bot.sync_commands = AsyncMock()
        
        # Mock the change_presence method
        bot.change_presence = AsyncMock()
        
        # Mock the register_basic_commands method
        bot.register_basic_commands = AsyncMock()
        
        # Mock bot properties
        bot.user = MagicMock()
        bot.user.id = 123456789
        bot.guilds = [MagicMock(), MagicMock()]
        
        # Call the on_ready method
        await bot.on_ready()
        
        # Check that the methods were called correctly
        bot.sync_commands.assert_called_once()
        bot.change_presence.assert_called_once()
        bot.register_basic_commands.assert_called_once()
        assert bot.is_ready is True
        assert bot.health_status["discord_connected"] is True
        assert bot.health_status["status"] == "running"


@pytest.mark.asyncio
async def test_bot_on_ready_reconnect():
    """Test the on_ready event handler when reconnecting."""
    with patch("discord_bot.bot.ticket_bot.config", create=True) as mock_config:
        # Configure the mock
        mock_config.token = "test_token"
        mock_config.command_prefix = "!"
        
        # Create the bot
        bot = TicketBot()
        
        # Set the bot as already ready
        bot.is_ready = True
        
        # Mock the sync_commands method
        bot.sync_commands = AsyncMock()
        
        # Mock the change_presence method
        bot.change_presence = AsyncMock()
        
        # Mock the register_basic_commands method
        bot.register_basic_commands = AsyncMock()
        
        # Mock bot properties
        bot.user = MagicMock()
        bot.user.id = 123456789
        bot.guilds = [MagicMock(), MagicMock()]
        
        # Call the on_ready method
        await bot.on_ready()
        
        # Check that the methods were not called
        bot.sync_commands.assert_not_called()
        bot.change_presence.assert_not_called()
        bot.register_basic_commands.assert_not_called()
        assert bot.is_ready is True
        assert bot.health_status["discord_connected"] is True
        assert bot.health_status["status"] == "running"


@pytest.mark.asyncio
async def test_bot_on_disconnect():
    """Test the on_disconnect event handler."""
    with patch("discord_bot.bot.ticket_bot.config", create=True) as mock_config:
        # Configure the mock
        mock_config.token = "test_token"
        mock_config.command_prefix = "!"
        
        # Create the bot
        bot = TicketBot()
        
        # Call the on_disconnect method
        await bot.on_disconnect()
        
        # Check that the health status was updated
        assert bot.health_status["discord_connected"] is False
        assert bot.health_status["status"] == "disconnected"


@pytest.mark.asyncio
async def test_bot_on_resumed():
    """Test the on_resumed event handler."""
    with patch("discord_bot.bot.ticket_bot.config", create=True) as mock_config:
        # Configure the mock
        mock_config.token = "test_token"
        mock_config.command_prefix = "!"
        
        # Create the bot
        bot = TicketBot()
        
        # Call the on_resumed method
        await bot.on_resumed()
        
        # Check that the health status was updated
        assert bot.health_status["discord_connected"] is True
        assert bot.health_status["status"] == "running"


@pytest.mark.asyncio
async def test_bot_check_health():
    """Test the check_health method."""
    with patch("discord_bot.bot.ticket_bot.config", create=True) as mock_config:
        # Configure the mock
        mock_config.token = "test_token"
        mock_config.command_prefix = "!"
        
        # Create the bot
        bot = TicketBot()
        
        # Mock bot methods
        bot.is_closed = MagicMock(return_value=False)
        bot.is_ready = True
        bot.synced = True
        bot.health_status["commands_synced"] = True
        bot.health_status["discord_connected"] = True
        bot.health_status["backend_connected"] = True
        bot.health_status["redis_connected"] = True
        
        # Set startup time
        bot.startup_time = discord.utils.utcnow() - datetime.timedelta(seconds=60)
        
        # Call the check_health method
        health_status = await bot.check_health()
        
        # Check the health status
        assert health_status["status"] == "healthy"
        assert health_status["discord_connected"] is True
        assert health_status["commands_synced"] is True
        assert health_status["backend_connected"] is True
        assert health_status["redis_connected"] is True
        assert health_status["uptime"] >= 60  # At least 60 seconds


@pytest.mark.asyncio
async def test_bot_check_health_degraded():
    """Test the check_health method with degraded status."""
    with patch("discord_bot.bot.ticket_bot.config", create=True) as mock_config:
        # Configure the mock
        mock_config.token = "test_token"
        mock_config.command_prefix = "!"
        
        # Create the bot
        bot = TicketBot()
        
        # Mock bot methods
        bot.is_closed = MagicMock(return_value=False)
        bot.is_ready = True
        bot.synced = True
        bot.health_status["commands_synced"] = True
        bot.health_status["discord_connected"] = True
        bot.health_status["backend_connected"] = False  # Backend not connected
        bot.health_status["redis_connected"] = True
        
        # Call the check_health method
        health_status = await bot.check_health()
        
        # Check the health status
        assert health_status["status"] == "degraded"
        assert health_status["discord_connected"] is True
        assert health_status["backend_connected"] is False


@pytest.mark.asyncio
async def test_bot_check_health_unhealthy():
    """Test the check_health method with unhealthy status."""
    with patch("discord_bot.bot.ticket_bot.config", create=True) as mock_config:
        # Configure the mock
        mock_config.token = "test_token"
        mock_config.command_prefix = "!"
        
        # Create the bot
        bot = TicketBot()
        
        # Mock bot methods
        bot.is_closed = MagicMock(return_value=False)
        bot.is_ready = False  # Bot not ready
        bot.synced = False
        bot.health_status["commands_synced"] = False
        bot.health_status["discord_connected"] = False
        bot.health_status["backend_connected"] = False
        bot.health_status["redis_connected"] = False
        
        # Call the check_health method
        health_status = await bot.check_health()
        
        # Check the health status
        assert health_status["status"] == "unhealthy"
        assert health_status["discord_connected"] is False


@pytest.mark.asyncio
async def test_bot_on_app_command_error_cooldown():
    """Test the on_app_command_error method with a cooldown error."""
    with patch("discord_bot.bot.ticket_bot.config", create=True) as mock_config:
        # Configure the mock
        mock_config.token = "test_token"
        mock_config.command_prefix = "!"
        
        # Create the bot
        bot = TicketBot()
        
        # Create a mock interaction
        interaction = MagicMock()
        interaction.response.send_message = AsyncMock()
        interaction.response.is_done = MagicMock(return_value=False)
        
        # Create a mock error
        error = discord.app_commands.CommandOnCooldown(retry_after=10)
        
        # Call the on_app_command_error method
        await bot.on_app_command_error(interaction, error)
        
        # Check that the response was sent
        interaction.response.send_message.assert_called_once()
        assert "cooldown" in interaction.response.send_message.call_args[0][0]


@pytest.mark.asyncio
async def test_bot_on_app_command_error_missing_permissions():
    """Test the on_app_command_error method with a missing permissions error."""
    with patch("discord_bot.bot.ticket_bot.config", create=True) as mock_config:
        # Configure the mock
        mock_config.token = "test_token"
        mock_config.command_prefix = "!"
        
        # Create the bot
        bot = TicketBot()
        
        # Create a mock interaction
        interaction = MagicMock()
        interaction.response.send_message = AsyncMock()
        interaction.response.is_done = MagicMock(return_value=False)
        
        # Create a mock error
        error = discord.app_commands.MissingPermissions(["manage_messages"])
        
        # Call the on_app_command_error method
        await bot.on_app_command_error(interaction, error)
        
        # Check that the response was sent
        interaction.response.send_message.assert_called_once()
        assert "permission" in interaction.response.send_message.call_args[0][0]


@pytest.mark.asyncio
async def test_bot_on_app_command_error_generic():
    """Test the on_app_command_error method with a generic error."""
    with patch("discord_bot.bot.ticket_bot.config", create=True) as mock_config:
        # Configure the mock
        mock_config.token = "test_token"
        mock_config.command_prefix = "!"
        
        # Create the bot
        bot = TicketBot()
        
        # Create a mock interaction
        interaction = MagicMock()
        interaction.response.send_message = AsyncMock()
        interaction.response.is_done = MagicMock(return_value=False)
        interaction.command = MagicMock()
        interaction.command.name = "test_command"
        
        # Create a mock error
        error = Exception("Test error")
        
        # Call the on_app_command_error method
        await bot.on_app_command_error(interaction, error)
        
        # Check that the response was sent
        interaction.response.send_message.assert_called_once()
        assert "error" in interaction.response.send_message.call_args[0][0]


@pytest.mark.asyncio
async def test_bot_on_app_command_error_response_done():
    """Test the on_app_command_error method when the response is already done."""
    with patch("discord_bot.bot.ticket_bot.config", create=True) as mock_config:
        # Configure the mock
        mock_config.token = "test_token"
        mock_config.command_prefix = "!"
        
        # Create the bot
        bot = TicketBot()
        
        # Create a mock interaction
        interaction = MagicMock()
        interaction.response.is_done = MagicMock(return_value=True)
        interaction.followup.send = AsyncMock()
        interaction.command = MagicMock()
        interaction.command.name = "test_command"
        
        # Create a mock error
        error = Exception("Test error")
        
        # Call the on_app_command_error method
        await bot.on_app_command_error(interaction, error)
        
        # Check that the followup was sent
        interaction.followup.send.assert_called_once()
        assert "error" in interaction.followup.send.call_args[0][0]