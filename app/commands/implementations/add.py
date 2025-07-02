"""
Add command implementation for adding users to support tickets.
"""

import logging
from typing import Optional

import interactions

from ..base import BaseCommand
from ..errors import CommandValidationError, CommandError
from ...database import get_db_session
from ...models.ticket import get_ticket_by_channel_id
from ...models.user import get_user_by_discord_id, create_user
from ...models.role_assignment import get_user_role_in_guild
from ...models.ticket_participant import (
    add_participant_to_ticket, 
    is_participant_in_ticket
)
from ...permissions import Permission


logger = logging.getLogger(__name__)


class AddCommand(BaseCommand):
    """Command to add users to support tickets."""
    
    def __init__(self):
        """Initialize add command."""
        # Define command options
        user_option = interactions.SlashCommandOption(
            name="user",
            description="User to add to the ticket",
            type=interactions.OptionType.USER,
            required=True
        )
        
        super().__init__(
            name="add",
            description="Add a user to the current ticket",
            required_permissions=[],  # Permission check is done in command logic
            cooldown_seconds=3.0,  # Prevent spam
            rate_limit_per_minute=20,  # Max 20 add operations per minute
            staff_only=True,  # Only staff can add users
            options=[user_option]
        )
    
    async def _execute(self, ctx: interactions.SlashContext, **kwargs) -> None:
        """
        Execute add user command.
        
        Args:
            ctx: Slash command context
            **kwargs: Command arguments including 'user'
        """
        # Extract user from kwargs
        target_user = kwargs.get('user')
        
        if not target_user:
            await ctx.send(
                content="❌ Please specify a valid user to add.",
                ephemeral=True
            )
            return
        
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
            
            # Check staff permissions
            guild_id = int(ctx.guild.id)
            author_id = int(ctx.author.id)
            
            # Get author's role in guild
            user_role = get_user_role_in_guild(db, author_id, guild_id)
            
            # Check if user has staff permissions
            if not user_role or user_role not in ['STAFF', 'ADMIN']:
                await ctx.send(
                    content="❌ Only staff members can add users to tickets.",
                    ephemeral=True
                )
                return
            
            # Validate target user parameter
            if not isinstance(target_user, (interactions.Member, interactions.User)):
                await ctx.send(
                    content="❌ Invalid user specified.",
                    ephemeral=True
                )
                return
            
            target_user_id = int(target_user.id)
            
            # Check if target user is already in ticket
            if is_participant_in_ticket(db, ticket.id, target_user_id):
                await ctx.send(
                    content=f"❌ {target_user.mention} is already a participant in this ticket.",
                    ephemeral=True
                )
                return
            
            # Send initial response
            await ctx.defer(ephemeral=True)
            
            try:
                # Add user to ticket participants
                participant = add_participant_to_ticket(
                    db, 
                    ticket.id, 
                    target_user_id, 
                    role='participant'
                )
                
                # Add channel permissions for target user
                await self._add_channel_permissions(ctx.channel, target_user)
                
                # Send notification embed to channel
                await self._send_participant_added_notification(
                    ctx.channel, 
                    target_user, 
                    ctx.author,
                    ticket
                )
                
                # Send DM to added user with ticket information
                await self._send_dm_to_added_user(target_user, ticket, ctx.guild)
                
                # Send confirmation to command user
                await ctx.edit_original_response(
                    content=f"✅ Successfully added {target_user.mention} to the ticket."
                )
                
                logger.info(
                    f"User {target_user_id} added to ticket {ticket.id} by {author_id}"
                )
                
            except ValueError as e:
                await ctx.edit_original_response(
                    content=f"❌ Error adding user: {str(e)}"
                )
                return
            except Exception as e:
                logger.error(f"Failed to add user {target_user_id} to ticket {ticket.id}: {e}")
                await ctx.edit_original_response(
                    content="❌ An error occurred while adding the user. Please try again."
                )
                return
                
        finally:
            db.close()
    
    async def _add_channel_permissions(
        self, 
        channel: interactions.GuildChannel, 
        user: interactions.Member | interactions.User
    ) -> None:
        """
        Add channel permissions for the target user.
        
        Args:
            channel: The ticket channel
            user: User to grant permissions to
        """
        try:
            # Grant read_messages and send_messages permissions
            await channel.edit_permission(
                target=user,
                allow=interactions.Permissions.VIEW_CHANNEL | interactions.Permissions.SEND_MESSAGES,
                reason="Added to ticket by staff"
            )
            
            logger.info(f"Added channel permissions for user {user.id} in channel {channel.id}")
            
        except Exception as e:
            logger.error(f"Failed to add channel permissions for user {user.id}: {e}")
            raise CommandError(f"Failed to add channel permissions: {str(e)}")
    
    async def _send_participant_added_notification(
        self,
        channel: interactions.GuildChannel,
        added_user: interactions.Member | interactions.User,
        staff_member: interactions.Member,
        ticket
    ) -> None:
        """
        Send notification embed about new participant.
        
        Args:
            channel: The ticket channel
            added_user: User who was added
            staff_member: Staff member who added the user
            ticket: Ticket object
        """
        try:
            embed = interactions.Embed(
                title="👥 Participant Added",
                description=f"{added_user.mention} has been added to this ticket.",
                color=0x00FF00,  # Green
                timestamp=interactions.Timestamp.now()
            )
            
            embed.add_field(
                name="Added by",
                value=staff_member.mention,
                inline=True
            )
            
            embed.add_field(
                name="Ticket ID",
                value=f"#{ticket.id}",
                inline=True
            )
            
            embed.set_footer(
                text="Ticket Bot",
                icon_url="https://cdn.discordapp.com/embed/avatars/0.png"
            )
            
            await channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Failed to send participant added notification: {e}")
    
    async def _send_dm_to_added_user(
        self,
        user: interactions.Member | interactions.User,
        ticket,
        guild: interactions.Guild
    ) -> None:
        """
        Send DM to added user with ticket information.
        
        Args:
            user: User who was added
            ticket: Ticket object
            guild: Guild where ticket is located
        """
        try:
            embed = interactions.Embed(
                title="🎫 Added to Ticket",
                description=f"You have been added to ticket **#{ticket.id}** in **{guild.name}**.",
                color=0x0099FF,  # Blue
                timestamp=interactions.Timestamp.now()
            )
            
            embed.add_field(
                name="Ticket Reason",
                value=ticket.reason[:200] + ("..." if len(ticket.reason) > 200 else ""),
                inline=False
            )
            
            embed.add_field(
                name="Current Status",
                value=ticket.status.upper(),
                inline=True
            )
            
            if ticket.created_at:
                embed.add_field(
                    name="Created",
                    value=f"<t:{int(ticket.created_at.timestamp())}:R>",
                    inline=True
                )
            
            embed.set_footer(
                text=f"Ticket Bot • {guild.name}",
                icon_url="https://cdn.discordapp.com/embed/avatars/0.png"
            )
            
            # Try to send DM
            try:
                dm_channel = await user.fetch_dm()
                await dm_channel.send(embed=embed)
                logger.info(f"Sent DM notification to user {user.id} about ticket {ticket.id}")
            except:
                # If DM fails (user has DMs disabled), just log it
                logger.warning(f"Could not send DM to user {user.id} - DMs may be disabled")
                
        except Exception as e:
            logger.error(f"Failed to send DM to added user {user.id}: {e}")
    
    def validate_arguments(self, **kwargs) -> None:
        """
        Validate command arguments.
        
        Args:
            **kwargs: Command arguments
            
        Raises:
            CommandValidationError: If validation fails
        """
        user = kwargs.get('user')
        
        if not user:
            raise CommandValidationError("user", "User parameter is required")
        
        # Additional validation can be added here if needed
