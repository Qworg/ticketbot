"""
Ticket command implementation for creating new support tickets.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

import interactions

from ..base import BaseCommand
from ..errors import CommandValidationError, CommandError
from ...database import get_db_session
from ...models.user import User, get_user_by_discord_id, create_user
from ...models.ticket import has_open_ticket_in_guild, create_ticket
from ...permissions import Permission


logger = logging.getLogger(__name__)


class TicketCommand(BaseCommand):
    """Command to create new support tickets."""
    
    def __init__(self):
        """Initialize ticket command."""
        # Define command options
        reason_option = interactions.SlashCommandOption(
            name="reason",
            description="Reason for creating the ticket (5-500 characters)",
            type=interactions.OptionType.STRING,
            required=True,
            min_length=5,
            max_length=500
        )
        
        super().__init__(
            name="ticket",
            description="Create a new support ticket",
            required_permissions=[Permission.CREATE_TICKET.value],
            cooldown_seconds=30.0,  # Prevent spam ticket creation
            rate_limit_per_minute=2,  # Max 2 tickets per minute
            options=[reason_option]
        )
    
    async def _execute(self, ctx: interactions.SlashContext, **kwargs) -> None:
        """
        Execute ticket creation command.
        
        Args:
            ctx: Slash command context
            **kwargs: Command arguments including 'reason'
        """
        # Extract reason from kwargs
        reason = kwargs.get('reason', '')
        
        # Validate reason parameter
        self.validate_arguments(reason=reason)
        
        # Ensure we're in a guild
        if not ctx.guild:
            await ctx.send("❌ This command can only be used in a server.", ephemeral=True)
            return
        
        # Ensure the author is a Member (not just User)
        if not isinstance(ctx.author, interactions.Member):
            await ctx.send("❌ This command can only be used by server members.", ephemeral=True)
            return
        
        user_id = int(ctx.author.id)
        guild_id = int(ctx.guild.id)
        guild = ctx.guild
        
        # Check if user already has open ticket in this guild
        db = get_db_session()
        try:
            if has_open_ticket_in_guild(db, user_id, guild_id):
                await ctx.send(
                    "❌ You already have an open ticket in this server. "
                    "Please close your existing ticket before creating a new one.",
                    ephemeral=True
                )
                return
        finally:
            db.close()
        
        # Send initial response
        await ctx.defer(ephemeral=True)
        
        try:
            # Ensure user exists in database
            user = await self._get_or_create_user(user_id, ctx.author)
            
            # Get or create ticket category
            category = await self._get_or_create_ticket_category(guild)
            
            # Generate unique ticket channel name
            channel_name = await self._generate_channel_name(ctx.author)
            
            # Create ticket channel with proper permissions
            ticket_channel = await self._create_ticket_channel(
                guild, category, channel_name, ctx.author
            )
            
            # Store ticket in database
            ticket_data = await self._create_ticket_in_database(
                guild_id, user_id, reason, ticket_channel.id
            )
            
            # Send initial embed in ticket channel
            await self._send_initial_embed(ticket_channel, ctx.author, reason, ticket_data)
            
            # Send confirmation to user
            await ctx.send(
                content=f"✅ Ticket created successfully! Please check {ticket_channel.mention} "
                f"for your ticket **#{ticket_data['id']}**."
            )
            
            # Send confirmation DM to user
            await self._send_confirmation_dm(ctx.author, ticket_data, ticket_channel)
            
            # Log ticket creation event
            logger.info(
                f"Ticket {ticket_data['id']} created by user {user_id} "
                f"in guild {guild_id}, channel {ticket_channel.id}"
            )
            
        except Exception as e:
            logger.error(f"Failed to create ticket for user {user_id}: {e}", exc_info=True)
            await ctx.send(
                content="❌ Failed to create ticket. Please try again later or contact an administrator."
            )
    
    def validate_arguments(self, **kwargs) -> None:
        """
        Validate ticket command arguments.
        
        Args:
            **kwargs: Command arguments
            
        Raises:
            CommandValidationError: If validation fails
        """
        reason = kwargs.get('reason', '')
        
        if not reason or not reason.strip():
            raise CommandValidationError("reason", "Ticket reason is required")
        
        if len(reason.strip()) < 5:
            raise CommandValidationError("reason", "Ticket reason must be at least 5 characters long")
        
        if len(reason.strip()) > 500:
            raise CommandValidationError("reason", "Ticket reason must not exceed 500 characters")
    
    async def _get_or_create_user(self, discord_id: int, discord_member: interactions.Member) -> User:
        """
        Get or create user in database.
        
        Args:
            discord_id: Discord user ID
            discord_member: Discord member object
            
        Returns:
            User database object
        """
        db = get_db_session()
        try:
            # Try to get existing user
            user = get_user_by_discord_id(db, discord_id)
            if user:
                return user
            
            # Create new user if not found
            user = create_user(
                db=db,
                discord_id=discord_id,
                username=discord_member.username,
                role="USER"
            )
            logger.info(f"Created new user {user.id} for Discord ID {discord_id}")
            return user
        finally:
            db.close()
    
    async def _get_or_create_ticket_category(self, guild: interactions.Guild) -> Optional[interactions.GuildCategory]:
        """
        Get or create ticket category in the guild.
        
        Args:
            guild: Discord guild
            
        Returns:
            Category channel or None if creation fails
        """
        try:
            # Look for existing ticket category
            channels = await guild.fetch_channels()
            for channel in channels:
                if (isinstance(channel, interactions.GuildCategory) and 
                    channel.name and channel.name.lower() in ['tickets', 'support', 'help']):
                    return channel
            
            # Create new ticket category
            category_channel = await guild.create_channel(
                channel_type=interactions.ChannelType.GUILD_CATEGORY,
                name="🎫 Tickets",
                reason="Ticket category for support tickets"
            )
            # Cast to the expected type since we know it's a category
            if isinstance(category_channel, interactions.GuildCategory):
                category = category_channel
                logger.info(f"Created ticket category {category.id} in guild {guild.id}")
                return category
            else:
                logger.error(f"Created channel is not a category: {type(category_channel)}")
                return None
            
        except Exception as e:
            logger.error(f"Failed to create ticket category in guild {guild.id}: {e}")
            return None
    
    async def _generate_channel_name(self, user: interactions.Member) -> str:
        """
        Generate unique ticket channel name.
        
        Args:
            user: Discord user who created the ticket
            
        Returns:
            Channel name string
        """
        # Create unique channel name with user identifier
        username = user.username.lower()
        # Remove special characters and limit length
        username = ''.join(c for c in username if c.isalnum() or c in '-_')[:10]
        user_id = str(user.id)[-4:]  # Last 4 digits of user ID
        
        return f"ticket-{username}-{user_id}"
    
    async def _create_ticket_channel(
        self, 
        guild: interactions.Guild,
        category: Optional[interactions.GuildCategory],
        channel_name: str,
        user: interactions.Member
    ) -> interactions.GuildText:
        """
        Create ticket channel with proper permissions.
        
        Args:
            guild: Discord guild
            category: Category to place channel in
            channel_name: Name for the channel
            user: User who created the ticket
            
        Returns:
            Created text channel
        """
        # Calculate permission overwrites
        overwrites = await self._calculate_channel_permissions(guild, user)
        
        # Create the channel
        if category is not None:
            channel = await guild.create_channel(
                channel_type=interactions.ChannelType.GUILD_TEXT,
                name=channel_name,
                category=category,
                permission_overwrites=overwrites,
                reason=f"Ticket channel created for {user.username}"
            )
        else:
            channel = await guild.create_channel(
                channel_type=interactions.ChannelType.GUILD_TEXT,
                name=channel_name,
                permission_overwrites=overwrites,
                reason=f"Ticket channel created for {user.username}"
            )
        
        # Cast to GuildText since we know we created a text channel
        if isinstance(channel, interactions.GuildText):
            logger.info(f"Created ticket channel {channel.id} for user {user.id} in guild {guild.id}")
            return channel
        else:
            logger.error(f"Created channel is not a text channel: {type(channel)}")
            raise CommandError("Failed to create ticket channel")
    
    async def _calculate_channel_permissions(
        self, 
        guild: interactions.Guild, 
        user: interactions.Member
    ) -> list:
        """
        Calculate permission overwrites for ticket channel.
        
        Args:
            guild: Discord guild
            user: Ticket creator
            
        Returns:
            List of permission overwrites
        """
        overwrites = []
        
        # Deny @everyone access
        overwrites.append(
            interactions.PermissionOverwrite(
                id=guild.default_role.id,
                type=interactions.OverwriteType.ROLE,
                allow=interactions.Permissions.NONE,
                deny=interactions.Permissions.VIEW_CHANNEL | interactions.Permissions.SEND_MESSAGES
            )
        )
        
        # Grant ticket creator access
        overwrites.append(
            interactions.PermissionOverwrite(
                id=user.id,
                type=interactions.OverwriteType.MEMBER,
                allow=interactions.Permissions.VIEW_CHANNEL | 
                      interactions.Permissions.SEND_MESSAGES | 
                      interactions.Permissions.READ_MESSAGE_HISTORY,
                deny=interactions.Permissions.NONE
            )
        )
        
        # Grant bot full access
        bot_member = guild.me
        if bot_member:
            overwrites.append(
                interactions.PermissionOverwrite(
                    id=bot_member.id,
                    type=interactions.OverwriteType.MEMBER,
                    allow=interactions.Permissions.VIEW_CHANNEL | 
                          interactions.Permissions.SEND_MESSAGES | 
                          interactions.Permissions.READ_MESSAGE_HISTORY |
                          interactions.Permissions.MANAGE_CHANNELS,
                    deny=interactions.Permissions.NONE
                )
            )
        
        # Add staff role permissions if configured
        # TODO: Query database for guild staff role configuration
        # For now, look for common staff role names
        staff_roles = []
        for role in guild.roles:
            if role.name.lower() in ['staff', 'support', 'moderator', 'admin', 'administrator']:
                staff_roles.append(role)
        
        for role in staff_roles:
            overwrites.append(
                interactions.PermissionOverwrite(
                    id=role.id,
                    type=interactions.OverwriteType.ROLE,
                    allow=interactions.Permissions.VIEW_CHANNEL | 
                          interactions.Permissions.SEND_MESSAGES | 
                          interactions.Permissions.READ_MESSAGE_HISTORY,
                    deny=interactions.Permissions.NONE
                )
            )
        
        return overwrites
    
    async def _create_ticket_in_database(
        self, 
        guild_id: int, 
        creator_id: int, 
        reason: str, 
        channel_id: int
    ) -> dict:
        """
        Create ticket record in database.
        
        Args:
            guild_id: Discord guild ID
            creator_id: Discord user ID of creator
            reason: Ticket reason
            channel_id: Discord channel ID
            
        Returns:
            Ticket data dictionary
        """
        db = get_db_session()
        try:
            # Create ticket directly in database
            ticket = create_ticket(
                db=db,
                guild_id=guild_id,
                creator_id=creator_id,
                reason=reason,
                channel_id=channel_id,
                category="General"  # Default category
            )
            
            # Convert to dictionary format similar to API response
            ticket_data = {
                'id': ticket.id,
                'channel_id': ticket.channel_id,
                'guild_id': ticket.guild_id,
                'creator_id': ticket.creator_id,
                'status': ticket.status,
                'reason': ticket.reason,
                'created_at': ticket.created_at,
                'category': ticket.category
            }
            
            return ticket_data
        finally:
            db.close()
    
    async def _send_initial_embed(
        self, 
        channel: interactions.GuildText, 
        creator: interactions.Member, 
        reason: str,
        ticket_data: dict
    ) -> None:
        """
        Send initial embed message in ticket channel.
        
        Args:
            channel: Ticket channel
            creator: Ticket creator
            reason: Ticket reason
            ticket_data: Ticket data from database
        """
        ticket_id = ticket_data['id']
        
        embed = interactions.Embed(
            title=f"🎫 Ticket #{ticket_id}",
            description=f"Thank you for creating a ticket! A staff member will assist you shortly.",
            color=0x5865F2  # Discord blurple
        )
        
        embed.add_field(
            name="📝 Reason",
            value=reason,
            inline=False
        )
        
        embed.add_field(
            name="👤 Created by",
            value=creator.mention,
            inline=True
        )
        
        embed.add_field(
            name="🕒 Created at",
            value=f"<t:{int(datetime.now().timestamp())}:f>",
            inline=True
        )
        
        embed.add_field(
            name="📋 Status",
            value="🟢 Open",
            inline=True
        )
        
        embed.set_footer(
            text=f"Ticket ID: {ticket_id} | Use /close to close this ticket"
        )
        
        # Create action buttons
        components = [
            interactions.ActionRow(
                interactions.Button(
                    style=interactions.ButtonStyle.SUCCESS,
                    label="Claim Ticket",
                    custom_id=f"claim_ticket_{ticket_id}",
                    emoji="🙋"
                ),
                interactions.Button(
                    style=interactions.ButtonStyle.DANGER,
                    label="Close Ticket",
                    custom_id=f"close_ticket_{ticket_id}",
                    emoji="🔒"
                ),
                interactions.Button(
                    style=interactions.ButtonStyle.SECONDARY,
                    label="Add User",
                    custom_id=f"add_user_{ticket_id}",
                    emoji="➕"
                )
            )
        ]
        
        await channel.send(embed=embed, components=components)
    
    async def _send_confirmation_dm(
        self, 
        user: interactions.Member, 
        ticket_data: dict,
        channel: interactions.GuildText
    ) -> None:
        """
        Send confirmation DM to ticket creator.
        
        Args:
            user: Ticket creator
            ticket_data: Ticket data from database
            channel: Ticket channel
        """
        try:
            ticket_id = ticket_data['id']
            
            embed = interactions.Embed(
                title="✅ Ticket Created Successfully",
                description=f"Your ticket **#{ticket_id}** has been created!",
                color=0x00FF00  # Green
            )
            
            embed.add_field(
                name="📍 Location",
                value=f"Check {channel.mention} for your ticket",
                inline=False
            )
            
            embed.add_field(
                name="💡 Next Steps",
                value=(
                    "• A staff member will respond to you shortly\n"
                    "• Please provide any additional details if needed\n"
                    "• Use `/close` in the ticket channel when resolved"
                ),
                inline=False
            )
            
            embed.set_footer(text=f"Ticket ID: {ticket_id}")
            
            await user.send(embed=embed)
            
        except Exception as e:
            # DM sending can fail, but don't let it break ticket creation
            logger.warning(f"Failed to send confirmation DM to user {user.id}: {e}")



