"""
Unit tests for the add command implementation.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

import interactions

from app.commands.implementations.add import AddCommand
from app.commands.errors import CommandValidationError, CommandError
from app.models.ticket import Ticket
from app.models.ticket_participant import TicketParticipant
from app.status import TicketStatus


class TestAddCommand:
    """Test cases for AddCommand."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.command = AddCommand()
        
        # Mock context
        self.mock_ctx = Mock(spec=interactions.SlashContext)
        self.mock_ctx.channel = Mock()
        self.mock_ctx.channel.id = "123456789"
        self.mock_ctx.guild = Mock()
        self.mock_ctx.guild.id = "987654321"
        self.mock_ctx.guild.name = "Test Guild"
        self.mock_ctx.author = Mock(spec=interactions.Member)
        self.mock_ctx.author.id = "555666777"
        self.mock_ctx.author.mention = "<@555666777>"
        self.mock_ctx.send = AsyncMock()
        self.mock_ctx.defer = AsyncMock()
        self.mock_ctx.edit_original_response = AsyncMock()
        
        # Mock target user
        self.mock_target_user = Mock(spec=interactions.Member)
        self.mock_target_user.id = "888999000"
        self.mock_target_user.mention = "<@888999000>"
        self.mock_target_user.username = "targetuser"
        self.mock_target_user.fetch_dm = AsyncMock()
        
        # Mock ticket
        self.mock_ticket = Mock(spec=Ticket)
        self.mock_ticket.id = 123
        self.mock_ticket.creator_id = 111222333
        self.mock_ticket.status = TicketStatus.OPEN.value
        self.mock_ticket.reason = "Test ticket reason"
        self.mock_ticket.created_at = datetime.utcnow()
        
        # Mock participant
        self.mock_participant = Mock(spec=TicketParticipant)
        self.mock_participant.id = 1
        self.mock_participant.ticket_id = 123
        self.mock_participant.user_id = 888999000
        self.mock_participant.role = "participant"
    
    def test_command_initialization(self):
        """Test command is properly initialized."""
        assert self.command.name == "add"
        assert self.command.description == "Add a user to the current ticket"
        assert self.command.staff_only == True
        assert len(self.command.options) == 1
        assert str(self.command.options[0].name) == "user"
    
    def test_validate_arguments_valid_user(self):
        """Test argument validation with valid user."""
        # Should not raise exception
        self.command.validate_arguments(user=self.mock_target_user)
    
    def test_validate_arguments_missing_user(self):
        """Test argument validation with missing user."""
        with pytest.raises(CommandValidationError):
            self.command.validate_arguments(user=None)
    
    @pytest.mark.asyncio
    async def test_execute_missing_user_parameter(self):
        """Test execution with missing user parameter."""
        with patch('app.commands.implementations.add.get_db_session') as mock_db:
            await self.command._execute(self.mock_ctx, user=None)
            
            self.mock_ctx.send.assert_called_once()
            call_args = self.mock_ctx.send.call_args[1]
            assert "❌ Please specify a valid user to add." in call_args['content']
            assert call_args['ephemeral'] == True
    
    @pytest.mark.asyncio
    async def test_execute_not_in_guild(self):
        """Test execution when not in a guild."""
        self.mock_ctx.guild = None
        
        with patch('app.commands.implementations.add.get_db_session') as mock_db:
            await self.command._execute(self.mock_ctx, user=self.mock_target_user)
            
            self.mock_ctx.send.assert_called_once()
            call_args = self.mock_ctx.send.call_args[1]
            assert "❌ This command can only be used in a server." in call_args['content']
            assert call_args['ephemeral'] == True
    
    @pytest.mark.asyncio
    async def test_execute_author_not_member(self):
        """Test execution when author is not a member."""
        self.mock_ctx.author = Mock(spec=interactions.User)  # Not a Member
        
        with patch('app.commands.implementations.add.get_db_session') as mock_db:
            await self.command._execute(self.mock_ctx, user=self.mock_target_user)
            
            self.mock_ctx.send.assert_called_once()
            call_args = self.mock_ctx.send.call_args[1]
            assert "❌ This command can only be used by server members." in call_args['content']
            assert call_args['ephemeral'] == True
    
    @pytest.mark.asyncio
    async def test_execute_not_ticket_channel(self):
        """Test execution when not in a ticket channel."""
        mock_db = Mock()
        
        with patch('app.commands.implementations.add.get_db_session', return_value=mock_db):
            with patch('app.commands.implementations.add.get_ticket_by_channel_id', return_value=None):
                await self.command._execute(self.mock_ctx, user=self.mock_target_user)
                
                self.mock_ctx.send.assert_called_once()
                call_args = self.mock_ctx.send.call_args[1]
                assert "❌ This command can only be used in a ticket channel." in call_args['content']
                assert call_args['ephemeral'] == True
    
    @pytest.mark.asyncio
    async def test_execute_insufficient_permissions(self):
        """Test execution with insufficient permissions."""
        mock_db = Mock()
        
        with patch('app.commands.implementations.add.get_db_session', return_value=mock_db):
            with patch('app.commands.implementations.add.get_ticket_by_channel_id', return_value=self.mock_ticket):
                with patch('app.commands.implementations.add.get_user_role_in_guild', return_value='USER'):
                    await self.command._execute(self.mock_ctx, user=self.mock_target_user)
                    
                    self.mock_ctx.send.assert_called_once()
                    call_args = self.mock_ctx.send.call_args[1]
                    assert "❌ Only staff members can add users to tickets." in call_args['content']
                    assert call_args['ephemeral'] == True
    
    @pytest.mark.asyncio
    async def test_execute_user_already_participant(self):
        """Test execution when user is already a participant."""
        mock_db = Mock()
        
        with patch('app.commands.implementations.add.get_db_session', return_value=mock_db):
            with patch('app.commands.implementations.add.get_ticket_by_channel_id', return_value=self.mock_ticket):
                with patch('app.commands.implementations.add.get_user_role_in_guild', return_value='STAFF'):
                    with patch('app.commands.implementations.add.is_participant_in_ticket', return_value=True):
                        await self.command._execute(self.mock_ctx, user=self.mock_target_user)
                        
                        self.mock_ctx.send.assert_called_once()
                        call_args = self.mock_ctx.send.call_args[1]
                        assert f"❌ {self.mock_target_user.mention} is already a participant" in call_args['content']
                        assert call_args['ephemeral'] == True
    
    @pytest.mark.asyncio
    async def test_execute_successful_add(self):
        """Test successful user addition to ticket."""
        mock_db = Mock()
        mock_dm_channel = Mock()
        mock_dm_channel.send = AsyncMock()
        self.mock_target_user.fetch_dm.return_value = mock_dm_channel
        
        with patch('app.commands.implementations.add.get_db_session', return_value=mock_db):
            with patch('app.commands.implementations.add.get_ticket_by_channel_id', return_value=self.mock_ticket):
                with patch('app.commands.implementations.add.get_user_role_in_guild', return_value='STAFF'):
                    with patch('app.commands.implementations.add.is_participant_in_ticket', return_value=False):
                        with patch('app.commands.implementations.add.add_participant_to_ticket', return_value=self.mock_participant):
                            # Mock the channel permission editing
                            self.mock_ctx.channel.edit_permission = AsyncMock()
                            # Mock channel sending
                            self.mock_ctx.channel.send = AsyncMock()
                            
                            await self.command._execute(self.mock_ctx, user=self.mock_target_user)
                            
                            # Verify defer was called
                            self.mock_ctx.defer.assert_called_once_with(ephemeral=True)
                            
                            # Verify success message
                            self.mock_ctx.edit_original_response.assert_called_once()
                            call_args = self.mock_ctx.edit_original_response.call_args[1]
                            assert "✅ Successfully added" in call_args['content']
                            assert self.mock_target_user.mention in call_args['content']
    
    @pytest.mark.asyncio
    async def test_execute_add_participant_error(self):
        """Test execution when add_participant_to_ticket raises ValueError."""
        mock_db = Mock()
        
        with patch('app.commands.implementations.add.get_db_session', return_value=mock_db):
            with patch('app.commands.implementations.add.get_ticket_by_channel_id', return_value=self.mock_ticket):
                with patch('app.commands.implementations.add.get_user_role_in_guild', return_value='STAFF'):
                    with patch('app.commands.implementations.add.is_participant_in_ticket', return_value=False):
                        with patch('app.commands.implementations.add.add_participant_to_ticket', side_effect=ValueError("Test error")):
                            await self.command._execute(self.mock_ctx, user=self.mock_target_user)
                            
                            # Verify defer was called
                            self.mock_ctx.defer.assert_called_once_with(ephemeral=True)
                            
                            # Verify error message
                            self.mock_ctx.edit_original_response.assert_called_once()
                            call_args = self.mock_ctx.edit_original_response.call_args[1]
                            assert "❌ Error adding user: Test error" in call_args['content']
    
    @pytest.mark.asyncio
    async def test_add_channel_permissions_success(self):
        """Test successful channel permission addition."""
        mock_channel = Mock()
        mock_channel.edit_permission = AsyncMock()
        
        await self.command._add_channel_permissions(mock_channel, self.mock_target_user)
        
        mock_channel.edit_permission.assert_called_once()
        call_args = mock_channel.edit_permission.call_args
        assert call_args[1]['target'] == self.mock_target_user
        assert call_args[1]['reason'] == "Added to ticket by staff"
    
    @pytest.mark.asyncio
    async def test_add_channel_permissions_failure(self):
        """Test channel permission addition failure."""
        mock_channel = Mock()
        mock_channel.edit_permission = AsyncMock(side_effect=Exception("Permission error"))
        
        with pytest.raises(CommandError):
            await self.command._add_channel_permissions(mock_channel, self.mock_target_user)
    
    @pytest.mark.asyncio
    async def test_send_participant_added_notification(self):
        """Test sending participant added notification."""
        mock_channel = Mock()
        mock_channel.send = AsyncMock()
        
        await self.command._send_participant_added_notification(
            mock_channel,
            self.mock_target_user,
            self.mock_ctx.author,
            self.mock_ticket
        )
        
        mock_channel.send.assert_called_once()
        # Verify embed was sent
        call_args = mock_channel.send.call_args[1]
        assert 'embed' in call_args
    
    @pytest.mark.asyncio
    async def test_send_dm_to_added_user_success(self):
        """Test sending DM to added user successfully."""
        mock_dm_channel = Mock()
        mock_dm_channel.send = AsyncMock()
        self.mock_target_user.fetch_dm.return_value = mock_dm_channel
        
        await self.command._send_dm_to_added_user(
            self.mock_target_user,
            self.mock_ticket,
            self.mock_ctx.guild
        )
        
        self.mock_target_user.fetch_dm.assert_called_once()
        mock_dm_channel.send.assert_called_once()
        # Verify embed was sent
        call_args = mock_dm_channel.send.call_args[1]
        assert 'embed' in call_args
    
    @pytest.mark.asyncio
    async def test_send_dm_to_added_user_dm_disabled(self):
        """Test sending DM when user has DMs disabled."""
        self.mock_target_user.fetch_dm.side_effect = Exception("DMs disabled")
        
        # Should not raise exception, just log warning
        await self.command._send_dm_to_added_user(
            self.mock_target_user,
            self.mock_ticket,
            self.mock_ctx.guild
        )
        
        self.mock_target_user.fetch_dm.assert_called_once()
