"""
Remove command implementation for removing users from support tickets.
"""

import logging
from typing import Optional, Any

import interactions

from ..base import BaseCommand
from ..errors import CommandValidationError, CommandError
from ...database import get_db_session
from ...models.ticket import get_ticket_by_channel_id
from ...models.user import get_user_by_discord_id, create_user
from ...models.role_assignment import get_user_role_in_guild
from ...models.ticket_participant import (
    remove_participant_from_ticket,
    is_participant_in_ticket,
    get_participant_role_in_ticket,
)
from ...permissions import Permission


logger = logging.getLogger(__name__)


class RemoveCommand(BaseCommand):
    """Command to remove users from support tickets."""

    def __init__(self):
        """Initialize remove command."""
        # Define command options
        user_option = interactions.SlashCommandOption(
            name="user",
            description="User to remove from the ticket",
            type=interactions.OptionType.USER,
            required=True,
        )

        super().__init__(
            name="remove",
            description="Remove a user from the current ticket",
            required_permissions=[],  # Permission check is done in command logic
            cooldown_seconds=3.0,  # Prevent spam
            rate_limit_per_minute=20,  # Max 20 remove operations per minute
            staff_only=True,  # Only staff can remove users
            options=[user_option],
        )

    async def _execute(self, ctx: interactions.SlashContext, **kwargs) -> None:
        """
        Execute remove user command.

        Args:
            ctx: Slash command context
            **kwargs: Command arguments including 'user'
        """
        # Extract user from kwargs
        target_user = kwargs.get("user")

        if not target_user:
            await ctx.send(
                content="❌ Please specify a valid user to remove.", ephemeral=True
            )
            return

        # Ensure we're in a guild
        if not ctx.guild:
            await ctx.send(
                content="❌ This command can only be used in a server.", ephemeral=True
            )
            return

        # Ensure the author is a Member (not just User)
        if not isinstance(ctx.author, interactions.Member):
            await ctx.send(
                content="❌ This command can only be used by server members.",
                ephemeral=True,
            )
            return

        # Validate this is a ticket channel
        db = get_db_session()
        try:
            channel_id = int(ctx.channel.id)
            ticket = get_ticket_by_channel_id(db, channel_id)

            if not ticket:
                await ctx.send(
                    content="❌ This command can only be used in a ticket channel.",
                    ephemeral=True,
                )
                return

            # Check staff permissions
            guild_id = int(ctx.guild.id)
            author_discord_id = int(ctx.author.id)

            # Get user from database first
            author_user = get_user_by_discord_id(db, author_discord_id)
            if not author_user:
                # Create user if they don't exist
                author_user = create_user(db, author_discord_id)

            # Get author's role in guild (use getattr to work around SQLAlchemy typing issues)
            author_user_id = getattr(author_user, 'id')
            user_role = get_user_role_in_guild(db, author_user_id, guild_id)

            # Check if user has staff permissions
            if not user_role or user_role not in ["STAFF", "ADMIN"]:
                await ctx.send(
                    content="❌ Only staff members can remove users from tickets.",
                    ephemeral=True,
                )
                return

            # Validate target user parameter
            if not isinstance(target_user, (interactions.Member, interactions.User)):
                await ctx.send(content="❌ Invalid user specified.", ephemeral=True)
                return

            target_user_id = int(target_user.id)

            # Get ticket ID and creator ID as values (work around SQLAlchemy typing issues)
            ticket_id_value = getattr(ticket, 'id')
            creator_id_value = getattr(ticket, 'creator_id')

            # Check if target user is in ticket participants
            if not is_participant_in_ticket(db, ticket_id_value, target_user_id):
                await ctx.send(
                    content=f"❌ {target_user.mention} is not a participant in this ticket.",
                    ephemeral=True,
                )
                return

            # Prevent removing ticket creator (special case)
            if creator_id_value == target_user_id:
                await ctx.send(
                    content="❌ Cannot remove the ticket creator from their own ticket.",
                    ephemeral=True,
                )
                return

            # Send initial response
            await ctx.defer(ephemeral=True)

            try:
                # Remove user from ticket participants
                removal_success = remove_participant_from_ticket(
                    db, ticket_id_value, target_user_id
                )

                if not removal_success:
                    # Cast to Any to bypass typing issues  
                    ctx_any: Any = ctx
                    await ctx_any.edit_original_response(
                        content=f"❌ Failed to remove {target_user.mention} from the ticket."
                    )
                    return

                # Cast channel to GuildChannel for permission operations
                if not isinstance(ctx.channel, interactions.GuildChannel):
                    await ctx.send(
                        content="❌ This command can only be used in a guild channel.",
                        ephemeral=True
                    )
                    return

                # Remove channel permissions for target user
                await self._remove_channel_permissions(ctx.channel, target_user)

                # Send notification embed to channel
                await self._send_participant_removed_notification(
                    ctx.channel, target_user, ctx.author, ticket
                )

                # Send DM to removed user about ticket removal
                await self._send_dm_to_removed_user(target_user, ticket, ctx.guild)

                # Send confirmation to command user
                ctx_any: Any = ctx
                await ctx_any.edit_original_response(
                    content=f"✅ Successfully removed {target_user.mention} from the ticket."
                )

                logger.info(
                    f"User {target_user_id} removed from ticket {ticket_id_value} by {author_discord_id}"
                )

            except ValueError as e:
                ctx_any: Any = ctx
                await ctx_any.edit_original_response(
                    content=f"❌ Error removing user: {str(e)}"
                )
                return
            except Exception as e:
                logger.error(
                    f"Failed to remove user {target_user_id} from ticket {ticket_id_value}: {e}"
                )
                ctx_any: Any = ctx
                await ctx_any.edit_original_response(
                    content="❌ An error occurred while removing the user. Please try again."
                )
                return

        finally:
            db.close()

    async def _remove_channel_permissions(
        self,
        channel: interactions.GuildChannel,
        user: interactions.Member | interactions.User,
    ) -> None:
        """
        Remove channel permissions for the target user.

        Args:
            channel: The ticket channel
            user: User to revoke permissions from
        """
        try:
            # Cast to Any to bypass typing issues
            channel_any: Any = channel
            if hasattr(channel_any, 'edit_permission'):
                await channel_any.edit_permission(
                    target=user,
                    allow=None,
                    deny=None,
                    reason="Removed from ticket by staff",
                )
                logger.info(
                    f"Removed channel permissions for user {user.id} in channel {channel.id}"
                )
            else:
                logger.warning(f"Channel {channel.id} does not support permission editing")

        except Exception as e:
            logger.error(
                f"Failed to remove channel permissions for user {user.id}: {e}"
            )
            # Don't raise error here as the user was already removed from database
            # This is just a Discord permission cleanup

    async def _send_participant_removed_notification(
        self,
        channel: interactions.GuildChannel,
        removed_user: interactions.Member | interactions.User,
        staff_member: interactions.Member,
        ticket,
    ) -> None:
        """
        Send notification embed about participant removal.

        Args:
            channel: The ticket channel
            removed_user: User who was removed
            staff_member: Staff member who removed the user
            ticket: Ticket object
        """
        try:
            embed = interactions.Embed(
                title="👥 Participant Removed",
                description=f"{removed_user.mention} has been removed from this ticket.",
                color=0xFF6B35,  # Orange-red
                timestamp=interactions.Timestamp.now(),
            )

            embed.add_field(name="Removed by", value=staff_member.mention, inline=True)

            embed.add_field(name="Ticket ID", value=f"#{ticket.id}", inline=True)

            embed.set_footer(
                text="Ticket Bot",
                icon_url="https://cdn.discordapp.com/embed/avatars/0.png",
            )

            # Send embed to channel (cast to Any to bypass typing issues)
            channel_any: Any = channel
            if hasattr(channel_any, 'send'):
                await channel_any.send(embed=embed)
            else:
                logger.warning(f"Channel {channel.id} does not support sending messages")

        except Exception as e:
            logger.error(f"Failed to send participant removed notification: {e}")

    async def _send_dm_to_removed_user(
        self,
        user: interactions.Member | interactions.User,
        ticket,
        guild: interactions.Guild,
    ) -> None:
        """
        Send DM to removed user about ticket removal.

        Args:
            user: User who was removed
            ticket: Ticket object
            guild: Guild where ticket is located
        """
        try:
            embed = interactions.Embed(
                title="🎫 Removed from Ticket",
                description=f"You have been removed from ticket **#{ticket.id}** in **{guild.name}**.",
                color=0xFF6B35,  # Orange-red
                timestamp=interactions.Timestamp.now(),
            )

            embed.add_field(
                name="Ticket Reason",
                value=ticket.reason[:200] + ("..." if len(ticket.reason) > 200 else ""),
                inline=False,
            )

            embed.add_field(
                name="Current Status", value=ticket.status.upper(), inline=True
            )

            if ticket.created_at:
                embed.add_field(
                    name="Created",
                    value=f"<t:{int(ticket.created_at.timestamp())}:R>",
                    inline=True,
                )

            embed.set_footer(
                text=f"Ticket Bot • {guild.name}",
                icon_url="https://cdn.discordapp.com/embed/avatars/0.png",
            )

            # Try to send DM
            try:
                dm_channel = await user.fetch_dm(force=False)
                await dm_channel.send(embed=embed)
                logger.info(
                    f"Sent DM notification to user {user.id} about removal from ticket {ticket.id}"
                )
            except:
                # If DM fails (user has DMs disabled or left server), just log it
                logger.warning(
                    f"Could not send DM to user {user.id} - DMs may be disabled or user left server"
                )

        except Exception as e:
            logger.error(f"Failed to send DM to removed user {user.id}: {e}")

    def validate_arguments(self, **kwargs) -> None:
        """
        Validate command arguments.

        Args:
            **kwargs: Command arguments

        Raises:
            CommandValidationError: If validation fails
        """
        user = kwargs.get("user")

        if not user:
            raise CommandValidationError("user", "User parameter is required")

        # Additional validation can be added here if needed
