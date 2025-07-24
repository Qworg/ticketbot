"""Tests for the message processor."""

import os
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

import discord
from typing import Dict, Any

# Add the parent directory to sys.path to allow imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock the http_client module before importing MessageProcessor
sys.modules['discord_bot.utils.http_client'] = MagicMock()
sys.modules['discord_bot.utils.http_client'].get_api_client = AsyncMock()

from bot.message_processor import MessageProcessor


@pytest.fixture
def mock_bot():
    """Create a mock bot for testing."""
    bot = MagicMock()
    return bot


@pytest.fixture
def mock_api_client():
    """Create a mock API client for testing."""
    client = AsyncMock()
    client.connected = True
    client.post = AsyncMock(return_value={"id": "message-123"})
    return client


@pytest.mark.asyncio
async def test_message_processor_initialization():
    """Test that the message processor initializes correctly."""
    # Create a mock bot
    bot = MagicMock()
    
    # Create the message processor
    processor = MessageProcessor(bot)
    
    # Check that the processor was initialized correctly
    assert processor.bot == bot
    assert processor.api_client is None


@pytest.mark.asyncio
async def test_process_message(mock_bot, mock_api_client):
    """Test processing a message."""
    # Create the message processor
    processor = MessageProcessor(mock_bot)
    processor.api_client = mock_api_client
    
    # Create a mock message
    message = MagicMock()
    message.author = MagicMock()
    message.author.bot = False
    message.type = discord.MessageType.default
    message.content = "Hello, this is a test message"
    message.id = 123456789
    message.author.id = 987654321
    message.attachments = []
    
    # Process the message
    result = await processor.process_message(message, "ticket-123")
    
    # Check that the API client was called correctly
    mock_api_client.post.assert_called_once()
    call_args = mock_api_client.post.call_args[0]
    assert call_args[0] == "/api/tickets/ticket-123/messages"
    
    # Check the message data
    message_data = mock_api_client.post.call_args[1]["data"]
    assert message_data["ticket_id"] == "ticket-123"
    assert message_data["discord_message_id"] == 123456789
    assert message_data["author_discord_id"] == 987654321
    assert message_data["content"] == "Hello, this is a test message"
    assert message_data["message_type"] == "user_message"
    
    # Check the result
    assert result == {"id": "message-123"}


@pytest.mark.asyncio
async def test_process_bot_message(mock_bot):
    """Test processing a bot message."""
    # Create the message processor
    processor = MessageProcessor(mock_bot)
    
    # Create a mock message from a bot
    message = MagicMock()
    message.author = MagicMock()
    message.author.bot = True
    
    # Process the message
    result = await processor.process_message(message, "ticket-123")
    
    # Check that the message was skipped
    assert result is None


@pytest.mark.asyncio
async def test_process_system_message(mock_bot):
    """Test processing a system message."""
    # Create the message processor
    processor = MessageProcessor(mock_bot)
    
    # Create a mock system message
    message = MagicMock()
    message.author = MagicMock()
    message.author.bot = False
    message.type = discord.MessageType.pins_add
    
    # Process the message
    result = await processor.process_message(message, "ticket-123")
    
    # Check that the message was skipped
    assert result is None


@pytest.mark.asyncio
async def test_process_command_message(mock_bot):
    """Test processing a command message."""
    # Create the message processor
    processor = MessageProcessor(mock_bot)
    processor.bot.command_prefix = "!"
    
    # Create a mock command message
    message = MagicMock()
    message.author = MagicMock()
    message.author.bot = False
    message.type = discord.MessageType.default
    message.content = "!help"
    
    # Process the message
    result = await processor.process_message(message, "ticket-123")
    
    # Check that the message was skipped
    assert result is None


