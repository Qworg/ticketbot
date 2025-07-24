"""Tests for the ticket manager."""

import os
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

import discord

# Add the parent directory to sys.path to allow imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from discord_bot.bot.ticket_bot import TicketBot
from discord_bot.bot.ticket_manager import TicketManager


@pytest.fixture
def mock_bot():
    """Create a mock bot for testing."""
    bot = MagicMock()
    bot.get_channel = MagicMock(return_value=MagicMock())
    return bot


@pytest.mark.asyncio
async def test_ticket_manager_initialization():
    """Test that the ticket manager initializes correctly."""
    # Create a mock bot
    bot = MagicMock()
    
    # Create the ticket manager
    manager = TicketManager(bot)
    
    # Check that the manager was initialized correctly
    assert manager.bot == bot
    assert manager.active_tickets == {}


@pytest.mark.asyncio
async def test_get_ticket_category():
    """Test getting the ticket category."""
    # Create a mock bot
    bot = MagicMock()
    
    # Create a mock category channel
    category = MagicMock()
    bot.get_channel.return_value = category
    
    # Create the ticket manager with a mock ticket category ID
    manager = TicketManager(bot)
    manager.ticket_category_id = 123456789
    
    # Get the category
    result = await manager.get_ticket_category()
    
    # Check that the bot's get_channel method was called correctly
    bot.get_channel.assert_called_once_with(123456789)
    
    # Check that the result is the mock category
    assert result == category


@pytest.mark.asyncio
async def test_get_staff_role():
    """Test getting the staff role."""
    # Create a mock bot
    bot = MagicMock()
    
    # Create a mock guild
    guild = MagicMock()
    
    # Create a mock role
    role = MagicMock()
    guild.get_role.return_value = role
    
    # Create the ticket manager with a mock staff role ID
    manager = TicketManager(bot)
    manager.staff_role_id = 123456789
    
    # Get the staff role
    result = await manager.get_staff_role(guild)
    
    # Check that the guild's get_role method was called correctly
    guild.get_role.assert_called_once_with(123456789)
    
    # Check that the result is the mock role
    assert result == role


@pytest.mark.asyncio
async def test_get_ticket_by_channel():
    """Test getting a ticket by channel ID."""
    # Create a mock bot
    bot = MagicMock()
    
    # Create the ticket manager
    manager = TicketManager(bot)
    
    # Add a mock ticket to the active tickets
    mock_ticket = {"id": "test-id", "title": "Test Ticket"}
    manager.active_tickets[123456789] = mock_ticket
    
    # Get the ticket
    result = await manager.get_ticket_by_channel(123456789)
    
    # Check that the result is the mock ticket
    assert result == mock_ticket


@pytest.mark.asyncio
async def test_get_ticket_by_channel_not_found():
    """Test getting a ticket by channel ID when not found."""
    # Create a mock bot
    bot = MagicMock()
    
    # Create the ticket manager
    manager = TicketManager(bot)
    
    # Mock the API client
    manager.api_client = AsyncMock()
    manager.api_client.connected = True
    manager.api_client.get.return_value = {"items": []}
    
    # Get a non-existent ticket
    result = await manager.get_ticket_by_channel(123456789)
    
    # Check that the API client's get method was called correctly
    manager.api_client.get.assert_called_once_with(
        "/api/tickets", 
        params={"discord_channel_id": 123456789}
    )
    
    # Check that the result is None
    assert result is None


@pytest.mark.asyncio
async def test_get_ticket_by_channel_from_api():
    """Test getting a ticket by channel ID from the API."""
    # Create a mock bot
    bot = MagicMock()
    
    # Create the ticket manager
    manager = TicketManager(bot)
    
    # Mock the API client
    mock_ticket = {"id": "test-id", "title": "Test Ticket"}
    manager.api_client = AsyncMock()
    manager.api_client.connected = True
    manager.api_client.get.return_value = {"items": [mock_ticket]}
    
    # Get the ticket
    result = await manager.get_ticket_by_channel(123456789)
    
    # Check that the API client's get method was called correctly
    manager.api_client.get.assert_called_once_with(
        "/api/tickets", 
        params={"discord_channel_id": 123456789}
    )
    
    # Check that the result is the mock ticket
    assert result == mock_ticket
    
    # Check that the ticket was added to the active tickets
    assert manager.active_tickets[123456789] == mock_ticket