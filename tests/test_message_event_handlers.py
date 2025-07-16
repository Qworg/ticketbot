"""
Unit tests for Discord message event handlers.
"""

import asyncio
import os
import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from datetime import datetime

from app.bot import TicketBot
from app.models.ticket import Ticket
from app.models.message import Message


class TestMessageEventHandlers:
    """Test cases for message event handlers."""
    
    @patch.dict(os.environ, {'DISCORD_TOKEN': 'test_token_123'})
    def setup_method(self, method):
        """Set up test bot instance."""
        self.bot = TicketBot()
    
    def test_message_rate_limit_check(self):
        """Test message rate limiting functionality."""
        channel_id = 123456789
        
        # Should allow first message
        assert self.bot._check_message_rate_limit(channel_id) == True
        
        # Fill up the rate limit
        for i in range(self.bot._message_rate_limit_per_minute - 1):
            assert self.bot._check_message_rate_limit(channel_id) == True
        
        # Should reject when rate limit exceeded
        assert self.bot._check_message_rate_limit(channel_id) == False
    
    @patch('app.bot.get_db_session')
    @patch('app.bot.get_ticket_by_channel')
    @patch('app.bot.save_discord_message')
    @patch('app.bot.is_user_staff')
    @patch('app.bot.extract_attachment_metadata')
    @pytest.mark.asyncio
    async def test_handle_message_create_success(self, mock_extract_attach, mock_is_staff, 
                                                mock_save_msg, mock_get_ticket, mock_db_session):
        """Test successful message creation handling."""
        # Set up mocks
        mock_db = Mock()
        mock_db_session.return_value = mock_db
        
        mock_ticket = Mock()
        mock_ticket.id = 1
        mock_get_ticket.return_value = mock_ticket
        
        mock_is_staff.return_value = False
        mock_extract_attach.return_value = []
        
        mock_message = Mock()
        mock_message.id = 987654321
        mock_message.author.bot = False
        mock_message.author.id = 123456789
        mock_message.content = "Test message"
        mock_message.channel.id = 111111111
        mock_message.guild.id = 222222222
        mock_message.attachments = []
        mock_message.created_at = datetime.utcnow()
        mock_message.guild.fetch_member = AsyncMock(return_value=Mock(roles=[]))
        
        mock_save_msg.return_value = Mock()
        
        # Create event mock
        event = Mock()
        event.message = mock_message
        
        # Test the handler
        await self.bot._handle_message_create(event)
        
        # Verify calls
        mock_get_ticket.assert_called_once_with(mock_db, 111111111)
        mock_save_msg.assert_called_once()
        mock_db.close.assert_called_once()
    
    @patch('app.bot.get_db_session')
    @patch('app.bot.get_ticket_by_channel')
    @pytest.mark.asyncio
    async def test_handle_message_create_not_ticket_channel(self, mock_get_ticket, mock_db_session):
        """Test message creation handling when not in ticket channel."""
        # Set up mocks
        mock_db = Mock()
        mock_db_session.return_value = mock_db
        mock_get_ticket.return_value = None  # Not a ticket channel
        
        mock_message = Mock()
        mock_message.author.bot = False
        mock_message.channel.id = 111111111
        
        event = Mock()
        event.message = mock_message
        
        # Test the handler
        await self.bot._handle_message_create(event)
        
        # Verify it exits early
        mock_get_ticket.assert_called_once_with(mock_db, 111111111)
        mock_db.close.assert_called_once()
    
    @patch('app.bot.get_db_session')
    @pytest.mark.asyncio
    async def test_handle_message_create_bot_message(self, mock_db_session):
        """Test message creation handling for bot messages."""
        mock_message = Mock()
        mock_message.author.bot = True  # Bot message
        
        event = Mock()
        event.message = mock_message
        
        # Test the handler
        await self.bot._handle_message_create(event)
        
        # Verify it exits early and doesn't touch database
        mock_db_session.assert_not_called()
    
    @patch('app.bot.get_db_session')
    @patch('app.bot.get_ticket_by_channel')
    @patch('app.bot.update_message_content')
    @pytest.mark.asyncio
    async def test_handle_message_update_success(self, mock_update_msg, mock_get_ticket, mock_db_session):
        """Test successful message update handling."""
        # Set up mocks
        mock_db = Mock()
        mock_db_session.return_value = mock_db
        
        mock_ticket = Mock()
        mock_ticket.id = 1
        mock_get_ticket.return_value = mock_ticket
        
        mock_message = Mock()
        mock_message.id = 987654321
        mock_message.author.bot = False
        mock_message.content = "Updated message"
        mock_message.channel.id = 111111111
        mock_message.edited_timestamp = datetime.utcnow()
        
        mock_update_msg.return_value = True
        
        # Create event mock
        event = Mock()
        event.after = mock_message
        
        # Test the handler
        await self.bot._handle_message_update(event)
        
        # Verify calls
        mock_get_ticket.assert_called_once_with(mock_db, 111111111)
        mock_update_msg.assert_called_once()
        mock_db.close.assert_called_once()
    
    @patch('app.bot.get_db_session')
    @patch('app.bot.get_ticket_by_channel')
    @patch('app.bot.soft_delete_message')
    @pytest.mark.asyncio
    async def test_handle_message_delete_success(self, mock_soft_delete, mock_get_ticket, mock_db_session):
        """Test successful message deletion handling."""
        # Set up mocks
        mock_db = Mock()
        mock_db_session.return_value = mock_db
        
        mock_ticket = Mock()
        mock_ticket.id = 1
        mock_get_ticket.return_value = mock_ticket
        
        mock_message = Mock()
        mock_message.id = 987654321
        mock_message.author.bot = False
        mock_message.channel.id = 111111111
        
        mock_soft_delete.return_value = True
        
        # Create event mock
        event = Mock()
        event.message = mock_message
        
        # Test the handler
        await self.bot._handle_message_delete(event)
        
        # Verify calls
        mock_get_ticket.assert_called_once_with(mock_db, 111111111)
        mock_soft_delete.assert_called_once_with(db=mock_db, message_id=987654321)
        mock_db.close.assert_called_once()
    
    @patch('app.bot.get_db_session')
    @patch('app.bot.get_ticket_by_channel')
    @patch('app.bot.save_discord_message')
    @patch('app.bot.is_user_staff')
    @patch('app.bot.extract_attachment_metadata')
    @pytest.mark.asyncio
    async def test_handle_message_create_with_attachments(self, mock_extract_attach, mock_is_staff,
                                                         mock_save_msg, mock_get_ticket, mock_db_session):
        """Test message creation handling with attachments."""
        # Set up mocks
        mock_db = Mock()
        mock_db_session.return_value = mock_db
        
        mock_ticket = Mock()
        mock_ticket.id = 1
        mock_get_ticket.return_value = mock_ticket
        
        mock_is_staff.return_value = True  # Staff message
        
        # Mock attachments
        mock_attachment = Mock()
        mock_attachment.filename = "test.jpg"
        mock_attachment.size = 1024
        mock_attachment.content_type = "image/jpeg"
        mock_attachment.url = "https://example.com/test.jpg"
        
        mock_extract_attach.return_value = [{
            "filename": "test.jpg",
            "size": 1024,
            "content_type": "image/jpeg",
            "url": "https://example.com/test.jpg"
        }]
        
        mock_message = Mock()
        mock_message.id = 987654321
        mock_message.author.bot = False
        mock_message.author.id = 123456789
        mock_message.content = "Message with attachment"
        mock_message.channel.id = 111111111
        mock_message.guild.id = 222222222
        mock_message.attachments = [mock_attachment]
        mock_message.created_at = datetime.utcnow()
        mock_message.guild.fetch_member = AsyncMock(return_value=Mock(roles=[Mock(id=333333333)]))
        
        mock_save_msg.return_value = Mock()
        
        # Create event mock
        event = Mock()
        event.message = mock_message
        
        # Test the handler
        await self.bot._handle_message_create(event)
        
        # Verify calls
        mock_extract_attach.assert_called_once_with([mock_attachment])
        mock_is_staff.assert_called_once()
        mock_save_msg.assert_called_once()
        
        # Verify save was called with staff-only flag
        save_call_args = mock_save_msg.call_args
        assert save_call_args[1]['is_staff_only'] == True
        assert save_call_args[1]['attachments'] == [{
            "filename": "test.jpg",
            "size": 1024,
            "content_type": "image/jpeg",
            "url": "https://example.com/test.jpg"
        }]
    
    @patch('app.bot.get_db_session')
    @patch('app.bot.get_ticket_by_channel')
    @pytest.mark.asyncio
    async def test_handle_message_create_rate_limit_exceeded(self, mock_get_ticket, mock_db_session):
        """Test message creation handling when rate limit is exceeded."""
        # Fill up the rate limit
        channel_id = 111111111
        for i in range(self.bot._message_rate_limit_per_minute):
            self.bot._check_message_rate_limit(channel_id)
        
        mock_message = Mock()
        mock_message.author.bot = False
        mock_message.channel.id = channel_id
        
        event = Mock()
        event.message = mock_message
        
        # Test the handler
        await self.bot._handle_message_create(event)
        
        # Verify it exits early due to rate limit
        mock_get_ticket.assert_not_called()
        mock_db_session.assert_not_called()
    
    @patch('app.bot.get_db_session')
    @patch('app.bot.get_ticket_by_channel')
    @patch('app.bot.save_discord_message')
    @patch('app.bot.is_user_staff')
    @patch('app.bot.extract_attachment_metadata')
    @pytest.mark.asyncio
    async def test_handle_message_create_database_error(self, mock_extract_attach, mock_is_staff,
                                                       mock_save_msg, mock_get_ticket, mock_db_session):
        """Test message creation handling with database error."""
        # Set up mocks
        mock_db = Mock()
        mock_db_session.return_value = mock_db
        
        mock_ticket = Mock()
        mock_ticket.id = 1
        mock_get_ticket.return_value = mock_ticket
        
        mock_is_staff.return_value = False
        mock_extract_attach.return_value = []
        
        mock_message = Mock()
        mock_message.id = 987654321
        mock_message.author.bot = False
        mock_message.author.id = 123456789
        mock_message.content = "Test message"
        mock_message.channel.id = 111111111
        mock_message.guild.id = 222222222
        mock_message.attachments = []
        mock_message.created_at = datetime.utcnow()
        mock_message.guild.fetch_member = AsyncMock(return_value=Mock(roles=[]))
        
        # Mock database error
        mock_save_msg.side_effect = Exception("Database error")
        
        # Create event mock
        event = Mock()
        event.message = mock_message
        
        # Test the handler - should not raise exception
        await self.bot._handle_message_create(event)
        
        # Verify database rollback was called
        mock_db.rollback.assert_called_once()
        mock_db.close.assert_called_once()
