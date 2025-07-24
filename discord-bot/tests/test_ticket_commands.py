"""Tests for ticket commands."""

import os
import sys
import pytest
import discord
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# Import the module directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# Use the direct import path instead of the package path
from bot.cogs.ticket_commands import TicketCommands


class TestTicketCommands:
    """Test suite for ticket commands."""
    
    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot instance."""
        bot = MagicMock()
        bot.ticket_manager = MagicMock()
        bot.permission_manager = MagicMock()
        bot.message_processor = MagicMock()
        return bot
    
    @pytest.fixture
    def mock_interaction(self):
        """Create a mock interaction."""
        interaction = AsyncMock()
        interaction.response = AsyncMock()
        interaction.followup = AsyncMock()
        interaction.user = MagicMock()
        interaction.user.id = 123456789
        interaction.user.display_name = "TestUser"
        interaction.user.mention = "<@123456789>"
        interaction.guild = MagicMock()
        interaction.channel = MagicMock()
        interaction.channel_id = 987654321
        return interaction
    
    @pytest.fixture
    def mock_api_client(self):
        """Create a mock API client."""
        api_client = AsyncMock()
        api_client.connected = True
        api_client.post.return_value = {"id": "test-ticket-id"}
        api_client.put.return_value = {"status": "success"}
        return api_client
    
    @pytest.mark.asyncio
    @patch("utils.http_client.get_api_client")
    async def test_create_ticket(self, mock_get_api_client, mock_bot, mock_interaction, mock_api_client):
        """Test creating a ticket."""
        # Setup mocks
        mock_get_api_client.return_value = mock_api_client
        mock_bot.ticket_manager.get_ticket_category.return_value = AsyncMock()
        mock_interaction.guild.create_text_channel.return_value = AsyncMock()
        
        # Create command instance
        commands = TicketCommands(mock_bot)
        
        # Call the create ticket method
        await commands.create_ticket(mock_interaction, "Test Ticket")
        
        # Verify API call was made
        mock_api_client.post.assert_called_once()
        assert "title" in mock_api_client.post.call_args[1]["data"]
        assert mock_api_client.post.call_args[1]["data"]["title"] == "Test Ticket"
        
        # Verify channel was created
        mock_interaction.guild.create_text_channel.assert_called_once()
        
        # Verify permissions were set
        mock_bot.permission_manager.setup_ticket_permissions.assert_called_once()
        
        # Verify response was sent
        mock_interaction.followup.send.assert_called_once()
    
    @pytest.mark.asyncio
    @patch("utils.http_client.get_api_client")
    async def test_close_ticket(self, mock_get_api_client, mock_bot, mock_interaction, mock_api_client):
        """Test closing a ticket."""
        # Setup mocks
        mock_get_api_client.return_value = mock_api_client
        mock_bot.ticket_manager.get_ticket_by_channel.return_value = {
            "id": "test-ticket-id",
            "creator_discord_id": 123456789
        }
        mock_interaction.user.guild_permissions.manage_channels = True
        
        # Create command instance
        commands = TicketCommands(mock_bot)
        
        # Call the close ticket method
        await commands.close_ticket(mock_interaction)
        
        # Verify API call was made
        mock_api_client.put.assert_called_once()
        assert "status" in mock_api_client.put.call_args[1]["data"]
        assert mock_api_client.put.call_args[1]["data"]["status"] == "closed"
        
        # Verify permissions were updated
        mock_bot.permission_manager.update_ticket_permissions.assert_called_once()
        
        # Verify channel was archived
        mock_interaction.channel.edit.assert_called_once_with(archived=True)
        
        # Verify response was sent
        mock_interaction.followup.send.assert_called_once()
    
    @pytest.mark.asyncio
    @patch("utils.http_client.get_api_client")
    async def test_assign_ticket(self, mock_get_api_client, mock_bot, mock_interaction, mock_api_client):
        """Test assigning a ticket."""
        # Setup mocks
        mock_get_api_client.return_value = mock_api_client
        mock_bot.ticket_manager.get_ticket_by_channel.return_value = {
            "id": "test-ticket-id",
            "creator_discord_id": 123456789
        }
        mock_interaction.user.guild_permissions.manage_channels = True
        
        # Create mock user to assign
        mock_user = MagicMock()
        mock_user.id = 987654321
        mock_user.mention = "<@987654321>"
        
        # Setup staff role
        mock_staff_role = MagicMock()
        mock_bot.ticket_manager.get_staff_role.return_value = mock_staff_role
        mock_user.roles = [mock_staff_role]
        
        # Create command instance
        commands = TicketCommands(mock_bot)
        
        # Call the assign ticket method
        await commands.assign_ticket(mock_interaction, mock_user)
        
        # Verify API call was made
        mock_api_client.put.assert_called_once()
        assert "assigned_staff_id" in mock_api_client.put.call_args[1]["data"]
        assert mock_api_client.put.call_args[1]["data"]["assigned_staff_id"] == 987654321
        
        # Verify permissions were updated
        mock_bot.permission_manager.update_ticket_permissions.assert_called_once()
        
        # Verify response was sent
        mock_interaction.followup.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ticket_command_create(self, mock_bot, mock_interaction):
        """Test the ticket command with create action."""
        # Create command instance
        commands = TicketCommands(mock_bot)
        
        # Mock the create_ticket method
        commands.create_ticket = AsyncMock()
        
        # Call the ticket command
        await commands.ticket_command(mock_interaction, "create", "Test Subject")
        
        # Verify create_ticket was called
        commands.create_ticket.assert_called_once_with(mock_interaction, "Test Subject")
    
    @pytest.mark.asyncio
    async def test_ticket_command_close(self, mock_bot, mock_interaction):
        """Test the ticket command with close action."""
        # Create command instance
        commands = TicketCommands(mock_bot)
        
        # Mock the close_ticket method
        commands.close_ticket = AsyncMock()
        
        # Call the ticket command
        await commands.ticket_command(mock_interaction, "close")
        
        # Verify close_ticket was called
        commands.close_ticket.assert_called_once_with(mock_interaction)
    
    @pytest.mark.asyncio
    async def test_ticket_command_assign(self, mock_bot, mock_interaction):
        """Test the ticket command with assign action."""
        # Create command instance
        commands = TicketCommands(mock_bot)
        
        # Mock the assign_ticket method
        commands.assign_ticket = AsyncMock()
        
        # Create mock user to assign
        mock_user = MagicMock()
        
        # Call the ticket command
        await commands.ticket_command(mock_interaction, "assign", user=mock_user)
        
        # Verify assign_ticket was called
        commands.assign_ticket.assert_called_once_with(mock_interaction, mock_user)