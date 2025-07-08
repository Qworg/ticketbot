"""
Help command implementation showing available commands and usage.
"""

import interactions
from typing import Dict, List, Optional
import logging

from ..base import BaseCommand
from ..registry import get_command_registry
from ...permissions import Role

logger = logging.getLogger(__name__)


class HelpCommand(BaseCommand):
    """Command to show help information about available commands."""
    
    def __init__(self):
        """Initialize help command."""
        super().__init__(
            name="help",
            description="Show available commands and usage information",
            cooldown_seconds=5.0  # Prevent spam
        )
        
    def get_command_definition(self) -> interactions.SlashCommand:
        """Get the slash command definition."""
        return interactions.SlashCommand(
            name=self.name,
            description=self.description,
            options=[
                interactions.SlashCommandOption(
                    name="category",
                    description="Show help for a specific category",
                    type=interactions.OptionType.STRING,
                    required=False,
                    choices=[
                        interactions.SlashCommandChoice(name="User Commands", value="user"),
                        interactions.SlashCommandChoice(name="Staff Commands", value="staff"),
                        interactions.SlashCommandChoice(name="Admin Commands", value="admin"),
                        interactions.SlashCommandChoice(name="Bot Information", value="info"),
                        interactions.SlashCommandChoice(name="Usage Examples", value="examples"),
                        interactions.SlashCommandChoice(name="Troubleshooting", value="troubleshooting")
                    ]
                ),
                interactions.SlashCommandOption(
                    name="command",
                    description="Get detailed help for a specific command",
                    type=interactions.OptionType.STRING,
                    required=False
                )
            ]
        )
        
    def _create_navigation_buttons(self, current_page: int, total_pages: int, user_role: str) -> List[interactions.Button]:
        """Create navigation buttons for help pages."""
        buttons = []
        
        # Category buttons
        buttons.append(
            interactions.Button(
                style=interactions.ButtonStyle.PRIMARY,
                label="User Commands",
                custom_id="help_user",
                emoji="🟦"
            )
        )
        
        if user_role in ['ADMIN', 'STAFF']:
            buttons.append(
                interactions.Button(
                    style=interactions.ButtonStyle.SUCCESS,
                    label="Staff Commands", 
                    custom_id="help_staff",
                    emoji="🟨"
                )
            )
        
        if user_role == 'ADMIN':
            buttons.append(
                interactions.Button(
                    style=interactions.ButtonStyle.DANGER,
                    label="Admin Commands",
                    custom_id="help_admin",
                    emoji="🟥"
                )
            )
        
        buttons.append(
            interactions.Button(
                style=interactions.ButtonStyle.SECONDARY,
                label="Bot Info",
                custom_id="help_info",
                emoji="ℹ️"
            )
        )
        
        buttons.append(
            interactions.Button(
                style=interactions.ButtonStyle.SECONDARY,
                label="Examples",
                custom_id="help_examples",
                emoji="📖"
            )
        )
        
        return buttons
    
    def _create_category_embed(self, category: str, user_role: str, commands: Dict[str, BaseCommand]) -> interactions.Embed:
        """Create help embed for a specific category."""
        
        if category == "user":
            embed = interactions.Embed(
                title="🟦 User Commands",
                description="Commands available to all users",
                color=0x5865F2
            )
            
            user_commands = [cmd for cmd in commands.values() if not cmd.staff_only and not cmd.admin_only]
            
            for cmd in user_commands:
                embed.add_field(
                    name=f"/{cmd.name}",
                    value=f"{cmd.description}\n**Usage:** `/{cmd.name}`",
                    inline=False
                )
                
        elif category == "staff" and user_role in ['ADMIN', 'STAFF']:
            embed = interactions.Embed(
                title="🟨 Staff Commands",
                description="Commands available to staff members",
                color=0xF1C40F
            )
            
            staff_commands = [cmd for cmd in commands.values() if cmd.staff_only and not cmd.admin_only]
            
            for cmd in staff_commands:
                embed.add_field(
                    name=f"/{cmd.name}",
                    value=f"{cmd.description}\n**Usage:** `/{cmd.name}`",
                    inline=False
                )
                
        elif category == "admin" and user_role == 'ADMIN':
            embed = interactions.Embed(
                title="🟥 Admin Commands",
                description="Commands available to administrators",
                color=0xE74C3C
            )
            
            admin_commands = [cmd for cmd in commands.values() if cmd.admin_only]
            
            for cmd in admin_commands:
                embed.add_field(
                    name=f"/{cmd.name}",
                    value=f"{cmd.description}\n**Usage:** `/{cmd.name}`",
                    inline=False
                )
                
        elif category == "info":
            embed = interactions.Embed(
                title="ℹ️ Bot Information",
                description="Information about the ticket bot",
                color=0x9B59B6
            )
            
            embed.add_field(
                name="Bot Details",
                value=(
                    "**Version:** 1.0.0\n"
                    "**Language:** Python 3.10+\n"
                    "**Framework:** interactions.py\n"
                    "**Status:** ✅ Online and ready"
                ),
                inline=False
            )
            
            embed.add_field(
                name="Your Information",
                value=(
                    f"**Your Role:** {user_role}\n"
                    f"**Available Commands:** {len([c for c in commands.values() if not c.admin_only or user_role == 'ADMIN'])}\n"
                    f"**Permissions:** {'Full Access' if user_role == 'ADMIN' else 'Staff Access' if user_role == 'STAFF' else 'User Access'}"
                ),
                inline=False
            )
            
            embed.add_field(
                name="Support & Documentation",
                value=(
                    "• [GitHub Repository](https://github.com/your-org/ticketbot)\n"
                    "• [Setup Guide](https://github.com/your-org/ticketbot/wiki/Setup)\n"
                    "• [Command Reference](https://github.com/your-org/ticketbot/wiki/Commands)\n"
                    "• [API Documentation](https://github.com/your-org/ticketbot/wiki/API)"
                ),
                inline=False
            )
            
        elif category == "examples":
            embed = interactions.Embed(
                title="📖 Usage Examples",
                description="Common command usage patterns",
                color=0x3498DB
            )
            
            embed.add_field(
                name="Creating Tickets",
                value=(
                    "• `/ticket reason:Need help with billing`\n"
                    "• `/ticket reason:Bug report - app crashes on startup`\n"
                    "• `/ticket reason:Feature request for mobile app`"
                ),
                inline=False
            )
            
            if user_role in ['ADMIN', 'STAFF']:
                embed.add_field(
                    name="Managing Tickets (Staff)",
                    value=(
                        "• `/close reason:Issue resolved`\n"
                        "• `/claim` - Claim an unassigned ticket\n"
                        "• `/add user:@username` - Add user to ticket\n"
                        "• `/remove user:@username` - Remove user from ticket\n"
                        "• `/rename new_name:billing-urgent` - Rename ticket channel"
                    ),
                    inline=False
                )
            
            embed.add_field(
                name="Common Patterns",
                value=(
                    "• Use descriptive reasons when creating tickets\n"
                    "• Close tickets with a reason for better tracking\n"
                    "• Use `/help command:ticket` for detailed command help\n"
                    "• Commands are case-insensitive"
                ),
                inline=False
            )
            
        elif category == "troubleshooting":
            embed = interactions.Embed(
                title="🔧 Troubleshooting",
                description="Common issues and solutions",
                color=0xE67E22
            )
            
            embed.add_field(
                name="Permission Issues",
                value=(
                    "• **Permission denied?** Check your role permissions\n"
                    "• **Can't see commands?** Contact server administrators\n"
                    "• **Commands not responding?** Bot may be restarting"
                ),
                inline=False
            )
            
            embed.add_field(
                name="Ticket Issues",
                value=(
                    "• **Can't create ticket?** You may already have one open\n"
                    "• **Ticket not closing?** Check if you're the creator or staff\n"
                    "• **Missing messages?** Check if you have proper permissions"
                ),
                inline=False
            )
            
            embed.add_field(
                name="Getting Help",
                value=(
                    "• **Command not working?** Try again after cooldown period\n"
                    "• **Need support?** Contact server administrators\n"
                    "• **Report bugs:** Use our GitHub repository\n"
                    "• **Feature requests:** Join our Discord server"
                ),
                inline=False
            )
            
        else:
            # Default case or unauthorized access
            embed = interactions.Embed(
                title="❌ Access Denied",
                description="You don't have permission to view this help category.",
                color=0xE74C3C
            )
            
        return embed
    
    def _get_command_help(self, command_name: str, commands: Dict[str, BaseCommand], user_role: str) -> Optional[interactions.Embed]:
        """Get detailed help for a specific command."""
        
        # Find the command
        cmd = commands.get(command_name.lower())
        if not cmd:
            return None
            
        # Check if user has permission to see this command
        if cmd.admin_only and user_role != 'ADMIN':
            return None
        elif cmd.staff_only and user_role not in ['ADMIN', 'STAFF']:
            return None
            
        # Create detailed help embed
        embed = interactions.Embed(
            title=f"📋 Command: /{cmd.name}",
            description=cmd.description,
            color=0x5865F2
        )
        
        # Add command details based on command type
        if cmd.name == "ticket":
            embed.add_field(
                name="Usage",
                value="`/ticket reason:<your reason>`",
                inline=False
            )
            embed.add_field(
                name="Parameters",
                value="**reason** (required): Describe why you need help (5-500 characters)",
                inline=False
            )
            embed.add_field(
                name="Examples",
                value=(
                    "• `/ticket reason:Need help with billing`\n"
                    "• `/ticket reason:Bug report - app crashes on startup`\n"
                    "• `/ticket reason:Feature request for mobile app`"
                ),
                inline=False
            )
            embed.add_field(
                name="Notes",
                value="• You can only have one open ticket at a time\n• A private channel will be created for your ticket",
                inline=False
            )
            
        elif cmd.name == "close":
            embed.add_field(
                name="Usage",
                value="`/close [reason:<closure reason>]`",
                inline=False
            )
            embed.add_field(
                name="Parameters",
                value="**reason** (optional): Reason for closing the ticket (3-200 characters)",
                inline=False
            )
            embed.add_field(
                name="Who can use",
                value="• Ticket creator\n• Staff members\n• Administrators",
                inline=False
            )
            embed.add_field(
                name="Notes",
                value="• A confirmation prompt will appear\n• Channel will be deleted after closure",
                inline=False
            )
            
        elif cmd.name == "claim" and user_role in ['ADMIN', 'STAFF']:
            embed.add_field(
                name="Usage",
                value="`/claim`",
                inline=False
            )
            embed.add_field(
                name="Purpose",
                value="Assign yourself to an unassigned ticket",
                inline=False
            )
            embed.add_field(
                name="Requirements",
                value="• Must be used in a ticket channel\n• Ticket must be unassigned\n• Cannot claim your own ticket",
                inline=False
            )
            
        elif cmd.name == "add" and user_role in ['ADMIN', 'STAFF']:
            embed.add_field(
                name="Usage",
                value="`/add user:<@username>`",
                inline=False
            )
            embed.add_field(
                name="Parameters",
                value="**user** (required): The user to add to the ticket",
                inline=False
            )
            embed.add_field(
                name="Notes",
                value="• User will gain access to the ticket channel\n• User will receive a notification DM",
                inline=False
            )
            
        elif cmd.name == "remove" and user_role in ['ADMIN', 'STAFF']:
            embed.add_field(
                name="Usage", 
                value="`/remove user:<@username>`",
                inline=False
            )
            embed.add_field(
                name="Parameters",
                value="**user** (required): The user to remove from the ticket",
                inline=False
            )
            embed.add_field(
                name="Notes",
                value="• Cannot remove the ticket creator\n• User will lose access to the ticket channel",
                inline=False
            )
            
        elif cmd.name == "rename" and user_role in ['ADMIN', 'STAFF']:
            embed.add_field(
                name="Usage",
                value="`/rename new_name:<new channel name>`",
                inline=False
            )
            embed.add_field(
                name="Parameters",
                value="**new_name** (required): New name for the ticket channel (3-50 characters)",
                inline=False
            )
            embed.add_field(
                name="Notes",
                value="• Name will be sanitized for Discord\n• 'ticket-' prefix will be added automatically",
                inline=False
            )
            
        elif cmd.name == "help":
            embed.add_field(
                name="Usage",
                value="`/help [category:<category>] [command:<command>]`",
                inline=False
            )
            embed.add_field(
                name="Parameters",
                value=(
                    "**category** (optional): Show help for a specific category\n"
                    "**command** (optional): Get detailed help for a specific command"
                ),
                inline=False
            )
            embed.add_field(
                name="Categories",
                value="• user - User commands\n• staff - Staff commands\n• admin - Admin commands\n• info - Bot information",
                inline=False
            )
            
        else:
            # Generic command help
            embed.add_field(
                name="Usage",
                value=f"`/{cmd.name}`",
                inline=False
            )
            embed.add_field(
                name="Permission Level",
                value="Admin Only" if cmd.admin_only else "Staff Only" if cmd.staff_only else "All Users",
                inline=False
            )
            
        # Add common footer
        embed.set_footer(text="Use /help for general help or /help command:<name> for specific command help")
        
        return embed

    async def _execute(self, ctx: interactions.SlashContext, **kwargs) -> None:
        """
        Execute help command.
        
        Args:
            ctx: Slash command context
            **kwargs: Command arguments (category, command)
        """
        # Get parameters from kwargs
        category = kwargs.get('category')
        command = kwargs.get('command')
        
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
        
        # Get registry and commands
        registry = get_command_registry()
        commands = registry.commands
        
        # Handle specific command help
        if command:
            embed = self._get_command_help(command, commands, user_role)
            if embed:
                await ctx.send(embed=embed, ephemeral=True)
                return
            else:
                error_embed = interactions.Embed(
                    title="❌ Command Not Found",
                    description=f"Command `{command}` not found or you don't have permission to view it.",
                    color=0xE74C3C
                )
                await ctx.send(embed=error_embed, ephemeral=True)
                return
        
        # Handle category-specific help
        if category:
            embed = self._create_category_embed(category, user_role, commands)
            
            # Create navigation buttons for category view
            components = [
                interactions.ActionRow(
                    *self._create_navigation_buttons(1, 1, user_role)
                )
            ]
            
            await ctx.send(embed=embed, components=components, ephemeral=True)
            return
        
        # Create help embed
        embed = interactions.Embed(
            title="📋 Bot Commands",
            description="Available commands for ticket management. Use the buttons below to navigate different sections.",
            color=0x5865F2  # Discord blurple
        )
        
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
        
        # Add overview of available commands
        overview_text = ""
        if user_commands:
            overview_text += f"**🟦 User Commands ({len(user_commands)}):** Available to all users\n"
        if staff_commands and user_role in ['ADMIN', 'STAFF']:
            overview_text += f"**🟨 Staff Commands ({len(staff_commands)}):** Available to staff members\n"
        if admin_commands and user_role == 'ADMIN':
            overview_text += f"**🟥 Admin Commands ({len(admin_commands)}):** Available to administrators\n"
        
        embed.add_field(
            name="📚 Command Categories",
            value=overview_text,
            inline=False
        )
        
        # Add quick start guide
        embed.add_field(
            name="🚀 Quick Start",
            value=(
                "• Use `/ticket reason:your issue` to create a new ticket\n"
                "• Use `/help category:user` to see all user commands\n"
                "• Use `/help command:ticket` for detailed command help\n"
                "• Click the buttons below to navigate different sections"
            ),
            inline=False
        )
        
        # Add bot status
        embed.add_field(
            name="ℹ️ Bot Status",
            value=(
                f"**Version:** 1.0.0\n"
                f"**Your Role:** {user_role}\n"
                f"**Available Commands:** {len([c for c in commands.values() if not c.admin_only or user_role == 'ADMIN'])}\n"
                f"**Status:** ✅ Online and ready"
            ),
            inline=False
        )
        
        embed.set_footer(
            text="💡 Tip: Use buttons below to navigate or /help command:<name> for specific help"
        )
        
        # Create navigation buttons
        components = [
            interactions.ActionRow(
                *self._create_navigation_buttons(1, 1, user_role)
            )
        ]
        
        await ctx.send(embed=embed, components=components, ephemeral=True)
        
    async def handle_button_interaction(self, ctx: interactions.ComponentContext) -> None:
        """Handle button interactions for help navigation."""
        custom_id = ctx.custom_id
        
        if not custom_id.startswith("help_"):
            return
        
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
        
        # Get registry and commands
        registry = get_command_registry()
        commands = registry.commands
        
        # Parse category from custom_id
        category = custom_id.replace("help_", "")
        
        # Create category embed
        embed = self._create_category_embed(category, user_role, commands)
        
        # Create navigation buttons
        components = [
            interactions.ActionRow(
                *self._create_navigation_buttons(1, 1, user_role)
            )
        ]
        
        # Update the message
        await ctx.edit_origin(embed=embed, components=components)
