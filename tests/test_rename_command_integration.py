"""
Integration tests for the rename command.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

import interactions

from app.commands.implementations.rename import RenameCommand
from app.models.ticket import Ticket
from app.models.user import User
from app.models.role_assignment import RoleAssignment
from app.database import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class TestRenameCommandIntegration:
    """Integration test cases for RenameCommand."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create in-memory database
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        
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
        
        # Set up test data
        self.setup_test_data()
    
    def setup_test_data(self):
        """Set up test data in the database."""
        db = self.Session()
        try:
            # Create test user
            self.test_user = User(
                discord_id=555666777,
                email="test@example.com",
                role="USER"
            )
            db.add(self.test_user)
            db.commit()
            
            # Store user ID for later use
            self.test_user_id = self.test_user.id
            
            # Create test ticket
            self.test_ticket = Ticket(
                channel_id=123456789,
                guild_id=987654321,
                creator_id=111222333,
                assigned_to=None,
                status="open",
                category="general",
                reason="Test ticket reason"
            )
            db.add(self.test_ticket)
            db.commit()
            
            # Store ticket ID for later use  
            self.test_ticket_id = self.test_ticket.id
            
            # Create staff role assignment
            self.staff_assignment = RoleAssignment(
                user_id=self.test_user_id,
                guild_id=987654321,
                role="STAFF"
            )
            db.add(self.staff_assignment)
            db.commit()
            
        finally:
            db.close()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        Base.metadata.drop_all(self.engine)
    
    @pytest.mark.asyncio
    @patch('app.commands.implementations.rename.get_db_session')
    async def test_rename_command_integration_success(self, mock_get_db):
        """Test successful rename command execution with real database interactions."""
        mock_get_db.return_value = self.Session()
        
        await self.command._execute(self.mock_ctx, new_name="New Test Name")
        
        # Verify channel was renamed
        self.mock_ctx.channel.edit.assert_called_once_with(name="ticket-new-test-name")
        
        # Verify success message was sent
        self.mock_ctx.send.assert_called_once()
        args, kwargs = self.mock_ctx.send.call_args
        assert "embed" in kwargs
        embed = kwargs["embed"]
        assert "✅ Ticket Renamed" in embed.title
        assert "Successfully renamed" in embed.description
    
    @pytest.mark.asyncio
    @patch('app.commands.implementations.rename.get_db_session')
    async def test_rename_command_integration_no_permission(self, mock_get_db):
        """Test rename command with user who doesn't have staff permissions."""
        # Remove staff role assignment
        db = self.Session()
        try:
            db.query(RoleAssignment).filter_by(
                user_id=self.test_user_id,
                guild_id=987654321
            ).delete()
            db.commit()
        finally:
            db.close()
        
        mock_get_db.return_value = self.Session()
        
        await self.command._execute(self.mock_ctx, new_name="New Test Name")
        
        # Verify no rename occurred
        self.mock_ctx.channel.edit.assert_not_called()
        
        # Verify error message was sent
        self.mock_ctx.send.assert_called_once()
        args, kwargs = self.mock_ctx.send.call_args
        assert "❌" in kwargs["content"]
        assert "staff members" in kwargs["content"]
        assert kwargs["ephemeral"] is True
    
    @pytest.mark.asyncio
    @patch('app.commands.implementations.rename.get_db_session')
    async def test_rename_command_integration_admin_user(self, mock_get_db):
        """Test rename command with admin user."""
        # Update role assignment to admin
        db = self.Session()
        try:
            role_assignment = db.query(RoleAssignment).filter_by(
                user_id=self.test_user_id,
                guild_id=987654321
            ).first()
            if role_assignment:
                db.query(RoleAssignment).filter_by(
                    user_id=self.test_user_id,
                    guild_id=987654321
                ).update({"role": "ADMIN"})
                db.commit()
        finally:
            db.close()
        
        mock_get_db.return_value = self.Session()
        
        await self.command._execute(self.mock_ctx, new_name="Admin Rename")
        
        # Verify channel was renamed
        self.mock_ctx.channel.edit.assert_called_once_with(name="ticket-admin-rename")
        
        # Verify success message was sent
        self.mock_ctx.send.assert_called_once()
        args, kwargs = self.mock_ctx.send.call_args
        assert "embed" in kwargs
        embed = kwargs["embed"]
        assert "✅ Ticket Renamed" in embed.title
    
    @pytest.mark.asyncio
    @patch('app.commands.implementations.rename.get_db_session')
    async def test_rename_command_integration_user_creation(self, mock_get_db):
        """Test rename command when user doesn't exist in database."""
        # Delete the test user
        db = self.Session()
        try:
            db.query(RoleAssignment).filter_by(user_id=self.test_user_id).delete()
            db.query(User).filter_by(id=self.test_user_id).delete()
            db.commit()
        finally:
            db.close()
        
        mock_get_db.return_value = self.Session()
        
        await self.command._execute(self.mock_ctx, new_name="New Name")
        
        # Verify user was created but command failed due to no permissions
        db = self.Session()
        try:
            created_user = db.query(User).filter_by(discord_id=555666777).first()
            assert created_user is not None
        finally:
            db.close()
        
        # Verify error message about permissions
        self.mock_ctx.send.assert_called_once()
        args, kwargs = self.mock_ctx.send.call_args
        assert "❌" in kwargs["content"]
        assert "staff members" in kwargs["content"]
    
    @pytest.mark.asyncio
    @patch('app.commands.implementations.rename.get_db_session')
    async def test_rename_command_integration_no_ticket(self, mock_get_db):
        """Test rename command when not in a ticket channel."""
        # Delete the test ticket
        db = self.Session()
        try:
            db.query(Ticket).filter_by(id=self.test_ticket_id).delete()
            db.commit()
        finally:
            db.close()
        
        mock_get_db.return_value = self.Session()
        
        await self.command._execute(self.mock_ctx, new_name="New Name")
        
        # Verify no rename occurred
        self.mock_ctx.channel.edit.assert_not_called()
        
        # Verify error message was sent
        self.mock_ctx.send.assert_called_once()
        args, kwargs = self.mock_ctx.send.call_args
        assert "❌" in kwargs["content"]
        assert "ticket channel" in kwargs["content"]
        assert kwargs["ephemeral"] is True
    
    @pytest.mark.asyncio
    @patch('app.commands.implementations.rename.get_db_session')
    async def test_rename_command_integration_validation_errors(self, mock_get_db):
        """Test rename command with various validation errors."""
        mock_get_db.return_value = self.Session()
        
        # Test empty name
        await self.command._execute(self.mock_ctx, new_name="")
        self.mock_ctx.send.assert_called()
        args, kwargs = self.mock_ctx.send.call_args
        assert "❌" in kwargs["content"]
        assert "required" in kwargs["content"]
        
        # Reset mock
        self.mock_ctx.send.reset_mock()
        
        # Test name too short
        await self.command._execute(self.mock_ctx, new_name="ab")
        self.mock_ctx.send.assert_called()
        args, kwargs = self.mock_ctx.send.call_args
        assert "❌" in kwargs["content"]
        assert "at least 3 characters" in kwargs["content"]
        
        # Reset mock
        self.mock_ctx.send.reset_mock()
        
        # Test name too long
        long_name = "a" * 51
        await self.command._execute(self.mock_ctx, new_name=long_name)
        self.mock_ctx.send.assert_called()
        args, kwargs = self.mock_ctx.send.call_args
        assert "❌" in kwargs["content"]
        assert "no more than 50 characters" in kwargs["content"]
        
        # Reset mock
        self.mock_ctx.send.reset_mock()
        
        # Test invalid characters
        await self.command._execute(self.mock_ctx, new_name="invalid@name")
        self.mock_ctx.send.assert_called()
        args, kwargs = self.mock_ctx.send.call_args
        assert "❌" in kwargs["content"]
        assert "can only contain letters, numbers, spaces, hyphens, and underscores" in kwargs["content"]
    
    @pytest.mark.asyncio
    @patch('app.commands.implementations.rename.get_db_session')
    async def test_rename_command_integration_discord_error(self, mock_get_db):
        """Test rename command with Discord API error."""
        mock_get_db.return_value = self.Session()
        
        # Mock Discord error
        class MockDiscordError(Exception):
            def __init__(self, message):
                super().__init__(message)
                self.status = 403
        
        mock_error = MockDiscordError("Discord API error")
        self.mock_ctx.channel.edit.side_effect = mock_error
        
        await self.command._execute(self.mock_ctx, new_name="New Name")
        
        # Verify error handling
        self.mock_ctx.send.assert_called()
        args, kwargs = self.mock_ctx.send.call_args
        assert "❌" in kwargs["content"]
        assert "permission" in kwargs["content"]
        assert kwargs["ephemeral"] is True
