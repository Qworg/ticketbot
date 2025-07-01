"""
Integration tests for the close command implementation.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

import interactions

from app.commands.implementations.close import CloseCommand
from app.models.ticket import Ticket
from app.models.user import User
from app.models.role_assignment import RoleAssignment
from app.status import TicketStatus
from app.database import get_db_session


@pytest.mark.integration
class TestCloseCommandIntegration:
    """Integration test cases for CloseCommand."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.command = CloseCommand()
    
    @pytest.mark.asyncio
    @patch('app.commands.implementations.close.get_db_session')
    @patch('app.commands.implementations.close.get_ticket_by_channel_id')
    @patch('app.commands.implementations.close.update_ticket')
    @patch('app.commands.implementations.close.get_user_role_in_guild')
    async def test_complete_close_flow_creator(
        self, 
        mock_get_role, 
        mock_update_ticket, 
        mock_get_ticket, 
        mock_get_db
    ):
        """Test complete close flow for ticket creator."""
        # Setup mocks
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        # Create mock ticket
        mock_ticket = Mock(spec=Ticket)
        mock_ticket.id = 123
        mock_ticket.creator_id = 555666777
        mock_ticket.status = TicketStatus.OPEN.value
        mock_ticket.created_at = datetime.utcnow()
        mock_ticket.assigned_to = None
        mock_get_ticket.return_value = mock_ticket
        
        # Create mock updated ticket
        updated_ticket = Mock()
        updated_ticket.id = 123
        updated_ticket.status = TicketStatus.CLOSED.value
        updated_ticket.closed_at = datetime.utcnow()
        mock_update_ticket.return_value = updated_ticket
        
        # Setup context
        mock_ctx = Mock(spec=interactions.SlashContext)
        mock_ctx.channel = Mock()
        mock_ctx.channel.id = "123456789"
        mock_ctx.channel.send = AsyncMock()
        mock_ctx.channel.edit_permission = AsyncMock()
        mock_ctx.channel.edit = AsyncMock()
        mock_ctx.channel.delete = AsyncMock()
        mock_ctx.channel.name = "ticket-123"
        mock_ctx.guild = Mock()
        mock_ctx.guild.id = "987654321"
        mock_ctx.guild.default_role = Mock()
        mock_ctx.author = Mock(spec=interactions.Member)
        mock_ctx.author.id = "555666777"  # Same as creator
        mock_ctx.author.mention = "<@555666777>"
        mock_ctx.author.username = "testuser"
        mock_ctx.author.discriminator = "1234"
        mock_ctx.send = AsyncMock()
        mock_ctx.edit = AsyncMock()
        mock_ctx.bot = Mock()
        
        # Mock button interaction
        mock_button_ctx = Mock()
        mock_button_ctx.ctx = Mock()
        mock_button_ctx.ctx.custom_id = f"close_confirm_{mock_ticket.id}"
        mock_button_ctx.ctx.channel = mock_ctx.channel
        mock_button_ctx.ctx.guild = mock_ctx.guild
        mock_button_ctx.ctx.author = mock_ctx.author
        mock_button_ctx.send = AsyncMock()
        
        mock_ctx.bot.wait_for_component = AsyncMock(return_value=mock_button_ctx)
        
        # Mock async sleep for deletion scheduling
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            # Execute command
            await self.command._execute(mock_ctx, reason="Integration test reason")
        
        # Verify database interactions
        mock_get_ticket.assert_called_once_with(mock_db, int(mock_ctx.channel.id))
        mock_update_ticket.assert_called_once()
        
        update_args = mock_update_ticket.call_args[1]
        assert update_args['ticket_id'] == mock_ticket.id
        assert update_args['user_id'] == int(mock_ctx.author.id)
        assert update_args['status'] == TicketStatus.CLOSED.value
        assert update_args['close_reason'] == "Integration test reason"
        
        # Verify confirmation was sent
        mock_ctx.send.assert_called_once()
        confirmation_args = mock_ctx.send.call_args[1]
        assert 'embeds' in confirmation_args
        assert 'components' in confirmation_args
        assert confirmation_args.get('ephemeral') is True
        
        # Verify success message
        mock_button_ctx.send.assert_called_once()
        success_args = mock_button_ctx.send.call_args[1]
        assert "closed successfully" in success_args.get('content', '')
        
        # Verify closure notification
        mock_ctx.channel.send.assert_called_once()
        notification_args = mock_ctx.channel.send.call_args[1]
        assert 'embeds' in notification_args
        
        # Verify channel permissions updated
        mock_ctx.channel.edit_permission.assert_called_once()
        
        # Verify channel name updated
        mock_ctx.channel.edit.assert_called_once()
        name_args = mock_ctx.channel.edit.call_args[1]
        assert name_args['name'] == "closed-ticket-123"
        
        # Verify database session closed
        mock_db.close.assert_called()
    
    @pytest.mark.asyncio
    @patch('app.commands.implementations.close.get_db_session')
    @patch('app.commands.implementations.close.get_ticket_by_channel_id')
    @patch('app.commands.implementations.close.get_user_role_in_guild')
    async def test_complete_close_flow_staff(
        self, 
        mock_get_role, 
        mock_get_ticket, 
        mock_get_db
    ):
        """Test complete close flow for staff member."""
        # Setup mocks
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        # Create mock ticket (different creator)
        mock_ticket = Mock(spec=Ticket)
        mock_ticket.id = 123
        mock_ticket.creator_id = 999999999  # Different user
        mock_ticket.status = TicketStatus.OPEN.value
        mock_ticket.created_at = datetime.utcnow()
        mock_ticket.assigned_to = None
        mock_get_ticket.return_value = mock_ticket
        
        # Mock staff role
        mock_role = Mock()
        mock_role.role = 'STAFF'
        mock_get_role.return_value = mock_role
        
        # Setup context (staff user)
        mock_ctx = Mock(spec=interactions.SlashContext)
        mock_ctx.channel = Mock()
        mock_ctx.channel.id = "123456789"
        mock_ctx.guild = Mock()
        mock_ctx.guild.id = "987654321"
        mock_ctx.author = Mock(spec=interactions.Member)
        mock_ctx.author.id = "555666777"  # Staff user
        mock_ctx.send = AsyncMock()
        
        # Execute permission check part of command
        result = await self.command._check_close_permissions(
            mock_db, int(mock_ctx.author.id), int(mock_ctx.guild.id), mock_ticket
        )
        
        # Verify staff has permission
        assert result is True
        mock_get_role.assert_called_once_with(
            mock_db, int(mock_ctx.author.id), int(mock_ctx.guild.id)
        )
        
        # Verify database session handling (called in actual command execution)
        mock_db.close.assert_not_called()  # Only called in full command execution
    
    @pytest.mark.asyncio
    @patch('app.commands.implementations.close.get_db_session')
    @patch('app.commands.implementations.close.get_ticket_by_channel_id')
    @patch('app.commands.implementations.close.get_user_role_in_guild')
    async def test_permission_denied_flow(
        self, 
        mock_get_role, 
        mock_get_ticket, 
        mock_get_db
    ):
        """Test flow when user doesn't have permission."""
        # Setup mocks
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        # Create mock ticket (different creator)
        mock_ticket = Mock(spec=Ticket)
        mock_ticket.id = 123
        mock_ticket.creator_id = 999999999  # Different user
        mock_ticket.status = TicketStatus.OPEN.value
        mock_ticket.assigned_to = None
        mock_get_ticket.return_value = mock_ticket
        
        # Mock regular user role
        mock_role = Mock()
        mock_role.role = 'USER'  # Not staff
        mock_get_role.return_value = mock_role
        
        # Setup context
        mock_ctx = Mock(spec=interactions.SlashContext)
        mock_ctx.channel = Mock()
        mock_ctx.channel.id = "123456789"
        mock_ctx.guild = Mock()
        mock_ctx.guild.id = "987654321"
        mock_ctx.author = Mock(spec=interactions.Member)
        mock_ctx.author.id = "555666777"  # Regular user
        mock_ctx.send = AsyncMock()
        
        # Execute command
        await self.command._execute(mock_ctx)
        
        # Verify permission denied message
        mock_ctx.send.assert_called_once()
        args = mock_ctx.send.call_args[1]
        assert "don't have permission" in args.get('content', '')
        assert args.get('ephemeral') is True
        
        # Verify database session closed
        mock_db.close.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.commands.implementations.close.get_db_session')
    @patch('app.commands.implementations.close.get_ticket_by_channel_id')
    async def test_channel_validation_flow(self, mock_get_ticket, mock_get_db):
        """Test flow when command is used outside ticket channel."""
        # Setup mocks
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        mock_get_ticket.return_value = None  # No ticket found
        
        # Setup context
        mock_ctx = Mock(spec=interactions.SlashContext)
        mock_ctx.channel = Mock()
        mock_ctx.channel.id = "123456789"
        mock_ctx.guild = Mock()
        mock_ctx.guild.id = "987654321"
        mock_ctx.author = Mock(spec=interactions.Member)
        mock_ctx.send = AsyncMock()
        
        # Execute command
        await self.command._execute(mock_ctx)
        
        # Verify channel validation message
        mock_ctx.send.assert_called_once()
        args = mock_ctx.send.call_args[1]
        assert "can only be used in a ticket channel" in args.get('content', '')
        assert args.get('ephemeral') is True
        
        # Verify database operations
        mock_get_ticket.assert_called_once_with(mock_db, int(mock_ctx.channel.id))
        mock_db.close.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.commands.implementations.close.get_db_session')
    @patch('app.commands.implementations.close.get_ticket_by_channel_id')
    async def test_already_closed_ticket_flow(self, mock_get_ticket, mock_get_db):
        """Test flow when ticket is already closed."""
        # Setup mocks
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        # Create mock closed ticket
        mock_ticket = Mock(spec=Ticket)
        mock_ticket.id = 123
        mock_ticket.status = TicketStatus.CLOSED.value
        mock_get_ticket.return_value = mock_ticket
        
        # Setup context
        mock_ctx = Mock(spec=interactions.SlashContext)
        mock_ctx.channel = Mock()
        mock_ctx.channel.id = "123456789"
        mock_ctx.guild = Mock()
        mock_ctx.guild.id = "987654321"
        mock_ctx.author = Mock(spec=interactions.Member)
        mock_ctx.send = AsyncMock()
        
        # Execute command
        await self.command._execute(mock_ctx)
        
        # Verify already closed message
        mock_ctx.send.assert_called_once()
        args = mock_ctx.send.call_args[1]
        assert "already closed" in args.get('content', '')
        assert args.get('ephemeral') is True
        
        # Verify database session closed
        mock_db.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_embed_creation_with_reason(self):
        """Test confirmation embed creation with reason."""
        # Create mock objects
        mock_ticket = Mock()
        mock_ticket.id = 123
        mock_ticket.status = TicketStatus.OPEN.value
        mock_ticket.created_at = datetime.utcnow()
        
        mock_author = Mock()
        mock_author.mention = "<@555666777>"
        mock_author.username = "testuser"
        mock_author.discriminator = "1234"
        
        # Create embed
        embed = await self.command._create_confirmation_embed(
            mock_ticket, mock_author, "Test close reason"
        )
        
        # Verify embed structure
        assert isinstance(embed, interactions.Embed)
        assert "Confirm Ticket Closure" in embed.title
        assert f"#{mock_ticket.id}" in embed.description
        assert embed.color == 0xFF9500
        
        # Verify fields
        field_names = [field.name for field in embed.fields]
        assert "📋 Ticket Details" in field_names
        assert "👤 Requested By" in field_names
        assert "📝 Close Reason" in field_names
        assert "⚠️ Warning" in field_names
        
        # Verify close reason field
        reason_field = next(field for field in embed.fields if "Close Reason" in field.name)
        assert "Test close reason" in reason_field.value
    
    @pytest.mark.asyncio
    async def test_embed_creation_without_reason(self):
        """Test confirmation embed creation without reason."""
        # Create mock objects
        mock_ticket = Mock()
        mock_ticket.id = 123
        mock_ticket.status = TicketStatus.OPEN.value
        mock_ticket.created_at = datetime.utcnow()
        
        mock_author = Mock()
        mock_author.mention = "<@555666777>"
        mock_author.username = "testuser"
        mock_author.discriminator = "1234"
        
        # Create embed without reason
        embed = await self.command._create_confirmation_embed(
            mock_ticket, mock_author, None
        )
        
        # Verify embed structure
        assert isinstance(embed, interactions.Embed)
        assert "Confirm Ticket Closure" in embed.title
        
        # Verify no close reason field when reason is None
        field_names = [field.name for field in embed.fields]
        assert "📝 Close Reason" not in field_names
        assert "📋 Ticket Details" in field_names
        assert "👤 Requested By" in field_names
        assert "⚠️ Warning" in field_names
    
    @pytest.mark.asyncio
    async def test_closure_notification_embed(self):
        """Test closure notification embed creation."""
        # Create mock objects
        mock_channel = Mock()
        mock_channel.send = AsyncMock()
        
        mock_ticket = Mock()
        mock_ticket.id = 123
        mock_ticket.status = TicketStatus.CLOSED.value
        mock_ticket.closed_at = datetime.utcnow()
        
        mock_closer = Mock()
        mock_closer.mention = "<@555666777>"
        
        # Send notification
        await self.command._send_closure_notification(
            mock_channel, mock_ticket, mock_closer, "Test reason"
        )
        
        # Verify notification was sent
        mock_channel.send.assert_called_once()
        args = mock_channel.send.call_args[1]
        assert 'embeds' in args
        
        embed = args['embeds'][0]
        assert "Ticket Closed" in embed.title
        assert mock_closer.mention in embed.description
        assert embed.color == 0xFF4444
        
        # Verify fields
        field_names = [field.name for field in embed.fields]
        assert "📋 Ticket Information" in field_names
        assert "📝 Close Reason" in field_names
        assert "📚 Archive Information" in field_names
