"""
Test-specific Redis service for integration tests.
Provides mock Redis service for testing.
"""
from unittest.mock import AsyncMock
from typing import Callable, Any


class TestRedisService:
    """Test-specific Redis service with mock functionality."""
    
    def __init__(self):
        """Initialize test Redis service."""
        self._subscribers = {}
        self._published_messages = []
    
    async def publish(self, channel: str, message: str):
        """Mock publish method."""
        self._published_messages.append({"channel": channel, "message": message})
        
        # Trigger subscribers if any
        if channel in self._subscribers:
            for callback in self._subscribers[channel]:
                await callback(channel, message)
    
    async def subscribe(self, channel: str, callback: Callable):
        """Mock subscribe method."""
        if channel not in self._subscribers:
            self._subscribers[channel] = []
        self._subscribers[channel].append(callback)
    
    async def cleanup(self):
        """Mock cleanup method."""
        self._subscribers.clear()
        self._published_messages.clear()
    
    def get_published_messages(self):
        """Get all published messages for testing."""
        return self._published_messages.copy()
    
    def get_subscribers(self):
        """Get all subscribers for testing."""
        return self._subscribers.copy()