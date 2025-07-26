"""Tests for Discord bot error handling functionality.

This module tests the comprehensive error handling system for the Discord bot
including custom exceptions, error handlers, and decorators.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import discord
from discord.ext import commands

from bot.exceptions import (
    DiscordBotException,
    DiscordAPIError,
    PermissionError,
    ChannelError,
    TicketError,
    BackendConnectionError,
    RateLimitError,
    ConfigurationError,
    CommandError,
    ValidationError
)
from bot.error_handler import (
    ErrorHandler,
    handle_discord_errors,
    handle_rate_limits,
    graceful_degradation
)


class TestDiscordBotExceptions:
    """Test Discord bot custom exception classes."""
    
    def test_discord_bot_exception_base(self):
        """Test base DiscordBotException."""
        exc = DiscordBotException(
            message="Test error",
            error_code="TEST_ERROR",
            details={"key": "value"},
            user_message="User friendly message"
        )
        
        assert str(exc) == "Test error"
        assert exc.message == "Test error"
        assert exc.error_code == "TEST_ERROR"
        assert exc.details == {"key": "value"}
        assert exc.user_message == "User friendly message"
    
    def test_discord_api_error(self):
        """Test DiscordAPIError exception."""
        discord_error = discord.Forbidden(Mock(), "Forbidden")
        exc = DiscordAPIError(
            message="API error",
            status_code=403,
            discord_error=discord_error
        )
        
        assert exc.error_code == "DISCORD_API_ERROR"
        assert exc.details["status_code"] == 403
        assert exc.details["discord_error_type"] == "Forbidden"
        assert "permission" in exc.user_message.lower()
    
    def test_permission_error(self):
        """Test PermissionError exception."""
        exc = PermissionError(
            message="Permission denied",
            required_permission="manage_channels",
            user_id=123456789,
            guild_id=987654321
        )
        
        assert exc.error_code == "PERMISSION_ERROR"
        assert exc.details["required_permission"] == "manage_channels"
        assert exc.details["user_id"] == 123456789
        assert exc.details["guild_id"] == 987654321
        assert "permission" in exc.user_message.lower()
    
    def test_channel_error(self):
        """Test ChannelError exception."""
        exc = ChannelError(
            message="Channel not found",
            channel_id=123456789,
            channel_type="text"
        )
        
        assert exc.error_code == "CHANNEL_ERROR"
        assert exc.details["channel_id"] == 123456789
        assert exc.details["channel_type"] == "text"
    
    def test_ticket_error(self):
        """Test TicketError exception."""
        exc = TicketError(
            message="Ticket operation failed",
            ticket_id="ticket-123",
            channel_id=123456789,
            operation="create"
        )
        
        assert exc.error_code == "TICKET_ERROR"
        assert exc.details["ticket_id"] == "ticket-123"
        assert exc.details["channel_id"] == 123456789
        assert exc.details["operation"] == "create"
    
    def test_backend_connection_error(self):
        """Test BackendConnectionError exception."""
        exc = BackendConnectionError(
            message="Backend connection failed",
            endpoint="/api/tickets",
            status_code=500
        )
        
        assert exc.error_code == "BACKEND_CONNECTION_ERROR"
        assert exc.details["endpoint"] == "/api/tickets"
        assert exc.details["status_code"] == 500
        assert "backend" in exc.user_message.lower()
    
    def test_rate_limit_error(self):
        """Test RateLimitError exception."""
        exc = RateLimitError(
            message="Rate limit exceeded",
            service="discord",
            retry_after=30.5
        )
        
        assert exc.error_code == "RATE_LIMIT_ERROR"
        assert exc.details["service"] == "discord"
        assert exc.details["retry_after"] == 30.5
        assert "30.5 seconds" in exc.user_message


class TestErrorHandler:
    """Test ErrorHandler class."""
    
    @pytest.fixture
    def mock_bot(self):
        """Create mock bot instance."""
        bot = Mock()
        bot.user = Mock()
        bot.user.id = 123456789
        return bot
    
    @pytest.fixture
    def error_handler(self, mock_bot):
        """Create ErrorHandler instance."""
        return ErrorHandler(mock_bot)
    
    @pytest.fixture
    def mock_interaction(self):
        """Create mock Discord interaction."""
        interaction = Mock(spec=discord.Interaction)
        interaction.user = Mock()
        interaction.user.id = 987654321
        interaction.guild_id = 111111111
        interaction.channel_id = 222222222
        interaction.command = Mock()
        interaction.command.name = "test_command"
        interaction.response = Mock()
        interaction.response.is_done.return_value = False
        interaction.response.send_message = AsyncMock()
        interaction.followup = Mock()
        interaction.followup.send = AsyncMock()
        return interaction
    
    @pytest.mark.asyncio
    async def test_handle_discord_forbidden_error(self, error_handler, mock_interaction):
        """Test handling Discord Forbidden errors."""
        error = discord.Forbidden(Mock(), "Forbidden")
        
        result = await error_handler.handle_discord_error(error, mock_interaction)
        
        assert result is True
        mock_interaction.response.send_message.assert_called_once()
        args, kwargs = mock_interaction.response.send_message.call_args
        assert "permission" in args[0].lower()
        assert kwargs.get("ephemeral") is True
    
    @pytest.mark.asyncio
    async def test_handle_discord_not_found_error(self, error_handler, mock_interaction):
        """Test handling Discord NotFound errors."""
        error = discord.NotFound(Mock(), "Not Found")
        
        result = await error_handler.handle_discord_error(error, mock_interaction)
        
        assert result is True
        mock_interaction.response.send_message.assert_called_once()
        args, kwargs = mock_interaction.response.send_message.call_args
        assert "not found" in args[0].lower()
    
    @pytest.mark.asyncio
    async def test_handle_discord_rate_limit_error(self, error_handler, mock_interaction):
        """Test handling Discord rate limit errors."""
        error = discord.HTTPException(Mock(), "Rate Limited")
        error.status = 429
        error.retry_after = 30.0
        
        result = await error_handler.handle_discord_error(error, mock_interaction)
        
        assert result is True
        mock_interaction.response.send_message.assert_called_once()
        args, kwargs = mock_interaction.response.send_message.call_args
        assert "rate limit" in args[0].lower()
        assert "30.0 seconds" in args[0]
    
    @pytest.mark.asyncio
    async def test_handle_custom_discord_bot_error(self, error_handler, mock_interaction):
        """Test handling custom DiscordBotException errors."""
        error = TicketError(
            message="Ticket creation failed",
            ticket_id="test-123",
            operation="create"
        )
        
        result = await error_handler.handle_discord_error(error, mock_interaction)
        
        assert result is True
        mock_interaction.response.send_message.assert_called_once()
        args, kwargs = mock_interaction.response.send_message.call_args
        assert args[0] == error.user_message
    
    @pytest.mark.asyncio
    async def test_handle_command_cooldown_error(self, error_handler, mock_interaction):
        """Test handling command cooldown errors."""
        error = Mock()
        error.retry_after = 15.5
        
        await error_handler.handle_command_error(mock_interaction, error)
        
        mock_interaction.response.send_message.assert_called_once()
        args, kwargs = mock_interaction.response.send_message.call_args
        assert "cooldown" in args[0].lower()
        assert "15.5" in args[0]
    
    @pytest.mark.asyncio
    async def test_handle_missing_permissions_error(self, error_handler, mock_interaction):
        """Test handling missing permissions errors."""
        error = commands.MissingPermissions(["manage_channels", "manage_messages"])
        
        await error_handler.handle_command_error(mock_interaction, error)
        
        mock_interaction.response.send_message.assert_called_once()
        args, kwargs = mock_interaction.response.send_message.call_args
        assert "manage_channels" in args[0]
        assert "manage_messages" in args[0]
    
    @pytest.mark.asyncio
    async def test_send_error_response_with_done_interaction(self, error_handler, mock_interaction):
        """Test sending error response when interaction is already done."""
        mock_interaction.response.is_done.return_value = True
        
        await error_handler._send_error_response(mock_interaction, "Test message")
        
        mock_interaction.followup.send.assert_called_once_with("Test message", ephemeral=True)
        mock_interaction.response.send_message.assert_not_called()
    
    def test_track_rate_limit(self, error_handler):
        """Test rate limit tracking."""
        error_handler._track_rate_limit("test_command", 30.0)
        
        assert "test_command" in error_handler.rate_limit_tracker
        assert len(error_handler.rate_limit_tracker["test_command"]) == 1
        assert error_handler.rate_limit_tracker["test_command"][0]["retry_after"] == 30.0
    
    def test_track_error(self, error_handler):
        """Test error tracking."""
        error_handler._track_error("TestError")
        error_handler._track_error("TestError")
        error_handler._track_error("AnotherError")
        
        assert error_handler.error_counts["TestError"] == 2
        assert error_handler.error_counts["AnotherError"] == 1
    
    def test_get_error_stats(self, error_handler):
        """Test getting error statistics."""
        error_handler._track_error("TestError")
        error_handler._track_rate_limit("test_command", 30.0)
        
        stats = error_handler.get_error_stats()
        
        assert "error_counts" in stats
        assert "rate_limit_tracker" in stats
        assert "last_reset" in stats
        assert stats["error_counts"]["TestError"] == 1
        assert stats["rate_limit_tracker"]["test_command"] == 1


class TestErrorDecorators:
    """Test error handling decorators."""
    
    @pytest.mark.asyncio
    async def test_handle_discord_errors_decorator(self):
        """Test handle_discord_errors decorator."""
        @handle_discord_errors(user_message="Custom error message")
        async def failing_function():
            raise discord.Forbidden(Mock(), "Forbidden")
        
        # Should not raise exception
        result = await failing_function()
        assert result is None
    
    @pytest.mark.asyncio
    async def test_handle_discord_errors_decorator_with_reraise(self):
        """Test handle_discord_errors decorator with reraise."""
        @handle_discord_errors(reraise=True)
        async def failing_function():
            raise discord.Forbidden(Mock(), "Forbidden")
        
        with pytest.raises(discord.Forbidden):
            await failing_function()
    
    @pytest.mark.asyncio
    async def test_handle_rate_limits_decorator_success(self):
        """Test handle_rate_limits decorator with successful operation."""
        call_count = 0
        
        @handle_rate_limits(max_retries=2, base_delay=0.01)
        async def test_function():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await test_function()
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_handle_rate_limits_decorator_with_retry(self):
        """Test handle_rate_limits decorator with retry logic."""
        call_count = 0
        
        @handle_rate_limits(max_retries=2, base_delay=0.01)
        async def test_function():
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                error = discord.HTTPException(Mock(), "Rate Limited")
                error.status = 429
                error.retry_after = 0.01
                raise error
            return "success"
        
        result = await test_function()
        assert result == "success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_handle_rate_limits_decorator_max_retries_exceeded(self):
        """Test handle_rate_limits decorator when max retries exceeded."""
        @handle_rate_limits(max_retries=1, base_delay=0.01)
        async def test_function():
            error = discord.HTTPException(Mock(), "Rate Limited")
            error.status = 429
            error.retry_after = 0.01
            raise error
        
        with pytest.raises(RateLimitError):
            await test_function()
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_decorator_success(self):
        """Test graceful_degradation decorator with successful operation."""
        @graceful_degradation(fallback_value="fallback")
        async def test_function():
            return "success"
        
        result = await test_function()
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_decorator_with_error(self):
        """Test graceful_degradation decorator with error."""
        @graceful_degradation(fallback_value="fallback")
        async def test_function():
            raise ValueError("Test error")
        
        result = await test_function()
        assert result == "fallback"
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_decorator_no_logging(self):
        """Test graceful_degradation decorator without logging."""
        @graceful_degradation(fallback_value="fallback", log_errors=False)
        async def test_function():
            raise ValueError("Test error")
        
        with patch('bot.error_handler.logger') as mock_logger:
            result = await test_function()
            assert result == "fallback"
            mock_logger.warning.assert_not_called()


class TestErrorHandlerIntegration:
    """Test error handler integration scenarios."""
    
    @pytest.fixture
    def mock_bot(self):
        """Create mock bot instance."""
        bot = Mock()
        bot.user = Mock()
        bot.user.id = 123456789
        return bot
    
    @pytest.fixture
    def error_handler(self, mock_bot):
        """Create ErrorHandler instance."""
        return ErrorHandler(mock_bot)
    
    @pytest.mark.asyncio
    async def test_multiple_error_tracking(self, error_handler):
        """Test tracking multiple errors over time."""
        # Track various errors
        for _ in range(5):
            error_handler._track_error("PermissionError")
        for _ in range(3):
            error_handler._track_error("RateLimitError")
        for _ in range(2):
            error_handler._track_error("ChannelError")
        
        stats = error_handler.get_error_stats()
        
        assert stats["error_counts"]["PermissionError"] == 5
        assert stats["error_counts"]["RateLimitError"] == 3
        assert stats["error_counts"]["ChannelError"] == 2
    
    @pytest.mark.asyncio
    async def test_rate_limit_tracking_cleanup(self, error_handler):
        """Test rate limit tracking cleanup of old entries."""
        from datetime import datetime, timedelta
        
        # Add old entries
        old_time = datetime.utcnow() - timedelta(hours=2)
        error_handler.rate_limit_tracker["test_command"] = [
            {"timestamp": old_time, "retry_after": 30.0}
        ]
        
        # Add new entry (this should trigger cleanup)
        error_handler._track_rate_limit("test_command", 15.0)
        
        # Old entry should be removed
        assert len(error_handler.rate_limit_tracker["test_command"]) == 1
        assert error_handler.rate_limit_tracker["test_command"][0]["retry_after"] == 15.0
    
    @pytest.mark.asyncio
    async def test_error_count_reset(self, error_handler):
        """Test error count reset after time period."""
        from datetime import datetime, timedelta
        
        # Track some errors
        error_handler._track_error("TestError")
        assert error_handler.error_counts["TestError"] == 1
        
        # Simulate time passing
        error_handler.last_error_reset = datetime.utcnow() - timedelta(hours=2)
        
        # Track another error (should trigger reset)
        error_handler._track_error("AnotherError")
        
        # Previous counts should be cleared
        assert "TestError" not in error_handler.error_counts
        assert error_handler.error_counts["AnotherError"] == 1


if __name__ == "__main__":
    pytest.main([__file__])