"""
Unit tests for the close command implementation.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

import interactions

from app.commands.implementations.close import CloseCommand
from app.commands.errors import CommandValidationError
from app.models.ticket import Ticket
from app.status import TicketStatus


class TestCloseCommand:
    """Test cases for CloseCommand."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.command = CloseCommand()
        
        # Mock context
        self.mock_ctx = Mock(spec=interactions.SlashContext)
        self.mock_ctx.channel = Mock()
        self.mock_ctx.channel.id = "123456789"
        self.mock_ctx.guild = Mock()
        self.mock_ctx.guild.id = "987654321"
        self.mock_ctx.author = Mock(spec=interactions.Member)
        self.mock_ctx.author.id = "555666777"
        self.mock_ctx.author.mention = "<@555666777>"
        self.mock_ctx.author.username = "testuser"
        self.mock_ctx.author.discriminator = "1234"
        self.mock_ctx.send = AsyncMock()
        self.mock_ctx.edit = AsyncMock()
        self.mock_ctx.bot = Mock()
        self.mock_ctx.bot.wait_for_component = AsyncMock()
        
        # Mock ticket
        self.mock_ticket = Mock(spec=Ticket)
        self.mock_ticket.id = 123
        self.mock_ticket.creator_id = 555666777
        self.mock_ticket.status = TicketStatus.OPEN.value
        self.mock_ticket.created_at = datetime.utcnow()
        self.mock_ticket.assigned_to = None
    
    def test_command_initialization(self):
        """Test command is properly initialized."""
        assert self.command.name == "close"
        assert self.command.description == "Close the current support ticket"
        assert len(self.command.options) == 1
        assert str(self.command.options[0].name) == "reason"
        assert not self.command.options[0].required
    
    def test_validate_arguments_valid_reason(self):
        """Test validation with valid reason."""
        # Should not raise exception
        self.command.validate_arguments(reason="Valid reason")
    
    def test_validate_arguments_empty_reason(self):
        """Test validation with empty reason (should be valid)."""
        # Should not raise exception
        self.command.validate_arguments(reason="")
    
    def test_validate_arguments_short_reason(self):
        """Test validation with too short reason."""
        with pytest.raises(CommandValidationError) as exc_info:
            self.command.validate_arguments(reason="Hi")
        
        assert "reason" in str(exc_info.value)
        assert "at least 3 characters" in str(exc_info.value)
    
    def test_validate_arguments_long_reason(self):
        """Test validation with too long reason."""
        long_reason = "x" * 201
        with pytest.raises(CommandValidationError) as exc_info:
            self.command.validate_arguments(reason=long_reason)
        
        assert "reason" in str(exc_info.value)
        assert "no more than 200 characters" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_execute_not_in_guild(self):
        """Test command execution when not in a guild."""
        self.mock_ctx.guild = None
        
        await self.command._execute(self.mock_ctx)
        
        self.mock_ctx.send.assert_called_once()
        args = self.mock_ctx.send.call_args[1]
        assert "can only be used in a server" in args.get('content', '')
        assert args.get('ephemeral') is True
    
    @pytest.mark.asyncio
    async def test_execute_author_not_member(self):
        """Test command execution when author is not a Member."""
        self.mock_ctx.author = Mock(spec=interactions.User)  # Not a Member
        
        await self.command._execute(self.mock_ctx)
        
        self.mock_ctx.send.assert_called_once()
        args = self.mock_ctx.send.call_args[1]
        assert "can only be used by server members" in args.get('content', '')
        assert args.get('ephemeral') is True
    
    @pytest.mark.asyncio
    @patch('app.commands.implementations.close.get_db_session')
    @patch('app.commands.implementations.close.get_ticket_by_channel_id')
    async def test_execute_not_ticket_channel(self, mock_get_ticket, mock_get_db):
        """Test command execution when not in a ticket channel."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        mock_get_ticket.return_value = None
        
        await self.command._execute(self.mock_ctx)
        
        self.mock_ctx.send.assert_called_once()
        args = self.mock_ctx.send.call_args[1]
        assert "can only be used in a ticket channel" in args.get('content', '')
        assert args.get('ephemeral') is True
        
        mock_db.close.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.commands.implementations.close.get_db_session')
    @patch('app.commands.implementations.close.get_ticket_by_channel_id')
    async def test_execute_already_closed_ticket(self, mock_get_ticket, mock_get_db):
        """Test command execution on already closed ticket."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        self.mock_ticket.status = TicketStatus.CLOSED.value
        mock_get_ticket.return_value = self.mock_ticket
        
        await self.command._execute(self.mock_ctx)
        
        self.mock_ctx.send.assert_called_once()
        args = self.mock_ctx.send.call_args[1]
        assert "already closed" in args.get('content', '')
        assert args.get('ephemeral') is True
        
        mock_db.close.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.commands.implementations.close.get_db_session')
    @patch('app.commands.implementations.close.get_ticket_by_channel_id')
    async def test_execute_no_permission(self, mock_get_ticket, mock_get_db):
        """Test command execution without permission to close."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        mock_get_ticket.return_value = self.mock_ticket
        
        # Make the user not the creator and not staff
        self.mock_ticket.creator_id = 999999999  # Different user
        
        with patch.object(self.command, '_check_close_permissions', return_value=False):
            await self.command._execute(self.mock_ctx)
        
        self.mock_ctx.send.assert_called_once()
        args = self.mock_ctx.send.call_args[1]
        assert "don't have permission" in args.get('content', '')
        assert args.get('ephemeral') is True
        
        mock_db.close.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.commands.implementations.close.get_db_session')
    @patch('app.commands.implementations.close.get_ticket_by_channel_id')
    async def test_execute_success_with_confirmation(self, mock_get_ticket, mock_get_db):
        """Test successful command execution with confirmation."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        mock_get_ticket.return_value = self.mock_ticket
        
        # Mock the confirmation button press
        mock_button_ctx = Mock()
        mock_button_ctx.ctx = Mock()
        mock_button_ctx.ctx.custom_id = f"close_confirm_{self.mock_ticket.id}"
        mock_button_ctx.ctx.channel = self.mock_ctx.channel
        mock_button_ctx.ctx.guild = self.mock_ctx.guild
        mock_button_ctx.ctx.author = self.mock_ctx.author
        mock_button_ctx.ctx.send = AsyncMock()
        
        self.mock_ctx.bot.wait_for_component.return_value = mock_button_ctx
        
        with patch.object(self.command, '_check_close_permissions', return_value=True), \
             patch.object(self.command, '_create_confirmation_embed', return_value=Mock()), \
             patch.object(self.command, '_handle_close_confirmation', new_callable=AsyncMock) as mock_handle:
            
            await self.command._execute(self.mock_ctx, reason="Test reason")
        
        # Verify confirmation embed was sent
        self.mock_ctx.send.assert_called_once()
        args = self.mock_ctx.send.call_args[1]
        assert 'embeds' in args
        assert 'components' in args
        assert args.get('ephemeral') is True
        
        # Verify handle close confirmation was called
        mock_handle.assert_called_once()
        
        mock_db.close.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.commands.implementations.close.get_db_session')
    @patch('app.commands.implementations.close.get_ticket_by_channel_id')
    async def test_execute_cancel_confirmation(self, mock_get_ticket, mock_get_db):
        """Test command execution with cancelled confirmation."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        mock_get_ticket.return_value = self.mock_ticket
        
        # Mock the cancel button press
        mock_button_ctx = Mock()
        mock_button_ctx.ctx = Mock()
        mock_button_ctx.ctx.custom_id = f"close_cancel_{self.mock_ticket.id}"
        mock_button_ctx.ctx.send = AsyncMock()
        
        self.mock_ctx.bot.wait_for_component.return_value = mock_button_ctx
        
        with patch.object(self.command, '_check_close_permissions', return_value=True), \
             patch.object(self.command, '_create_confirmation_embed', return_value=Mock()):
            
            await self.command._execute(self.mock_ctx)
        
        # Verify cancellation message was sent
        mock_button_ctx.ctx.send.assert_called_once()
        args = mock_button_ctx.ctx.send.call_args[1]
        assert "cancelled" in args.get('content', '')
        assert args.get('ephemeral') is True
        
        mock_db.close.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.commands.implementations.close.get_db_session')
    @patch('app.commands.implementations.close.get_ticket_by_channel_id')
    async def test_execute_confirmation_timeout(self, mock_get_ticket, mock_get_db):
        """Test command execution with confirmation timeout."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        mock_get_ticket.return_value = self.mock_ticket
        
        # Mock timeout
        self.mock_ctx.bot.wait_for_component.side_effect = asyncio.TimeoutError()
        
        with patch.object(self.command, '_check_close_permissions', return_value=True), \
             patch.object(self.command, '_create_confirmation_embed', return_value=Mock()):
            
            await self.command._execute(self.mock_ctx)
        
        # Verify timeout message was sent
        self.mock_ctx.edit.assert_called_once()
        args = self.mock_ctx.edit.call_args[1]
        assert 'embeds' in args
        assert 'components' in args
        
        mock_db.close.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.commands.implementations.close.get_user_role_in_guild')
    async def test_check_close_permissions_creator(self, mock_get_role):
        """Test permission check for ticket creator."""
        mock_db = Mock()
        
        result = await self.command._check_close_permissions(
            mock_db, self.mock_ticket.creator_id, 123, self.mock_ticket
        )
        
        assert result is True
        # Should not need to check role for creator
        mock_get_role.assert_not_called()
    
    @pytest.mark.asyncio
    @patch('app.commands.implementations.close.get_user_by_discord_id')
    @patch('app.commands.implementations.close.get_user_role_in_guild')
    async def test_check_close_permissions_staff(self, mock_get_role, mock_get_user):
        """Test permission check for staff member."""
        mock_db = Mock()
        
        # Mock user with UUID
        mock_user = Mock()
        mock_user.id = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
        mock_get_user.return_value = mock_user
        
        # Mock role return value as string
        mock_get_role.return_value = 'STAFF'
        
        # Different user (not creator)
        user_id = 999999999
        
        result = await self.command._check_close_permissions(
            mock_db, user_id, 123, self.mock_ticket
        )
        
        assert result is True
        mock_get_user.assert_called_once_with(mock_db, user_id)
    
    @pytest.mark.asyncio
    @patch('app.commands.implementations.close.get_user_role_in_guild')
    async def test_check_close_permissions_assigned_staff(self, mock_get_role):
        """Test permission check for assigned staff member."""
        mock_db = Mock()
        
        # Set assigned user
        user_id = 999999999
        self.mock_ticket.assigned_to = user_id
        
        result = await self.command._check_close_permissions(
            mock_db, user_id, 123, self.mock_ticket
        )
        
        assert result is True
        # Should not need to check role for assigned staff
        mock_get_role.assert_not_called()
    
    @pytest.mark.asyncio
    @patch('app.commands.implementations.close.get_user_by_discord_id')
    @patch('app.commands.implementations.close.get_user_role_in_guild')
    async def test_check_close_permissions_no_permission(self, mock_get_role, mock_get_user):
        """Test permission check for user without permission."""
        mock_db = Mock()
        
        # Mock user with UUID
        mock_user = Mock()
        mock_user.id = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
        mock_get_user.return_value = mock_user
        
        # Mock role return value as string
        mock_get_role.return_value = 'USER'  # Regular user
        
        # Different user (not creator, not assigned)
        user_id = 999999999
        
        result = await self.command._check_close_permissions(
            mock_db, user_id, 123, self.mock_ticket
        )
        
        assert result is False
        mock_get_user.assert_called_once_with(mock_db, user_id)
    
    def test_create_confirmation_embed(self):
        """Test creation of confirmation embed."""
        embed = asyncio.run(self.command._create_confirmation_embed(
            self.mock_ticket, self.mock_ctx.author, "Test reason"
        ))
        
        assert isinstance(embed, interactions.Embed)
        assert embed.title and "Confirm Ticket Closure" in embed.title
        assert embed.description and str(self.mock_ticket.id) in embed.description
    
    @pytest.mark.asyncio
    @patch('app.commands.implementations.close.get_db_session')
    @patch('app.commands.implementations.close.update_ticket')
    async def test_handle_close_confirmation_success(self, mock_update_ticket, mock_get_db):
        """Test successful close confirmation handling."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        # Mock updated ticket
        updated_ticket = Mock()
        updated_ticket.id = self.mock_ticket.id
        updated_ticket.status = TicketStatus.CLOSED.value
        updated_ticket.closed_at = datetime.utcnow()
        mock_update_ticket.return_value = updated_ticket
        
        # Mock button context
        mock_button_ctx = Mock()
        mock_button_ctx.send = AsyncMock()
        mock_button_ctx.author = Mock(spec=interactions.Member)  # Make it a Member
        mock_button_ctx.channel = self.mock_ctx.channel
        mock_button_ctx.guild = self.mock_ctx.guild
        
        with patch.object(self.command, '_send_closure_notification', new_callable=AsyncMock) as mock_notify, \
             patch.object(self.command, '_update_channel_permissions_readonly', new_callable=AsyncMock) as mock_perms, \
             patch.object(self.command, '_update_channel_name_closed', new_callable=AsyncMock) as mock_name, \
             patch.object(self.command, '_schedule_channel_deletion', new_callable=AsyncMock) as mock_delete:
            
            await self.command._handle_close_confirmation(
                mock_button_ctx, self.mock_ticket, 555666777, "Test reason"
            )
        
        # Verify ticket was updated
        mock_update_ticket.assert_called_once()
        args = mock_update_ticket.call_args[1]
        assert args['ticket_id'] == self.mock_ticket.id
        assert args['status'] == TicketStatus.CLOSED.value
        assert args['close_reason'] == "Test reason"
        
        # Verify success message
        mock_button_ctx.send.assert_called_once()
        call_args, call_kwargs = mock_button_ctx.send.call_args
        # Check if message is in positional args or kwargs
        if call_args:
            assert "Ticket closed successfully" in call_args[0]
        else:
            success_args = call_kwargs
            assert "Ticket closed successfully" in success_args.get('content', '')
        
        # Verify all cleanup methods were called
        mock_notify.assert_called_once()
        mock_perms.assert_called_once()
        mock_name.assert_called_once()
        
        mock_db.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_closure_notification(self):
        """Test sending closure notification."""
        mock_channel = Mock()
        mock_channel.send = AsyncMock()
        
        updated_ticket = Mock()
        updated_ticket.id = 123
        updated_ticket.status = TicketStatus.CLOSED.value
        updated_ticket.closed_at = datetime.utcnow()
        
        await self.command._send_closure_notification(
            mock_channel, updated_ticket, self.mock_ctx.author, "Test reason"
        )
        
        mock_channel.send.assert_called_once()
        args = mock_channel.send.call_args[1]
        assert 'embeds' in args
        
        embed = args['embeds'][0]
        assert "Ticket Closed" in embed.title
    
    @pytest.mark.asyncio
    async def test_update_channel_permissions_readonly(self):
        """Test updating channel permissions to read-only."""
        mock_channel = Mock()
        mock_channel.edit_permission = AsyncMock()
        
        mock_guild = Mock()
        mock_guild.default_role = Mock()
        
        await self.command._update_channel_permissions_readonly(mock_channel, mock_guild)
        
        mock_channel.edit_permission.assert_called_once()
        # Check the call arguments - first positional arg should be the role, then keyword args
        call_args, call_kwargs = mock_channel.edit_permission.call_args
        assert call_args[0] == mock_guild.default_role
        assert 'deny' in call_kwargs
    
    @pytest.mark.asyncio
    async def test_update_channel_name_closed(self):
        """Test updating channel name with closed prefix."""
        mock_channel = Mock()
        mock_channel.name = "ticket-123"
        mock_channel.edit = AsyncMock()
        
        await self.command._update_channel_name_closed(mock_channel)
        
        mock_channel.edit.assert_called_once()
        args = mock_channel.edit.call_args[1]
        assert args['name'] == "closed-ticket-123"
    
    @pytest.mark.asyncio
    async def test_update_channel_name_already_closed(self):
        """Test updating channel name when already has closed prefix."""
        mock_channel = Mock()
        mock_channel.name = "closed-ticket-123"
        mock_channel.edit = AsyncMock()
        
        await self.command._update_channel_name_closed(mock_channel)
        
        # Should not edit if already has closed prefix
        mock_channel.edit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_schedule_channel_deletion(self):
        """Test scheduling channel deletion."""
        mock_channel = Mock()
        mock_channel.delete = AsyncMock()
        
        # Mock sleep to avoid actual delay in tests
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            # Use 1 hour (integer) instead of 0.001 hours (float)
            await self.command._schedule_channel_deletion(mock_channel, delay_hours=1)
        
        mock_sleep.assert_called_once_with(3600)  # 1 hour * 3600 seconds
        mock_channel.delete.assert_called_once()
        call_kwargs = mock_channel.delete.call_args[1]
        assert "Automatic deletion" in call_kwargs['reason']
