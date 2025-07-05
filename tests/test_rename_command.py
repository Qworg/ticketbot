"""
Unit tests for the rename command implementation.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

import interactions

from app.commands.implementations.rename import RenameCommand
from app.commands.errors import CommandValidationError, CommandError
from app.models.ticket import Ticket
from app.models.user import User


class TestRenameCommand:
    """Test cases for RenameCommand."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.command = RenameCommand()
        
        # Mock context
        self.mock_ctx = Mock(spec=interactions.SlashContext)
        self.mock_ctx.channel = Mock()
        self.mock_ctx.channel.id = "123456789"
        self.mock_ctx.channel.name = "ticket-old-name"
        self.mock_ctx.channel.edit = AsyncMock()
        self.mock_ctx.guild = Mock()
        self.mock_ctx.guild.id = "987654321"
        self.mock_ctx.guild.name = "Test Guild"
        self.mock_ctx.author = Mock(spec=interactions.Member)
        self.mock_ctx.author.id = "555666777"
        self.mock_ctx.author.mention = "<@555666777>"
        self.mock_ctx.send = AsyncMock()
        
        # Mock ticket
        self.mock_ticket = Mock(spec=Ticket)
        self.mock_ticket.id = 123
        self.mock_ticket.creator_id = 111222333
        self.mock_ticket.assigned_to = None
        self.mock_ticket.status = "open"
        self.mock_ticket.reason = "Test ticket reason"
        
        # Mock user
        self.mock_user = Mock(spec=User)
        self.mock_user.id = "user-uuid-123"
        self.mock_user.discord_id = 555666777
        self.mock_user.role = "USER"
    
    def test_init(self):
        """Test command initialization."""
        assert self.command.name == "rename"
        assert self.command.description == "Rename the current ticket channel"
        assert self.command.staff_only is True
        assert self.command.cooldown_seconds == 30.0
        assert self.command.rate_limit_per_minute == 5
        assert len(self.command.options) == 1
        assert str(self.command.options[0].name) == "new_name"
        assert self.command.options[0].required is True
        assert self.command.options[0].min_length == 3
        assert self.command.options[0].max_length == 50
    
    def test_validate_arguments_success(self):
        """Test successful argument validation."""
        # Should not raise any exception
        self.command.validate_arguments(new_name="Valid Name")
        self.command.validate_arguments(new_name="test-name_123")
        self.command.validate_arguments(new_name="Another Valid Name")
    
    def test_validate_arguments_empty_name(self):
        """Test validation with empty name."""
        with pytest.raises(CommandValidationError) as exc_info:
            self.command.validate_arguments(new_name="")
        assert exc_info.value.field == "new_name"
        assert "required" in exc_info.value.user_message
        
        with pytest.raises(CommandValidationError) as exc_info:
            self.command.validate_arguments(new_name="   ")
        assert exc_info.value.field == "new_name"
        assert "required" in exc_info.value.user_message
    
    def test_validate_arguments_too_short(self):
        """Test validation with name too short."""
        with pytest.raises(CommandValidationError) as exc_info:
            self.command.validate_arguments(new_name="ab")
        assert exc_info.value.field == "new_name"
        assert "at least 3 characters" in exc_info.value.user_message
    
    def test_validate_arguments_too_long(self):
        """Test validation with name too long."""
        long_name = "a" * 51  # 51 characters
        with pytest.raises(CommandValidationError) as exc_info:
            self.command.validate_arguments(new_name=long_name)
        assert exc_info.value.field == "new_name"
        assert "no more than 50 characters" in exc_info.value.user_message
    
    def test_validate_arguments_invalid_characters(self):
        """Test validation with invalid characters."""
        invalid_names = [
            "invalid@name",
            "test#name",
            "name$with%symbols",
            "name!with?special&chars",
            "name.with.dots"
        ]
        
        for invalid_name in invalid_names:
            with pytest.raises(CommandValidationError) as exc_info:
                self.command.validate_arguments(new_name=invalid_name)
            assert exc_info.value.field == "new_name"
            assert "can only contain letters, numbers, spaces, hyphens, and underscores" in exc_info.value.user_message
    
    def test_sanitize_channel_name(self):
        """Test channel name sanitization."""
        # Test basic sanitization
        assert self.command.sanitize_channel_name("Test Name") == "ticket-test-name"
        
        # Test lowercase conversion
        assert self.command.sanitize_channel_name("UPPERCASE") == "ticket-uppercase"
        
        # Test space replacement
        assert self.command.sanitize_channel_name("Multiple   Spaces") == "ticket-multiple-spaces"
        
        # Test special character removal
        assert self.command.sanitize_channel_name("Test_Name-With_Chars") == "ticket-test-name-with-chars"
        
        # Test leading/trailing hyphen removal
        assert self.command.sanitize_channel_name("-test-name-") == "ticket-test-name"
        
        # Test empty after sanitization
        assert self.command.sanitize_channel_name("@#$%") == "ticket-ticket"
        
        # Test multiple consecutive hyphens
        assert self.command.sanitize_channel_name("test---name") == "ticket-test-name"
    
    def test_create_audit_entry(self):
        """Test audit entry creation."""
        ticket_id = 123
        user_id = 555666777
        old_name = "ticket-old-name"
        new_name = "ticket-new-name"
        
        entry = self.command.create_audit_entry(ticket_id, user_id, old_name, new_name)
        
        assert entry["action"] == "ticket_renamed"
        assert entry["ticket_id"] == ticket_id
        assert entry["user_id"] == user_id
        assert "timestamp" in entry
        assert entry["details"]["old_name"] == old_name
        assert entry["details"]["new_name"] == new_name
        assert entry["details"]["renamed_by"] == user_id
    
    @pytest.mark.asyncio
    async def test_execute_not_in_guild(self):
        """Test execution when not in a guild."""
        self.mock_ctx.guild = None
        
        await self.command._execute(self.mock_ctx)
        
        self.mock_ctx.send.assert_called_once()
        args, kwargs = self.mock_ctx.send.call_args
        assert "❌" in kwargs["content"]
        assert "server" in kwargs["content"]
        assert kwargs["ephemeral"] is True
    
    @pytest.mark.asyncio
    async def test_execute_not_member(self):
        """Test execution when author is not a member."""
        self.mock_ctx.author = Mock(spec=interactions.User)  # Not a Member
        
        await self.command._execute(self.mock_ctx)
        
        self.mock_ctx.send.assert_called_once()
        args, kwargs = self.mock_ctx.send.call_args
        assert "❌" in kwargs["content"]
        assert "server members" in kwargs["content"]
        assert kwargs["ephemeral"] is True
    
    @pytest.mark.asyncio
    @patch('app.commands.implementations.rename.get_db_session')
    @patch('app.commands.implementations.rename.get_ticket_by_channel_id')
    async def test_execute_not_ticket_channel(self, mock_get_ticket, mock_get_db):
        """Test execution when not in a ticket channel."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        mock_get_ticket.return_value = None
        
        await self.command._execute(self.mock_ctx, new_name="test-name")
        
        mock_get_ticket.assert_called_once_with(mock_db, 123456789)
        self.mock_ctx.send.assert_called_once()
        args, kwargs = self.mock_ctx.send.call_args
        assert "❌" in kwargs["content"]
        assert "ticket channel" in kwargs["content"]
        assert kwargs["ephemeral"] is True
        mock_db.close.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.commands.implementations.rename.get_db_session')
    @patch('app.commands.implementations.rename.get_ticket_by_channel_id')
    @patch('app.commands.implementations.rename.get_user_by_discord_id')
    @patch('app.commands.implementations.rename.get_user_role_in_guild')
    async def test_execute_not_staff(self, mock_get_role, mock_get_user, mock_get_ticket, mock_get_db):
        """Test execution when user is not staff."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        mock_get_ticket.return_value = self.mock_ticket
        mock_get_user.return_value = self.mock_user
        mock_get_role.return_value = "USER"  # Not staff
        
        await self.command._execute(self.mock_ctx, new_name="test-name")
        
        self.mock_ctx.send.assert_called_once()
        args, kwargs = self.mock_ctx.send.call_args
        assert "❌" in kwargs["content"]
        assert "staff members" in kwargs["content"]
        assert kwargs["ephemeral"] is True
        mock_db.close.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.commands.implementations.rename.get_db_session')
    @patch('app.commands.implementations.rename.get_ticket_by_channel_id')
    @patch('app.commands.implementations.rename.get_user_by_discord_id')
    @patch('app.commands.implementations.rename.get_user_role_in_guild')
    async def test_execute_validation_error(self, mock_get_role, mock_get_user, mock_get_ticket, mock_get_db):
        """Test execution with validation error."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        mock_get_ticket.return_value = self.mock_ticket
        mock_get_user.return_value = self.mock_user
        mock_get_role.return_value = "STAFF"
        
        await self.command._execute(self.mock_ctx, new_name="ab")  # Too short
        
        self.mock_ctx.send.assert_called_once()
        args, kwargs = self.mock_ctx.send.call_args
        assert "❌" in kwargs["content"]
        assert "at least 3 characters" in kwargs["content"]
        assert kwargs["ephemeral"] is True
        mock_db.close.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.commands.implementations.rename.get_db_session')
    @patch('app.commands.implementations.rename.get_ticket_by_channel_id')
    @patch('app.commands.implementations.rename.get_user_by_discord_id')
    @patch('app.commands.implementations.rename.get_user_role_in_guild')
    async def test_execute_same_name(self, mock_get_role, mock_get_user, mock_get_ticket, mock_get_db):
        """Test execution when new name is same as current name."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        mock_get_ticket.return_value = self.mock_ticket
        mock_get_user.return_value = self.mock_user
        mock_get_role.return_value = "STAFF"
        
        # Set channel name to match what would be sanitized
        self.mock_ctx.channel.name = "ticket-old-name"
        
        await self.command._execute(self.mock_ctx, new_name="Old Name")
        
        self.mock_ctx.send.assert_called_once()
        args, kwargs = self.mock_ctx.send.call_args
        assert "❌" in kwargs["content"]
        assert "same as the current name" in kwargs["content"]
        assert kwargs["ephemeral"] is True
        mock_db.close.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.commands.implementations.rename.get_db_session')
    @patch('app.commands.implementations.rename.get_ticket_by_channel_id')
    @patch('app.commands.implementations.rename.get_user_by_discord_id')
    @patch('app.commands.implementations.rename.get_user_role_in_guild')
    async def test_execute_success(self, mock_get_role, mock_get_user, mock_get_ticket, mock_get_db):
        """Test successful execution."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        mock_get_ticket.return_value = self.mock_ticket
        mock_get_user.return_value = self.mock_user
        mock_get_role.return_value = "STAFF"
        
        await self.command._execute(self.mock_ctx, new_name="New Name")
        
        # Verify channel was renamed
        self.mock_ctx.channel.edit.assert_called_once_with(name="ticket-new-name")
        
        # Verify success message was sent
        self.mock_ctx.send.assert_called_once()
        args, kwargs = self.mock_ctx.send.call_args
        assert "embed" in kwargs
        embed = kwargs["embed"]
        assert "✅ Ticket Renamed" in embed.title
        assert "Successfully renamed" in embed.description
        
        mock_db.close.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.commands.implementations.rename.get_db_session')
    @patch('app.commands.implementations.rename.get_ticket_by_channel_id')
    @patch('app.commands.implementations.rename.get_user_by_discord_id')
    @patch('app.commands.implementations.rename.get_user_role_in_guild')
    async def test_execute_discord_permission_error(self, mock_get_role, mock_get_user, mock_get_ticket, mock_get_db):
        """Test execution with Discord permission error."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        mock_get_ticket.return_value = self.mock_ticket
        mock_get_user.return_value = self.mock_user
        mock_get_role.return_value = "STAFF"
        
        # Mock Discord API permission error
        class MockDiscordError(Exception):
            def __init__(self, message, status):
                super().__init__(message)
                self.status = status
                self.message = message
        
        mock_exception = MockDiscordError("Missing Permissions", 403)
        self.mock_ctx.channel.edit = AsyncMock(side_effect=mock_exception)
        
        await self.command._execute(self.mock_ctx, new_name="New Name")
        
        self.mock_ctx.send.assert_called_once()
        args, kwargs = self.mock_ctx.send.call_args
        assert "❌" in kwargs["content"]
        assert "permission" in kwargs["content"]
        assert kwargs["ephemeral"] is True
        mock_db.close.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.commands.implementations.rename.get_db_session')
    @patch('app.commands.implementations.rename.get_ticket_by_channel_id')
    @patch('app.commands.implementations.rename.get_user_by_discord_id')
    @patch('app.commands.implementations.rename.get_user_role_in_guild')
    async def test_execute_discord_bad_request(self, mock_get_role, mock_get_user, mock_get_ticket, mock_get_db):
        """Test execution with Discord bad request error."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        mock_get_ticket.return_value = self.mock_ticket
        mock_get_user.return_value = self.mock_user
        mock_get_role.return_value = "STAFF"
        
        # Mock Discord API bad request error
        class MockDiscordError(Exception):
            def __init__(self, message, status):
                super().__init__(message)
                self.status = status
                self.message = message
        
        mock_exception = MockDiscordError("Bad Request", 400)
        self.mock_ctx.channel.edit = AsyncMock(side_effect=mock_exception)
        
        await self.command._execute(self.mock_ctx, new_name="New Name")
        
        self.mock_ctx.send.assert_called_once()
        args, kwargs = self.mock_ctx.send.call_args
        assert "❌" in kwargs["content"]
        assert "not valid for Discord" in kwargs["content"]
        assert kwargs["ephemeral"] is True
        mock_db.close.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.commands.implementations.rename.get_db_session')
    @patch('app.commands.implementations.rename.get_ticket_by_channel_id')
    @patch('app.commands.implementations.rename.get_user_by_discord_id')
    @patch('app.commands.implementations.rename.get_user_role_in_guild')
    async def test_execute_create_user_if_not_exists(self, mock_get_role, mock_get_user, mock_get_ticket, mock_get_db):
        """Test execution when user doesn't exist in database."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        mock_get_ticket.return_value = self.mock_ticket
        mock_get_user.return_value = None  # User doesn't exist
        mock_get_role.return_value = "STAFF"
        
        with patch('app.commands.implementations.rename.create_user') as mock_create_user:
            mock_create_user.return_value = self.mock_user
            
            await self.command._execute(self.mock_ctx, new_name="New Name")
            
            # Verify user was created
            mock_create_user.assert_called_once_with(mock_db, 555666777)
            
            # Verify rename succeeded
            self.mock_ctx.channel.edit.assert_called_once_with(name="ticket-new-name")
            
            mock_db.close.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.commands.implementations.rename.get_db_session')
    @patch('app.commands.implementations.rename.get_ticket_by_channel_id')
    @patch('app.commands.implementations.rename.get_user_by_discord_id')
    @patch('app.commands.implementations.rename.get_user_role_in_guild')
    async def test_execute_admin_user(self, mock_get_role, mock_get_user, mock_get_ticket, mock_get_db):
        """Test execution with admin user."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        mock_get_ticket.return_value = self.mock_ticket
        mock_get_user.return_value = self.mock_user
        mock_get_role.return_value = "ADMIN"  # Admin user
        
        await self.command._execute(self.mock_ctx, new_name="New Name")
        
        # Verify rename succeeded
        self.mock_ctx.channel.edit.assert_called_once_with(name="ticket-new-name")
        
        # Verify success message was sent
        self.mock_ctx.send.assert_called_once()
        args, kwargs = self.mock_ctx.send.call_args
        assert "embed" in kwargs
        embed = kwargs["embed"]
        assert "✅ Ticket Renamed" in embed.title
        
        mock_db.close.assert_called_once()
