"""
Integration tests for the remove command implementation.
"""

import pytest
import asyncio
import uuid
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

import interactions

from app.commands.implementations.remove import RemoveCommand
from app.models.ticket import Ticket
from app.models.user import User
from app.models.role_assignment import RoleAssignment
from app.models.ticket_participant import TicketParticipant
from app.status import TicketStatus
from app.database import get_db_session


@pytest.mark.integration
class TestRemoveCommandIntegration:
    """Integration test cases for RemoveCommand."""

    def setup_method(self):
        """Set up test fixtures."""
        self.command = RemoveCommand()

    @pytest.mark.asyncio
    @patch("app.commands.implementations.remove.get_db_session")
    @patch("app.commands.implementations.remove.get_ticket_by_channel_id")
    @patch("app.commands.implementations.remove.remove_participant_from_ticket")
    @patch("app.commands.implementations.remove.is_participant_in_ticket")
    @patch("app.commands.implementations.remove.get_user_role_in_guild")
    async def test_complete_remove_flow_staff(
        self,
        mock_get_role,
        mock_is_participant,
        mock_remove_participant,
        mock_get_ticket,
        mock_get_db,
    ):
        """Test complete remove flow for staff member removing participant."""
        # Setup mocks
        mock_db = Mock()
        mock_get_db.return_value = mock_db

        # Create mock ticket
        mock_ticket = Mock(spec=Ticket)
        mock_ticket.id = 123
        mock_ticket.creator_id = 111222333  # Different from staff and target
        mock_ticket.status = TicketStatus.OPEN.value
        mock_ticket.reason = "Test ticket"
        mock_ticket.created_at = datetime.utcnow()
        mock_get_ticket.return_value = mock_ticket

        # Mock staff role
        mock_get_role.return_value = "STAFF"

        # Mock participant exists
        mock_is_participant.return_value = True

        # Mock successful removal
        mock_remove_participant.return_value = True

        # Create mock context
        mock_ctx = Mock(spec=interactions.SlashContext)
        mock_ctx.channel = Mock()
        mock_ctx.channel.id = "123456789"
        mock_ctx.channel.edit_permission = AsyncMock()
        mock_ctx.channel.send = AsyncMock()
        mock_ctx.guild = Mock()
        mock_ctx.guild.id = "987654321"
        mock_ctx.guild.name = "Test Guild"
        mock_ctx.author = Mock(spec=interactions.Member)
        mock_ctx.author.id = "555666777"
        mock_ctx.author.mention = "<@555666777>"
        mock_ctx.defer = AsyncMock()
        mock_ctx.edit_original_response = AsyncMock()

        # Create mock target user
        mock_target_user = Mock(spec=interactions.Member)
        mock_target_user.id = "888999000"
        mock_target_user.mention = "<@888999000>"
        mock_target_user.fetch_dm = AsyncMock()

        # Mock DM channel
        mock_dm_channel = Mock()
        mock_dm_channel.send = AsyncMock()
        mock_target_user.fetch_dm.return_value = mock_dm_channel

        # Execute command
        await self.command._execute(mock_ctx, user=mock_target_user)

        # Verify database calls
        mock_get_db.assert_called_once()
        mock_get_ticket.assert_called_once_with(mock_db, 123456789)
        mock_get_role.assert_called_once_with(mock_db, 555666777, 987654321)
        mock_is_participant.assert_called_once_with(mock_db, 123, 888999000)
        mock_remove_participant.assert_called_once_with(mock_db, 123, 888999000)

        # Verify UI interactions
        mock_ctx.defer.assert_called_once_with(ephemeral=True)
        mock_ctx.edit_original_response.assert_called_once()

        # Verify channel permission removal
        mock_ctx.channel.edit_permission.assert_called_once_with(
            target=mock_target_user,
            allow=None,
            deny=None,
            reason="Removed from ticket by staff",
        )

        # Verify channel notification
        mock_ctx.channel.send.assert_called_once()

        # Verify DM sent
        mock_target_user.fetch_dm.assert_called_once()
        mock_dm_channel.send.assert_called_once()

        # Verify success response
        response_call = mock_ctx.edit_original_response.call_args[1]
        assert "✅ Successfully removed" in response_call["content"]
        assert mock_target_user.mention in response_call["content"]

    @pytest.mark.asyncio
    @patch("app.commands.implementations.remove.get_db_session")
    @patch("app.commands.implementations.remove.get_ticket_by_channel_id")
    @patch("app.commands.implementations.remove.is_participant_in_ticket")
    @patch("app.commands.implementations.remove.get_user_role_in_guild")
    async def test_complete_remove_flow_admin(
        self, mock_get_role, mock_is_participant, mock_get_ticket, mock_get_db
    ):
        """Test complete remove flow for admin removing participant."""
        # Setup mocks
        mock_db = Mock()
        mock_get_db.return_value = mock_db

        # Create mock ticket
        mock_ticket = Mock(spec=Ticket)
        mock_ticket.id = 123
        mock_ticket.creator_id = 111222333
        mock_ticket.status = TicketStatus.IN_PROGRESS.value
        mock_get_ticket.return_value = mock_ticket

        # Mock admin role
        mock_get_role.return_value = "ADMIN"

        # Mock participant exists
        mock_is_participant.return_value = True

        # Create mock context
        mock_ctx = Mock(spec=interactions.SlashContext)
        mock_ctx.channel = Mock()
        mock_ctx.channel.id = "123456789"
        mock_ctx.guild = Mock()
        mock_ctx.guild.id = "987654321"
        mock_ctx.author = Mock(spec=interactions.Member)
        mock_ctx.author.id = "444555666"  # Admin user
        mock_ctx.defer = AsyncMock()
        mock_ctx.edit_original_response = AsyncMock()

        # Create mock target user
        mock_target_user = Mock(spec=interactions.Member)
        mock_target_user.id = "888999000"

        with patch(
            "app.commands.implementations.remove.remove_participant_from_ticket",
            return_value=True,
        ):
            with patch.object(
                self.command, "_remove_channel_permissions"
            ) as mock_remove_perms:
                with patch.object(
                    self.command, "_send_participant_removed_notification"
                ) as mock_notify:
                    with patch.object(
                        self.command, "_send_dm_to_removed_user"
                    ) as mock_dm:
                        # Execute command
                        await self.command._execute(mock_ctx, user=mock_target_user)

                        # Verify admin can remove participants
                        mock_get_role.assert_called_once_with(
                            mock_db, 444555666, 987654321
                        )
                        mock_is_participant.assert_called_once_with(
                            mock_db, 123, 888999000
                        )

                        # Verify removal functions called
                        mock_remove_perms.assert_called_once()
                        mock_notify.assert_called_once()
                        mock_dm.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.commands.implementations.remove.get_db_session")
    @patch("app.commands.implementations.remove.get_ticket_by_channel_id")
    @patch("app.commands.implementations.remove.get_user_role_in_guild")
    async def test_integration_permission_denied_user(
        self, mock_get_role, mock_get_ticket, mock_get_db
    ):
        """Test integration with permission system - regular user denied."""
        # Setup mocks
        mock_db = Mock()
        mock_get_db.return_value = mock_db

        # Create mock ticket
        mock_ticket = Mock(spec=Ticket)
        mock_ticket.id = 123
        mock_get_ticket.return_value = mock_ticket

        # Mock regular user role
        mock_get_role.return_value = "USER"

        # Create mock context
        mock_ctx = Mock(spec=interactions.SlashContext)
        mock_ctx.channel = Mock()
        mock_ctx.channel.id = "123456789"
        mock_ctx.guild = Mock()
        mock_ctx.guild.id = "987654321"
        mock_ctx.author = Mock(spec=interactions.Member)
        mock_ctx.author.id = "777888999"
        mock_ctx.send = AsyncMock()

        # Create mock target user
        mock_target_user = Mock(spec=interactions.Member)
        mock_target_user.id = "888999000"

        # Execute command
        await self.command._execute(mock_ctx, user=mock_target_user)

        # Verify permission check
        mock_get_role.assert_called_once_with(mock_db, 777888999, 987654321)

        # Verify permission denied
        mock_ctx.send.assert_called_once()
        call_args = mock_ctx.send.call_args[1]
        assert (
            "❌ Only staff members can remove users from tickets."
            in call_args["content"]
        )
        assert call_args["ephemeral"] == True

    @pytest.mark.asyncio
    @patch("app.commands.implementations.remove.get_db_session")
    @patch("app.commands.implementations.remove.get_ticket_by_channel_id")
    @patch("app.commands.implementations.remove.is_participant_in_ticket")
    @patch("app.commands.implementations.remove.get_user_role_in_guild")
    async def test_integration_cannot_remove_creator(
        self, mock_get_role, mock_is_participant, mock_get_ticket, mock_get_db
    ):
        """Test integration preventing removal of ticket creator."""
        # Setup mocks
        mock_db = Mock()
        mock_get_db.return_value = mock_db

        # Create mock ticket where target user is the creator
        mock_ticket = Mock(spec=Ticket)
        mock_ticket.id = 123
        mock_ticket.creator_id = 888999000  # Same as target user
        mock_get_ticket.return_value = mock_ticket

        # Mock staff role
        mock_get_role.return_value = "STAFF"

        # Mock participant exists
        mock_is_participant.return_value = True

        # Create mock context
        mock_ctx = Mock(spec=interactions.SlashContext)
        mock_ctx.channel = Mock()
        mock_ctx.channel.id = "123456789"
        mock_ctx.guild = Mock()
        mock_ctx.guild.id = "987654321"
        mock_ctx.author = Mock(spec=interactions.Member)
        mock_ctx.author.id = "555666777"
        mock_ctx.send = AsyncMock()

        # Create mock target user (who is the creator)
        mock_target_user = Mock(spec=interactions.Member)
        mock_target_user.id = "888999000"
        mock_target_user.mention = "<@888999000>"

        # Execute command
        await self.command._execute(mock_ctx, user=mock_target_user)

        # Verify creator removal prevented
        mock_ctx.send.assert_called_once()
        call_args = mock_ctx.send.call_args[1]
        assert "❌ Cannot remove the ticket creator" in call_args["content"]
        assert call_args["ephemeral"] == True

    @pytest.mark.asyncio
    @patch("app.commands.implementations.remove.get_db_session")
    @patch("app.commands.implementations.remove.get_ticket_by_channel_id")
    @patch("app.commands.implementations.remove.is_participant_in_ticket")
    @patch("app.commands.implementations.remove.remove_participant_from_ticket")
    @patch("app.commands.implementations.remove.get_user_role_in_guild")
    async def test_integration_database_error_handling(
        self,
        mock_get_role,
        mock_remove_participant,
        mock_is_participant,
        mock_get_ticket,
        mock_get_db,
    ):
        """Test integration with database error handling."""
        # Setup mocks
        mock_db = Mock()
        mock_get_db.return_value = mock_db

        # Create mock ticket
        mock_ticket = Mock(spec=Ticket)
        mock_ticket.id = 123
        mock_ticket.creator_id = 111222333
        mock_get_ticket.return_value = mock_ticket

        # Mock staff role
        mock_get_role.return_value = "STAFF"

        # Mock participant exists
        mock_is_participant.return_value = True

        # Mock database error
        mock_remove_participant.side_effect = Exception("Database connection failed")

        # Create mock context
        mock_ctx = Mock(spec=interactions.SlashContext)
        mock_ctx.channel = Mock()
        mock_ctx.channel.id = "123456789"
        mock_ctx.guild = Mock()
        mock_ctx.guild.id = "987654321"
        mock_ctx.author = Mock(spec=interactions.Member)
        mock_ctx.author.id = "555666777"
        mock_ctx.defer = AsyncMock()
        mock_ctx.edit_original_response = AsyncMock()

        # Create mock target user
        mock_target_user = Mock(spec=interactions.Member)
        mock_target_user.id = "888999000"

        # Execute command
        await self.command._execute(mock_ctx, user=mock_target_user)

        # Verify error handling
        mock_ctx.defer.assert_called_once_with(ephemeral=True)
        mock_ctx.edit_original_response.assert_called_once()

        # Verify error message
        call_args = mock_ctx.edit_original_response.call_args[1]
        assert "❌ An error occurred while removing the user" in call_args["content"]

    @pytest.mark.asyncio
    @patch("app.commands.implementations.remove.get_db_session")
    @patch("app.commands.implementations.remove.get_ticket_by_channel_id")
    @patch("app.commands.implementations.remove.is_participant_in_ticket")
    @patch("app.commands.implementations.remove.remove_participant_from_ticket")
    @patch("app.commands.implementations.remove.get_user_role_in_guild")
    async def test_integration_discord_permission_failure(
        self,
        mock_get_role,
        mock_remove_participant,
        mock_is_participant,
        mock_get_ticket,
        mock_get_db,
    ):
        """Test integration when Discord permission removal fails."""
        # Setup mocks
        mock_db = Mock()
        mock_get_db.return_value = mock_db

        # Create mock ticket
        mock_ticket = Mock(spec=Ticket)
        mock_ticket.id = 123
        mock_ticket.creator_id = 111222333
        mock_ticket.reason = "Test"
        mock_ticket.created_at = datetime.utcnow()
        mock_get_ticket.return_value = mock_ticket

        # Mock staff role
        mock_get_role.return_value = "STAFF"

        # Mock participant exists
        mock_is_participant.return_value = True

        # Mock successful database removal
        mock_remove_participant.return_value = True

        # Create mock context with failing channel permissions
        mock_ctx = Mock(spec=interactions.SlashContext)
        mock_ctx.channel = Mock()
        mock_ctx.channel.id = "123456789"
        mock_ctx.channel.edit_permission = AsyncMock(
            side_effect=Exception("Permission denied")
        )
        mock_ctx.channel.send = AsyncMock()
        mock_ctx.guild = Mock()
        mock_ctx.guild.id = "987654321"
        mock_ctx.guild.name = "Test Guild"
        mock_ctx.author = Mock(spec=interactions.Member)
        mock_ctx.author.id = "555666777"
        mock_ctx.author.mention = "<@555666777>"
        mock_ctx.defer = AsyncMock()
        mock_ctx.edit_original_response = AsyncMock()

        # Create mock target user
        mock_target_user = Mock(spec=interactions.Member)
        mock_target_user.id = "888999000"
        mock_target_user.mention = "<@888999000>"
        mock_target_user.fetch_dm = AsyncMock(side_effect=Exception("DM failed"))

        # Execute command
        await self.command._execute(mock_ctx, user=mock_target_user)

        # Verify database removal still succeeded
        mock_remove_participant.assert_called_once_with(mock_db, 123, 888999000)

        # Verify success response despite Discord failures
        mock_ctx.edit_original_response.assert_called_once()
        call_args = mock_ctx.edit_original_response.call_args[1]
        assert "✅ Successfully removed" in call_args["content"]

        # Verify channel notification still sent
        mock_ctx.channel.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_integration_end_to_end_workflow(self):
        """Test complete end-to-end workflow simulation."""
        # This would be a more comprehensive test that simulates
        # the entire workflow from Discord interaction to database update
        # and back to Discord response. For now, we'll keep it simple
        # as a placeholder for future comprehensive integration testing.

        command = RemoveCommand()

        # Verify command is properly configured
        assert command.name == "remove"
        assert command.staff_only == True
        assert len(command.options) == 1
        assert str(command.options[0].name) == "user"
        assert command.options[0].required == True