@pytest.mark.asyncio
async def test_process_message_with_attachments(mock_bot, mock_api_client):
    """Test processing a message with attachments."""
    # Create the message processor
    processor = MessageProcessor(mock_bot)
    processor.api_client = mock_api_client
    
    # Create a mock message with attachments
    message = MagicMock()
    message.author = MagicMock()
    message.author.bot = False
    message.type = discord.MessageType.default
    message.content = "Here's a file"
    message.id = 123456789
    message.author.id = 987654321
    
    # Create mock attachments
    attachment = MagicMock()
    attachment.url = "https://example.com/file.txt"
    attachment.filename = "file.txt"
    attachment.content_type = "text/plain"
    attachment.size = 1024
    message.attachments = [attachment]
    
    # Process the message
    result = await processor.process_message(message, "ticket-123")
    
    # Check the message data
    message_data = mock_api_client.post.call_args[1]["data"]
    assert "attachments" in message_data
    assert len(message_data["attachments"]) == 1
    assert message_data["attachments"][0]["url"] == "https://example.com/file.txt"
    assert message_data["attachments"][0]["filename"] == "file.txt"
    assert message_data["attachments"][0]["content_type"] == "text/plain"
    assert message_data["attachments"][0]["size"] == 1024


@pytest.mark.asyncio
async def test_process_message_api_error(mock_bot):
    """Test processing a message when the API client fails."""
    # Create the message processor
    processor = MessageProcessor(mock_bot)
    
    # Create a mock API client that raises an exception
    api_client = AsyncMock()
    api_client.connected = True
    api_client.post = AsyncMock(side_effect=Exception("API error"))
    processor.api_client = api_client
    
    # Create a mock message
    message = MagicMock()
    message.author = MagicMock()
    message.author.bot = False
    message.type = discord.MessageType.default
    message.content = "Hello, this is a test message"
    message.id = 123456789
    message.author.id = 987654321
    message.attachments = []
    
    # Process the message
    result = await processor.process_message(message, "ticket-123")
    
    # Check that the result is None due to the API error
    assert result is None


@pytest.mark.asyncio
async def test_format_message(mock_bot):
    """Test formatting a message."""
    # Create the message processor
    processor = MessageProcessor(mock_bot)
    
    # Create a mock guild and member
    guild = MagicMock()
    member = MagicMock()
    member.display_name = "TestUser"
    guild.get_member = MagicMock(return_value=member)
    mock_bot.guilds = [guild]
    
    # Create message data
    message_data = {
        "content": "Hello, this is a test message",
        "author_discord_id": 987654321
    }
    
    # Format the message
    formatted = await processor.format_message(message_data)
    
    # Check the formatted message
    assert formatted == "**TestUser:** Hello, this is a test message"
    
    # Check that the guild's get_member method was called correctly
    guild.get_member.assert_called_with(987654321)


@pytest.mark.asyncio
async def test_format_message_with_attachments(mock_bot):
    """Test formatting a message with attachments."""
    # Create the message processor
    processor = MessageProcessor(mock_bot)
    
    # Create a mock guild and member
    guild = MagicMock()
    member = MagicMock()
    member.display_name = "TestUser"
    guild.get_member = MagicMock(return_value=member)
    mock_bot.guilds = [guild]
    
    # Create message data with attachments
    message_data = {
        "content": "Here's a file",
        "author_discord_id": 987654321,
        "attachments": [
            {
                "url": "https://example.com/file.txt",
                "filename": "file.txt"
            }
        ]
    }
    
    # Format the message
    formatted = await processor.format_message(message_data)
    
    # Check the formatted message
    assert "**TestUser:** Here's a file" in formatted
    assert "**Attachments:**" in formatted
    assert "[file.txt](https://example.com/file.txt)" in formatted


@pytest.mark.asyncio
async def test_format_message_unknown_user(mock_bot):
    """Test formatting a message from an unknown user."""
    # Create the message processor
    processor = MessageProcessor(mock_bot)
    
    # Create a mock guild where the member is not found
    guild = MagicMock()
    guild.get_member = MagicMock(return_value=None)
    mock_bot.guilds = [guild]
    
    # Create message data
    message_data = {
        "content": "Hello, this is a test message",
        "author_discord_id": 987654321
    }
    
    # Format the message
    formatted = await processor.format_message(message_data)
    
    # Check the formatted message
    assert formatted == "**<@987654321>:** Hello, this is a test message"