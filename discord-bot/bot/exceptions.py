"""Custom exceptions for the Discord Ticket Bot.

This module defines Discord-specific exception classes that provide structured
error handling throughout the Discord bot application.
"""

from typing import Any, Dict, Optional, Union
import discord


class DiscordBotException(Exception):
    """Base exception class for all Discord bot errors.
    
    Attributes:
        message: Human-readable error message
        error_code: Application-specific error code
        details: Additional error details
        user_message: User-friendly message for Discord responses
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = "DISCORD_BOT_ERROR",
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.user_message = user_message or "An error occurred. Please try again later."
        super().__init__(self.message)


class DiscordAPIError(DiscordBotException):
    """Exception raised for Discord API errors."""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        discord_error: Optional[discord.DiscordException] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if status_code:
            error_details["status_code"] = status_code
        if discord_error:
            error_details["discord_error"] = str(discord_error)
            error_details["discord_error_type"] = type(discord_error).__name__
            
        # Determine user message based on error type
        user_message = "A Discord API error occurred. Please try again later."
        if isinstance(discord_error, discord.Forbidden):
            user_message = "I don't have permission to perform this action."
        elif isinstance(discord_error, discord.NotFound):
            user_message = "The requested resource was not found."
        elif isinstance(discord_error, discord.HTTPException) and status_code == 429:
            user_message = "Rate limit exceeded. Please wait a moment and try again."
            
        super().__init__(
            message=message,
            error_code="DISCORD_API_ERROR",
            details=error_details,
            user_message=user_message
        )


class PermissionError(DiscordBotException):
    """Exception raised for permission-related errors."""
    
    def __init__(
        self,
        message: str,
        required_permission: Optional[str] = None,
        user_id: Optional[int] = None,
        guild_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if required_permission:
            error_details["required_permission"] = required_permission
        if user_id:
            error_details["user_id"] = user_id
        if guild_id:
            error_details["guild_id"] = guild_id
            
        super().__init__(
            message=message,
            error_code="PERMISSION_ERROR",
            details=error_details,
            user_message="You don't have permission to perform this action."
        )


class ChannelError(DiscordBotException):
    """Exception raised for channel-related errors."""
    
    def __init__(
        self,
        message: str,
        channel_id: Optional[int] = None,
        channel_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if channel_id:
            error_details["channel_id"] = channel_id
        if channel_type:
            error_details["channel_type"] = channel_type
            
        super().__init__(
            message=message,
            error_code="CHANNEL_ERROR",
            details=error_details,
            user_message="There was an issue with the channel. Please try again."
        )


class TicketError(DiscordBotException):
    """Exception raised for ticket-related errors."""
    
    def __init__(
        self,
        message: str,
        ticket_id: Optional[str] = None,
        channel_id: Optional[int] = None,
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if ticket_id:
            error_details["ticket_id"] = ticket_id
        if channel_id:
            error_details["channel_id"] = channel_id
        if operation:
            error_details["operation"] = operation
            
        super().__init__(
            message=message,
            error_code="TICKET_ERROR",
            details=error_details,
            user_message="There was an issue with the ticket operation. Please try again."
        )


class BackendConnectionError(DiscordBotException):
    """Exception raised for backend API connection errors."""
    
    def __init__(
        self,
        message: str,
        endpoint: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if endpoint:
            error_details["endpoint"] = endpoint
        if status_code:
            error_details["status_code"] = status_code
            
        super().__init__(
            message=message,
            error_code="BACKEND_CONNECTION_ERROR",
            details=error_details,
            user_message="Unable to connect to the backend service. Please try again later."
        )


class RateLimitError(DiscordBotException):
    """Exception raised when rate limits are exceeded."""
    
    def __init__(
        self,
        message: str,
        service: str,
        retry_after: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        error_details["service"] = service
        if retry_after:
            error_details["retry_after"] = retry_after
            
        user_message = "Rate limit exceeded. Please wait a moment and try again."
        if retry_after:
            user_message = f"Rate limit exceeded. Please wait {retry_after:.1f} seconds and try again."
            
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_ERROR",
            details=error_details,
            user_message=user_message
        )


class ConfigurationError(DiscordBotException):
    """Exception raised for configuration errors."""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if config_key:
            error_details["config_key"] = config_key
            
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            details=error_details,
            user_message="The bot is not properly configured. Please contact an administrator."
        )


class CommandError(DiscordBotException):
    """Exception raised for command execution errors."""
    
    def __init__(
        self,
        message: str,
        command_name: Optional[str] = None,
        user_id: Optional[int] = None,
        guild_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if command_name:
            error_details["command_name"] = command_name
        if user_id:
            error_details["user_id"] = user_id
        if guild_id:
            error_details["guild_id"] = guild_id
            
        super().__init__(
            message=message,
            error_code="COMMAND_ERROR",
            details=error_details,
            user_message="There was an error executing the command. Please try again."
        )


class ValidationError(DiscordBotException):
    """Exception raised for input validation errors."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if field:
            error_details["field"] = field
        if value is not None:
            error_details["value"] = str(value)
            
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details=error_details,
            user_message="Invalid input provided. Please check your input and try again."
        )