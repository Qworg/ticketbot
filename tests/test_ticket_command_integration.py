"""
Integration tests for the ticket command implementation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import interactions

from app.commands.implementations.ticket import TicketCommand
from app.commands.errors import CommandValidationError


class TestTicketCommandIntegration:
    """Integration test cases for the TicketCommand class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.command = TicketCommand()
    
    @patch('app.commands.implementations.ticket.get_db_session')
    @patch('app.commands.implementations.ticket.create_ticket')
    def test_create_ticket_in_database(self, mock_create_ticket, mock_db_session):
        """Test ticket creation in database."""
        # Mock database session
        mock_db = MagicMock()
        mock_db_session.return_value = mock_db
        
        # Mock ticket creation
        mock_ticket = MagicMock()
        mock_ticket.id = 123
        mock_ticket.channel_id = 987654321
        mock_ticket.guild_id = 123456789
        mock_ticket.creator_id = 555666777
        mock_ticket.status = "open"
        mock_ticket.reason = "Test ticket reason"
        mock_ticket.created_at = "2023-01-01T00:00:00Z"
        mock_ticket.category = "General"
        mock_create_ticket.return_value = mock_ticket
        
        # Test ticket creation
        import asyncio
        result = asyncio.run(self.command._create_ticket_in_database(
            guild_id=123456789,
            creator_id=555666777,
            reason="Test ticket reason",
            channel_id=987654321
        ))
        
        # Verify the call was made correctly
        mock_create_ticket.assert_called_once_with(
            db=mock_db,
            guild_id=123456789,
            creator_id=555666777,
            reason="Test ticket reason",
            channel_id=987654321,
            category="General"
        )
        
        # Verify the result format
        assert result['id'] == 123
        assert result['channel_id'] == 987654321
        assert result['guild_id'] == 123456789
        assert result['creator_id'] == 555666777
        assert result['status'] == "open"
        assert result['reason'] == "Test ticket reason"
        assert result['category'] == "General"
    
    def test_permission_overwrites_structure(self):
        """Test that permission overwrites are structured correctly."""
        # Mock guild and user
        mock_guild = MagicMock()
        mock_guild.default_role.id = 111111111
        mock_guild.me.id = 222222222
        mock_guild.roles = []
        
        mock_user = MagicMock()
        mock_user.id = 333333333
        
        # Test permission calculation
        import asyncio
        overwrites = asyncio.run(self.command._calculate_channel_permissions(mock_guild, mock_user))
        
        # Should have at least 3 overwrites: @everyone, user, bot
        assert len(overwrites) >= 3
        
        # Check @everyone permissions (should be first)
        everyone_overwrite = overwrites[0]
        assert everyone_overwrite.id == 111111111
        assert everyone_overwrite.type == interactions.OverwriteType.ROLE
        assert interactions.Permissions.VIEW_CHANNEL in everyone_overwrite.deny
        assert interactions.Permissions.SEND_MESSAGES in everyone_overwrite.deny
        
        # Check user permissions (should be second)
        user_overwrite = overwrites[1]
        assert user_overwrite.id == 333333333
        assert user_overwrite.type == interactions.OverwriteType.MEMBER
        assert interactions.Permissions.VIEW_CHANNEL in user_overwrite.allow
        assert interactions.Permissions.SEND_MESSAGES in user_overwrite.allow
        
        # Check bot permissions (should be third)
        bot_overwrite = overwrites[2]
        assert bot_overwrite.id == 222222222
        assert bot_overwrite.type == interactions.OverwriteType.MEMBER
        assert interactions.Permissions.VIEW_CHANNEL in bot_overwrite.allow
        assert interactions.Permissions.MANAGE_CHANNELS in bot_overwrite.allow
    
    def test_permission_overwrites_with_staff_roles(self):
        """Test permission overwrites when staff roles are present."""
        # Mock guild with staff roles
        mock_guild = MagicMock()
        mock_guild.default_role.id = 111111111
        mock_guild.me.id = 222222222
        
        # Mock staff roles
        staff_role = MagicMock()
        staff_role.id = 444444444
        staff_role.name = "Staff"
        
        admin_role = MagicMock()
        admin_role.id = 555555555
        admin_role.name = "Admin"
        
        mock_guild.roles = [staff_role, admin_role]
        
        mock_user = MagicMock()
        mock_user.id = 333333333
        
        # Test permission calculation
        import asyncio
        overwrites = asyncio.run(self.command._calculate_channel_permissions(mock_guild, mock_user))
        
        # Should have 5 overwrites: @everyone, user, bot, staff, admin
        assert len(overwrites) == 5
        
        # Check staff role permissions
        staff_overwrite = overwrites[3]
        assert staff_overwrite.id == 444444444
        assert staff_overwrite.type == interactions.OverwriteType.ROLE
        assert interactions.Permissions.VIEW_CHANNEL in staff_overwrite.allow
        
        # Check admin role permissions
        admin_overwrite = overwrites[4]
        assert admin_overwrite.id == 555555555
        assert admin_overwrite.type == interactions.OverwriteType.ROLE
        assert interactions.Permissions.VIEW_CHANNEL in admin_overwrite.allow


if __name__ == "__main__":
    pytest.main([__file__])
