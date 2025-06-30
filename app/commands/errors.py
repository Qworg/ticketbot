"""
Custom exceptions for Discord bot commands.
"""


class CommandError(Exception):
    """Base exception for command-related errors."""
    
    def __init__(self, message: str, user_message: str | None = None):
        """
        Initialize command error.
        
        Args:
            message: Technical error message for logging
            user_message: User-friendly error message for Discord response
        """
        super().__init__(message)
        self.user_message = user_message or message


class CommandCooldownError(CommandError):
    """Exception raised when a command is on cooldown."""
    
    def __init__(self, retry_after: float):
        """
        Initialize cooldown error.
        
        Args:
            retry_after: Seconds until command can be used again
        """
        self.retry_after = retry_after
        message = f"Command is on cooldown. Try again in {retry_after:.1f} seconds."
        super().__init__(message, message)


class CommandPermissionError(CommandError):
    """Exception raised when user lacks permission for a command."""
    
    def __init__(self, required_permission: str | None = None):
        """
        Initialize permission error.
        
        Args:
            required_permission: The permission that was required
        """
        self.required_permission = required_permission
        if required_permission:
            message = f"You don't have the required permission: {required_permission}"
        else:
            message = "You don't have permission to use this command."
        super().__init__(message, message)


class CommandValidationError(CommandError):
    """Exception raised when command arguments are invalid."""
    
    def __init__(self, field: str, message: str):
        """
        Initialize validation error.
        
        Args:
            field: The field that failed validation
            message: Validation error message
        """
        self.field = field
        super().__init__(f"Validation error for {field}: {message}", message)


class CommandRateLimitError(CommandError):
    """Exception raised when command rate limit is exceeded."""
    
    def __init__(self, retry_after: float):
        """
        Initialize rate limit error.
        
        Args:
            retry_after: Seconds until rate limit resets
        """
        self.retry_after = retry_after
        message = f"Rate limit exceeded. Try again in {retry_after:.1f} seconds."
        super().__init__(message, message)
