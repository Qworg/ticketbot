"""Tests for the help command implementation."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import interactions
import uuid

from app.commands.implementations.help import HelpCommand
from app.commands.registry import CommandRegistry
from app.commands.base import BaseCommand


class TestHelpCommand:
    """Test the help command functionality."""

    @pytest.fixture
    def help_command(self):
        """Create a help command instance."""
        return HelpCommand()

    @pytest.fixture
    def mock_context(self):
        """Create a mock slash context."""
        ctx = Mock(spec=interactions.SlashContext)
        ctx.author = Mock()
        ctx.author.id = "123456789"
        ctx.guild = Mock()
        ctx.guild.id = "987654321"
        ctx.send = AsyncMock()
        return ctx

    @pytest.fixture
    def mock_component_context(self):
        """Create a mock component context."""
        ctx = Mock(spec=interactions.ComponentContext)
        ctx.author = Mock()
        ctx.author.id = "123456789"
        ctx.guild = Mock()
        ctx.guild.id = "987654321"
        ctx.custom_id = "help_user"
        ctx.edit_origin = AsyncMock()
        return ctx

    @pytest.fixture
    def mock_registry(self):
        """Create a mock command registry with sample commands."""
        registry = Mock(spec=CommandRegistry)
        
        # Create mock commands
        user_cmd = Mock(spec=BaseCommand)
        user_cmd.name = "ticket"
        user_cmd.description = "Create a new ticket"
        user_cmd.staff_only = False
        user_cmd.admin_only = False
        
        staff_cmd = Mock(spec=BaseCommand)
        staff_cmd.name = "claim"
        staff_cmd.description = "Claim a ticket"
        staff_cmd.staff_only = True
        staff_cmd.admin_only = False
        
        admin_cmd = Mock(spec=BaseCommand)
        admin_cmd.name = "admin"
        admin_cmd.description = "Admin command"
        admin_cmd.staff_only = False
        admin_cmd.admin_only = True
        
        registry.commands = {
            "ticket": user_cmd,
            "claim": staff_cmd,
            "admin": admin_cmd
        }
        
        return registry

    def test_command_initialization(self, help_command):
        """Test that the help command initializes correctly."""
        assert help_command.name == "help"
        assert help_command.description == "Show available commands and usage information"
        assert help_command.cooldown_seconds == 5.0

    def test_get_command_definition(self, help_command):
        """Test that the slash command definition is correct."""
        definition = help_command.get_command_definition()
        
        assert isinstance(definition, interactions.SlashCommand)
        assert str(definition.name) == "help"
        assert str(definition.description) == "Show available commands and usage information"
        assert len(definition.options) == 2
        
        # Check category option
        category_option = definition.options[0]
        assert hasattr(category_option, 'name')
        assert hasattr(category_option, 'required')
        assert hasattr(category_option, 'choices')
        
        # Check command option
        command_option = definition.options[1]
        assert hasattr(command_option, 'name')
        assert hasattr(command_option, 'required')

    def test_create_navigation_buttons_user(self, help_command):
        """Test navigation buttons for regular users."""
        buttons = help_command._create_navigation_buttons(1, 1, "USER")
        
        assert len(buttons) == 3  # User commands, Bot info, Examples
        assert buttons[0].label == "User Commands"
        assert buttons[0].custom_id == "help_user"

    def test_create_navigation_buttons_staff(self, help_command):
        """Test navigation buttons for staff users."""
        buttons = help_command._create_navigation_buttons(1, 1, "STAFF")
        
        assert len(buttons) == 4  # User + Staff commands, Bot info, Examples
        assert any(button.label == "Staff Commands" for button in buttons)
        assert any(button.custom_id == "help_staff" for button in buttons)

    def test_create_navigation_buttons_admin(self, help_command):
        """Test navigation buttons for admin users."""
        buttons = help_command._create_navigation_buttons(1, 1, "ADMIN")
        
        assert len(buttons) == 5  # User + Staff + Admin commands, Bot info, Examples
        assert any(button.label == "Admin Commands" for button in buttons)
        assert any(button.custom_id == "help_admin" for button in buttons)

    def test_create_category_embed_user(self, help_command, mock_registry):
        """Test creating category embed for user commands."""
        embed = help_command._create_category_embed("user", "USER", mock_registry.commands)
        
        assert embed.title == "🟦 User Commands"
        assert embed.description == "Commands available to all users"
        assert embed.color == 0x5865F2

    def test_create_category_embed_staff(self, help_command, mock_registry):
        """Test creating category embed for staff commands."""
        embed = help_command._create_category_embed("staff", "STAFF", mock_registry.commands)
        
        assert embed.title == "🟨 Staff Commands"
        assert embed.description == "Commands available to staff members"
        assert embed.color == 0xF1C40F

    def test_create_category_embed_admin(self, help_command, mock_registry):
        """Test creating category embed for admin commands."""
        embed = help_command._create_category_embed("admin", "ADMIN", mock_registry.commands)
        
        assert embed.title == "🟥 Admin Commands"
        assert embed.description == "Commands available to administrators"
        assert embed.color == 0xE74C3C

    def test_create_category_embed_info(self, help_command, mock_registry):
        """Test creating category embed for bot info."""
        embed = help_command._create_category_embed("info", "USER", mock_registry.commands)
        
        assert embed.title == "ℹ️ Bot Information"
        assert embed.description == "Information about the ticket bot"
        assert embed.color == 0x9B59B6

    def test_create_category_embed_examples(self, help_command, mock_registry):
        """Test creating category embed for examples."""
        embed = help_command._create_category_embed("examples", "USER", mock_registry.commands)
        
        assert embed.title == "📖 Usage Examples"
        assert embed.description == "Common command usage patterns"
        assert embed.color == 0x3498DB

    def test_create_category_embed_troubleshooting(self, help_command, mock_registry):
        """Test creating category embed for troubleshooting."""
        embed = help_command._create_category_embed("troubleshooting", "USER", mock_registry.commands)
        
        assert embed.title == "🔧 Troubleshooting"
        assert embed.description == "Common issues and solutions"
        assert embed.color == 0xE67E22

    def test_create_category_embed_unauthorized(self, help_command, mock_registry):
        """Test creating category embed for unauthorized access."""
        embed = help_command._create_category_embed("admin", "USER", mock_registry.commands)
        
        assert embed.title == "❌ Access Denied"
        assert embed.description == "You don't have permission to view this help category."
        assert embed.color == 0xE74C3C

    def test_get_command_help_existing_command(self, help_command, mock_registry):
        """Test getting help for an existing command."""
        embed = help_command._get_command_help("ticket", mock_registry.commands, "USER")
        
        assert embed is not None
        assert embed.title == "📋 Command: /ticket"
        assert embed.color == 0x5865F2

    def test_get_command_help_nonexistent_command(self, help_command, mock_registry):
        """Test getting help for a non-existent command."""
        embed = help_command._get_command_help("nonexistent", mock_registry.commands, "USER")
        
        assert embed is None

    def test_get_command_help_unauthorized_admin(self, help_command, mock_registry):
        """Test getting help for admin command as user."""
        embed = help_command._get_command_help("admin", mock_registry.commands, "USER")
        
        assert embed is None

    def test_get_command_help_unauthorized_staff(self, help_command, mock_registry):
        """Test getting help for staff command as user."""
        embed = help_command._get_command_help("claim", mock_registry.commands, "USER")
        
        assert embed is None

    def test_get_command_help_authorized_staff(self, help_command, mock_registry):
        """Test getting help for staff command as staff."""
        embed = help_command._get_command_help("claim", mock_registry.commands, "STAFF")
        
        assert embed is not None
        assert embed.title == "📋 Command: /claim"

    @patch('app.commands.implementations.help.get_command_registry')
    @patch('app.database.get_db_session')
    async def test_execute_default_help(self, mock_db_session, mock_get_registry, help_command, mock_context, mock_registry):
        """Test executing help command with default parameters."""
        # Setup mocks
        mock_get_registry.return_value = mock_registry
        mock_db_session.return_value.__enter__.return_value = Mock()
        mock_db_session.return_value.__exit__.return_value = None
        
        # Execute command
        await help_command._execute(mock_context)
        
        # Verify response
        mock_context.send.assert_called_once()
        call_args = mock_context.send.call_args
        assert call_args[1]['ephemeral'] is True
        assert 'embed' in call_args[1]
        assert 'components' in call_args[1]

    @patch('app.commands.implementations.help.get_command_registry')
    @patch('app.database.get_db_session')
    async def test_execute_help_with_category(self, mock_db_session, mock_get_registry, help_command, mock_context, mock_registry):
        """Test executing help command with category parameter."""
        # Setup mocks
        mock_get_registry.return_value = mock_registry
        mock_db_session.return_value.__enter__.return_value = Mock()
        mock_db_session.return_value.__exit__.return_value = None
        
        # Execute command with category
        await help_command._execute(mock_context, category="user")
        
        # Verify response
        mock_context.send.assert_called_once()
        call_args = mock_context.send.call_args
        assert call_args[1]['ephemeral'] is True
        assert 'embed' in call_args[1]
        assert 'components' in call_args[1]

    @patch('app.commands.implementations.help.get_command_registry')
    @patch('app.database.get_db_session')
    async def test_execute_help_with_command(self, mock_db_session, mock_get_registry, help_command, mock_context, mock_registry):
        """Test executing help command with command parameter."""
        # Setup mocks
        mock_get_registry.return_value = mock_registry
        mock_db_session.return_value.__enter__.return_value = Mock()
        mock_db_session.return_value.__exit__.return_value = None
        
        # Execute command with specific command
        await help_command._execute(mock_context, command="ticket")
        
        # Verify response
        mock_context.send.assert_called_once()
        call_args = mock_context.send.call_args
        assert call_args[1]['ephemeral'] is True
        assert 'embed' in call_args[1]

    @patch('app.commands.implementations.help.get_command_registry')
    @patch('app.database.get_db_session')
    async def test_execute_help_with_invalid_command(self, mock_db_session, mock_get_registry, help_command, mock_context, mock_registry):
        """Test executing help command with invalid command parameter."""
        # Setup mocks
        mock_get_registry.return_value = mock_registry
        mock_db_session.return_value.__enter__.return_value = Mock()
        mock_db_session.return_value.__exit__.return_value = None
        
        # Execute command with invalid command
        await help_command._execute(mock_context, command="nonexistent")
        
        # Verify error response
        mock_context.send.assert_called_once()
        call_args = mock_context.send.call_args
        assert call_args[1]['ephemeral'] is True
        embed = call_args[1]['embed']
        assert embed.title == "❌ Command Not Found"

    @patch('app.commands.implementations.help.get_command_registry')
    @patch('app.database.get_db_session')
    async def test_handle_button_interaction(self, mock_db_session, mock_get_registry, help_command, mock_component_context, mock_registry):
        """Test handling button interactions."""
        # Setup mocks
        mock_get_registry.return_value = mock_registry
        mock_db_session.return_value.__enter__.return_value = Mock()
        mock_db_session.return_value.__exit__.return_value = None
        
        # Handle button interaction
        await help_command.handle_button_interaction(mock_component_context)
        
        # Verify response
        mock_component_context.edit_origin.assert_called_once()
        call_args = mock_component_context.edit_origin.call_args
        assert 'embed' in call_args[1]
        assert 'components' in call_args[1]

    async def test_handle_button_interaction_invalid_id(self, help_command, mock_component_context):
        """Test handling button interactions with invalid custom_id."""
        mock_component_context.custom_id = "invalid_id"
        
        # Handle button interaction - should return early
        await help_command.handle_button_interaction(mock_component_context)
        
        # Verify no response
        mock_component_context.edit_origin.assert_not_called()

    def test_command_permission_filtering(self, help_command, mock_registry):
        """Test that commands are properly filtered based on permissions."""
        # Test user permissions - should only see user commands
        user_commands = []
        staff_commands = []
        admin_commands = []
        
        for cmd_name, cmd in mock_registry.commands.items():
            if cmd.admin_only and "USER" != 'ADMIN':
                continue
            elif cmd.staff_only and "USER" not in ['ADMIN', 'STAFF']:
                continue
            
            if cmd.admin_only:
                admin_commands.append(cmd)
            elif cmd.staff_only:
                staff_commands.append(cmd)
            else:
                user_commands.append(cmd)
        
        assert len(user_commands) == 1  # Only ticket command
        assert len(staff_commands) == 0  # No staff commands visible
        assert len(admin_commands) == 0  # No admin commands visible

    def test_command_permission_filtering_staff(self, help_command, mock_registry):
        """Test that commands are properly filtered for staff users."""
        # Test staff permissions - should see user and staff commands
        user_commands = []
        staff_commands = []
        admin_commands = []
        
        for cmd_name, cmd in mock_registry.commands.items():
            if cmd.admin_only and "STAFF" != 'ADMIN':
                continue
            elif cmd.staff_only and "STAFF" not in ['ADMIN', 'STAFF']:
                continue
            
            if cmd.admin_only:
                admin_commands.append(cmd)
            elif cmd.staff_only:
                staff_commands.append(cmd)
            else:
                user_commands.append(cmd)
        
        assert len(user_commands) == 1  # Ticket command
        assert len(staff_commands) == 1  # Claim command
        assert len(admin_commands) == 0  # No admin commands visible

    def test_command_permission_filtering_admin(self, help_command, mock_registry):
        """Test that commands are properly filtered for admin users."""
        # Test admin permissions - should see all commands
        user_commands = []
        staff_commands = []
        admin_commands = []
        
        for cmd_name, cmd in mock_registry.commands.items():
            if cmd.admin_only and "ADMIN" != 'ADMIN':
                continue
            elif cmd.staff_only and "ADMIN" not in ['ADMIN', 'STAFF']:
                continue
            
            if cmd.admin_only:
                admin_commands.append(cmd)
            elif cmd.staff_only:
                staff_commands.append(cmd)
            else:
                user_commands.append(cmd)
        
        assert len(user_commands) == 1  # Ticket command
        assert len(staff_commands) == 1  # Claim command
        assert len(admin_commands) == 1  # Admin command
