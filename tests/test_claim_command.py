"""
Unit tests for the claim command implementation.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

import interactions
import httpx

from app.commands.implementations.claim import ClaimCommand
from app.commands.errors import CommandValidationError, CommandError
from app.models.ticket import Ticket
from app.models.user import User
from app.status import TicketStatus


class TestClaimCommand:
    """Test cases for ClaimCommand."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.command = ClaimCommand()
        
        # Mock context
        self.mock_ctx = Mock(spec=interactions.SlashContext)
        self.mock_ctx.channel = Mock()
        self.mock_ctx.channel.id = "123456789"
        self.mock_ctx.channel.edit = AsyncMock()
        self.mock_ctx.channel.send = AsyncMock()
        self.mock_ctx.guild = Mock()
        self.mock_ctx.guild.id = "987654321"
        self.mock_ctx.guild.name = "Test Guild"
        self.mock_ctx.guild.fetch_member = AsyncMock()
        self.mock_ctx.author = Mock(spec=interactions.Member)
        self.mock_ctx.author.id = "555666777"
        self.mock_ctx.author.mention = "<@555666777>"
        self.mock_ctx.send = AsyncMock()
        self.mock_ctx.defer = AsyncMock()
        self.mock_ctx.edit_original_response = AsyncMock()
        
        # Mock ticket
        self.mock_ticket = Mock(spec=Ticket)
        self.mock_ticket.id = 123
        self.mock_ticket.creator_id = 111222333  # Different from staff member
        self.mock_ticket.assigned_to = None  # Unassigned initially
        self.mock_ticket.status = TicketStatus.OPEN.value
        self.mock_ticket.reason = "Test ticket reason"
        self.mock_ticket.created_at = datetime.utcnow()
        
        # Mock user
        self.mock_user = Mock(spec=User)
        self.mock_user.id = "mock-user-uuid"
        self.mock_user.discord_id = 555666777
        self.mock_user.role = "STAFF"
        self.mock_user.email = "staff@example.com"
    
    def test_command_initialization(self):
        """Test command is properly initialized."""
        assert self.command.name == "claim"
        assert self.command.description == "Claim the current support ticket"
        assert self.command.staff_only == True
        assert len(self.command.options) == 0  # No options for claim command
        assert self.command.cooldown_seconds == 5.0
        assert self.command.rate_limit_per_minute == 10
    
    def test_validate_arguments_no_args(self):
        """Test argument validation with no arguments."""
        # Should not raise exception - claim has no arguments
        self.command.validate_arguments()
    
    @pytest.mark.asyncio
    async def test_execute_not_in_guild(self):
        """Test execution when not in a guild."""
        self.mock_ctx.guild = None
        
        await self.command._execute(self.mock_ctx)
        
        self.mock_ctx.send.assert_called_once()
        call_args = self.mock_ctx.send.call_args[1]
        assert "❌ This command can only be used in a server." in call_args['content']
        assert call_args['ephemeral'] == True
    
    @pytest.mark.asyncio
    async def test_execute_author_not_member(self):
        """Test execution when author is not a guild member."""
        self.mock_ctx.author = Mock(spec=interactions.User)  # User instead of Member
        
        await self.command._execute(self.mock_ctx)
        
        self.mock_ctx.send.assert_called_once()
        call_args = self.mock_ctx.send.call_args[1]
        assert "❌ This command can only be used by server members." in call_args['content']
        assert call_args['ephemeral'] == True
    
    @pytest.mark.asyncio
    async def test_execute_not_ticket_channel(self):
        """Test execution when not in a ticket channel."""
        mock_db = Mock()
        
        with patch('app.commands.implementations.claim.get_db_session', return_value=mock_db):
            with patch('app.commands.implementations.claim.get_ticket_by_channel_id', return_value=None):
                await self.command._execute(self.mock_ctx)
                
                self.mock_ctx.send.assert_called_once()
                call_args = self.mock_ctx.send.call_args[1]
                assert "❌ This command can only be used in a ticket channel." in call_args['content']
                assert call_args['ephemeral'] == True
    
    @pytest.mark.asyncio
    async def test_execute_insufficient_permissions(self):
        """Test execution with insufficient permissions."""
        mock_db = Mock()
        
        with patch('app.commands.implementations.claim.get_db_session', return_value=mock_db):
            with patch('app.commands.implementations.claim.get_ticket_by_channel_id', return_value=self.mock_ticket):
                with patch('app.commands.implementations.claim.get_user_by_discord_id', return_value=self.mock_user):
                    with patch('app.commands.implementations.claim.get_user_role_in_guild', return_value="USER"):
                        await self.command._execute(self.mock_ctx)
                        
                        self.mock_ctx.send.assert_called_once()
                        call_args = self.mock_ctx.send.call_args[1]
                        assert "❌ Only staff members can claim tickets." in call_args['content']
                        assert call_args['ephemeral'] == True
    
    @pytest.mark.asyncio
    async def test_execute_ticket_already_assigned(self):
        """Test execution when ticket is already assigned."""
        mock_db = Mock()
        self.mock_ticket.assigned_to = 999888777  # Already assigned
        
        with patch('app.commands.implementations.claim.get_db_session', return_value=mock_db):
            with patch('app.commands.implementations.claim.get_ticket_by_channel_id', return_value=self.mock_ticket):
                with patch('app.commands.implementations.claim.get_user_by_discord_id', return_value=self.mock_user):
                    with patch('app.commands.implementations.claim.get_user_role_in_guild', return_value="STAFF"):
                        await self.command._execute(self.mock_ctx)
                        
                        self.mock_ctx.send.assert_called_once()
                        call_args = self.mock_ctx.send.call_args[1]
                        assert "❌ This ticket is already assigned to" in call_args['content']
                        assert call_args['ephemeral'] == True
    
    @pytest.mark.asyncio
    async def test_execute_cannot_claim_own_ticket(self):
        """Test execution when trying to claim own ticket."""
        mock_db = Mock()
        self.mock_ticket.creator_id = 555666777  # Same as author ID
        
        with patch('app.commands.implementations.claim.get_db_session', return_value=mock_db):
            with patch('app.commands.implementations.claim.get_ticket_by_channel_id', return_value=self.mock_ticket):
                with patch('app.commands.implementations.claim.get_user_by_discord_id', return_value=self.mock_user):
                    with patch('app.commands.implementations.claim.get_user_role_in_guild', return_value="STAFF"):
                        await self.command._execute(self.mock_ctx)
                        
                        self.mock_ctx.send.assert_called_once()
                        call_args = self.mock_ctx.send.call_args[1]
                        assert "❌ You cannot claim your own ticket." in call_args['content']
                        assert call_args['ephemeral'] == True
    
    @pytest.mark.asyncio
    async def test_execute_invalid_status(self):
        """Test execution when ticket status doesn't allow claiming."""
        mock_db = Mock()
        self.mock_ticket.status = TicketStatus.CLOSED.value
        
        with patch('app.commands.implementations.claim.get_db_session', return_value=mock_db):
            with patch('app.commands.implementations.claim.get_ticket_by_channel_id', return_value=self.mock_ticket):
                with patch('app.commands.implementations.claim.get_user_by_discord_id', return_value=self.mock_user):
                    with patch('app.commands.implementations.claim.get_user_role_in_guild', return_value="STAFF"):
                        await self.command._execute(self.mock_ctx)
                        
                        self.mock_ctx.send.assert_called_once()
                        call_args = self.mock_ctx.send.call_args[1]
                        assert "❌ Tickets with status 'closed' cannot be claimed." in call_args['content']
                        assert call_args['ephemeral'] == True
    
    @pytest.mark.asyncio
    async def test_execute_successful_claim(self):
        """Test successful ticket claim."""
        mock_db = Mock()
        
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "message": "Ticket claimed successfully",
            "ticket": {"id": 123, "assigned_to": 555666777}
        }
        
        with patch('app.commands.implementations.claim.get_db_session', return_value=mock_db):
            with patch('app.commands.implementations.claim.get_ticket_by_channel_id', return_value=self.mock_ticket):
                with patch('app.commands.implementations.claim.get_user_by_discord_id', return_value=self.mock_user):
                    with patch('app.commands.implementations.claim.get_user_role_in_guild', return_value="STAFF"):
                        with patch('app.auth.generate_token', return_value="mock-token"):
                            with patch('httpx.AsyncClient') as mock_client:
                                mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
                                
                                with patch.object(self.command, '_send_claim_confirmation') as mock_confirm:
                                    with patch.object(self.command, '_send_claim_notification_to_creator') as mock_notify:
                                        await self.command._execute(self.mock_ctx)
                                        
                                        # Check that defer was called
                                        self.mock_ctx.defer.assert_called_once_with(ephemeral=True)
                                        
                                        # Check that confirmation and notification were sent
                                        mock_confirm.assert_called_once()
                                        mock_notify.assert_called_once()
                                        
                                        # Check success response
                                        self.mock_ctx.edit_original_response.assert_called_once()
                                        call_args = self.mock_ctx.edit_original_response.call_args[1]
                                        assert "✅ Successfully claimed ticket #123." in call_args['content']
    
    @pytest.mark.asyncio
    async def test_execute_api_error_403(self):
        """Test execution when API returns 403 error."""
        mock_db = Mock()
        
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.json.return_value = {"detail": "Insufficient permissions"}
        
        with patch('app.commands.implementations.claim.get_db_session', return_value=mock_db):
            with patch('app.commands.implementations.claim.get_ticket_by_channel_id', return_value=self.mock_ticket):
                with patch('app.commands.implementations.claim.get_user_by_discord_id', return_value=self.mock_user):
                    with patch('app.commands.implementations.claim.get_user_role_in_guild', return_value="STAFF"):
                        with patch('app.auth.generate_token', return_value="mock-token"):
                            with patch('httpx.AsyncClient') as mock_client:
                                mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
                                
                                await self.command._execute(self.mock_ctx)
                                
                                # Check error response
                                self.mock_ctx.edit_original_response.assert_called_once()
                                call_args = self.mock_ctx.edit_original_response.call_args[1]
                                assert "❌ Insufficient permissions" in call_args['content']
    
    @pytest.mark.asyncio
    async def test_execute_api_error_409(self):
        """Test execution when API returns 409 conflict error."""
        mock_db = Mock()
        
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 409
        mock_response.json.return_value = {"detail": "Ticket is already assigned"}
        
        with patch('app.commands.implementations.claim.get_db_session', return_value=mock_db):
            with patch('app.commands.implementations.claim.get_ticket_by_channel_id', return_value=self.mock_ticket):
                with patch('app.commands.implementations.claim.get_user_by_discord_id', return_value=self.mock_user):
                    with patch('app.commands.implementations.claim.get_user_role_in_guild', return_value="STAFF"):
                        with patch('app.auth.generate_token', return_value="mock-token"):
                            with patch('httpx.AsyncClient') as mock_client:
                                mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
                                
                                await self.command._execute(self.mock_ctx)
                                
                                # Check error response
                                self.mock_ctx.edit_original_response.assert_called_once()
                                call_args = self.mock_ctx.edit_original_response.call_args[1]
                                assert "❌ Ticket is already assigned" in call_args['content']
    
    @pytest.mark.asyncio
    async def test_execute_api_connection_error(self):
        """Test execution when API connection fails."""
        mock_db = Mock()
        
        with patch('app.commands.implementations.claim.get_db_session', return_value=mock_db):
            with patch('app.commands.implementations.claim.get_ticket_by_channel_id', return_value=self.mock_ticket):
                with patch('app.commands.implementations.claim.get_user_by_discord_id', return_value=self.mock_user):
                    with patch('app.commands.implementations.claim.get_user_role_in_guild', return_value="STAFF"):
                        with patch('app.auth.generate_token', return_value="mock-token"):
                            with patch('httpx.AsyncClient') as mock_client:
                                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                                    side_effect=httpx.RequestError("Connection failed")
                                )
                                
                                await self.command._execute(self.mock_ctx)
                                
                                # Check error response
                                self.mock_ctx.edit_original_response.assert_called_once()
                                call_args = self.mock_ctx.edit_original_response.call_args[1]
                                assert "❌ Failed to claim ticket due to connection error" in call_args['content']
    
    @pytest.mark.asyncio
    async def test_send_claim_confirmation(self):
        """Test sending claim confirmation embed."""
        await self.command._send_claim_confirmation(self.mock_ctx, self.mock_ticket, self.mock_ctx.author)
        
        self.mock_ctx.channel.send.assert_called_once()
        # Check that an embed was sent
        call_args = self.mock_ctx.channel.send.call_args[1]
        assert 'embed' in call_args
    
    @pytest.mark.asyncio
    async def test_send_claim_confirmation_exception(self):
        """Test claim confirmation with exception."""
        self.mock_ctx.channel.send = AsyncMock(side_effect=Exception("Send failed"))
        
        # Should not raise exception, just log it
        await self.command._send_claim_confirmation(self.mock_ctx, self.mock_ticket, self.mock_ctx.author)
        
        self.mock_ctx.channel.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_claim_notification_to_creator_success(self):
        """Test sending claim notification to creator successfully."""
        mock_creator = Mock(spec=interactions.Member)
        mock_creator.id = 111222333
        mock_dm_channel = Mock()
        mock_dm_channel.send = AsyncMock()
        mock_creator.fetch_dm = AsyncMock(return_value=mock_dm_channel)
        
        self.mock_ctx.guild.fetch_member.return_value = mock_creator
        
        await self.command._send_claim_notification_to_creator(self.mock_ctx, self.mock_ticket, self.mock_ctx.author)
        
        self.mock_ctx.guild.fetch_member.assert_called_once_with(111222333)
        mock_creator.fetch_dm.assert_called_once_with(force=False)
        mock_dm_channel.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_claim_notification_to_creator_dm_failure(self):
        """Test sending claim notification when user has DMs disabled."""
        mock_creator = Mock(spec=interactions.Member)
        mock_creator.id = 111222333
        mock_creator.fetch_dm = AsyncMock(side_effect=Exception("DM disabled"))
        
        self.mock_ctx.guild.fetch_member.return_value = mock_creator
        
        # Should not raise exception, just log it
        await self.command._send_claim_notification_to_creator(self.mock_ctx, self.mock_ticket, self.mock_ctx.author)
        
        self.mock_ctx.guild.fetch_member.assert_called_once_with(111222333)
    
    @pytest.mark.asyncio
    async def test_send_claim_notification_creator_not_found(self):
        """Test sending claim notification when creator is not found."""
        self.mock_ctx.guild.fetch_member = AsyncMock(side_effect=Exception("Member not found"))
        
        # Should not raise exception, just log it
        await self.command._send_claim_notification_to_creator(self.mock_ctx, self.mock_ticket, self.mock_ctx.author)
        
        self.mock_ctx.guild.fetch_member.assert_called_once_with(111222333)
    
    @pytest.mark.asyncio
    async def test_execute_exception_handling(self):
        """Test exception handling during execution."""
        mock_db = Mock()
        
        with patch('app.commands.implementations.claim.get_db_session', return_value=mock_db):
            with patch('app.commands.implementations.claim.get_ticket_by_channel_id', side_effect=Exception("DB Error")):
                # Exception should be raised but database should still be closed
                try:
                    await self.command._execute(self.mock_ctx)
                    # If we get here, the exception was handled
                    assert False, "Expected exception to be raised"
                except Exception as e:
                    # Exception was re-raised, which is expected since it's not caught
                    assert str(e) == "DB Error"
                    
                # Database session should be closed even on exception
                mock_db.close.assert_called_once()
