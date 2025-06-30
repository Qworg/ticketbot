"""
Integration tests for ticket channel permission setup.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import interactions

from app.commands.implementations.ticket import TicketCommand
from app.models.guild import Guild, create_or_update_guild, get_guild_staff_role_ids, get_guild_admin_role_ids
from app.database import get_db_session


class TestTicketPermissionIntegration:
    """Integration tests for ticket channel permission setup."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.command = TicketCommand()
    
    @pytest.mark.asyncio
    async def test_permission_setup_with_database_guild_config(self):
        """Test complete permission setup flow with database guild configuration."""
        # Mock database session
        mock_db = MagicMock()
        
        # Create test guild configuration
        guild_id = 123456789012345678
        staff_role_id = 111111111111111111
        admin_role_id = 222222222222222222
        
        # Mock guild in database
        mock_guild_config = Guild(
            id=guild_id,
            name="Test Guild",
            staff_role_ids=[staff_role_id],
            admin_role_ids=[admin_role_id],
            ticket_category_name="🎫 Support"
        )
        
        # Mock Discord guild
        mock_discord_guild = MagicMock()
        mock_discord_guild.id = guild_id
        mock_discord_guild.name = "Test Guild"
        mock_discord_guild.default_role = MagicMock()
        mock_discord_guild.default_role.id = 999999999999999999
        mock_discord_guild.me = MagicMock()
        mock_discord_guild.me.id = 888888888888888888
        
        # Mock roles
        staff_role = MagicMock()
        staff_role.id = staff_role_id
        staff_role.name = "Support Staff"
        
        admin_role = MagicMock()
        admin_role.id = admin_role_id
        admin_role.name = "Administrator"
        
        other_role = MagicMock()
        other_role.id = 333333333333333333
        other_role.name = "Member"
        
        mock_discord_guild.roles = [staff_role, admin_role, other_role]
        
        # Mock user
        mock_user = MagicMock()
        mock_user.id = 444444444444444444
        mock_user.username = "testuser"
        
        with patch('app.commands.implementations.ticket.get_db_session', return_value=mock_db):
            with patch('app.commands.implementations.ticket.get_guild_staff_role_ids', return_value=[staff_role_id]):
                with patch('app.commands.implementations.ticket.get_guild_admin_role_ids', return_value=[admin_role_id]):
                    overwrites = await self.command._calculate_channel_permissions(mock_discord_guild, mock_user)
        
        # Verify permission overwrites
        assert len(overwrites) >= 5  # @everyone, user, bot, staff, admin
        
        # Check staff role permissions
        staff_overwrite = next((ow for ow in overwrites if ow.id == staff_role_id), None)
        assert staff_overwrite is not None
        assert staff_overwrite.type == interactions.OverwriteType.ROLE
        assert interactions.Permissions.VIEW_CHANNEL in staff_overwrite.allow
        assert interactions.Permissions.SEND_MESSAGES in staff_overwrite.allow
        assert interactions.Permissions.READ_MESSAGE_HISTORY in staff_overwrite.allow
        # Staff should NOT have manage permissions
        assert interactions.Permissions.MANAGE_CHANNELS not in staff_overwrite.allow
        
        # Check admin role permissions
        admin_overwrite = next((ow for ow in overwrites if ow.id == admin_role_id), None)
        assert admin_overwrite is not None
        assert admin_overwrite.type == interactions.OverwriteType.ROLE
        assert interactions.Permissions.VIEW_CHANNEL in admin_overwrite.allow
        assert interactions.Permissions.SEND_MESSAGES in admin_overwrite.allow
        assert interactions.Permissions.READ_MESSAGE_HISTORY in admin_overwrite.allow
        # Admin should have manage permissions
        assert interactions.Permissions.MANAGE_CHANNELS in admin_overwrite.allow
        assert interactions.Permissions.MANAGE_MESSAGES in admin_overwrite.allow
        
        # Verify "Member" role does not get permissions
        member_overwrite = next((ow for ow in overwrites if ow.id == 333333333333333333), None)
        assert member_overwrite is None
    
    @pytest.mark.asyncio
    async def test_permission_setup_insufficient_bot_permissions(self):
        """Test error handling when bot has insufficient permissions."""
        mock_channel = AsyncMock()
        mock_channel.edit_permission.side_effect = Exception("Missing permissions")
        
        mock_user = MagicMock()
        mock_user.id = 123456789
        mock_user.username = "testuser"
        
        result = await self.command.update_channel_permissions_for_user(
            mock_channel, mock_user, grant_access=True
        )
        
        # Should return False on permission error
        assert result is False
    
    @pytest.mark.asyncio 
    async def test_permission_setup_logs_failures(self):
        """Test that permission setup failures are properly logged."""
        mock_channel = AsyncMock()
        mock_channel.edit_permission.side_effect = Exception("API Error")
        
        mock_role = MagicMock()
        mock_role.id = 123456789
        mock_role.name = "Staff"
        
        with patch('app.commands.implementations.ticket.logger') as mock_logger:
            result = await self.command.update_channel_permissions_for_role(
                mock_channel, mock_role, grant_access=True
            )
            
            # Should log the error
            assert result is False
            mock_logger.error.assert_called_once()
            assert "Failed to update permissions" in str(mock_logger.error.call_args)
    
    @pytest.mark.asyncio
    async def test_fallback_role_detection_case_insensitive(self):
        """Test that fallback role detection is case-insensitive."""
        mock_guild = MagicMock()
        mock_guild.id = 123456789
        mock_guild.default_role = MagicMock()
        mock_guild.default_role.id = 111111111
        mock_guild.me = MagicMock()
        mock_guild.me.id = 222222222
        
        # Create roles with different cases
        staff_role = MagicMock()
        staff_role.id = 444444444
        staff_role.name = "STAFF"  # Uppercase
        
        support_role = MagicMock()
        support_role.id = 555555555
        support_role.name = "Support"  # Mixed case
        
        admin_role = MagicMock()
        admin_role.id = 666666666
        support_role.name = "administrator"  # Lowercase
        
        mock_guild.roles = [staff_role, support_role, admin_role]
        
        mock_user = MagicMock()
        mock_user.id = 333333333
        
        with patch('app.commands.implementations.ticket.get_db_session') as mock_db:
            mock_session = MagicMock()
            mock_db.return_value = mock_session
            
            # No configured roles - should use fallback
            with patch('app.commands.implementations.ticket.get_guild_staff_role_ids', return_value=[]):
                with patch('app.commands.implementations.ticket.get_guild_admin_role_ids', return_value=[]):
                    overwrites = await self.command._calculate_channel_permissions(mock_guild, mock_user)
        
        # Should detect both staff and support roles regardless of case
        staff_overwrite = next((ow for ow in overwrites if ow.id == staff_role.id), None)
        assert staff_overwrite is not None
        
        support_overwrite = next((ow for ow in overwrites if ow.id == support_role.id), None)
        assert support_overwrite is not None
    
    def test_guild_role_configuration_functions(self):
        """Test guild role configuration helper functions."""
        # Mock database session
        mock_db = MagicMock()
        
        # Mock guild with roles
        mock_guild = Guild(
            id=123456789,
            name="Test Guild",
            staff_role_ids=[111, 222],
            admin_role_ids=[333, 444]
        )
        
        with patch('app.models.guild.get_guild_by_id', return_value=mock_guild):
            staff_roles = get_guild_staff_role_ids(mock_db, 123456789)
            admin_roles = get_guild_admin_role_ids(mock_db, 123456789)
        
        assert staff_roles == [111, 222]
        assert admin_roles == [333, 444]
        
        # Test with non-existent guild
        with patch('app.models.guild.get_guild_by_id', return_value=None):
            staff_roles = get_guild_staff_role_ids(mock_db, 999999999)
            admin_roles = get_guild_admin_role_ids(mock_db, 999999999)
        
        assert staff_roles == []
        assert admin_roles == []
    
    def test_guild_role_configuration_empty_lists(self):
        """Test guild role configuration with empty role lists."""
        mock_db = MagicMock()
        
        # Mock guild with empty role lists
        mock_guild = Guild(
            id=123456789,
            name="Test Guild",
            staff_role_ids=[],
            admin_role_ids=None  # None should be handled
        )
        
        with patch('app.models.guild.get_guild_by_id', return_value=mock_guild):
            staff_roles = get_guild_staff_role_ids(mock_db, 123456789)
            admin_roles = get_guild_admin_role_ids(mock_db, 123456789)
        
        assert staff_roles == []
        assert admin_roles == []
