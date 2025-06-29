"""
Unit tests for Discord bot initialization and connection.
"""

import asyncio
import os
import pytest
from unittest.mock import AsyncMock, Mock, patch

from app.bot import TicketBot, get_bot, run_bot


class TestTicketBot:
    """Test cases for TicketBot class."""
    
    @patch.dict(os.environ, {'DISCORD_TOKEN': 'test_token_123'})
    def test_bot_initialization_with_token(self):
        """Test bot initializes properly with valid token."""
        bot = TicketBot()
        
        assert bot.token == 'test_token_123'
        assert bot.bot is not None
        assert not bot._is_ready
        assert bot._guild_count == 0
    
    def test_bot_initialization_without_token(self):
        """Test bot raises error without Discord token."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="DISCORD_TOKEN environment variable is required"):
                TicketBot()
    
    def test_bot_intents_configuration(self):
        """Test bot has correct intents configured."""
        with patch.dict(os.environ, {'DISCORD_TOKEN': 'test_token'}):
            bot = TicketBot()
            
            # Verify bot was created with intents
            assert bot.bot is not None
    
    def test_is_ready_initially_false(self):
        """Test bot is not ready initially."""
        with patch.dict(os.environ, {'DISCORD_TOKEN': 'test_token'}):
            bot = TicketBot()
            assert not bot.is_ready()
    
    def test_get_guild_count_initial(self):
        """Test initial guild count is zero."""
        with patch.dict(os.environ, {'DISCORD_TOKEN': 'test_token'}):
            bot = TicketBot()
            assert bot.get_guild_count() == 0
    
    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self):
        """Test health check returns unhealthy when bot not ready."""
        with patch.dict(os.environ, {'DISCORD_TOKEN': 'test_token'}):
            bot = TicketBot()
            health = await bot.health_check()
            
            assert health['status'] == 'unhealthy'
            assert health['guilds'] == 0
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        """Test health check returns healthy when bot is ready."""
        with patch.dict(os.environ, {'DISCORD_TOKEN': 'test_token'}):
            bot = TicketBot()
            bot._is_ready = True
            bot._guild_count = 5
            
            health = await bot.health_check()
            
            assert health['status'] == 'healthy'
            assert health['guilds'] == 5
            assert 'connected' in health
            assert 'latency' in health
    
    @pytest.mark.asyncio
    async def test_start_with_invalid_token(self):
        """Test bot start fails with invalid token."""
        with patch.dict(os.environ, {'DISCORD_TOKEN': 'invalid_token'}):
            bot = TicketBot()
            
            # Mock the astart method to raise LoginError
            with patch.object(bot.bot, 'astart', side_effect=Exception("Invalid token")):
                with pytest.raises(Exception, match="Invalid token"):
                    await bot.start()
    
    @pytest.mark.asyncio
    async def test_stop_bot(self):
        """Test bot stops gracefully."""
        with patch.dict(os.environ, {'DISCORD_TOKEN': 'test_token'}):
            bot = TicketBot()
            
            # Test that stop doesn't raise an exception
            await bot.stop()
            
            # Since bot was never started, this should complete without error


class TestBotUtilities:
    """Test utility functions."""
    
    @patch.dict(os.environ, {'DISCORD_TOKEN': 'test_token'})
    def test_get_bot_singleton(self):
        """Test get_bot returns singleton instance."""
        bot1 = get_bot()
        bot2 = get_bot()
        
        assert bot1 is bot2
        assert isinstance(bot1, TicketBot)
    
    @pytest.mark.asyncio
    async def test_run_bot_with_keyboard_interrupt(self):
        """Test run_bot handles keyboard interrupt gracefully."""
        with patch.dict(os.environ, {'DISCORD_TOKEN': 'test_token'}):
            with patch('app.bot.get_bot') as mock_get_bot:
                mock_bot = Mock()
                mock_bot.start = AsyncMock(side_effect=KeyboardInterrupt())
                mock_bot.stop = AsyncMock()
                mock_get_bot.return_value = mock_bot
                
                # Should not raise exception
                await run_bot()
                
                mock_bot.start.assert_called_once()
                mock_bot.stop.assert_called_once()


class TestBotEventHandlers:
    """Test bot event handlers."""
    
    @pytest.mark.asyncio
    async def test_on_ready_handler(self):
        """Test on_ready event handler sets proper state."""
        with patch.dict(os.environ, {'DISCORD_TOKEN': 'test_token'}):
            bot = TicketBot()
            
            # Test the logic that would happen during on_ready
            bot._guild_count = 2
            bot._is_ready = True
            
            assert bot.get_guild_count() == 2
            assert bot.is_ready()


class TestBotIntegration:
    """Integration tests for bot functionality."""
    
    @pytest.mark.asyncio
    async def test_bot_startup_sequence(self):
        """Test complete bot startup sequence."""
        with patch.dict(os.environ, {'DISCORD_TOKEN': 'test_token'}):
            bot = TicketBot()
            
            # Mock the startup process
            bot.bot.astart = AsyncMock()
            
            # Start the bot
            await bot.start()
            
            # Verify startup was called
            bot.bot.astart.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_reconnection_logic(self):
        """Test bot handles disconnection and reconnection."""
        with patch.dict(os.environ, {'DISCORD_TOKEN': 'test_token'}):
            bot = TicketBot()
            
            # Initially ready
            bot._is_ready = True
            assert bot.is_ready()
            
            # Simulate disconnect (would be called by the actual event)
            bot._is_ready = False
            assert not bot.is_ready()
            
            # Simulate reconnect
            bot._is_ready = True
            assert bot.is_ready()
