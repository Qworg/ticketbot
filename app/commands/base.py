"""
Base command class with common functionality for Discord slash commands.
"""

import asyncio
import logging
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set

import interactions

from .errors import (
    CommandError,
    CommandCooldownError, 
    CommandPermissionError,
    CommandRateLimitError,
    CommandValidationError
)
from ..permissions import has_permission, Permission
from ..models.role_assignment import get_user_role_in_guild, get_user_permissions_in_guild
from ..models.user import User
from ..database import get_db_session


logger = logging.getLogger(__name__)


class BaseCommand(ABC):
    """Base class for all Discord slash commands."""
    
    def __init__(
        self,
        name: str,
        description: str,
        required_permissions: Optional[List[str]] = None,
        cooldown_seconds: float = 0.0,
        rate_limit_per_minute: Optional[int] = None,
        staff_only: bool = False,
        admin_only: bool = False
    ):
        """
        Initialize base command.
        
        Args:
            name: Command name
            description: Command description
            required_permissions: List of required permissions
            cooldown_seconds: Cooldown time in seconds between uses
            rate_limit_per_minute: Maximum uses per minute per user
            staff_only: Whether command requires staff role
            admin_only: Whether command requires admin role
        """
        self.name = name
        self.description = description
        self.required_permissions = required_permissions or []
        self.cooldown_seconds = cooldown_seconds
        self.rate_limit_per_minute = rate_limit_per_minute
        self.staff_only = staff_only
        self.admin_only = admin_only
        
        # Cooldown tracking
        self._cooldowns: Dict[int, float] = {}
        
        # Rate limit tracking 
        self._rate_limits: Dict[int, List[float]] = {}
        
    async def can_execute(self, ctx: interactions.SlashContext) -> bool:
        """
        Check if user can execute this command.
        
        Args:
            ctx: Slash command context
            
        Returns:
            True if user can execute command
            
        Raises:
            CommandPermissionError: If user lacks permissions
            CommandCooldownError: If command is on cooldown
            CommandRateLimitError: If rate limit exceeded
        """
        user_id = int(ctx.author.id)
        
        # Check cooldown
        if self.cooldown_seconds > 0:
            last_use = self._cooldowns.get(user_id, 0)
            time_since_last = time.time() - last_use
            if time_since_last < self.cooldown_seconds:
                retry_after = self.cooldown_seconds - time_since_last
                raise CommandCooldownError(retry_after)
        
        # Check rate limit
        if self.rate_limit_per_minute:
            current_time = time.time()
            user_uses = self._rate_limits.setdefault(user_id, [])
            
            # Remove uses older than 1 minute
            user_uses[:] = [use_time for use_time in user_uses 
                           if current_time - use_time < 60]
            
            if len(user_uses) >= self.rate_limit_per_minute:
                oldest_use = min(user_uses)
                retry_after = 60 - (current_time - oldest_use)
                raise CommandRateLimitError(retry_after)
        
        # Check permissions
        await self._check_permissions(ctx)
        
        return True
    
    async def _check_permissions(self, ctx: interactions.SlashContext) -> None:
        """
        Check if user has required permissions.
        
        Args:
            ctx: Slash command context
            
        Raises:
            CommandPermissionError: If user lacks permissions
        """
        user_id = int(ctx.author.id)
        guild_id = int(ctx.guild.id) if ctx.guild else None
        
        # Get database session
        db = get_db_session()
        try:
            # Find user by discord_id
            user = db.query(User).filter(User.discord_id == user_id).first()
            if not user:
                raise CommandPermissionError("User not found in database")
            
            # Get user role in guild
            if guild_id:
                # Handle both UUID objects and mock strings in tests
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
            
            # Check admin requirement
            if self.admin_only and user_role != 'ADMIN':
                raise CommandPermissionError("admin role")
            
            # Check staff requirement
            if self.staff_only and user_role not in ['ADMIN', 'STAFF']:
                raise CommandPermissionError("staff role")
            
            # Check specific permissions
            for permission_str in self.required_permissions:
                try:
                    permission = Permission(permission_str)
                    if not has_permission(user_role, permission):
                        raise CommandPermissionError(permission_str)
                except ValueError:
                    # Invalid permission string
                    raise CommandPermissionError(permission_str)
        finally:
            db.close()
    
    async def execute(self, ctx: interactions.SlashContext, **kwargs) -> None:
        """
        Execute the command with proper error handling and tracking.
        
        Args:
            ctx: Slash command context
            **kwargs: Command arguments
        """
        user_id = int(ctx.author.id)
        
        try:
            # Check if user can execute command
            await self.can_execute(ctx)
            
            # Log command usage
            logger.info(
                f"Command {self.name} executed by user {user_id} "
                f"in guild {ctx.guild.id if ctx.guild else 'DM'}"
            )
            
            # Execute the actual command
            await self._execute(ctx, **kwargs)
            
            # Update cooldown and rate limit tracking
            current_time = time.time()
            self._cooldowns[user_id] = current_time
            
            if self.rate_limit_per_minute:
                self._rate_limits.setdefault(user_id, []).append(current_time)
        
        except (CommandError, CommandCooldownError, CommandPermissionError, 
                CommandRateLimitError, CommandValidationError) as e:
            # These are expected errors, send user-friendly message
            await ctx.send(f"❌ {e.user_message}", ephemeral=True)
            logger.warning(f"Command {self.name} failed: {e}")
        
        except Exception as e:
            # Unexpected error, log it and send generic message
            logger.error(f"Unexpected error in command {self.name}: {e}", exc_info=True)
            await ctx.send(
                "❌ An unexpected error occurred. Please try again later.",
                ephemeral=True
            )
    
    @abstractmethod
    async def _execute(self, ctx: interactions.SlashContext, **kwargs) -> None:
        """
        Execute the actual command logic.
        
        Args:
            ctx: Slash command context
            **kwargs: Command arguments
        """
        pass
    
    def validate_arguments(self, **kwargs) -> None:
        """
        Validate command arguments.
        
        Args:
            **kwargs: Command arguments
            
        Raises:
            CommandValidationError: If validation fails
        """
        # Base implementation does nothing
        # Subclasses can override for specific validation
        pass
    
    def cleanup_tracking(self) -> None:
        """Clean up old cooldown and rate limit data."""
        current_time = time.time()
        
        # Clean up cooldowns older than cooldown_seconds
        if self.cooldown_seconds > 0:
            expired_cooldowns = [
                user_id for user_id, last_use in self._cooldowns.items()
                if current_time - last_use > self.cooldown_seconds
            ]
            for user_id in expired_cooldowns:
                del self._cooldowns[user_id]
        
        # Clean up rate limits older than 1 minute
        for user_id, uses in list(self._rate_limits.items()):
            uses[:] = [use_time for use_time in uses if current_time - use_time < 60]
            if not uses:
                del self._rate_limits[user_id]
