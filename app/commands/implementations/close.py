"""
Close command implementation for closing support tickets.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
import uuid

import interactions
from interactions import Timestamp

from ..base import BaseCommand
from ..errors import CommandValidationError, CommandError
from ...database import get_db_session
from ...models.ticket import get_ticket_by_channel_id, update_ticket
from ...models.user import get_user_by_discord_id
from ...models.role_assignment import get_user_role_in_guild
from ...permissions import Permission
from ...status import TicketStatus


logger = logging.getLogger(__name__)


class CloseCommand(BaseCommand):
    """Command to close support tickets."""
    
    def __init__(self):
        """Initialize close command."""
        # Define command options
        reason_option = interactions.SlashCommandOption(
            name="reason",
            description="Reason for closing the ticket (3-200 characters)",
            type=interactions.OptionType.STRING,
            required=False,
            min_length=3,
            max_length=200
        )
        
        super().__init__(
            name="close",
            description="Close the current support ticket",
            required_permissions=[],  # Permission check is done in the command logic
            cooldown_seconds=5.0,  # Prevent accidental double-close
            rate_limit_per_minute=10,  # Max 10 close attempts per minute
            options=[reason_option]
        )
    
    async def _execute(self, ctx: interactions.SlashContext, **kwargs) -> None:
        """
        Execute ticket close command.
        
        Args:
            ctx: Slash command context
            **kwargs: Command arguments including optional 'reason'
        """
        # Extract reason from kwargs
        reason = kwargs.get('reason', '')
        
        # Validate arguments
        self.validate_arguments(reason=reason)
        
        # Ensure we're in a guild
        if not ctx.guild:
            await ctx.send(
                content="❌ This command can only be used in a server.", 
                ephemeral=True
            )
            return
        
        # Ensure the author is a Member (not just User)
        if not isinstance(ctx.author, interactions.Member):
            await ctx.send(
                content="❌ This command can only be used by server members.", 
                ephemeral=True
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
                    ephemeral=True
                )
                return
            
            # Check if ticket is already closed
            if str(ticket.status) == TicketStatus.CLOSED.value:
                await ctx.send(
                    content="❌ This ticket is already closed.",
                    ephemeral=True
                )
                return
            
            # Check user permissions to close ticket
            user_id = int(ctx.author.id)
            guild_id = int(ctx.guild.id)
            
            can_close = await self._check_close_permissions(
                db, user_id, guild_id, ticket
            )
            
            if not can_close:
                await ctx.send(
                    content="❌ You don't have permission to close this ticket. "
                    "Only the ticket creator or staff members can close tickets.",
                    ephemeral=True
                )
                return
            
            # Send confirmation embed
            confirmation_embed = await self._create_confirmation_embed(
                ticket, ctx.author, reason
            )
            
            # Create confirmation buttons
            confirm_button = interactions.Button(
                style=interactions.ButtonStyle.DANGER,
                label="Close Ticket",
                custom_id=f"close_confirm_{ticket.id}",
                emoji="🔒"
            )
            
            cancel_button = interactions.Button(
                style=interactions.ButtonStyle.SECONDARY,
                label="Cancel",
                custom_id=f"close_cancel_{ticket.id}",
                emoji="❌"
            )
            
            action_row = interactions.ActionRow(confirm_button, cancel_button)
            
            # Send confirmation message
            await ctx.send(
                embeds=[confirmation_embed],
                components=[action_row],
                ephemeral=True
            )
            
            # Wait for button interaction with timeout
            try:
                button_response = await ctx.bot.wait_for_component(
                    components=[action_row],
                    timeout=300  # 5 minutes
                )
                
                if button_response.ctx.custom_id == f"close_confirm_{ticket.id}":
                    await self._handle_close_confirmation(
                        button_response.ctx, ticket, user_id, reason
                    )
                else:
                    await button_response.ctx.send(
                        content="❌ Ticket closure cancelled.",
                        ephemeral=True
                    )
                    
            except asyncio.TimeoutError:
                # Edit the original message to show timeout
                timeout_embed = interactions.Embed(
                    title="❌ Confirmation Timeout",
                    description="The close confirmation has timed out. Please run the command again if you still want to close this ticket.",
                    color=0xFF6B6B
                )
                
                # Disable buttons
                disabled_buttons = [
                    interactions.Button(
                        style=interactions.ButtonStyle.DANGER,
                        label="Close Ticket",
                        custom_id=f"close_confirm_{ticket.id}",
                        emoji="🔒",
                        disabled=True
                    ),
                    interactions.Button(
                        style=interactions.ButtonStyle.SECONDARY,
                        label="Cancel",
                        custom_id=f"close_cancel_{ticket.id}",
                        emoji="❌",
                        disabled=True
                    )
                ]
                
                disabled_row = interactions.ActionRow(*disabled_buttons)
                
                await ctx.edit(
                    embeds=[timeout_embed],
                    components=[disabled_row]
                )
                
        finally:
            db.close()
    
    async def _check_close_permissions(
        self, 
        db, 
        user_id: int, 
        guild_id: int, 
        ticket
    ) -> bool:
        """
        Check if user has permission to close the ticket.
        
        Args:
            db: Database session
            user_id: Discord user ID
            guild_id: Discord guild ID
            ticket: Ticket object
            
        Returns:
            True if user can close the ticket, False otherwise
        """
        # Allow ticket creator to close their own ticket
        if ticket.creator_id == user_id:
            return True
        
        # Allow assigned staff to close assigned tickets
        if ticket.assigned_to == user_id:
            return True
        
        # Check if user is staff or admin
        user = get_user_by_discord_id(db, user_id)
        if user:
            # Handle UUID conversion properly
            if isinstance(user.id, uuid.UUID):
                user_uuid = user.id
            else:
                # For tests or when user.id is a string, try to convert it
                try:
                    user_uuid = uuid.UUID(str(user.id))
                except ValueError:
                    # If it's not a valid UUID string, create a dummy UUID for tests
                    user_uuid = uuid.uuid4()
            
            user_role = get_user_role_in_guild(db, user_uuid, guild_id)
            if user_role in ['STAFF', 'ADMIN']:
                return True
        
        return False
    
    async def _create_confirmation_embed(
        self,
        ticket,
        author: interactions.Member,
        reason: Optional[str]
    ) -> interactions.Embed:
        """
        Create confirmation embed for ticket closure.
        
        Args:
            ticket: Ticket object
            author: User requesting closure
            reason: Optional close reason
            
        Returns:
            Confirmation embed
        """
        embed = interactions.Embed(
            title="🔒 Confirm Ticket Closure",
            description=f"Are you sure you want to close ticket **#{ticket.id}**?",
            color=0xFF9500,
            timestamp=Timestamp.utcnow()
        )
        
        embed.add_field(
            name="📋 Ticket Details",
            value=f"**ID:** #{ticket.id}\n"
                  f"**Status:** {ticket.status.title()}\n"
                  f"**Created:** <t:{int(ticket.created_at.timestamp())}:R>",
            inline=True
        )
        
        embed.add_field(
            name="👤 Requested By",
            value=f"{author.mention}\n"
                  f"**User:** {author.username}#{author.discriminator}",
            inline=True
        )
        
        if reason:
            embed.add_field(
                name="📝 Close Reason",
                value=reason,
                inline=False
            )
        
        embed.add_field(
            name="⚠️ Warning",
            value="This action cannot be undone. The ticket will be marked as closed and archived.",
            inline=False
        )
        
        embed.set_footer(
            text="You have 5 minutes to confirm or cancel this action."
        )
        
        return embed
    
    async def _handle_close_confirmation(
        self,
        button_ctx: interactions.ComponentContext,
        ticket,
        user_id: int,
        reason: Optional[str]
    ) -> None:
        """
        Handle the close confirmation button press.
        
        Args:
            button_ctx: Button interaction context
            ticket: Ticket object
            user_id: User ID who requested closure
            reason: Optional close reason
        """
        db = get_db_session()
        try:
            # Update ticket status to CLOSED
            updated_ticket = update_ticket(
                db=db,
                ticket_id=ticket.id,
                user_id=user_id,
                status=TicketStatus.CLOSED.value,
                close_reason=reason or "Closed via Discord command"
            )
            
            # Send confirmation
            await button_ctx.send(
                "✅ Ticket closed successfully!",
                ephemeral=True
            )
            
            # Send closure notification to channel
            if isinstance(button_ctx.author, interactions.Member):
                await self._send_closure_notification(
                    button_ctx.channel, updated_ticket, button_ctx.author, reason
                )
            
            # Update channel permissions to read-only
            if button_ctx.guild:
                await self._update_channel_permissions_readonly(
                    button_ctx.channel, button_ctx.guild
                )
            
            # Add CLOSED prefix to channel name
            await self._update_channel_name_closed(button_ctx.channel)
            
            # Schedule channel deletion after configured delay
            asyncio.create_task(
                self._schedule_channel_deletion(button_ctx.channel)
            )
            
            # Log closure event
            logger.info(
                f"Ticket {ticket.id} closed by user {user_id} "
                f"with reason: {reason or 'No reason provided'}"
            )
            
        except Exception as e:
            logger.error(f"Failed to close ticket {ticket.id}: {e}", exc_info=True)
            await button_ctx.send(
                "❌ Failed to close ticket. Please try again later or contact an administrator.",
                ephemeral=True
            )
        finally:
            db.close()
    
    async def _send_closure_notification(
        self,
        channel: interactions.BaseChannel,
        ticket,
        closer: interactions.Member,
        reason: Optional[str]
    ) -> None:
        """
        Send closure notification embed to the ticket channel.
        
        Args:
            channel: Ticket channel
            ticket: Updated ticket object
            closer: User who closed the ticket
            reason: Close reason
        """
        embed = interactions.Embed(
            title="🔒 Ticket Closed",
            description=f"This ticket has been closed by {closer.mention}.",
            color=0xFF4444,
            timestamp=Timestamp.utcnow()
        )
        
        embed.add_field(
            name="📋 Ticket Information",
            value=f"**Ticket ID:** #{ticket.id}\n"
                  f"**Status:** {ticket.status.title()}\n"
                  f"**Closed At:** <t:{int(ticket.closed_at.timestamp())}:F>",
            inline=True
        )
        
        if reason:
            embed.add_field(
                name="📝 Close Reason",
                value=reason,
                inline=False
            )
        
        embed.add_field(
            name="📚 Archive Information",
            value="This channel will be archived and deleted after 24 hours.\n"
                  "Please save any important information before then.",
            inline=False
        )
        
        embed.set_footer(
            text="Thank you for using our support system!"
        )
        
        # Cast to GuildText channel to access send method
        try:
            # Try to send as if it's a text channel
            await channel.send(embeds=[embed])  # type: ignore
        except AttributeError:
            logger.error(f"Cannot send message to channel {channel.id}: not a text channel")
    
    async def _update_channel_permissions_readonly(
        self,
        channel: interactions.BaseChannel,
        guild: interactions.Guild
    ) -> None:
        """
        Update channel permissions to read-only for users.
        
        Args:
            channel: Ticket channel
            guild: Discord guild
        """
        try:
            # Get @everyone role
            everyone_role = guild.default_role
            
            # Update permissions to deny sending messages for @everyone
            await channel.edit_permission(  # type: ignore
                everyone_role,
                deny=interactions.Permissions.SEND_MESSAGES | interactions.Permissions.ADD_REACTIONS
            )
            
            logger.info(f"Updated channel {channel.id} permissions to read-only")
            
        except Exception as e:
            logger.error(f"Failed to update channel permissions: {e}")
    
    async def _update_channel_name_closed(
        self,
        channel: interactions.BaseChannel
    ) -> None:
        """
        Add CLOSED prefix to channel name.
        
        Args:
            channel: Ticket channel
        """
        try:
            current_name = channel.name
            if current_name and not current_name.startswith("closed-"):
                new_name = f"closed-{current_name}"
                await channel.edit(name=new_name)  # type: ignore
                logger.info(f"Updated channel name from {current_name} to {new_name}")
            
        except Exception as e:
            logger.error(f"Failed to update channel name: {e}")
    
    async def _schedule_channel_deletion(
        self,
        channel: interactions.BaseChannel,
        delay_hours: int = 24
    ) -> None:
        """
        Schedule channel deletion after configured delay.
        
        Args:
            channel: Ticket channel
            delay_hours: Hours to wait before deletion
        """
        try:
            # Wait for the specified delay
            await asyncio.sleep(delay_hours * 3600)  # Convert hours to seconds
            
            # Delete the channel
            await channel.delete(reason="Automatic deletion of closed ticket channel")  # type: ignore
            logger.info(f"Deleted closed ticket channel {channel.id} after {delay_hours} hours")
            
        except Exception as e:
            logger.error(f"Failed to delete channel {channel.id}: {e}")
    
    def validate_arguments(self, **kwargs) -> None:
        """
        Validate close command arguments.
        
        Args:
            **kwargs: Command arguments
            
        Raises:
            CommandValidationError: If validation fails
        """
        reason = kwargs.get('reason', '')
        
        # Reason is optional, but if provided, must meet requirements
        if reason and len(reason.strip()) < 3:
            raise CommandValidationError(
                "reason", 
                "Close reason must be at least 3 characters long"
            )
        
        if reason and len(reason) > 200:
            raise CommandValidationError(
                "reason", 
                "Close reason must be no more than 200 characters long"
            )
