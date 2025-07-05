"""
Rename command implementation for renaming ticket channels.
"""

import logging
import re
from typing import Optional

import interactions

from ..base import BaseCommand
from ..errors import CommandValidationError, CommandError
from ...database import get_db_session
from ...models.ticket import get_ticket_by_channel_id
from ...models.user import get_user_by_discord_id, create_user
from ...models.role_assignment import get_user_role_in_guild
from ...permissions import Permission


logger = logging.getLogger(__name__)


class RenameCommand(BaseCommand):
    """Command to rename ticket channels."""
    
    def __init__(self):
        """Initialize rename command."""
        # Define command options
        new_name_option = interactions.SlashCommandOption(
            name="new_name",
            description="New name for the ticket (3-50 characters, alphanumeric only)",
            type=interactions.OptionType.STRING,
            required=True,
            min_length=3,
            max_length=50
        )
        
        super().__init__(
            name="rename",
            description="Rename the current ticket channel",
            required_permissions=[],  # Permission check is done in the command logic
            cooldown_seconds=30.0,  # Prevent rename spam
            rate_limit_per_minute=5,  # Max 5 renames per minute
            staff_only=True,  # Only staff can rename tickets
            options=[new_name_option]
        )
    
    def validate_arguments(self, **kwargs) -> None:
        """
        Validate rename command arguments.
        
        Args:
            **kwargs: Command arguments
            
        Raises:
            CommandValidationError: If validation fails
        """
        new_name = kwargs.get("new_name", "").strip()
        
        if not new_name:
            raise CommandValidationError("new_name", "New name is required")
        
        if len(new_name) < 3:
            raise CommandValidationError("new_name", "New name must be at least 3 characters long")
        
        if len(new_name) > 50:
            raise CommandValidationError("new_name", "New name must be no more than 50 characters long")
        
        # Check for appropriate content (alphanumeric, spaces, hyphens, underscores)
        if not re.match(r'^[a-zA-Z0-9\s\-_]+$', new_name):
            raise CommandValidationError("new_name", "New name can only contain letters, numbers, spaces, hyphens, and underscores")
    
    def sanitize_channel_name(self, name: str) -> str:
        """
        Sanitize name for Discord channel naming rules.
        
        Args:
            name: Original name
            
        Returns:
            Sanitized channel name
        """
        # Convert to lowercase
        name = name.lower()
        
        # Replace spaces with hyphens
        name = re.sub(r'\s+', '-', name)
        
        # Remove special characters except hyphens and underscores
        name = re.sub(r'[^a-z0-9\-_]', '', name)
        
        # Remove multiple consecutive hyphens/underscores
        name = re.sub(r'[-_]+', '-', name)
        
        # Remove leading/trailing hyphens
        name = name.strip('-_')
        
        # Ensure it's not empty after sanitization
        if not name:
            name = "ticket"
        
        # Add ticket prefix
        return f"ticket-{name}"
    
    def create_audit_entry(self, ticket_id: int, user_id: int, old_name: str, new_name: str) -> dict:
        """
        Create audit log entry for rename action.
        
        Args:
            ticket_id: ID of the renamed ticket
            user_id: Discord user ID who renamed the ticket
            old_name: Original channel name
            new_name: New channel name
            
        Returns:
            Audit log entry dictionary
        """
        from datetime import datetime
        
        return {
            "action": "ticket_renamed",
            "ticket_id": ticket_id,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "details": {
                "old_name": old_name,
                "new_name": new_name,
                "renamed_by": user_id
            }
        }
    
    async def _execute(self, ctx: interactions.SlashContext, **kwargs) -> None:
        """
        Execute rename ticket command.
        
        Args:
            ctx: Slash command context
            **kwargs: Command arguments
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
            
            # Get author's role in guild - access id within the session
            author_user_id = getattr(author_user, 'id', None)
            if not author_user_id:
                await ctx.send(
                    content="❌ Unable to verify user permissions.",
                    ephemeral=True
                )
                return
            user_role = get_user_role_in_guild(db, author_user_id, guild_id)
            
            # Check if user has staff permissions
            if not user_role or user_role not in ["STAFF", "ADMIN"]:
                await ctx.send(
                    content="❌ Only staff members can rename tickets.",
                    ephemeral=True
                )
                return
            
            # Get the new name from arguments
            new_name = kwargs.get("new_name", "").strip()
            
            # Validate the new name
            try:
                self.validate_arguments(new_name=new_name)
            except CommandValidationError as e:
                await ctx.send(
                    content=f"❌ {e.user_message}",
                    ephemeral=True
                )
                return
            
            # Sanitize the new name for Discord
            sanitized_name = self.sanitize_channel_name(new_name)
            
            # Get current channel name
            current_channel = ctx.channel
            old_name = current_channel.name or "unknown"
            
            # Check if the name is actually changing
            if old_name == sanitized_name:
                await ctx.send(
                    content="❌ The new name is the same as the current name.",
                    ephemeral=True
                )
                return
            
            # Get ticket id for audit log - access within session
            ticket_id = getattr(ticket, 'id', 0)
            
            # Attempt to rename the channel
            try:
                await current_channel.edit(name=sanitized_name)
                
                # Create audit log entry
                audit_entry = self.create_audit_entry(
                    ticket_id=ticket_id,
                    user_id=author_discord_id,
                    old_name=old_name,
                    new_name=sanitized_name
                )
                
                # Log the audit entry (for now just log to console)
                logger.info(f"Ticket renamed: {audit_entry}")
                
                # Send confirmation embed
                embed = interactions.Embed(
                    title="✅ Ticket Renamed",
                    description=f"Successfully renamed the ticket channel!",
                    color=0x00FF00  # Green
                )
                embed.add_field(
                    name="Old Name",
                    value=f"`{old_name}`",
                    inline=True
                )
                embed.add_field(
                    name="New Name", 
                    value=f"`{sanitized_name}`",
                    inline=True
                )
                embed.add_field(
                    name="Renamed By",
                    value=f"{ctx.author.mention}",
                    inline=True
                )
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                # Handle Discord API errors
                try:
                    status = getattr(e, 'status', None)
                    if status == 403:
                        await ctx.send(
                            content="❌ I don't have permission to rename this channel. Please check my permissions.",
                            ephemeral=True
                        )
                    elif status == 400:
                        await ctx.send(
                            content="❌ The new name is not valid for Discord. Please try a different name.",
                            ephemeral=True
                        )
                    else:
                        await ctx.send(
                            content=f"❌ Failed to rename channel: {str(e)}",
                            ephemeral=True
                        )
                except Exception:
                    await ctx.send(
                        content="❌ An unexpected error occurred while renaming the channel.",
                        ephemeral=True
                    )
                logger.error(f"Failed to rename channel {channel_id}: {e}")
                
        except Exception as e:
            await ctx.send(
                content="❌ An unexpected error occurred while renaming the channel.",
                ephemeral=True
            )
            logger.error(f"Unexpected error in rename command: {e}", exc_info=True)
                
        finally:
            db.close()
