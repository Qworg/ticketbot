"""Comprehensive error handler for the Discord bot.

This module provides error handling utilities, decorators, and handlers
for Discord bot operations including rate limiting, permission errors,
and graceful degradation.
"""

import asyncio
import logging
import traceback
from typing import Optional, Callable, Any, Dict, Union
from functools import wraps
from datetime import datetime, timedelta

import discord
from discord.ext import commands

from bot.exceptions import (
    DiscordBotException,
    DiscordAPIError,
    PermissionError,
    ChannelError,
    TicketError,
    BackendConnectionError,
    RateLimitError,
    ConfigurationError,
    CommandError,
    ValidationError
)

# Configure logger
logger = logging.getLogger(__name__)


class ErrorHandler:
    """Centralized error handler for Discord bot operations."""
    
    def __init__(self, bot):
        """Initialize the error handler.
        
        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
        self.rate_limit_tracker = {}
        self.error_counts = {}
        self.last_error_reset = datetime.utcnow()
    
    async def handle_discord_error(
        self,
        error: Exception,
        interaction: Optional[discord.Interaction] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Handle Discord-related errors with appropriate responses.
        
        Args:
            error: The exception that occurred
            interaction: Discord interaction (if applicable)
            context: Additional context information
            
        Returns:
            True if error was handled, False otherwise
        """
        context = context or {}
        
        # Log the error
        self._log_error(error, interaction, context)
        
        # Handle specific Discord errors
        if isinstance(error, discord.Forbidden):
            await self._handle_forbidden_error(error, interaction, context)
            return True
            
        elif isinstance(error, discord.NotFound):
            await self._handle_not_found_error(error, interaction, context)
            return True
            
        elif isinstance(error, discord.HTTPException):
            if error.status == 429:  # Rate limit
                await self._handle_rate_limit_error(error, interaction, context)
            else:
                await self._handle_http_error(error, interaction, context)
            return True
            
        elif isinstance(error, discord.ConnectionClosed):
            await self._handle_connection_error(error, interaction, context)
            return True
            
        elif isinstance(error, DiscordBotException):
            await self._handle_custom_error(error, interaction, context)
            return True
        
        return False
    
    async def handle_command_error(
        self,
        interaction: discord.Interaction,
        error: discord.ApplicationCommandError
    ) -> None:
        """Handle application command errors.
        
        Args:
            interaction: Discord interaction
            error: Application command error
        """
        context = {
            "command": interaction.command.name if interaction.command else "unknown",
            "user_id": interaction.user.id,
            "guild_id": interaction.guild_id,
            "channel_id": interaction.channel_id
        }
        
        # Handle specific command errors
        if hasattr(error, 'retry_after'):  # Cooldown error
            await self._handle_cooldown_error(error, interaction, context)
            
        elif isinstance(error, commands.MissingPermissions):
            await self._handle_missing_permissions_error(error, interaction, context)
            
        elif isinstance(error, commands.BotMissingPermissions):
            await self._handle_bot_missing_permissions_error(error, interaction, context)
            
        elif isinstance(error, commands.CommandNotFound):
            await self._handle_command_not_found_error(error, interaction, context)
            
        else:
            # Handle as generic error
            await self.handle_discord_error(error, interaction, context)
    
    async def _handle_forbidden_error(
        self,
        error: discord.Forbidden,
        interaction: Optional[discord.Interaction],
        context: Dict[str, Any]
    ) -> None:
        """Handle Discord Forbidden errors."""
        message = "I don't have permission to perform this action. Please check my permissions and try again."
        
        if interaction:
            await self._send_error_response(interaction, message, ephemeral=True)
        
        # Log specific permission issue
        logger.warning(
            f"Permission denied: {error}",
            extra={
                "error_type": "permission_denied",
                "status_code": error.status,
                **context
            }
        )
    
    async def _handle_not_found_error(
        self,
        error: discord.NotFound,
        interaction: Optional[discord.Interaction],
        context: Dict[str, Any]
    ) -> None:
        """Handle Discord NotFound errors."""
        message = "The requested resource was not found. It may have been deleted or moved."
        
        if interaction:
            await self._send_error_response(interaction, message, ephemeral=True)
        
        logger.warning(
            f"Resource not found: {error}",
            extra={
                "error_type": "not_found",
                "status_code": error.status,
                **context
            }
        )
    
    async def _handle_rate_limit_error(
        self,
        error: discord.HTTPException,
        interaction: Optional[discord.Interaction],
        context: Dict[str, Any]
    ) -> None:
        """Handle Discord rate limit errors."""
        retry_after = getattr(error, 'retry_after', 60)
        message = f"Rate limit exceeded. Please wait {retry_after:.1f} seconds and try again."
        
        if interaction:
            await self._send_error_response(interaction, message, ephemeral=True)
        
        # Track rate limits
        self._track_rate_limit(context.get("command", "unknown"), retry_after)
        
        logger.warning(
            f"Rate limit exceeded: {error}",
            extra={
                "error_type": "rate_limit",
                "retry_after": retry_after,
                **context
            }
        )
    
    async def _handle_http_error(
        self,
        error: discord.HTTPException,
        interaction: Optional[discord.Interaction],
        context: Dict[str, Any]
    ) -> None:
        """Handle generic Discord HTTP errors."""
        message = "A Discord API error occurred. Please try again later."
        
        if interaction:
            await self._send_error_response(interaction, message, ephemeral=True)
        
        logger.error(
            f"Discord HTTP error: {error}",
            extra={
                "error_type": "http_error",
                "status_code": error.status,
                **context
            }
        )
    
    async def _handle_connection_error(
        self,
        error: discord.ConnectionClosed,
        interaction: Optional[discord.Interaction],
        context: Dict[str, Any]
    ) -> None:
        """Handle Discord connection errors."""
        message = "Connection to Discord was lost. Please try again in a moment."
        
        if interaction:
            await self._send_error_response(interaction, message, ephemeral=True)
        
        logger.error(
            f"Discord connection error: {error}",
            extra={
                "error_type": "connection_error",
                "code": error.code,
                **context
            }
        )
    
    async def _handle_custom_error(
        self,
        error: DiscordBotException,
        interaction: Optional[discord.Interaction],
        context: Dict[str, Any]
    ) -> None:
        """Handle custom Discord bot errors."""
        if interaction:
            await self._send_error_response(interaction, error.user_message, ephemeral=True)
        
        logger.error(
            f"Custom bot error: {error.message}",
            extra={
                "error_type": error.error_code.lower(),
                "details": error.details,
                **context
            }
        )
    
    async def _handle_cooldown_error(
        self,
        error: discord.ApplicationCommandError,
        interaction: discord.Interaction,
        context: Dict[str, Any]
    ) -> None:
        """Handle command cooldown errors."""
        retry_after = getattr(error, 'retry_after', 60)
        message = f"This command is on cooldown. Try again in {retry_after:.2f} seconds."
        await self._send_error_response(interaction, message, ephemeral=True)
    
    async def _handle_missing_permissions_error(
        self,
        error: commands.MissingPermissions,
        interaction: discord.Interaction,
        context: Dict[str, Any]
    ) -> None:
        """Handle missing user permissions errors."""
        permissions = ", ".join(error.missing_permissions)
        message = f"You need the following permissions to use this command: {permissions}"
        await self._send_error_response(interaction, message, ephemeral=True)
    
    async def _handle_bot_missing_permissions_error(
        self,
        error: commands.BotMissingPermissions,
        interaction: discord.Interaction,
        context: Dict[str, Any]
    ) -> None:
        """Handle missing bot permissions errors."""
        permissions = ", ".join(error.missing_permissions)
        message = f"I need the following permissions to execute this command: {permissions}"
        await self._send_error_response(interaction, message, ephemeral=True)
    
    async def _handle_command_not_found_error(
        self,
        error: commands.CommandNotFound,
        interaction: discord.Interaction,
        context: Dict[str, Any]
    ) -> None:
        """Handle command not found errors."""
        message = "Command not found. Use `/help` to see available commands."
        await self._send_error_response(interaction, message, ephemeral=True)
    
    async def _send_error_response(
        self,
        interaction: discord.Interaction,
        message: str,
        ephemeral: bool = True
    ) -> None:
        """Send an error response to the user.
        
        Args:
            interaction: Discord interaction
            message: Error message to send
            ephemeral: Whether the message should be ephemeral
        """
        try:
            if interaction.response.is_done():
                await interaction.followup.send(message, ephemeral=ephemeral)
            else:
                await interaction.response.send_message(message, ephemeral=ephemeral)
        except Exception as e:
            logger.error(f"Failed to send error response: {e}")
    
    def _log_error(
        self,
        error: Exception,
        interaction: Optional[discord.Interaction],
        context: Dict[str, Any]
    ) -> None:
        """Log error with context information.
        
        Args:
            error: The exception that occurred
            interaction: Discord interaction (if applicable)
            context: Additional context information
        """
        # Prepare log context
        log_context = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            **context
        }
        
        if interaction:
            log_context.update({
                "user_id": interaction.user.id,
                "guild_id": interaction.guild_id,
                "channel_id": interaction.channel_id,
                "command": interaction.command.name if interaction.command else None
            })
        
        # Track error counts
        self._track_error(type(error).__name__)
        
        # Log with appropriate level
        if isinstance(error, (discord.Forbidden, discord.NotFound)):
            logger.warning(f"Discord error: {error}", extra=log_context)
        else:
            logger.error(f"Discord error: {error}", extra=log_context, exc_info=True)
    
    def _track_rate_limit(self, command: str, retry_after: float) -> None:
        """Track rate limit occurrences.
        
        Args:
            command: Command that was rate limited
            retry_after: Seconds to wait before retry
        """
        now = datetime.utcnow()
        if command not in self.rate_limit_tracker:
            self.rate_limit_tracker[command] = []
        
        self.rate_limit_tracker[command].append({
            "timestamp": now,
            "retry_after": retry_after
        })
        
        # Clean old entries (older than 1 hour)
        cutoff = now - timedelta(hours=1)
        self.rate_limit_tracker[command] = [
            entry for entry in self.rate_limit_tracker[command]
            if entry["timestamp"] > cutoff
        ]
    
    def _track_error(self, error_type: str) -> None:
        """Track error occurrences for monitoring.
        
        Args:
            error_type: Type of error that occurred
        """
        now = datetime.utcnow()
        
        # Reset counters every hour
        if now - self.last_error_reset > timedelta(hours=1):
            self.error_counts.clear()
            self.last_error_reset = now
        
        if error_type not in self.error_counts:
            self.error_counts[error_type] = 0
        
        self.error_counts[error_type] += 1
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics for monitoring.
        
        Returns:
            Dictionary with error statistics
        """
        return {
            "error_counts": self.error_counts.copy(),
            "rate_limit_tracker": {
                command: len(entries)
                for command, entries in self.rate_limit_tracker.items()
            },
            "last_reset": self.last_error_reset.isoformat()
        }


# Decorator for handling errors in Discord bot functions
def handle_discord_errors(
    user_message: str = "An error occurred. Please try again later.",
    log_level: str = "error",
    reraise: bool = False
):
    """Decorator to handle Discord errors in bot functions.
    
    Args:
        user_message: Message to show to users on error
        log_level: Logging level for the error
        reraise: Whether to reraise the exception after handling
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except discord.DiscordException as e:
                # Log the error
                log_func = getattr(logger, log_level, logger.error)
                log_func(f"Discord error in {func.__name__}: {e}", exc_info=True)
                
                # Try to find interaction in args
                interaction = None
                for arg in args:
                    if isinstance(arg, discord.Interaction):
                        interaction = arg
                        break
                
                # Send user message if interaction found
                if interaction:
                    try:
                        if interaction.response.is_done():
                            await interaction.followup.send(user_message, ephemeral=True)
                        else:
                            await interaction.response.send_message(user_message, ephemeral=True)
                    except Exception:
                        pass  # Ignore errors when sending error messages
                
                if reraise:
                    raise
                return None
            except Exception as e:
                # Log unexpected errors
                logger.error(f"Unexpected error in {func.__name__}: {e}", exc_info=True)
                
                if reraise:
                    raise
                return None
        return wrapper
    return decorator


