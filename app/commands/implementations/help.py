"""
Help command implementation showing available commands and usage.
"""

import interactions

from ..base import BaseCommand
from ..registry import get_command_registry
from ...permissions import Role


class HelpCommand(BaseCommand):
    """Command to show help information about available commands."""
    
    def __init__(self):
        """Initialize help command."""
        super().__init__(
            name="help",
            description="Show available commands and usage information",
            cooldown_seconds=5.0  # Prevent spam
        )
    
    async def _execute(self, ctx: interactions.SlashContext, **kwargs) -> None:
        """
        Execute help command.
        
        Args:
            ctx: Slash command context
            **kwargs: Command arguments (none for help)
        """
        # Get user role for filtering commands
        user_id = int(ctx.author.id)
        guild_id = int(ctx.guild.id) if ctx.guild else None
        
        # Get user role (simplified for help command)
        user_role = "USER"  # Default role
        try:
            from ...database import get_db_session
            from ...models.user import User
            from ...models.role_assignment import get_user_role_in_guild
            
            db = get_db_session()
            try:
                user = db.query(User).filter(User.discord_id == user_id).first()
                if user:
                    if guild_id:
                        # Handle both UUID objects and mock strings in tests
                        import uuid
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
                    else:
                        user_role = str(user.role)
            finally:
                db.close()
        except Exception:
            pass  # Use default role if error
        
        # Create help embed
        embed = interactions.Embed(
            title="📋 Bot Commands",
            description="Available commands for ticket management",
            color=0x5865F2  # Discord blurple
        )
        
        # Get registry and commands
        registry = get_command_registry()
        commands = registry.commands
        
        # Separate commands by category
        user_commands = []
        staff_commands = []
        admin_commands = []
        
        for cmd_name, cmd in commands.items():
            if cmd.admin_only and user_role != 'ADMIN':
                continue  # Don't show admin commands to non-admins
            elif cmd.staff_only and user_role not in ['ADMIN', 'STAFF']:
                continue  # Don't show staff commands to users
            
            # Categorize commands
            if cmd.admin_only:
                admin_commands.append(cmd)
            elif cmd.staff_only:
                staff_commands.append(cmd)
            else:
                user_commands.append(cmd)
        
        # Add user commands
        if user_commands:
            user_cmd_text = ""
            for cmd in user_commands:
                user_cmd_text += f"`/{cmd.name}` - {cmd.description}\n"
            embed.add_field(
                name="🟦 User Commands",
                value=user_cmd_text,
                inline=False
            )
        
        # Add staff commands
        if staff_commands and user_role in ['ADMIN', 'STAFF']:
            staff_cmd_text = ""
            for cmd in staff_commands:
                staff_cmd_text += f"`/{cmd.name}` - {cmd.description}\n"
            embed.add_field(
                name="🟨 Staff Commands",
                value=staff_cmd_text,
                inline=False
            )
        
        # Add admin commands
        if admin_commands and user_role == 'ADMIN':
            admin_cmd_text = ""
            for cmd in admin_commands:
                admin_cmd_text += f"`/{cmd.name}` - {cmd.description}\n"
            embed.add_field(
                name="🟥 Admin Commands",
                value=admin_cmd_text,
                inline=False
            )
        
        # Add footer with additional info
        embed.add_field(
            name="💡 Usage Tips",
            value=(
                "• Use `/help` to see this message again\n"
                "• Commands have cooldowns to prevent spam\n"
                "• Some commands require specific permissions"
            ),
            inline=False
        )
        
        embed.set_footer(
            text=f"Your role: {user_role} • Total commands: {len([c for c in commands.values() if not c.admin_only or user_role == 'ADMIN'])}"
        )
        
        await ctx.send(embed=embed, ephemeral=True)
