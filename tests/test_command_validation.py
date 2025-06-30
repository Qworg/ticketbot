"""
Integration tests for command validation functionality.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import interactions

from app.commands.implementations.help import HelpCommand
from app.commands.errors import CommandValidationError
from app.permissions import Permission


class TestCommandValidation:
    """Test cases for command validation functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_ctx = Mock(spec=interactions.SlashContext)
        self.mock_ctx.author.id = "12345"
        self.mock_ctx.guild.id = "67890"
        self.mock_ctx.send = AsyncMock()
    
    @pytest.mark.asyncio
    async def test_help_command_execution(self):
        """Test help command execution."""
        command = HelpCommand()
        
        with patch('app.commands.base.get_db_session') as mock_get_db_base:
            with patch('app.database.get_db_session') as mock_get_db:
                with patch('app.commands.implementations.help.get_command_registry') as mock_registry:
                    # Mock database for base command
                    mock_db_base = Mock()
                    mock_get_db_base.return_value = mock_db_base
                    mock_user_base = Mock()
                    mock_user_base.discord_id = 12345
                    mock_user_base.role = "USER"
                    mock_user_base.id = "test-uuid"
                    mock_db_base.query.return_value.filter.return_value.first.return_value = mock_user_base
                    
                    # Mock database for help command
                    mock_db = Mock()
                    mock_get_db.return_value = mock_db
                    mock_user = Mock()
                    mock_user.discord_id = 12345
                    mock_user.role = "USER"
                    mock_user.id = "test-uuid"
                    mock_db.query.return_value.filter.return_value.first.return_value = mock_user
                    
                    # Mock registry
                    mock_reg = Mock()
                    mock_reg.commands = {"help": command}
                    mock_registry.return_value = mock_reg
                    
                    # Execute command
                    await command.execute(self.mock_ctx)
                    
                    # Verify embed was sent
                    self.mock_ctx.send.assert_called_once()
                    call_args = self.mock_ctx.send.call_args
                    assert "embed" in call_args[1]
                    assert call_args[1]["ephemeral"] is True


class TestCommandPermissions:
    """Test cases for command permission validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_ctx = Mock(spec=interactions.SlashContext)
        self.mock_ctx.author.id = "12345"
        self.mock_ctx.guild.id = "67890"
        self.mock_ctx.send = AsyncMock()
    
    @patch('app.commands.base.get_db_session')
    @patch('app.commands.base.User')
    @patch('app.commands.base.get_user_role_in_guild')
    @pytest.mark.asyncio
    async def test_admin_only_command_permission(self, mock_get_role, mock_user_model, mock_get_db):
        """Test admin-only command permission checking."""
        from app.commands.base import BaseCommand
        
        class AdminCommand(BaseCommand):
            def __init__(self):
                super().__init__(
                    name="admin_test",
                    description="Admin test command",
                    admin_only=True
                )
            
            async def _execute(self, ctx, **kwargs):
                pass
        
        command = AdminCommand()
        
        # Mock database setup
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        mock_user = Mock()
        mock_user.id = "user-uuid"
        mock_user.role = "USER"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Test with USER role
        mock_get_role.return_value = "USER"
        
        with pytest.raises(Exception):  # Should raise CommandPermissionError
            await command.can_execute(self.mock_ctx)
        
        # Test with ADMIN role
        mock_get_role.return_value = "ADMIN"
        
        # Should not raise exception
        result = await command.can_execute(self.mock_ctx)
        assert result is True
    
    @patch('app.commands.base.get_db_session')
    @patch('app.commands.base.User')
    @patch('app.commands.base.get_user_role_in_guild')
    @patch('app.commands.base.has_permission')
    @pytest.mark.asyncio
    async def test_specific_permission_command(self, mock_has_perm, mock_get_role, mock_user_model, mock_get_db):
        """Test command with specific permission requirements."""
        from app.commands.base import BaseCommand
        
        class PermissionCommand(BaseCommand):
            def __init__(self):
                super().__init__(
                    name="perm_test",
                    description="Permission test command",
                    required_permissions=["MANAGE_TICKETS"]
                )
            
            async def _execute(self, ctx, **kwargs):
                pass
        
        command = PermissionCommand()
        
        # Mock database setup
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        mock_user = Mock()
        mock_user.id = "user-uuid"
        mock_user.role = "STAFF"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        mock_get_role.return_value = "STAFF"
        
        # Test without permission
        mock_has_perm.return_value = False
        
        with pytest.raises(Exception):  # Should raise CommandPermissionError
            await command.can_execute(self.mock_ctx)
        
        # Test with permission
        mock_has_perm.return_value = True
        
        result = await command.can_execute(self.mock_ctx)
        assert result is True


class TestCommandCooldownAndRateLimit:
    """Test cases for command cooldown and rate limiting."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_ctx = Mock(spec=interactions.SlashContext)
        self.mock_ctx.author.id = "12345"
        self.mock_ctx.guild.id = "67890"
        self.mock_ctx.send = AsyncMock()
    
    @patch('app.commands.base.get_db_session')
    @patch('app.commands.base.User')
    @patch('app.commands.base.get_user_role_in_guild')
    @pytest.mark.asyncio
    async def test_command_cooldown(self, mock_get_role, mock_user_model, mock_get_db):
        """Test command cooldown functionality."""
        from app.commands.base import BaseCommand
        import time
        
        class CooldownCommand(BaseCommand):
            def __init__(self):
                super().__init__(
                    name="cooldown_test",
                    description="Cooldown test command",
                    cooldown_seconds=10.0
                )
            
            async def _execute(self, ctx, **kwargs):
                pass
        
        command = CooldownCommand()
        
        # Mock database setup
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        mock_user = Mock()
        mock_user.id = "user-uuid"
        mock_user.role = "USER"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        mock_get_role.return_value = "USER"
        
        user_id = int(self.mock_ctx.author.id)
        
        # First execution should work
        result = await command.can_execute(self.mock_ctx)
        assert result is True
        
        # Set recent cooldown
        command._cooldowns[user_id] = time.time() - 5.0  # 5 seconds ago
        
        # Second execution should fail
        with pytest.raises(Exception):  # Should raise CommandCooldownError
            await command.can_execute(self.mock_ctx)
    
    @patch('app.commands.base.get_db_session')
    @patch('app.commands.base.User')
    @patch('app.commands.base.get_user_role_in_guild')
    @pytest.mark.asyncio
    async def test_command_rate_limit(self, mock_get_role, mock_user_model, mock_get_db):
        """Test command rate limiting functionality."""
        from app.commands.base import BaseCommand
        import time
        
        class RateLimitCommand(BaseCommand):
            def __init__(self):
                super().__init__(
                    name="rate_test",
                    description="Rate limit test command",
                    rate_limit_per_minute=2
                )
            
            async def _execute(self, ctx, **kwargs):
                pass
        
        command = RateLimitCommand()
        
        # Mock database setup
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        mock_user = Mock()
        mock_user.id = "user-uuid"
        mock_user.role = "USER"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        mock_get_role.return_value = "USER"
        
        user_id = int(self.mock_ctx.author.id)
        current_time = time.time()
        
        # Add rate limit entries (2 uses in last minute)
        command._rate_limits[user_id] = [
            current_time - 30.0,  # 30 seconds ago
            current_time - 10.0   # 10 seconds ago
        ]
        
        # Should fail due to rate limit
        with pytest.raises(Exception):  # Should raise CommandRateLimitError
            await command.can_execute(self.mock_ctx)
