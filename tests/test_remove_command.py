"""
Unit tests for the remove command implementation.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

import interactions

from app.commands.implementations.remove import RemoveCommand
from app.commands.errors import CommandValidationError, CommandError
from app.models.ticket import Ticket
from app.models.ticket_participant import TicketParticipant
from app.status import TicketStatus


class TestRemoveCommand:
    """Test cases for RemoveCommand."""

    def setup_method(self):
        """Set up test fixtures."""
        self.command = RemoveCommand()

        # Mock context
        self.mock_ctx = Mock(spec=interactions.SlashContext)
        self.mock_ctx.channel = Mock(spec=interactions.GuildChannel)
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
        self.mock_ticket.creator_id = 111222333  # Different from target user
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
        assert self.command.name == "remove"
        assert self.command.description == "Remove a user from the current ticket"
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
        with patch("app.commands.implementations.remove.get_db_session") as mock_db:
            await self.command._execute(self.mock_ctx, user=None)

            self.mock_ctx.send.assert_called_once()
            call_args = self.mock_ctx.send.call_args[1]
            assert "❌ Please specify a valid user to remove." in call_args["content"]
            assert call_args["ephemeral"] == True

    @pytest.mark.asyncio
    async def test_execute_not_in_guild(self):
        """Test execution when not in a guild."""
        self.mock_ctx.guild = None

        with patch("app.commands.implementations.remove.get_db_session") as mock_db:
            await self.command._execute(self.mock_ctx, user=self.mock_target_user)

            self.mock_ctx.send.assert_called_once()
            call_args = self.mock_ctx.send.call_args[1]
            assert (
                "❌ This command can only be used in a server." in call_args["content"]
            )
            assert call_args["ephemeral"] == True

    @pytest.mark.asyncio
    async def test_execute_author_not_member(self):
        """Test execution when author is not a member."""
        self.mock_ctx.author = Mock(spec=interactions.User)  # Not a Member

        with patch("app.commands.implementations.remove.get_db_session") as mock_db:
            await self.command._execute(self.mock_ctx, user=self.mock_target_user)

            self.mock_ctx.send.assert_called_once()
            call_args = self.mock_ctx.send.call_args[1]
            assert (
                "❌ This command can only be used by server members."
                in call_args["content"]
            )
            assert call_args["ephemeral"] == True

    @pytest.mark.asyncio
    async def test_execute_not_ticket_channel(self):
        """Test execution when not in a ticket channel."""
        mock_db = Mock()

        with patch(
            "app.commands.implementations.remove.get_db_session", return_value=mock_db
        ):
            with patch(
                "app.commands.implementations.remove.get_ticket_by_channel_id",
                return_value=None,
            ):
                await self.command._execute(self.mock_ctx, user=self.mock_target_user)

                self.mock_ctx.send.assert_called_once()
                call_args = self.mock_ctx.send.call_args[1]
                assert (
                    "❌ This command can only be used in a ticket channel."
                    in call_args["content"]
                )
                assert call_args["ephemeral"] == True

    @pytest.mark.asyncio
    async def test_execute_insufficient_permissions(self):
        """Test execution with insufficient permissions."""
        mock_db = Mock()

        with patch(
            "app.commands.implementations.remove.get_db_session", return_value=mock_db
        ):
            with patch(
                "app.commands.implementations.remove.get_ticket_by_channel_id",
                return_value=self.mock_ticket,
            ):
                with patch(
                    "app.commands.implementations.remove.get_user_role_in_guild",
                    return_value="USER",
                ):
                    await self.command._execute(
                        self.mock_ctx, user=self.mock_target_user
                    )

                    self.mock_ctx.send.assert_called_once()
                    call_args = self.mock_ctx.send.call_args[1]
                    assert (
                        "❌ Only staff members can remove users from tickets."
                        in call_args["content"]
                    )
                    assert call_args["ephemeral"] == True

    @pytest.mark.asyncio
    async def test_execute_user_not_participant(self):
        """Test execution when user is not a participant."""
        mock_db = Mock()

        with patch(
            "app.commands.implementations.remove.get_db_session", return_value=mock_db
        ):
            with patch(
                "app.commands.implementations.remove.get_ticket_by_channel_id",
                return_value=self.mock_ticket,
            ):
                with patch(
                    "app.commands.implementations.remove.get_user_role_in_guild",
                    return_value="STAFF",
                ):
                    with patch(
                        "app.commands.implementations.remove.is_participant_in_ticket",
                        return_value=False,
                    ):
                        await self.command._execute(
                            self.mock_ctx, user=self.mock_target_user
                        )

                        self.mock_ctx.send.assert_called_once()
                        call_args = self.mock_ctx.send.call_args[1]
                        assert (
                            f"❌ {self.mock_target_user.mention} is not a participant"
                            in call_args["content"]
                        )
                        assert call_args["ephemeral"] == True

    @pytest.mark.asyncio
    async def test_execute_cannot_remove_creator(self):
        """Test execution when trying to remove ticket creator."""
        mock_db = Mock()
        # Set target user as the ticket creator
        self.mock_target_user.id = str(self.mock_ticket.creator_id)

        with patch(
            "app.commands.implementations.remove.get_db_session", return_value=mock_db
        ):
            with patch(
                "app.commands.implementations.remove.get_ticket_by_channel_id",
                return_value=self.mock_ticket,
            ):
                with patch(
                    "app.commands.implementations.remove.get_user_role_in_guild",
                    return_value="STAFF",
                ):
                    with patch(
                        "app.commands.implementations.remove.is_participant_in_ticket",
                        return_value=True,
                    ):
                        await self.command._execute(
                            self.mock_ctx, user=self.mock_target_user
                        )

                        self.mock_ctx.send.assert_called_once()
                        call_args = self.mock_ctx.send.call_args[1]
                        assert (
                            "❌ Cannot remove the ticket creator" in call_args["content"]
                        )
                        assert call_args["ephemeral"] == True

    @pytest.mark.asyncio
    async def test_execute_successful_removal(self):
        """Test successful user removal."""
        mock_db = Mock()
        mock_dm_channel = Mock()
        self.mock_target_user.fetch_dm.return_value = mock_dm_channel
        mock_dm_channel.send = AsyncMock()

        # Mock author user for permission check
        mock_author_user = Mock()
        mock_author_user.id = "mock-user-uuid"

        with patch(
            "app.commands.implementations.remove.get_db_session", return_value=mock_db
        ):
            with patch(
                "app.commands.implementations.remove.get_ticket_by_channel_id",
                return_value=self.mock_ticket,
            ):
                with patch(
                    "app.commands.implementations.remove.get_user_by_discord_id",
                    return_value=mock_author_user,
                ):
                    with patch(
                        "app.commands.implementations.remove.get_user_role_in_guild",
                        return_value="STAFF",
                    ):
                        with patch(
                            "app.commands.implementations.remove.is_participant_in_ticket",
                            return_value=True,
                        ):
                            with patch(
                                "app.commands.implementations.remove.remove_participant_from_ticket",
                                return_value=True,
                            ):
                                with patch.object(
                                    self.command, "_remove_channel_permissions"
                                ) as mock_remove_perms:
                                    with patch.object(
                                        self.command,
                                        "_send_participant_removed_notification",
                                    ) as mock_notify:
                                        with patch.object(
                                            self.command, "_send_dm_to_removed_user"
                                        ) as mock_dm:
                                            await self.command._execute(
                                                self.mock_ctx, user=self.mock_target_user
                                            )

                                            # Check that defer was called
                                            self.mock_ctx.defer.assert_called_once_with(
                                                ephemeral=True
                                            )

                                            # Check that removal functions were called
                                            mock_remove_perms.assert_called_once()
                                            mock_notify.assert_called_once()
                                            mock_dm.assert_called_once()

                                            # Check success response
                                            self.mock_ctx.edit_original_response.assert_called_once()
                                            call_args = self.mock_ctx.edit_original_response.call_args[
                                                1
                                            ]
                                            assert (
                                                "✅ Successfully removed"
                                                in call_args["content"]
                                            )

    @pytest.mark.asyncio
    async def test_execute_removal_failure(self):
        """Test when database removal fails."""
        mock_db = Mock()

        # Mock author user for permission check
        mock_author_user = Mock()
        mock_author_user.id = "mock-user-uuid"

        with patch(
            "app.commands.implementations.remove.get_db_session", return_value=mock_db
        ):
            with patch(
                "app.commands.implementations.remove.get_ticket_by_channel_id",
                return_value=self.mock_ticket,
            ):
                with patch(
                    "app.commands.implementations.remove.get_user_by_discord_id",
                    return_value=mock_author_user,
                ):
                    with patch(
                        "app.commands.implementations.remove.get_user_role_in_guild",
                        return_value="STAFF",
                    ):
                        with patch(
                            "app.commands.implementations.remove.is_participant_in_ticket",
                            return_value=True,
                        ):
                            with patch(
                                "app.commands.implementations.remove.remove_participant_from_ticket",
                                return_value=False,
                            ):
                                await self.command._execute(
                                    self.mock_ctx, user=self.mock_target_user
                                )

                                # Check that defer was called
                                self.mock_ctx.defer.assert_called_once_with(ephemeral=True)

                                # Check error response
                                self.mock_ctx.edit_original_response.assert_called_once()
                                call_args = self.mock_ctx.edit_original_response.call_args[
                                    1
                                ]
                                assert "❌ Failed to remove" in call_args["content"]

    @pytest.mark.asyncio
    async def test_execute_exception_handling(self):
        """Test exception handling during execution."""
        mock_db = Mock()

        # Mock author user for permission check
        mock_author_user = Mock()
        mock_author_user.id = "mock-user-uuid"

        with patch(
            "app.commands.implementations.remove.get_db_session", return_value=mock_db
        ):
            with patch(
                "app.commands.implementations.remove.get_ticket_by_channel_id",
                return_value=self.mock_ticket,
            ):
                with patch(
                    "app.commands.implementations.remove.get_user_by_discord_id",
                    return_value=mock_author_user,
                ):
                    with patch(
                        "app.commands.implementations.remove.get_user_role_in_guild",
                        return_value="STAFF",
                    ):
                        with patch(
                            "app.commands.implementations.remove.is_participant_in_ticket",
                            return_value=True,
                        ):
                            with patch(
                                "app.commands.implementations.remove.remove_participant_from_ticket",
                                side_effect=Exception("Database error"),
                            ):
                                await self.command._execute(
                                    self.mock_ctx, user=self.mock_target_user
                                )

                                # Check that defer was called
                                self.mock_ctx.defer.assert_called_once_with(ephemeral=True)

                                # Check error response
                                self.mock_ctx.edit_original_response.assert_called_once()
                                call_args = self.mock_ctx.edit_original_response.call_args[
                                    1
                                ]
                                assert (
                                    "❌ An error occurred while removing the user"
                                    in call_args["content"]
                                )

    @pytest.mark.asyncio
    async def test_remove_channel_permissions(self):
        """Test removing channel permissions."""
        mock_channel = Mock()
        mock_channel.edit_permission = AsyncMock()

        await self.command._remove_channel_permissions(
            mock_channel, self.mock_target_user
        )

        mock_channel.edit_permission.assert_called_once_with(
            target=self.mock_target_user,
            allow=None,
            deny=None,
            reason="Removed from ticket by staff",
        )

    @pytest.mark.asyncio
    async def test_remove_channel_permissions_exception(self):
        """Test channel permission removal with exception."""
        mock_channel = Mock()
        mock_channel.edit_permission = AsyncMock(
            side_effect=Exception("Permission error")
        )

        # Should not raise exception, just log it
        await self.command._remove_channel_permissions(
            mock_channel, self.mock_target_user
        )

        mock_channel.edit_permission.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_participant_removed_notification(self):
        """Test sending participant removed notification."""
        mock_channel = Mock()
        mock_channel.send = AsyncMock()

        await self.command._send_participant_removed_notification(
            mock_channel, self.mock_target_user, self.mock_ctx.author, self.mock_ticket
        )

        mock_channel.send.assert_called_once()
        # Check that an embed was sent
        call_args = mock_channel.send.call_args[1]
        assert "embed" in call_args

    @pytest.mark.asyncio
    async def test_send_dm_to_removed_user_success(self):
        """Test sending DM to removed user successfully."""
        mock_dm_channel = Mock()
        mock_dm_channel.send = AsyncMock()
        self.mock_target_user.fetch_dm.return_value = mock_dm_channel

        await self.command._send_dm_to_removed_user(
            self.mock_target_user, self.mock_ticket, self.mock_ctx.guild
        )

        self.mock_target_user.fetch_dm.assert_called_once()
        mock_dm_channel.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_dm_to_removed_user_dm_failure(self):
        """Test sending DM when user has DMs disabled."""
        self.mock_target_user.fetch_dm.side_effect = Exception("DMs disabled")

        # Should not raise exception
        await self.command._send_dm_to_removed_user(
            self.mock_target_user, self.mock_ticket, self.mock_ctx.guild
        )

        self.mock_target_user.fetch_dm.assert_called_once()
