"""
Unit tests for the ticket command implementation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import interactions

from app.commands.implementations.ticket import TicketCommand
from app.commands.errors import CommandValidationError


class TestTicketCommand:
    """Test cases for the TicketCommand class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.command = TicketCommand()
    
    def test_command_initialization(self):
        """Test that the command is initialized correctly."""
        assert self.command.name == "ticket"
        assert self.command.description == "Create a new support ticket"
        assert self.command.cooldown_seconds == 30.0
        assert self.command.rate_limit_per_minute == 2
        assert len(self.command.options) == 1
        assert str(self.command.options[0].name) == "reason"
    
    def test_validate_arguments_valid(self):
        """Test argument validation with valid inputs."""
        # Should not raise any exception
        self.command.validate_arguments(reason="This is a valid ticket reason")
    
    def test_validate_arguments_empty_reason(self):
        """Test argument validation with empty reason."""
        with pytest.raises(CommandValidationError) as exc_info:
            self.command.validate_arguments(reason="")
        assert "required" in str(exc_info.value)
    
    def test_validate_arguments_short_reason(self):
        """Test argument validation with too short reason."""
        with pytest.raises(CommandValidationError) as exc_info:
            self.command.validate_arguments(reason="hi")
        assert "at least 5 characters" in str(exc_info.value)
    
    def test_validate_arguments_long_reason(self):
        """Test argument validation with too long reason."""
        long_reason = "x" * 501
        with pytest.raises(CommandValidationError) as exc_info:
            self.command.validate_arguments(reason=long_reason)
        assert "not exceed 500 characters" in str(exc_info.value)
    
    def test_generate_channel_name(self):
        """Test channel name generation."""
        # Mock user
        mock_user = MagicMock()
        mock_user.username = "TestUser123!"
        mock_user.id = 1234567890123456789
        
        # Test channel name generation
        import asyncio
        channel_name = asyncio.run(self.command._generate_channel_name(mock_user))
        
        # Should sanitize username and include user ID
        assert channel_name.startswith("ticket-")
        assert "testuser12" in channel_name  # Truncated to 10 chars
        assert "6789" in channel_name  # Last 4 digits
    
    @patch('app.commands.implementations.ticket.get_db_session')
    @patch('app.commands.implementations.ticket.get_user_by_discord_id')
    @patch('app.commands.implementations.ticket.create_user')
    def test_get_or_create_user_existing(self, mock_create_user, mock_get_user, mock_db_session):
        """Test getting an existing user."""
        # Mock database session
        mock_db = MagicMock()
        mock_db_session.return_value = mock_db
        
        # Mock existing user
        mock_user = MagicMock()
        mock_get_user.return_value = mock_user
        
        # Mock Discord member
        mock_member = MagicMock()
        mock_member.username = "TestUser"
        
        # Test getting existing user
        import asyncio
        result = asyncio.run(self.command._get_or_create_user(123456789, mock_member))
        
        assert result == mock_user
        mock_get_user.assert_called_once_with(mock_db, 123456789)
        mock_create_user.assert_not_called()
    
    @patch('app.commands.implementations.ticket.get_db_session')
    @patch('app.commands.implementations.ticket.get_user_by_discord_id')
    @patch('app.commands.implementations.ticket.create_user')
    def test_get_or_create_user_new(self, mock_create_user, mock_get_user, mock_db_session):
        """Test creating a new user."""
        # Mock database session
        mock_db = MagicMock()
        mock_db_session.return_value = mock_db
        
        # Mock no existing user
        mock_get_user.return_value = None
        
        # Mock new user creation
        mock_new_user = MagicMock()
        mock_create_user.return_value = mock_new_user
        
        # Mock Discord member
        mock_member = MagicMock()
        mock_member.username = "NewUser"
        
        # Test creating new user
        import asyncio
        result = asyncio.run(self.command._get_or_create_user(987654321, mock_member))
        
        assert result == mock_new_user
        mock_get_user.assert_called_once_with(mock_db, 987654321)
        mock_create_user.assert_called_once_with(
            db=mock_db,
            discord_id=987654321,
            username="NewUser",
            role="USER"
        )
    
    @pytest.mark.asyncio
    async def test_calculate_channel_permissions_basic(self):
        """Test basic channel permission calculation."""
        # Mock guild and user
        mock_guild = MagicMock()
        mock_guild.id = 123456789
        mock_guild.default_role = MagicMock()
        mock_guild.default_role.id = 111111111
        mock_guild.me = MagicMock()
        mock_guild.me.id = 222222222
        mock_guild.roles = []
        
        mock_user = MagicMock()
        mock_user.id = 333333333
        
        # Mock database session
        with patch('app.commands.implementations.ticket.get_db_session') as mock_db:
            mock_session = MagicMock()
            mock_db.return_value = mock_session
            
            # Mock database functions
            with patch('app.commands.implementations.ticket.get_guild_staff_role_ids', return_value=[]):
                with patch('app.commands.implementations.ticket.get_guild_admin_role_ids', return_value=[]):
                    overwrites = await self.command._calculate_channel_permissions(mock_guild, mock_user)
        
        # Should have at least 3 overwrites: @everyone (deny), user (allow), bot (allow)
        assert len(overwrites) >= 3
        
        # Check @everyone deny permissions
        everyone_overwrite = next((ow for ow in overwrites if ow.id == mock_guild.default_role.id), None)
        assert everyone_overwrite is not None
        assert everyone_overwrite.type == interactions.OverwriteType.ROLE
        assert interactions.Permissions.VIEW_CHANNEL in everyone_overwrite.deny
        
        # Check user allow permissions
        user_overwrite = next((ow for ow in overwrites if ow.id == mock_user.id), None)
        assert user_overwrite is not None
        assert user_overwrite.type == interactions.OverwriteType.MEMBER
        assert interactions.Permissions.VIEW_CHANNEL in user_overwrite.allow
        
        # Check bot allow permissions
        bot_overwrite = next((ow for ow in overwrites if ow.id == mock_guild.me.id), None)
        assert bot_overwrite is not None
        assert bot_overwrite.type == interactions.OverwriteType.MEMBER
        assert interactions.Permissions.MANAGE_CHANNELS in bot_overwrite.allow
    
    @pytest.mark.asyncio
    async def test_calculate_channel_permissions_with_configured_staff(self):
        """Test channel permission calculation with configured staff roles."""
        # Mock guild with staff roles
        mock_guild = MagicMock()
        mock_guild.id = 123456789
        mock_guild.default_role = MagicMock()
        mock_guild.default_role.id = 111111111
        mock_guild.me = MagicMock()
        mock_guild.me.id = 222222222
        
        # Create mock staff role
        staff_role = MagicMock()
        staff_role.id = 444444444
        staff_role.name = "Support Staff"
        
        admin_role = MagicMock()
        admin_role.id = 555555555
        admin_role.name = "Admin"
        
        mock_guild.roles = [staff_role, admin_role]
        
        mock_user = MagicMock()
        mock_user.id = 333333333
        
        # Mock database session
        with patch('app.commands.implementations.ticket.get_db_session') as mock_db:
            mock_session = MagicMock()
            mock_db.return_value = mock_session
            
            # Mock database functions to return configured role IDs
            with patch('app.commands.implementations.ticket.get_guild_staff_role_ids', return_value=[444444444]):
                with patch('app.commands.implementations.ticket.get_guild_admin_role_ids', return_value=[555555555]):
                    overwrites = await self.command._calculate_channel_permissions(mock_guild, mock_user)
        
        # Should have overwrites for staff and admin roles
        staff_overwrite = next((ow for ow in overwrites if ow.id == staff_role.id), None)
        assert staff_overwrite is not None
        assert staff_overwrite.type == interactions.OverwriteType.ROLE
        assert interactions.Permissions.VIEW_CHANNEL in staff_overwrite.allow
        
        admin_overwrite = next((ow for ow in overwrites if ow.id == admin_role.id), None)
        assert admin_overwrite is not None
        assert admin_overwrite.type == interactions.OverwriteType.ROLE
        assert interactions.Permissions.VIEW_CHANNEL in admin_overwrite.allow
        assert interactions.Permissions.MANAGE_CHANNELS in admin_overwrite.allow
    
    @pytest.mark.asyncio
    async def test_calculate_channel_permissions_fallback_role_names(self):
        """Test channel permission calculation with fallback role names."""
        # Mock guild with common staff role names
        mock_guild = MagicMock()
        mock_guild.id = 123456789
        mock_guild.default_role = MagicMock()
        mock_guild.default_role.id = 111111111
        mock_guild.me = MagicMock()
        mock_guild.me.id = 222222222
        
        # Create mock roles with common names
        staff_role = MagicMock()
        staff_role.id = 444444444
        staff_role.name = "Staff"
        
        admin_role = MagicMock()
        admin_role.id = 555555555
        admin_role.name = "Administrator"
        
        other_role = MagicMock()
        other_role.id = 666666666
        other_role.name = "Member"
        
        mock_guild.roles = [staff_role, admin_role, other_role]
        
        mock_user = MagicMock()
        mock_user.id = 333333333
        
        # Mock database session
        with patch('app.commands.implementations.ticket.get_db_session') as mock_db:
            mock_session = MagicMock()
            mock_db.return_value = mock_session
            
            # Mock database functions to return empty lists (no configured roles)
            with patch('app.commands.implementations.ticket.get_guild_staff_role_ids', return_value=[]):
                with patch('app.commands.implementations.ticket.get_guild_admin_role_ids', return_value=[]):
                    overwrites = await self.command._calculate_channel_permissions(mock_guild, mock_user)
        
        # Should have overwrites for staff and admin roles based on names
        staff_overwrite = next((ow for ow in overwrites if ow.id == staff_role.id), None)
        assert staff_overwrite is not None
        
        admin_overwrite = next((ow for ow in overwrites if ow.id == admin_role.id), None)
        assert admin_overwrite is not None
        
        # Should NOT have overwrite for "Member" role
        member_overwrite = next((ow for ow in overwrites if ow.id == other_role.id), None)
        assert member_overwrite is None
    
    @pytest.mark.asyncio
    async def test_calculate_channel_permissions_database_error(self):
        """Test channel permission calculation when database query fails."""
        mock_guild = MagicMock()
        mock_guild.id = 123456789
        mock_guild.default_role = MagicMock()
        mock_guild.default_role.id = 111111111
        mock_guild.me = MagicMock()
        mock_guild.me.id = 222222222
        
        # Create mock role with common name for fallback
        staff_role = MagicMock()
        staff_role.id = 444444444
        staff_role.name = "Staff"
        
        mock_guild.roles = [staff_role]
        
        mock_user = MagicMock()
        mock_user.id = 333333333
        
        # Mock database session to raise an exception
        with patch('app.commands.implementations.ticket.get_db_session') as mock_db:
            mock_session = MagicMock()
            mock_db.return_value = mock_session
            
            # Mock database functions to raise an exception
            with patch('app.commands.implementations.ticket.get_guild_staff_role_ids', side_effect=Exception("Database error")):
                overwrites = await self.command._calculate_channel_permissions(mock_guild, mock_user)
        
        # Should still work with fallback behavior
        staff_overwrite = next((ow for ow in overwrites if ow.id == staff_role.id), None)
        assert staff_overwrite is not None
    
    @pytest.mark.asyncio
    async def test_update_channel_permissions_for_user_grant(self):
        """Test granting channel permissions to a user."""
        mock_channel = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = 123456789
        mock_user.username = "testuser"
        
        result = await self.command.update_channel_permissions_for_user(
            mock_channel, mock_user, grant_access=True
        )
        
        assert result is True
        mock_channel.edit_permission.assert_called_once()
        
        # Check the overwrite parameter
        call_args = mock_channel.edit_permission.call_args
        overwrite = call_args.kwargs['overwrite']
        assert overwrite.id == mock_user.id
        assert overwrite.type == interactions.OverwriteType.MEMBER
        assert interactions.Permissions.VIEW_CHANNEL in overwrite.allow
    
    @pytest.mark.asyncio
    async def test_update_channel_permissions_for_user_revoke(self):
        """Test revoking channel permissions from a user."""
        mock_channel = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = 123456789
        mock_user.username = "testuser"
        
        result = await self.command.update_channel_permissions_for_user(
            mock_channel, mock_user, grant_access=False
        )
        
        assert result is True
        mock_channel.edit_permission.assert_called_once()
        
        # Check the overwrite parameter
        call_args = mock_channel.edit_permission.call_args
        overwrite = call_args.kwargs['overwrite']
        assert overwrite.id == mock_user.id
        assert interactions.Permissions.VIEW_CHANNEL in overwrite.deny
    
    @pytest.mark.asyncio
    async def test_update_channel_permissions_for_role_grant_admin(self):
        """Test granting admin channel permissions to a role."""
        mock_channel = AsyncMock()
        mock_role = MagicMock()
        mock_role.id = 123456789
        mock_role.name = "Admin"
        
        result = await self.command.update_channel_permissions_for_role(
            mock_channel, mock_role, grant_access=True, is_admin=True
        )
        
        assert result is True
        mock_channel.edit_permission.assert_called_once()
        
        # Check the overwrite parameter
        call_args = mock_channel.edit_permission.call_args
        overwrite = call_args.kwargs['overwrite']
        assert overwrite.id == mock_role.id
        assert overwrite.type == interactions.OverwriteType.ROLE
        assert interactions.Permissions.MANAGE_CHANNELS in overwrite.allow
    
    @pytest.mark.asyncio
    async def test_update_channel_permissions_for_role_grant_staff(self):
        """Test granting staff channel permissions to a role."""
        mock_channel = AsyncMock()
        mock_role = MagicMock()
        mock_role.id = 123456789
        mock_role.name = "Staff"
        
        result = await self.command.update_channel_permissions_for_role(
            mock_channel, mock_role, grant_access=True, is_admin=False
        )
        
        assert result is True
        mock_channel.edit_permission.assert_called_once()
        
        # Check the overwrite parameter
        call_args = mock_channel.edit_permission.call_args
        overwrite = call_args.kwargs['overwrite']
        assert overwrite.id == mock_role.id
        assert overwrite.type == interactions.OverwriteType.ROLE
        assert interactions.Permissions.VIEW_CHANNEL in overwrite.allow
        # Staff roles should NOT have manage permissions
        assert interactions.Permissions.MANAGE_CHANNELS not in overwrite.allow


if __name__ == "__main__":
    pytest.main([__file__])
