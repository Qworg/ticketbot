"""Tests for Redis pub/sub service."""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from backend.services.redis_service import (
    RedisService, EventType, TICKET_EVENTS_CHANNEL,
    MESSAGE_EVENTS_CHANNEL, TRANSCRIPT_EVENTS_CHANNEL
)


@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client."""
    client = AsyncMock()
    client.pubsub.return_value = AsyncMock()
    return client


@pytest.fixture
def redis_service(mock_redis_client):
    """Create a Redis service with mock client."""
    return RedisService(mock_redis_client)


@pytest.mark.asyncio
async def test_publish_event(redis_service, mock_redis_client):
    """Test publishing an event to Redis."""
    # Arrange
    channel = TICKET_EVENTS_CHANNEL
    event_type = EventType.TICKET_CREATED
    data = {"id": str(uuid4()), "title": "Test Ticket"}
    
    # Act
    result = await redis_service.publish_event(channel, event_type, data)
    
    # Assert
    assert result is True
    mock_redis_client.publish.assert_called_once()
    
    # Verify the published message format
    call_args = mock_redis_client.publish.call_args
    assert call_args[0][0] == channel
    
    # Parse the JSON message to verify structure
    message = json.loads(call_args[0][1])
    assert message["type"] == event_type
    assert message["data"] == data


@pytest.mark.asyncio
async def test_publish_ticket_event(redis_service):
    """Test publishing a ticket event."""
    # Arrange
    event_type = EventType.TICKET_UPDATED
    data = {"id": str(uuid4()), "title": "Updated Ticket"}
    
    # Mock the publish_event method
    redis_service.publish_event = AsyncMock(return_value=True)
    
    # Act
    result = await redis_service.publish_ticket_event(event_type, data)
    
    # Assert
    assert result is True
    redis_service.publish_event.assert_called_once_with(
        TICKET_EVENTS_CHANNEL, event_type, data
    )


@pytest.mark.asyncio
async def test_publish_message_event(redis_service):
    """Test publishing a message event."""
    # Arrange
    event_type = EventType.MESSAGE_CREATED
    data = {"id": str(uuid4()), "content": "Test message"}
    
    # Mock the publish_event method
    redis_service.publish_event = AsyncMock(return_value=True)
    
    # Act
    result = await redis_service.publish_message_event(event_type, data)
    
    # Assert
    assert result is True
    redis_service.publish_event.assert_called_once_with(
        MESSAGE_EVENTS_CHANNEL, event_type, data
    )


@pytest.mark.asyncio
async def test_subscribe(redis_service, mock_redis_client):
    """Test subscribing to Redis channels."""
    # Arrange
    channels = [TICKET_EVENTS_CHANNEL, MESSAGE_EVENTS_CHANNEL]
    
    # Act
    await redis_service.subscribe(channels)
    
    # Assert
    redis_service.pubsub.subscribe.assert_called_once_with(*channels)


@pytest.mark.asyncio
async def test_register_handler(redis_service):
    """Test registering an event handler."""
    # Arrange
    channel = TICKET_EVENTS_CHANNEL
    handler = AsyncMock()
    
    # Act
    await redis_service.register_handler(channel, handler)
    
    # Assert
    assert channel in redis_service._subscribers
    assert handler in redis_service._subscribers[channel]


@pytest.mark.asyncio
async def test_process_message(redis_service):
    """Test processing a Redis message."""
    # Arrange
    channel = TICKET_EVENTS_CHANNEL
    event_type = EventType.TICKET_CREATED
    data = {"id": str(uuid4()), "title": "Test Ticket"}
    
    # Create a message as it would come from Redis
    message = {
        "channel": channel.encode(),
        "data": json.dumps({"type": event_type, "data": data}).encode()
    }
    
    # Register a mock handler
    handler = AsyncMock()
    await redis_service.register_handler(channel, handler)
    
    # Act
    await redis_service._process_message(message)
    
    # Assert
    handler.assert_called_once_with(event_type, data)


@pytest.mark.asyncio
async def test_set_get_cache(redis_service, mock_redis_client):
    """Test setting and getting cache values."""
    # Arrange
    key = "test_key"
    value = {"name": "Test", "value": 123}
    ttl = 60
    
    # Mock Redis client responses
    mock_redis_client.setex.return_value = True
    mock_redis_client.get.return_value = json.dumps(value)
    
    # Act - Set cache
    set_result = await redis_service.set_cache(key, value, ttl)
    
    # Assert - Set cache
    assert set_result is True
    mock_redis_client.setex.assert_called_once_with(key, ttl, json.dumps(value))
    
    # Act - Get cache
    get_result = await redis_service.get_cache(key)
    
    # Assert - Get cache
    assert get_result == value
    mock_redis_client.get.assert_called_once_with(key)


@pytest.mark.asyncio
async def test_delete_cache(redis_service, mock_redis_client):
    """Test deleting cache values."""
    # Arrange
    key = "test_key"
    mock_redis_client.delete.return_value = 1
    
    # Act
    result = await redis_service.delete_cache(key)
    
    # Assert
    assert result is True
    mock_redis_client.delete.assert_called_once_with(key)


@pytest.mark.asyncio
async def test_check_health(redis_service, mock_redis_client):
    """Test health check."""
    # Arrange
    mock_redis_client.ping.return_value = True
    mock_redis_client.info.return_value = {
        "redis_version": "7.0.0",
        "used_memory_human": "1.5M",
        "used_memory_peak_human": "2.0M",
        "connected_clients": 5,
        "uptime_in_days": 2
    }
    
    # Act
    result = await redis_service.check_health()
    
    # Assert
    assert result["status"] == "healthy"
    assert "version" in result
    assert "memory" in result
    assert "clients" in result
    assert "uptime_days" in result
    mock_redis_client.ping.assert_called_once()
    mock_redis_client.info.assert_called_once()