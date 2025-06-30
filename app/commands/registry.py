"""
Command registration system for Discord slash commands.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Type

import interactions

from .base import BaseCommand
from .errors import CommandError


logger = logging.getLogger(__name__)


class CommandRegistry:
    """Registry for managing Discord slash command registration and execution."""
    
    def __init__(self, bot: interactions.Client):
        """
        Initialize command registry.
        
        Args:
            bot: Discord bot client instance
        """
        self.bot = bot
        self.commands: Dict[str, BaseCommand] = {}
        self._registered = False
        
    def register_command(self, command: BaseCommand) -> None:
        """
        Register a command in the registry.
        
        Args:
            command: Command instance to register
        """
        if command.name in self.commands:
            logger.warning(f"Command {command.name} is already registered, overwriting")
        
        self.commands[command.name] = command
        logger.info(f"Registered command: {command.name}")
    
    def get_command(self, name: str) -> Optional[BaseCommand]:
        """
        Get a registered command by name.
        
        Args:
            name: Command name
            
        Returns:
            Command instance or None if not found
        """
        return self.commands.get(name)
    
    def list_commands(self) -> List[str]:
        """
        Get list of all registered command names.
        
        Returns:
            List of command names
        """
        return list(self.commands.keys())
    
    async def setup_slash_commands(self) -> None:
        """
        Set up slash command registration with Discord.
        This should be called after bot is ready.
        """
        if self._registered:
            logger.warning("Commands already registered, skipping setup")
            return
        
        logger.info("Setting up slash commands...")
        
        # Register each command with Discord
        for command_name, command in self.commands.items():
            await self._create_slash_command(command)
        
        # Sync commands with Discord globally
        try:
            await self.bot.synchronise_interactions()  # Global commands
            logger.info(f"Successfully synchronized {len(self.commands)} commands globally")
        except Exception as e:
            logger.error(f"Failed to sync commands with Discord: {e}")
            raise
        
        self._registered = True
        logger.info("Command registration completed")
    
    async def _create_slash_command(self, command: BaseCommand) -> None:
        """
        Create a slash command registration with Discord.
        
        Args:
            command: Command to register
        """
        try:
            # Create the slash command decorator with options
            if command.options:
                @self.bot.command(
                    name=command.name,
                    description=command.description,
                    options=command.options
                )
                async def command_handler(ctx: interactions.SlashContext, **kwargs):
                    """Generated command handler."""
                    await command.execute(ctx, **kwargs)
            else:
                @self.bot.command(
                    name=command.name,
                    description=command.description
                )
                async def command_handler(ctx: interactions.SlashContext, **kwargs):
                    """Generated command handler."""
                    await command.execute(ctx, **kwargs)
            
            # Store reference to prevent garbage collection
            setattr(self, f"_handler_{command.name}", command_handler)
            
            logger.debug(f"Created slash command: {command.name}")
            
        except Exception as e:
            logger.error(f"Failed to create slash command {command.name}: {e}")
            raise
    
    def cleanup_tracking(self) -> None:
        """
        Clean up old tracking data from all commands.
        Should be called periodically to prevent memory leaks.
        """
        for command in self.commands.values():
            try:
                command.cleanup_tracking()
            except Exception as e:
                logger.error(f"Error cleaning up command {command.name}: {e}")
    
    async def handle_command_error(self, ctx: interactions.SlashContext, error: Exception) -> None:
        """
        Global error handler for commands.
        
        Args:
            ctx: Command context
            error: Exception that occurred
        """
        if isinstance(error, CommandError):
            # Expected command error
            await ctx.send(f"❌ {error.user_message}", ephemeral=True)
            command_name = ctx.command.name if ctx.command else "unknown"
            logger.warning(f"Command error in {command_name}: {error}")
        else:
            # Unexpected error
            command_name = ctx.command.name if ctx.command else "unknown"
            logger.error(f"Unexpected error in command {command_name}: {error}", exc_info=True)
            await ctx.send(
                "❌ An unexpected error occurred. Please try again later.",
                ephemeral=True
            )
    
    def get_command_stats(self) -> Dict[str, Dict]:
        """
        Get statistics about registered commands.
        
        Returns:
            Dictionary with command stats
        """
        stats = {
            "total_commands": len(self.commands),
            "registered": self._registered,
            "commands": {}
        }
        
        for name, command in self.commands.items():
            stats["commands"][name] = {
                "description": command.description,
                "cooldown_seconds": command.cooldown_seconds,
                "rate_limit_per_minute": command.rate_limit_per_minute,
                "staff_only": command.staff_only,
                "admin_only": command.admin_only,
                "required_permissions": command.required_permissions
            }
        
        return stats


# Global registry instance
_registry: Optional[CommandRegistry] = None


def get_command_registry(bot: Optional[interactions.Client] = None) -> CommandRegistry:
    """
    Get the global command registry instance.
    
    Args:
        bot: Bot instance (required on first call)
        
    Returns:
        CommandRegistry instance
    """
    global _registry
    
    if _registry is None:
        if bot is None:
            raise ValueError("Bot instance required for first registry creation")
        _registry = CommandRegistry(bot)
    
    return _registry


def register_command(command: BaseCommand) -> None:
    """
    Convenience function to register a command.
    
    Args:
        command: Command to register
    """
    registry = get_command_registry()
    registry.register_command(command)
