"""
Integration tests for the claim command implementation.
"""

import pytest
import asyncio
import uuid
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

import interactions
import httpx

from app.commands.implementations.claim import ClaimCommand
from app.models.ticket import Ticket
from app.models.user import User
from app.models.role_assignment import RoleAssignment
from app.status import TicketStatus
from app.database import get_db_session


@pytest.mark.integration
class TestClaimCommandIntegration:
    """Integration test cases for ClaimCommand."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.command = ClaimCommand()
    
    @pytest.mark.asyncio
    @patch("app.commands.implementations.claim.get_db_session")
    @patch("app.commands.implementations.claim.get_ticket_by_channel_id")
    @patch("app.commands.implementations.claim.get_user_by_discord_id")
    @patch("app.commands.implementations.claim.get_user_role_in_guild")
    @patch("app.auth.generate_token")
    @patch("httpx.AsyncClient")
    async def test_complete_claim_flow_staff(
        self, mock_http_client, mock_generate_token, mock_get_role, 
        mock_get_user, mock_get_ticket, mock_get_db
    ):
        """Test complete claim flow for staff member claiming ticket."""
        # Setup mocks
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        # Mock author user for permission check
        mock_author_user = Mock()
        mock_author_user.id = "mock-user-uuid"
        mock_author_user.email = "staff@example.com"
        mock_get_user.return_value = mock_author_user
        
        # Create mock ticket
        mock_ticket = Mock(spec=Ticket)
        mock_ticket.id = 123
        mock_ticket.creator_id = 111222333  # Different from staff
        mock_ticket.assigned_to = None  # Unassigned
        mock_ticket.status = TicketStatus.OPEN.value
        mock_ticket.reason = "Test ticket"
        mock_ticket.created_at = datetime.utcnow()
        mock_get_ticket.return_value = mock_ticket
        
        # Mock staff role
        mock_get_role.return_value = "STAFF"
        
        # Mock JWT token generation
        mock_generate_token.return_value = "mock-jwt-token"
        
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "message": "Ticket claimed successfully",
            "ticket": {"id": 123, "assigned_to": 555666777}
        }
        mock_http_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        
        # Create mock context
        mock_ctx = Mock(spec=interactions.SlashContext)
        mock_ctx.channel = Mock()
        mock_ctx.channel.id = "123456789"
        mock_ctx.channel.edit = AsyncMock()
        mock_ctx.channel.send = AsyncMock()
        mock_ctx.guild = Mock()
        mock_ctx.guild.id = "987654321"
        mock_ctx.guild.name = "Test Guild"
        mock_ctx.guild.fetch_member = AsyncMock()
        mock_ctx.author = Mock(spec=interactions.Member)
        mock_ctx.author.id = "555666777"
        mock_ctx.author.mention = "<@555666777>"
        mock_ctx.defer = AsyncMock()
        mock_ctx.edit_original_response = AsyncMock()
        
        # Execute command
        await self.command._execute(mock_ctx)
        
        # Verify database interactions
        mock_get_ticket.assert_called_once_with(mock_db, 123456789)
        mock_get_user.assert_called_once_with(mock_db, 555666777)
        mock_get_role.assert_called_once_with(mock_db, "mock-user-uuid", 987654321)
        
        # Verify JWT token generation
        mock_generate_token.assert_called_once()
        token_call_args = mock_generate_token.call_args[0][0]
        assert token_call_args["user_id"] == "mock-user-uuid"
        assert token_call_args["discord_id"] == 555666777
        assert token_call_args["role"] == "STAFF"
        
        # Verify API call
        mock_http_client.return_value.__aenter__.return_value.post.assert_called_once()
        api_call_args = mock_http_client.return_value.__aenter__.return_value.post.call_args
        assert "api/tickets/123/claim" in api_call_args[0][0]  # First positional argument is URL
        assert api_call_args[1]["headers"]["Authorization"] == "Bearer mock-jwt-token"
        
        # Verify UI interactions
        mock_ctx.defer.assert_called_once_with(ephemeral=True)
        mock_ctx.edit_original_response.assert_called_once()
        
        # Verify channel update
        mock_ctx.channel.edit.assert_called_once()
        
        # Verify notification sent to channel
        mock_ctx.channel.send.assert_called_once()
        
        # Verify database cleanup
        mock_db.close.assert_called_once()
    
    @pytest.mark.asyncio
    @patch("app.commands.implementations.claim.get_db_session")
    @patch("app.commands.implementations.claim.get_ticket_by_channel_id")
    @patch("app.commands.implementations.claim.get_user_by_discord_id")
    @patch("app.commands.implementations.claim.get_user_role_in_guild")
    async def test_integration_permission_denied_user(
        self, mock_get_role, mock_get_user, mock_get_ticket, mock_get_db
    ):
        """Test integration with permission system - regular user denied."""
        # Setup mocks
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        # Mock author user for permission check
        mock_author_user = Mock()
        mock_author_user.id = "mock-user-uuid"
        mock_get_user.return_value = mock_author_user
        
        # Create mock ticket
        mock_ticket = Mock(spec=Ticket)
        mock_ticket.id = 123
        mock_get_ticket.return_value = mock_ticket
        
        # Mock regular user role
        mock_get_role.return_value = "USER"
        
        # Create mock context
        mock_ctx = Mock(spec=interactions.SlashContext)
        mock_ctx.channel = Mock()
        mock_ctx.channel.id = "123456789"
        mock_ctx.guild = Mock()
        mock_ctx.guild.id = "987654321"
        mock_ctx.author = Mock(spec=interactions.Member)
        mock_ctx.author.id = "777888999"
        mock_ctx.send = AsyncMock()
        
        # Execute command
        await self.command._execute(mock_ctx)
        
        # Verify permission check
        mock_get_user.assert_called_once_with(mock_db, 777888999)
        mock_get_role.assert_called_once_with(mock_db, "mock-user-uuid", 987654321)
        
        # Verify permission denied
        mock_ctx.send.assert_called_once()
        call_args = mock_ctx.send.call_args[1]
        assert "❌ Only staff members can claim tickets." in call_args["content"]
        assert call_args["ephemeral"] == True
    
    @pytest.mark.asyncio
    @patch("app.commands.implementations.claim.get_db_session")
    @patch("app.commands.implementations.claim.get_ticket_by_channel_id")
    @patch("app.commands.implementations.claim.get_user_by_discord_id")
    @patch("app.commands.implementations.claim.get_user_role_in_guild")
    async def test_integration_already_assigned_ticket(
        self, mock_get_role, mock_get_user, mock_get_ticket, mock_get_db
    ):
        """Test integration with already assigned ticket."""
        # Setup mocks
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        # Mock author user for permission check
        mock_author_user = Mock()
        mock_author_user.id = "mock-user-uuid"
        mock_get_user.return_value = mock_author_user
        
        # Create mock ticket that's already assigned
        mock_ticket = Mock(spec=Ticket)
        mock_ticket.id = 123
        mock_ticket.creator_id = 111222333
        mock_ticket.assigned_to = 999888777  # Already assigned to someone else
        mock_ticket.status = TicketStatus.IN_PROGRESS.value
        mock_get_ticket.return_value = mock_ticket
        
        # Mock staff role
        mock_get_role.return_value = "STAFF"
        
        # Create mock context
        mock_ctx = Mock(spec=interactions.SlashContext)
        mock_ctx.channel = Mock()
        mock_ctx.channel.id = "123456789"
        mock_ctx.guild = Mock()
        mock_ctx.guild.id = "987654321"
        mock_ctx.author = Mock(spec=interactions.Member)
        mock_ctx.author.id = "555666777"
        mock_ctx.send = AsyncMock()
        
        # Execute command
        await self.command._execute(mock_ctx)
        
        # Verify assigned ticket rejection
        mock_ctx.send.assert_called_once()
        call_args = mock_ctx.send.call_args[1]
        assert "❌ This ticket is already assigned to" in call_args["content"]
        assert call_args["ephemeral"] == True
    
    @pytest.mark.asyncio
    @patch("app.commands.implementations.claim.get_db_session")
    @patch("app.commands.implementations.claim.get_ticket_by_channel_id")
    @patch("app.commands.implementations.claim.get_user_by_discord_id")
    @patch("app.commands.implementations.claim.get_user_role_in_guild")
    async def test_integration_cannot_claim_own_ticket(
        self, mock_get_role, mock_get_user, mock_get_ticket, mock_get_db
    ):
        """Test integration preventing self-claim."""
        # Setup mocks
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        # Mock author user for permission check
        mock_author_user = Mock()
        mock_author_user.id = "mock-user-uuid"
        mock_get_user.return_value = mock_author_user
        
        # Create mock ticket where staff member is the creator
        mock_ticket = Mock(spec=Ticket)
        mock_ticket.id = 123
        mock_ticket.creator_id = 555666777  # Same as staff member
        mock_ticket.assigned_to = None
        mock_ticket.status = TicketStatus.OPEN.value
        mock_get_ticket.return_value = mock_ticket
        
        # Mock staff role
        mock_get_role.return_value = "STAFF"
        
        # Create mock context
        mock_ctx = Mock(spec=interactions.SlashContext)
        mock_ctx.channel = Mock()
        mock_ctx.channel.id = "123456789"
        mock_ctx.guild = Mock()
        mock_ctx.guild.id = "987654321"
        mock_ctx.author = Mock(spec=interactions.Member)
        mock_ctx.author.id = "555666777"
        mock_ctx.send = AsyncMock()
        
        # Execute command
        await self.command._execute(mock_ctx)
        
        # Verify self-claim prevention
        mock_ctx.send.assert_called_once()
        call_args = mock_ctx.send.call_args[1]
        assert "❌ You cannot claim your own ticket." in call_args["content"]
        assert call_args["ephemeral"] == True
    
    @pytest.mark.asyncio
    @patch("app.commands.implementations.claim.get_db_session")
    @patch("app.commands.implementations.claim.get_ticket_by_channel_id")
    @patch("app.commands.implementations.claim.get_user_by_discord_id")
    @patch("app.commands.implementations.claim.get_user_role_in_guild")
    @patch("app.auth.generate_token")
    @patch("httpx.AsyncClient")
    async def test_integration_api_error_handling(
        self, mock_http_client, mock_generate_token, mock_get_role,
        mock_get_user, mock_get_ticket, mock_get_db
    ):
        """Test integration with API error handling."""
        # Setup mocks
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        # Mock author user
        mock_author_user = Mock()
        mock_author_user.id = "mock-user-uuid"
        mock_author_user.email = "staff@example.com"
        mock_get_user.return_value = mock_author_user
        
        # Create mock ticket
        mock_ticket = Mock(spec=Ticket)
        mock_ticket.id = 123
        mock_ticket.creator_id = 111222333
        mock_ticket.assigned_to = None
        mock_ticket.status = TicketStatus.OPEN.value
        mock_get_ticket.return_value = mock_ticket
        
        # Mock staff role
        mock_get_role.return_value = "STAFF"
        
        # Mock JWT token generation
        mock_generate_token.return_value = "mock-jwt-token"
        
        # Mock API error response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_http_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        
        # Create mock context
        mock_ctx = Mock(spec=interactions.SlashContext)
        mock_ctx.channel = Mock()
        mock_ctx.channel.id = "123456789"
        mock_ctx.guild = Mock()
        mock_ctx.guild.id = "987654321"
        mock_ctx.author = Mock(spec=interactions.Member)
        mock_ctx.author.id = "555666777"
        mock_ctx.defer = AsyncMock()
        mock_ctx.edit_original_response = AsyncMock()
        
        # Execute command
        await self.command._execute(mock_ctx)
        
        # Verify error handling
        mock_ctx.defer.assert_called_once_with(ephemeral=True)
        mock_ctx.edit_original_response.assert_called_once()
        call_args = mock_ctx.edit_original_response.call_args[1]
        assert "❌ Failed to claim ticket. Please try again later." in call_args["content"]
    
    @pytest.mark.asyncio
    @patch("app.commands.implementations.claim.get_db_session")
    @patch("app.commands.implementations.claim.get_ticket_by_channel_id")
    @patch("app.commands.implementations.claim.get_user_by_discord_id")
    @patch("app.commands.implementations.claim.get_user_role_in_guild")
    @patch("app.auth.generate_token")
    @patch("httpx.AsyncClient")
    async def test_integration_connection_error_handling(
        self, mock_http_client, mock_generate_token, mock_get_role,
        mock_get_user, mock_get_ticket, mock_get_db
    ):
        """Test integration with connection error handling."""
        # Setup mocks
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        # Mock author user
        mock_author_user = Mock()
        mock_author_user.id = "mock-user-uuid"
        mock_author_user.email = "staff@example.com"
        mock_get_user.return_value = mock_author_user
        
        # Create mock ticket
        mock_ticket = Mock(spec=Ticket)
        mock_ticket.id = 123
        mock_ticket.creator_id = 111222333
        mock_ticket.assigned_to = None
        mock_ticket.status = TicketStatus.OPEN.value
        mock_get_ticket.return_value = mock_ticket
        
        # Mock staff role
        mock_get_role.return_value = "STAFF"
        
        # Mock JWT token generation
        mock_generate_token.return_value = "mock-jwt-token"
        
        # Mock connection error
        mock_http_client.return_value.__aenter__.return_value.post = AsyncMock(
            side_effect=httpx.RequestError("Connection failed")
        )
        
        # Create mock context
        mock_ctx = Mock(spec=interactions.SlashContext)
        mock_ctx.channel = Mock()
        mock_ctx.channel.id = "123456789"
        mock_ctx.guild = Mock()
        mock_ctx.guild.id = "987654321"
        mock_ctx.author = Mock(spec=interactions.Member)
        mock_ctx.author.id = "555666777"
        mock_ctx.defer = AsyncMock()
        mock_ctx.edit_original_response = AsyncMock()
        
        # Execute command
        await self.command._execute(mock_ctx)
        
        # Verify connection error handling
        mock_ctx.defer.assert_called_once_with(ephemeral=True)
        mock_ctx.edit_original_response.assert_called_once()
        call_args = mock_ctx.edit_original_response.call_args[1]
        assert "❌ Failed to claim ticket due to connection error" in call_args["content"]
    
    @pytest.mark.asyncio
    @patch("app.commands.implementations.claim.get_db_session")
    @patch("app.commands.implementations.claim.get_ticket_by_channel_id")
    @patch("app.commands.implementations.claim.get_user_by_discord_id")
    @patch("app.commands.implementations.claim.get_user_role_in_guild")
    @patch("app.auth.generate_token")
    @patch("httpx.AsyncClient")
    async def test_complete_claim_flow_admin(
        self, mock_http_client, mock_generate_token, mock_get_role,
        mock_get_user, mock_get_ticket, mock_get_db
    ):
        """Test complete claim flow for admin claiming ticket."""
        # Setup mocks
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        # Mock author user for permission check
        mock_author_user = Mock()
        mock_author_user.id = "mock-admin-uuid"
        mock_author_user.email = "admin@example.com"
        mock_get_user.return_value = mock_author_user
        
        # Create mock ticket
        mock_ticket = Mock(spec=Ticket)
        mock_ticket.id = 123
        mock_ticket.creator_id = 111222333
        mock_ticket.assigned_to = None
        mock_ticket.status = TicketStatus.OPEN.value
        mock_ticket.reason = "Test ticket"
        mock_ticket.created_at = datetime.utcnow()
        mock_get_ticket.return_value = mock_ticket
        
        # Mock admin role
        mock_get_role.return_value = "ADMIN"
        
        # Mock JWT token generation
        mock_generate_token.return_value = "mock-jwt-token"
        
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "message": "Ticket claimed successfully",
            "ticket": {"id": 123, "assigned_to": 444555666}
        }
        mock_http_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        
        # Create mock context
        mock_ctx = Mock(spec=interactions.SlashContext)
        mock_ctx.channel = Mock()
        mock_ctx.channel.id = "123456789"
        mock_ctx.channel.edit = AsyncMock()
        mock_ctx.channel.send = AsyncMock()
        mock_ctx.guild = Mock()
        mock_ctx.guild.id = "987654321"
        mock_ctx.guild.name = "Test Guild"
        mock_ctx.guild.fetch_member = AsyncMock()
        mock_ctx.author = Mock(spec=interactions.Member)
        mock_ctx.author.id = "444555666"  # Admin user
        mock_ctx.author.mention = "<@444555666>"
        mock_ctx.defer = AsyncMock()
        mock_ctx.edit_original_response = AsyncMock()
        
        # Mock creator for notification
        mock_creator = Mock(spec=interactions.Member)
        mock_creator.id = 111222333
        mock_dm_channel = Mock()
        mock_dm_channel.send = AsyncMock()
        mock_creator.fetch_dm = AsyncMock(return_value=mock_dm_channel)
        mock_ctx.guild.fetch_member.return_value = mock_creator
        
        # Execute command
        await self.command._execute(mock_ctx)
        
        # Verify admin can claim tickets
        mock_get_user.assert_called_once_with(mock_db, 444555666)
        mock_get_role.assert_called_once_with(mock_db, "mock-admin-uuid", 987654321)
        
        # Verify successful execution
        mock_ctx.edit_original_response.assert_called_once()
        call_args = mock_ctx.edit_original_response.call_args[1]
        assert "✅ Successfully claimed ticket #123." in call_args["content"]
        
        # Verify creator notification
        mock_ctx.guild.fetch_member.assert_called_once_with(111222333)
        mock_creator.fetch_dm.assert_called_once()
        mock_dm_channel.send.assert_called_once()
