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


if __name__ == "__main__":
    pytest.main([__file__])
