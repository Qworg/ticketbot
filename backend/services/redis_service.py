"""Redis service for pub/sub messaging and caching.

This module provides a Redis service for:
1. Pub/sub messaging for real-time event broadcasting
2. Caching for improved performance
3. Connection pooling and management
4. Error handling and recovery
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, Optional, List, Callable, Awaitable, Union
from contextlib import asynccontextmanager

import redis.asyncio as redis
from redis.asyncio.client import Redis
from redis.asyncio.connection import ConnectionPool
from redis.exceptions import RedisError, ConnectionError

# Configure logger
logger = logging.getLogger(__name__)

# Get Redis configuration from environment variables
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
REDIS_POOL_SIZE = int(os.getenv("REDIS_POOL_SIZE", "10"))
REDIS_POOL_TIMEOUT = int(os.getenv("REDIS_POOL_TIMEOUT", "30"))
REDIS_SOCKET_TIMEOUT = int(os.getenv("REDIS_SOCKET_TIMEOUT", "5"))
REDIS_RETRY_ON_TIMEOUT = os.getenv("REDIS_RETRY_ON_TIMEOUT", "true").lower() == "true"

# Define event channels
TICKET_EVENTS_CHANNEL = "ticket_events"
MESSAGE_EVENTS_CHANNEL = "message_events"
TRANSCRIPT_EVENTS_CHANNEL = "transcript_events"
SYSTEM_EVENTS_CHANNEL = "system_events"

# Event types
class EventType:
    """Event types for the pub/sub system."""
    # Ticket events
    TICKET_CREATED = "ticket_created"
    TICKET_UPDATED = "ticket_updated"
    TICKET_CLOSED = "ticket_closed"
    TICKET_REOPENED = "ticket_reopened"
    TICKET_ASSIGNED = "ticket_assigned"
    
    # Message events
    MESSAGE_CREATED = "message_created"
    MESSAGE_UPDATED = "message_updated"
    MESSAGE_DELETED = "message_deleted"
    
    # Transcript events
    TRANSCRIPT_CREATED = "transcript_created"
    TRANSCRIPT_UPDATED = "transcript_updated"
    TRANSCRIPT_SHARED = "transcript_shared"
    
    # System events
    SYSTEM_ERROR = "system_error"
    SYSTEM_WARNING = "system_warning"
    SYSTEM_INFO = "system_info"


# Create Redis connection pool
redis_pool = ConnectionPool.from_url(
    REDIS_URL,
    max_connections=REDIS_POOL_SIZE,
    socket_timeout=REDIS_SOCKET_TIMEOUT,
    socket_connect_timeout=REDIS_SOCKET_TIMEOUT,
    retry_on_timeout=REDIS_RETRY_ON_TIMEOUT
)


class RedisService:
    """Redis service for pub/sub messaging and caching.
    
    This service provides methods for:
    1. Publishing events to Redis channels
    2. Subscribing to Redis channels
    3. Caching data with TTL
    4. Connection management and error handling
    
    Attributes:
        redis_client: Redis client instance
        pubsub: Redis pubsub instance for subscriptions
        _subscribers: Dictionary of event subscribers
    """
    
    def __init__(self, redis_client: Redis):
        """Initialize Redis service with client.
        
        Args:
            redis_client: Redis client instance
        """
        self.redis_client = redis_client
        self.pubsub = self.redis_client.pubsub()
        self._subscribers: Dict[str, List[Callable[[str, Dict[str, Any]], Awaitable[None]]]] = {}
        self._running_tasks = []
    
    async def publish_event(self, channel: str, event_type: str, data: Dict[str, Any]) -> bool:
        """Publish an event to a Redis channel.
        
        Args:
            channel: Redis channel to publish to
            event_type: Type of event (use EventType constants)
            data: Event data dictionary
            
        Returns:
            bool: True if published successfully, False otherwise
        """
        try:
            event_data = {
                "type": event_type,
                "data": data
            }
            message = json.dumps(event_data)
            await self.redis_client.publish(channel, message)
            logger.debug(f"Published event {event_type} to channel {channel}")
            return True
        except RedisError as e:
            logger.error(f"Error publishing event to Redis: {str(e)}")
            return False
    
    async def publish_ticket_event(self, event_type: str, ticket_data: Dict[str, Any]) -> bool:
        """Publish a ticket event.
        
        Args:
            event_type: Type of ticket event (use EventType constants)
            ticket_data: Ticket data dictionary
            
        Returns:
            bool: True if published successfully, False otherwise
        """
        return await self.publish_event(TICKET_EVENTS_CHANNEL, event_type, ticket_data)
    
    async def publish_message_event(self, event_type: str, message_data: Dict[str, Any]) -> bool:
        """Publish a message event.
        
        Args:
            event_type: Type of message event (use EventType constants)
            message_data: Message data dictionary
            
        Returns:
            bool: True if published successfully, False otherwise
        """
        return await self.publish_event(MESSAGE_EVENTS_CHANNEL, event_type, message_data)
    
    async def publish_transcript_event(self, event_type: str, transcript_data: Dict[str, Any]) -> bool:
        """Publish a transcript event.
        
        Args:
            event_type: Type of transcript event (use EventType constants)
            transcript_data: Transcript data dictionary
            
        Returns:
            bool: True if published successfully, False otherwise
        """
        return await self.publish_event(TRANSCRIPT_EVENTS_CHANNEL, event_type, transcript_data)
    
    async def publish_system_event(self, event_type: str, system_data: Dict[str, Any]) -> bool:
        """Publish a system event.
        
        Args:
            event_type: Type of system event (use EventType constants)
            system_data: System data dictionary
            
        Returns:
            bool: True if published successfully, False otherwise
        """
        return await self.publish_event(SYSTEM_EVENTS_CHANNEL, event_type, system_data)
    
    async def subscribe(self, channels: List[str]) -> None:
        """Subscribe to Redis channels.
        
        Args:
            channels: List of channel names to subscribe to
        """
        try:
            await self.pubsub.subscribe(*channels)
            logger.info(f"Subscribed to channels: {', '.join(channels)}")
        except RedisError as e:
            logger.error(f"Error subscribing to Redis channels: {str(e)}")
            raise
    
    async def register_handler(self, channel: str, callback: Callable[[str, Dict[str, Any]], Awaitable[None]]) -> None:
        """Register an event handler for a channel.
        
        Args:
            channel: Channel to handle events for
            callback: Async callback function that takes event_type and data
        """
        if channel not in self._subscribers:
            self._subscribers[channel] = []
        
        self._subscribers[channel].append(callback)
        logger.debug(f"Registered handler for channel {channel}")
    
    async def start_listener(self) -> None:
        """Start listening for messages on subscribed channels.
        
        This method starts a background task that listens for messages
        on all subscribed channels and dispatches them to registered handlers.
        """
        task = asyncio.create_task(self._message_listener())
        self._running_tasks.append(task)
        logger.info("Started Redis message listener")
    
    async def _message_listener(self) -> None:
        """Background task that listens for messages and dispatches them."""
        try:
            while True:
                try:
                    message = await self.pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if message is not None:
                        await self._process_message(message)
                    await asyncio.sleep(0.01)  # Small sleep to avoid CPU spinning
                except ConnectionError as e:
                    logger.error(f"Redis connection error: {str(e)}")
                    await asyncio.sleep(1)  # Wait before reconnecting
                    try:
                        # Try to reconnect
                        await self.pubsub.close()
                        self.pubsub = self.redis_client.pubsub()
                        channels = list(self._subscribers.keys())
                        if channels:
                            await self.subscribe(channels)
                    except RedisError as e:
                        logger.error(f"Failed to reconnect to Redis: {str(e)}")
                        await asyncio.sleep(5)  # Longer wait after failed reconnect
        except asyncio.CancelledError:
            logger.info("Redis message listener cancelled")
            await self.pubsub.close()
        except Exception as e:
            logger.error(f"Unexpected error in Redis message listener: {str(e)}")
            await self.pubsub.close()
    
    async def _process_message(self, message: Dict[str, Any]) -> None:
        """Process a Redis pubsub message.
        
        Args:
            message: Redis pubsub message
        """
        try:
            channel = message.get("channel", b"").decode("utf-8")
            data = message.get("data", b"").decode("utf-8")
            
            if not data:
                return
            
            event_data = json.loads(data)
            event_type = event_data.get("type")
            event_payload = event_data.get("data", {})
            
            if channel in self._subscribers:
                for handler in self._subscribers[channel]:
                    try:
                        await handler(event_type, event_payload)
                    except Exception as e:
                        logger.error(f"Error in event handler for channel {channel}: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding Redis message: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing Redis message: {str(e)}")
    
    async def stop_listener(self) -> None:
        """Stop the message listener and clean up resources."""
        for task in self._running_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self._running_tasks = []
        await self.pubsub.close()
        logger.info("Stopped Redis message listener")
    
    async def set_cache(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in the Redis cache.
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time-to-live in seconds (None for no expiration)
            
        Returns:
            bool: True if set successfully, False otherwise
        """
        try:
            serialized = json.dumps(value)
            if ttl is not None:
                await self.redis_client.setex(key, ttl, serialized)
            else:
                await self.redis_client.set(key, serialized)
            return True
        except RedisError as e:
            logger.error(f"Error setting cache value: {str(e)}")
            return False
        except (TypeError, ValueError) as e:
            logger.error(f"Error serializing cache value: {str(e)}")
            return False
    
    async def get_cache(self, key: str) -> Optional[Any]:
        """Get a value from the Redis cache.
        
        Args:
            key: Cache key
            
        Returns:
            Any: Cached value or None if not found
        """
        try:
            value = await self.redis_client.get(key)
            if value is None:
                return None
            return json.loads(value)
        except RedisError as e:
            logger.error(f"Error getting cache value: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Error deserializing cache value: {str(e)}")
            return None
    
    async def delete_cache(self, key: str) -> bool:
        """Delete a value from the Redis cache.
        
        Args:
            key: Cache key
            
        Returns:
            bool: True if deleted successfully, False otherwise
        """
        try:
            await self.redis_client.delete(key)
            return True
        except RedisError as e:
            logger.error(f"Error deleting cache value: {str(e)}")
            return False
    
    async def check_health(self) -> Dict[str, Any]:
        """Check Redis health and return status information.
        
        Returns:
            Dict[str, Any]: Dictionary with health check information
        """
        try:
            # Ping Redis to check connection
            pong = await self.redis_client.ping()
            
            # Get Redis info
            info = await self.redis_client.info()
            
            return {
                "status": "healthy" if pong else "unhealthy",
                "version": info.get("redis_version", "unknown"),
                "memory": {
                    "used_memory_human": info.get("used_memory_human", "unknown"),
                    "used_memory_peak_human": info.get("used_memory_peak_human", "unknown"),
                },
                "clients": info.get("connected_clients", 0),
                "uptime_days": info.get("uptime_in_days", 0)
            }
        except RedisError as e:
            logger.error(f"Redis health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }


@asynccontextmanager
async def get_redis_service() -> Redis:
    """Get a Redis service instance.
    
    This context manager provides a Redis service instance with
    automatic connection management.
    
    Usage:
        async def some_function():
            async with get_redis_service() as redis_service:
                await redis_service.publish_ticket_event(...)
                
    Yields:
        RedisService instance
    """
    redis_client = redis.Redis(connection_pool=redis_pool)
    service = RedisService(redis_client)
    try:
        yield service
    finally:
        await redis_client.close()


# Dependency for FastAPI
async def get_redis() -> RedisService:
    """FastAPI dependency for Redis service.
    
    This function is designed to be used as a FastAPI dependency
    to provide a Redis service to API endpoints.
    
    Usage in FastAPI endpoints:
        @app.get("/tickets")
        async def get_tickets(redis: RedisService = Depends(get_redis)):
            await redis.publish_ticket_event(...)
            
    Yields:
        RedisService instance
    """
    redis_client = redis.Redis(connection_pool=redis_pool)
    service = RedisService(redis_client)
    try:
        yield service
    finally:
        await redis_client.close()