"""Tests for the Redis client."""

import os
import pytest
import asyncio
import json
from unittest.mock import patch, MagicMock, AsyncMock

# Add the parent directory to sys.path to allow imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from discord_bot.utils.redis_client import RedisClient


@pytest.fixture
def mock_redis():
    """Create a mock Redis client for testing."""
    mock_client = AsyncMock()
    mock_client.ping = AsyncMock(return_value=True)
    mock_client.publish = AsyncMock(return_value=1)
    
    # Create a mock pubsub
    mock_pubsub = AsyncMock()
    mock_pubsub.subscribe = AsyncMock()
    mock_pubsub.unsubscribe = AsyncMock()
    mock_pubsub.close = AsyncMock()
    
    # Configure the listen method to return a message
    async def mock_listen():
        yield {
            "type": "message",
            "channel": b"test_channel",
            "data": b'{"key": "value"}'
        }
    
    mock_pubsub.listen = mock_listen
    
    # Configure the redis client to return the mock pubsub
    mock_client.pubsub = MagicMock(return_value=mock_pubsub)
    
    return mock_client


@pytest.mark.asyncio
async def test_redis_client_initialization():
    """Test that the Redis client initializes correctly."""
    with patch("discord_bot.utils.redis_client.config", create=True) as mock_config:
        # Configure the mock
        mock_config.redis_url = "redis://localhost:6379"
        
        # Create the client
        client = RedisClient()
        
        # Check that the client was initialized correctly
        assert client.redis_url == "redis://localhost:6379"
        assert client.redis is None
        assert client.pubsub is None
        assert client.connected is False
        assert client.listener_task is None
        assert client.event_handlers == {}


@pytest.mark.asyncio
async def test_redis_client_connect_success(mock_redis):
    """Test that connect returns True when Redis is reachable."""
    with patch("discord_bot.utils.redis_client.config", create=True) as mock_config:
        # Configure the mock
        mock_config.redis_url = "redis://localhost:6379"
        
        with patch("discord_bot.utils.redis_client.redis.from_url", return_value=mock_redis):
            # Create the client
            client = RedisClient()
            
            # Call connect
            result = await client.connect()
            
            # Check that the method returned True
            assert result is True
            assert client.connected is True
            assert client.redis is mock_redis
            
            # Check that ping was called
            mock_redis.ping.assert_called_once()


@pytest.mark.asyncio
async def test_redis_client_connect_failure(mock_redis):
    """Test that connect returns False when Redis is not reachable."""
    with patch("discord_bot.utils.redis_client.config", create=True) as mock_config:
        # Configure the mock
        mock_config.redis_url = "redis://localhost:6379"
        
        with patch("discord_bot.utils.redis_client.redis.from_url", return_value=mock_redis):
            # Configure the mock to raise an exception
            mock_redis.ping.side_effect = Exception("Connection refused")
            
            # Create the client
            client = RedisClient()
            
            # Call connect
            result = await client.connect()
            
            # Check that the method returned False
            assert result is False
            assert client.connected is False


@pytest.mark.asyncio
async def test_redis_client_subscribe(mock_redis):
    """Test the subscribe method."""
    with patch("discord_bot.utils.redis_client.config", create=True) as mock_config:
        # Configure the mock
        mock_config.redis_url = "redis://localhost:6379"
        
        with patch("discord_bot.utils.redis_client.redis.from_url", return_value=mock_redis):
            # Create the client
            client = RedisClient()
            
            # Call subscribe
            await client.subscribe(["channel1", "channel2"])
            
            # Check that the pubsub was created and subscribe was called
            assert client.pubsub is not None
            mock_redis.pubsub.assert_called_once()
            client.pubsub.subscribe.assert_called_once_with("channel1", "channel2")


@pytest.mark.asyncio
async def test_redis_client_publish(mock_redis):
    """Test the publish method."""
    with patch("discord_bot.utils.redis_client.config", create=True) as mock_config:
        # Configure the mock
        mock_config.redis_url = "redis://localhost:6379"
        
        with patch("discord_bot.utils.redis_client.redis.from_url", return_value=mock_redis):
            # Create the client
            client = RedisClient()
            client.redis = mock_redis
            client.connected = True
            
            # Call publish
            await client.publish("test_channel", {"key": "value"})
            
            # Check that publish was called with the correct arguments
            mock_redis.publish.assert_called_once_with("test_channel", json.dumps({"key": "value"}))


@pytest.mark.asyncio
async def test_redis_client_register_handler():
    """Test the register_handler method."""
    with patch("discord_bot.utils.redis_client.config", create=True) as mock_config:
        # Configure the mock
        mock_config.redis_url = "redis://localhost:6379"
        
        # Create the client
        client = RedisClient()
        
        # Create a mock handler
        async def mock_handler(data):
            pass
        
        # Register the handler
        client.register_handler("test_channel", mock_handler)
        
        # Check that the handler was registered
        assert "test_channel" in client.event_handlers
        assert mock_handler in client.event_handlers["test_channel"]


@pytest.mark.asyncio
async def test_redis_client_start_listener(mock_redis):
    """Test the start_listener method."""
    with patch("discord_bot.utils.redis_client.config", create=True) as mock_config:
        # Configure the mock
        mock_config.redis_url = "redis://localhost:6379"
        
        with patch("discord_bot.utils.redis_client.redis.from_url", return_value=mock_redis):
            # Create the client
            client = RedisClient()
            client.redis = mock_redis
            client.pubsub = mock_redis.pubsub()
            
            # Create a mock handler
            async def mock_handler(data):
                pass
            
            # Register the handler
            client.register_handler("test_channel", mock_handler)
            
            # Call start_listener
            with patch("asyncio.create_task") as mock_create_task:
                await client.start_listener()
                
                # Check that create_task was called
                mock_create_task.assert_called_once()
                assert client.listener_task is not None