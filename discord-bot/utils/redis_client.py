"""Redis client for real-time synchronization."""

import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional
import redis.asyncio as redis

from discord_bot.config.settings import config, logger

class RedisClient:
    """Redis client for real-time synchronization."""
    
    def __init__(self):
        """Initialize the Redis client with configuration."""
        self.redis_url = config.redis_url
        self.redis = None
        self.pubsub = None
        self.connected = False
        self.listener_task = None
        self.event_handlers = {}
    
    async def connect(self) -> bool:
        """Connect to Redis server."""
        try:
            self.redis = redis.from_url(self.redis_url)
            # Test connection
            await self.redis.ping()
            self.connected = True
            logger.info("Connected to Redis server")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.connected = False
            return False
    
    async def subscribe(self, channels: List[str]) -> None:
        """Subscribe to Redis channels.
        
        Args:
            channels: List of channel names to subscribe to
        """
        if not self.connected:
            await self.connect()
        
        if not self.pubsub:
            self.pubsub = self.redis.pubsub()
        
        await self.pubsub.subscribe(*channels)
        logger.info(f"Subscribed to Redis channels: {channels}")
    
    async def publish(self, channel: str, message: Dict[str, Any]) -> None:
        """Publish a message to a Redis channel.
        
        Args:
            channel: Channel name
            message: Message data to publish
        """
        if not self.connected:
            await self.connect()
        
        await self.redis.publish(channel, json.dumps(message))
    
    async def start_listener(self) -> None:
        """Start the Redis message listener."""
        if not self.pubsub:
            logger.error("Cannot start listener: not subscribed to any channels")
            return
        
        if self.listener_task:
            logger.warning("Listener already running")
            return
        
        self.listener_task = asyncio.create_task(self._listen_for_messages())
        logger.info("Started Redis message listener")
    
    async def stop_listener(self) -> None:
        """Stop the Redis message listener."""
        if self.listener_task:
            self.listener_task.cancel()
            try:
                await self.listener_task
            except asyncio.CancelledError:
                pass
            self.listener_task = None
            logger.info("Stopped Redis message listener")
    
    async def _listen_for_messages(self) -> None:
        """Listen for messages on subscribed channels."""
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    channel = message["channel"].decode("utf-8")
                    data = json.loads(message["data"].decode("utf-8"))
                    
                    # Call registered handlers for this channel
                    if channel in self.event_handlers:
                        for handler in self.event_handlers[channel]:
                            try:
                                await handler(data)
                            except Exception as e:
                                logger.error(f"Error in Redis event handler: {e}")
        except asyncio.CancelledError:
            logger.info("Redis listener cancelled")
        except Exception as e:
            logger.error(f"Error in Redis listener: {e}")
            # Attempt to reconnect
            await asyncio.sleep(5)
            await self.start_listener()
    
    def register_handler(self, channel: str, handler: Callable) -> None:
        """Register a handler function for a specific channel.
        
        Args:
            channel: Channel name
            handler: Async function to call when a message is received
        """
        if channel not in self.event_handlers:
            self.event_handlers[channel] = []
        
        self.event_handlers[channel].append(handler)
        logger.info(f"Registered handler for channel: {channel}")
    
    async def close(self) -> None:
        """Close the Redis connection."""
        if self.listener_task:
            await self.stop_listener()
        
        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()
        
        if self.redis:
            await self.redis.close()
        
        self.connected = False
        logger.info("Closed Redis connection")


# Create a global Redis client instance
redis_client = None


async def get_redis_client() -> RedisClient:
    """Get or create the Redis client instance."""
    global redis_client
    if redis_client is None:
        redis_client = RedisClient()
        await redis_client.connect()
    return redis_client