"""
Unit tests for command registration system.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
import interactions

from app.commands.registry import CommandRegistry, get_command_registry
from app.commands.base import BaseCommand
from app.commands.errors import CommandError, CommandCooldownError, CommandPermissionError


class TestCommand(BaseCommand):
    """Test command for unit testing."""
    
    def __init__(self, **kwargs):
        super().__init__(
            name="test",
            description="Test command",
            **kwargs
        )
        self.executed = False
        self.execute_kwargs = {}
    
    async def _execute(self, ctx, **kwargs):
        self.executed = True
        self.execute_kwargs = kwargs


class TestCommandRegistry:
    """Test cases for CommandRegistry."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_bot = Mock(spec=interactions.Client)
        self.mock_bot.synchronise_interactions = AsyncMock()
        self.registry = CommandRegistry(self.mock_bot)
    
    def test_register_command(self):
        """Test command registration."""
        command = TestCommand()
        self.registry.register_command(command)
        
        assert "test" in self.registry.commands
        assert self.registry.get_command("test") is command
    
    def test_register_duplicate_command(self):
        """Test registering duplicate command name."""
        command1 = TestCommand()
        command2 = TestCommand()
        
        self.registry.register_command(command1)
        self.registry.register_command(command2)  # Should overwrite
        
        assert self.registry.get_command("test") is command2
    
    def test_list_commands(self):
        """Test listing registered commands."""
        command1 = TestCommand()
        command2 = TestCommand()
        command2.name = "test2"
        
        self.registry.register_command(command1)
        self.registry.register_command(command2)
        
        commands = self.registry.list_commands()
        assert "test" in commands
        assert "test2" in commands
        assert len(commands) == 2
    
    @pytest.mark.asyncio
    async def test_setup_slash_commands(self):
        """Test slash command setup."""
        command = TestCommand()
        self.registry.register_command(command)
        
        await self.registry.setup_slash_commands()
        
        self.mock_bot.synchronise_interactions.assert_called_once()
        assert self.registry._registered is True
    
    @pytest.mark.asyncio
    async def test_setup_slash_commands_already_registered(self):
        """Test that setup doesn't run twice."""
        self.registry._registered = True
        
        await self.registry.setup_slash_commands()
        
        self.mock_bot.synchronise_interactions.assert_not_called()
    
    def test_get_command_stats(self):
        """Test getting command statistics."""
        command = TestCommand(cooldown_seconds=5.0, staff_only=True)
        self.registry.register_command(command)
        
        stats = self.registry.get_command_stats()
        
        assert stats["total_commands"] == 1
        assert stats["registered"] is False
        assert "test" in stats["commands"]
        assert stats["commands"]["test"]["cooldown_seconds"] == 5.0
        assert stats["commands"]["test"]["staff_only"] is True


class TestBaseCommand:
    """Test cases for BaseCommand."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_ctx = Mock(spec=interactions.SlashContext)
        self.mock_ctx.author.id = "12345"
        self.mock_ctx.guild.id = "67890"
        self.mock_ctx.send = AsyncMock()
    
    @pytest.mark.asyncio
    async def test_execute_successful(self):
        """Test successful command execution."""
        command = TestCommand()
        
        with patch.object(command, 'can_execute', return_value=True):
            await command.execute(self.mock_ctx, arg1="value1")
        
        assert command.executed is True
        assert command.execute_kwargs == {"arg1": "value1"}
    
    @pytest.mark.asyncio
    async def test_execute_permission_error(self):
        """Test command execution with permission error."""
        command = TestCommand()
        
        with patch.object(command, 'can_execute', side_effect=CommandPermissionError("test permission")):
            await command.execute(self.mock_ctx)
        
        assert command.executed is False
        self.mock_ctx.send.assert_called_once()
        call_args = self.mock_ctx.send.call_args
        assert "❌" in call_args[0][0]
        assert call_args[1]["ephemeral"] is True
    
    @pytest.mark.asyncio
    async def test_execute_cooldown_error(self):
        """Test command execution with cooldown error."""
        command = TestCommand()
        
        with patch.object(command, 'can_execute', side_effect=CommandCooldownError(5.0)):
            await command.execute(self.mock_ctx)
        
        assert command.executed is False
        self.mock_ctx.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_unexpected_error(self):
        """Test command execution with unexpected error."""
        command = TestCommand()
        
        with patch.object(command, 'can_execute', return_value=True):
            with patch.object(command, '_execute', side_effect=Exception("Test error")):
                await command.execute(self.mock_ctx)
        
        self.mock_ctx.send.assert_called_once()
        call_args = self.mock_ctx.send.call_args
        assert "unexpected error" in call_args[0][0].lower()
    
    def test_cooldown_tracking(self):
        """Test cooldown tracking functionality."""
        command = TestCommand(cooldown_seconds=10.0)
        user_id = 12345
        
        # Simulate command use
        import time
        current_time = time.time()
        command._cooldowns[user_id] = current_time - 5.0  # Used 5 seconds ago
        
        # Should be on cooldown
        with pytest.raises(CommandCooldownError):
            asyncio.run(command.can_execute(self.mock_ctx))
    
    @patch('app.commands.base.get_db_session')
    @patch('app.commands.base.User')
    def test_permission_checking_staff_only(self, mock_user_model, mock_get_db):
        """Test staff-only permission checking."""
        command = TestCommand(staff_only=True)
        
        # Mock database session and user
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        mock_user = Mock()
        mock_user.id = "user-uuid"
        mock_user.role = "USER"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        with patch('app.commands.base.get_user_role_in_guild', return_value="USER"):
            with pytest.raises(CommandPermissionError):
                asyncio.run(command.can_execute(self.mock_ctx))
    
    def test_cleanup_tracking(self):
        """Test cleanup of old tracking data."""
        command = TestCommand(cooldown_seconds=10.0, rate_limit_per_minute=5)
        
        import time
        current_time = time.time()
        
        # Add old cooldown data
        command._cooldowns[12345] = current_time - 20.0  # Expired
        command._cooldowns[67890] = current_time - 5.0   # Not expired
        
        # Add old rate limit data
        command._rate_limits[12345] = [current_time - 70.0]  # Expired
        command._rate_limits[67890] = [current_time - 30.0]  # Not expired
        
        command.cleanup_tracking()
        
        # Check that expired data was removed
        assert 12345 not in command._cooldowns
        assert 67890 in command._cooldowns
        assert 12345 not in command._rate_limits
        assert 67890 in command._rate_limits


def test_get_command_registry():
    """Test global registry function."""
    # Reset global registry state before test
    import app.commands.registry
    app.commands.registry._registry = None
    
    mock_bot = Mock(spec=interactions.Client)
    
    # First call should require bot
    with pytest.raises(ValueError):
        get_command_registry()
    
    # Second call should work with bot
    registry1 = get_command_registry(mock_bot)
    assert isinstance(registry1, CommandRegistry)
    
    # Third call should return same instance
    registry2 = get_command_registry()
    assert registry1 is registry2
