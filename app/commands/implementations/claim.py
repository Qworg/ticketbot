"""
Claim command implementation for claiming support tickets.
"""

import logging
from typing import Optional
import uuid

import interactions
import httpx

from ..base import BaseCommand
from ..errors import CommandValidationError, CommandError
from ...database import get_db_session
from ...models.ticket import get_ticket_by_channel_id
from ...models.user import get_user_by_discord_id, create_user
from ...models.role_assignment import get_user_role_in_guild
from ...permissions import Permission
from ...status import TicketStatus


logger = logging.getLogger(__name__)


class ClaimCommand(BaseCommand):
    """Command to claim support tickets."""
    
    def __init__(self):
        """Initialize claim command."""
        super().__init__(
            name="claim",
            description="Claim the current support ticket",
            required_permissions=[],  # Permission check is done in the command logic
            cooldown_seconds=5.0,  # Prevent accidental double-claim
            rate_limit_per_minute=10,  # Max 10 claim attempts per minute
            staff_only=True,  # Only staff can claim tickets
            options=[]  # No options needed for claim command
        )
    
    async def _execute(self, ctx: interactions.SlashContext, **kwargs) -> None:
        """
        Execute claim ticket command.
        
        Args:
            ctx: Slash command context
            **kwargs: Command arguments (none for claim)
        """
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
                    content="❌ Only staff members can claim tickets.",
                    ephemeral=True
                )
                return
            
            # Get ticket details
            ticket_id_value = getattr(ticket, 'id')
            assigned_to_value = getattr(ticket, 'assigned_to', None)
            creator_id_value = getattr(ticket, 'creator_id')
            status_value = getattr(ticket, 'status')
            
            # Check if ticket is already assigned
            if assigned_to_value is not None:
                # Get assigned user for display
                assigned_user = get_user_by_discord_id(db, assigned_to_value) if assigned_to_value else None
                assigned_mention = f"<@{assigned_to_value}>" if assigned_to_value else "Unknown user"
                
                await ctx.send(
                    content=f"❌ This ticket is already assigned to {assigned_mention}.",
                    ephemeral=True
                )
                return
            
            # Prevent users from claiming their own tickets
            if creator_id_value == author_discord_id:
                await ctx.send(
                    content="❌ You cannot claim your own ticket.",
                    ephemeral=True
                )
                return
            
            # Check if ticket status allows claiming
            if status_value not in [TicketStatus.OPEN.value, TicketStatus.IN_PROGRESS.value]:
                await ctx.send(
                    content=f"❌ Tickets with status '{status_value}' cannot be claimed.",
                    ephemeral=True
                )
                return
            
            # Send initial response
            await ctx.defer(ephemeral=True)
            
            try:
                # Call the API endpoint to claim the ticket
                api_base_url = "http://localhost:8000"  # TODO: Make this configurable
                
                # Generate a temporary token for API access
                # TODO: Use proper service-to-service authentication
                import os
                from ...auth import generate_token
                
                user_data = {
                    'user_id': str(author_user_id),
                    'discord_id': author_discord_id,
                    'role': user_role,
                    'email': getattr(author_user, 'email', None)
                }
                token = generate_token(user_data)
                
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{api_base_url}/api/tickets/{ticket_id_value}/claim",
                        headers=headers,
                        timeout=10.0
                    )
                
                if response.status_code == 200:
                    claim_data = response.json()
                    
                    # Update channel topic to show assigned staff
                    try:
                        new_topic = f"🎫 Ticket #{ticket_id_value} • Assigned to {ctx.author.mention}"
                        if hasattr(ctx.channel, 'edit'):
                            await ctx.channel.edit(topic=new_topic)
                    except Exception as e:
                        logger.warning(f"Failed to update channel topic: {e}")
                    
                    # Send confirmation embed
                    await self._send_claim_confirmation(ctx, ticket, ctx.author)
                    
                    # Send notification to ticket creator
                    await self._send_claim_notification_to_creator(ctx, ticket, ctx.author)
                    
                    # Send success response to command user
                    await ctx.edit_original_response(
                        content=f"✅ Successfully claimed ticket #{ticket_id_value}."
                    )
                    
                    logger.info(f"Ticket {ticket_id_value} claimed by user {author_discord_id}")
                    
                elif response.status_code == 403:
                    error_detail = response.json().get("detail", "Insufficient permissions")
                    await ctx.edit_original_response(
                        content=f"❌ {error_detail}"
                    )
                elif response.status_code == 409:
                    error_detail = response.json().get("detail", "Ticket cannot be claimed")
                    await ctx.edit_original_response(
                        content=f"❌ {error_detail}"
                    )
                else:
                    await ctx.edit_original_response(
                        content="❌ Failed to claim ticket. Please try again later."
                    )
                    logger.error(f"API claim request failed with status {response.status_code}: {response.text}")
                
            except httpx.RequestError as e:
                logger.error(f"Failed to make claim API request: {e}")
                await ctx.edit_original_response(
                    content="❌ Failed to claim ticket due to connection error. Please try again."
                )
            except Exception as e:
                logger.error(f"Unexpected error claiming ticket {ticket_id_value}: {e}")
                await ctx.edit_original_response(
                    content="❌ An unexpected error occurred while claiming the ticket."
                )
        
        finally:
            db.close()
    
    async def _send_claim_confirmation(
        self,
        ctx: interactions.SlashContext,
        ticket,
        claimer: interactions.Member
    ) -> None:
        """
        Send confirmation embed about ticket claim.
        
        Args:
            ctx: Slash command context
            ticket: Ticket object
            claimer: Staff member who claimed the ticket
        """
        try:
            embed = interactions.Embed(
                title="🎯 Ticket Claimed",
                description=f"This ticket has been claimed by {claimer.mention}.",
                color=0x28A745,  # Green
                timestamp=interactions.Timestamp.now()
            )
            
            embed.add_field(
                name="Assigned Staff",
                value=claimer.mention,
                inline=True
            )
            
            embed.add_field(
                name="Ticket ID",
                value=f"#{getattr(ticket, 'id')}",
                inline=True
            )
            
            embed.add_field(
                name="Status",
                value="In Progress",
                inline=True
            )
            
            embed.set_footer(
                text="Ticket Bot",
                icon_url="https://cdn.discordapp.com/embed/avatars/0.png"
            )
            
            # Send embed to channel
            if hasattr(ctx.channel, 'send'):
                await ctx.channel.send(embed=embed)
        
        except Exception as e:
            logger.error(f"Failed to send claim confirmation: {e}")
    
    async def _send_claim_notification_to_creator(
        self,
        ctx: interactions.SlashContext,
        ticket,
        claimer: interactions.Member
    ) -> None:
        """
        Send notification to ticket creator about assignment.
        
        Args:
            ctx: Slash command context
            ticket: Ticket object
            claimer: Staff member who claimed the ticket
        """
        try:
            creator_id = getattr(ticket, 'creator_id')
            if not creator_id:
                return
            
            # Try to get the creator member
            try:
                if not ctx.guild:
                    logger.warning("Guild context not available for creator notification")
                    return
                creator = await ctx.guild.fetch_member(creator_id)
                if not creator:
                    logger.warning(f"Could not find creator member {creator_id}")
                    return
            except:
                logger.warning(f"Could not fetch creator member {creator_id}")
                return
            
            guild_name = ctx.guild.name if ctx.guild else "Unknown Server"
            
            embed = interactions.Embed(
                title="🎫 Ticket Assignment Update",
                description=f"Your ticket **#{getattr(ticket, 'id')}** in **{guild_name}** has been assigned to a staff member.",
                color=0x007BFF,  # Blue
                timestamp=interactions.Timestamp.now()
            )
            
            embed.add_field(
                name="Assigned Staff",
                value=claimer.mention,
                inline=True
            )
            
            embed.add_field(
                name="Status",
                value="In Progress",
                inline=True
            )
            
            ticket_reason = getattr(ticket, 'reason', '')
            if ticket_reason:
                embed.add_field(
                    name="Original Reason",
                    value=ticket_reason[:200] + ("..." if len(ticket_reason) > 200 else ""),
                    inline=False
                )
            
            embed.set_footer(
                text=f"Ticket Bot • {guild_name}",
                icon_url="https://cdn.discordapp.com/embed/avatars/0.png"
            )
            
            # Try to send DM to creator
            try:
                dm_channel = await creator.fetch_dm(force=False)
                await dm_channel.send(embed=embed)
                logger.info(f"Sent claim notification DM to ticket creator {creator_id}")
            except:
                logger.warning(f"Could not send DM to ticket creator {creator_id}")
        
        except Exception as e:
            logger.error(f"Failed to send claim notification to creator: {e}")
    
    def validate_arguments(self, **kwargs) -> None:
        """
        Validate command arguments.
        
        Args:
            **kwargs: Command arguments
        
        Raises:
            CommandValidationError: If validation fails
        """
        # No arguments to validate for claim command
        pass