# Decorator for handling rate limits with exponential backoff
def handle_rate_limits(
    max_retries: int = 3,
    base_delay: float = 1.0,
    exponential_backoff: bool = True
):
    """Decorator to handle rate limits with retry logic.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay between retries (seconds)
        exponential_backoff: Whether to use exponential backoff
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except discord.HTTPException as e:
                    if e.status == 429:  # Rate limit
                        last_error = e
                        retry_after = getattr(e, 'retry_after', base_delay)
                        
                        if attempt < max_retries:
                            if exponential_backoff:
                                delay = retry_after * (2 ** attempt)
                            else:
                                delay = retry_after
                            
                            logger.warning(
                                f"Rate limited in {func.__name__}, "
                                f"retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries + 1})"
                            )
                            await asyncio.sleep(delay)
                        else:
                            logger.error(f"Rate limit exceeded in {func.__name__} after {max_retries} retries")
                            raise RateLimitError(
                                message=f"Rate limit exceeded in {func.__name__}",
                                service="discord",
                                retry_after=retry_after
                            )
                    else:
                        raise
                except Exception as e:
                    if attempt == max_retries:
                        raise
                    last_error = e
            
            # If we get here, all retries failed
            if last_error:
                raise last_error
        return wrapper
    return decorator


# Decorator for graceful degradation
def graceful_degradation(
    fallback_value: Any = None,
    log_errors: bool = True
):
    """Decorator for graceful degradation on errors.
    
    Args:
        fallback_value: Value to return on error
        log_errors: Whether to log errors
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    logger.warning(
                        f"Graceful degradation in {func.__name__}: {e}",
                        exc_info=True
                    )
                return fallback_value
        return wrapper
    return decorator