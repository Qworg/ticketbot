"""Synchronization service for bidirectional Discord-Backend communication."""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
import discord

from config.settings import config, logger
from utils.http_client import get_api_client, APIError, ConnectionError
from utils.redis_client import get_redis_client


class SyncEventType(Enum):
    """Types of synchronization events."""
    TICKET_CREATED = "ticket_created"
    TICKET_UPDATED = "ticket_updated"
    TICKET_CLOSED = "ticket_closed"
    MESSAGE_CREATED = "message_created"
    MESSAGE_UPDATED = "message_updated"
    MESSAGE_DELETED = "message_deleted"


class ConflictResolutionStrategy(Enum):
    """Strategies for resolving synchronization conflicts."""
    BACKEND_WINS = "backend_wins"
    DISCORD_WINS = "discord_wins"
    TIMESTAMP_WINS = "timestamp_wins"
    MERGE = "merge"


class SyncEvent:
    """Represents a synchronization event."""
    
    def __init__(self, 
                 event_type: SyncEventType,
                 data: Dict[str, Any],
                 source: str,
                 timestamp: Optional[float] = None,
                 correlation_id: Optional[str] = None):
        """Initialize a sync event.
        
        Args:
            event_type: Type of the event
            data: Event data
            source: Source of the event (discord/backend)
            timestamp: Event timestamp
            correlation_id: Correlation ID for tracking related events
        """
        self.event_type = event_type
        self.data = data
        self.source = source
        self.timestamp = timestamp or time.time()
        self.correlation_id = correlation_id
        self.retry_count = 0
        self.max_retries = 3


class SynchronizationService:
    """Service for handling bidirectional synchronization between Discord and Backend."""
    
    def __init__(self, bot):
        """Initialize the synchronization service.
        
        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
        self.api_client = None
        self.redis_client = None
        self.event_handlers: Dict[SyncEventType, List[Callable]] = {}
        self.pending_events: List[SyncEvent] = []
        self.conflict_resolution = ConflictResolutionStrategy.TIMESTAMP_WINS
        self.sync_lock = asyncio.Lock()
        self.running = False
        
        # Event tracking for conflict resolution
        self.recent_events: Dict[str, SyncEvent] = {}  # key: resource_id, value: last event
        self.event_timeout = 30.0  # seconds
    
    async def initialize(self) -> None:
        """Initialize the synchronization service."""
        # Get API client
        self.api_client = await get_api_client()
        
        # Get Redis client
        self.redis_client = await get_redis_client()
        
        # Register default event handlers
        await self._register_default_handlers()
        
        # Start the sync worker
        self.running = True
        asyncio.create_task(self._sync_worker())
        
        logger.info("Synchronization service initialized")
    
    async def shutdown(self) -> None:
        """Shutdown the synchronization service."""
        self.running = False
        logger.info("Synchronization service shutdown")
    
    def register_handler(self, event_type: SyncEventType, handler: Callable) -> None:
        """Register an event handler.
        
        Args:
            event_type: Type of event to handle
            handler: Handler function
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    async def _register_default_handlers(self) -> None:
        """Register default event handlers."""
        # Backend-to-Discord handlers
        self.register_handler(SyncEventType.TICKET_CREATED, self._handle_backend_ticket_created)
        self.register_handler(SyncEventType.TICKET_UPDATED, self._handle_backend_ticket_updated)
        self.register_handler(SyncEventType.TICKET_CLOSED, self._handle_backend_ticket_closed)
        self.register_handler(SyncEventType.MESSAGE_CREATED, self._handle_backend_message_created)
        
        # Discord-to-Backend handlers
        self.register_handler(SyncEventType.MESSAGE_CREATED, self._handle_discord_message_created)
    
    async def emit_event(self, event: SyncEvent) -> None:
        """Emit a synchronization event.
        
        Args:
            event: The event to emit
        """
        async with self.sync_lock:
            # Check for conflicts
            if await self._check_conflict(event):
                logger.warning(f"Conflict detected for event {event.event_type}, applying resolution strategy")
                if not await self._resolve_conflict(event):
                    logger.error(f"Failed to resolve conflict for event {event.event_type}")
                    return
            
            # Add to pending events
            self.pending_events.append(event)
            
            # Update recent events for conflict detection
            resource_id = self._get_resource_id(event)
            if resource_id:
                self.recent_events[resource_id] = event
    
    async def _check_conflict(self, event: SyncEvent) -> bool:
        """Check if an event conflicts with recent events.
        
        Args:
            event: The event to check
            
        Returns:
            True if there's a conflict
        """
        resource_id = self._get_resource_id(event)
        if not resource_id:
            return False
        
        # Check if there's a recent event for the same resource
        if resource_id in self.recent_events:
            recent_event = self.recent_events[resource_id]
            
            # Check if events are too close in time
            time_diff = abs(event.timestamp - recent_event.timestamp)
            if time_diff < 1.0:  # Less than 1 second apart
                # Check if they're from different sources
                if event.source != recent_event.source:
                    return True
        
        return False
    
    async def _resolve_conflict(self, event: SyncEvent) -> bool:
        """Resolve a synchronization conflict.
        
        Args:
            event: The conflicting event
            
        Returns:
            True if conflict was resolved
        """
        resource_id = self._get_resource_id(event)
        if not resource_id or resource_id not in self.recent_events:
            return True
        
        recent_event = self.recent_events[resource_id]
        
        if self.conflict_resolution == ConflictResolutionStrategy.BACKEND_WINS:
            return event.source == "backend"
        elif self.conflict_resolution == ConflictResolutionStrategy.DISCORD_WINS:
            return event.source == "discord"
        elif self.conflict_resolution == ConflictResolutionStrategy.TIMESTAMP_WINS:
            return event.timestamp > recent_event.timestamp
        elif self.conflict_resolution == ConflictResolutionStrategy.MERGE:
            # Attempt to merge the events
            return await self._merge_events(recent_event, event)
        
        return True
    
    async def _merge_events(self, event1: SyncEvent, event2: SyncEvent) -> bool:
        """Merge two conflicting events.
        
        Args:
            event1: First event
            event2: Second event
            
        Returns:
            True if merge was successful
        """
        # Simple merge strategy: combine data from both events
        # More sophisticated merging can be implemented based on specific needs
        try:
            merged_data = {**event1.data, **event2.data}
            event2.data = merged_data
            return True
        except Exception as e:
            logger.error(f"Failed to merge events: {e}")
            return False
    
    def _get_resource_id(self, event: SyncEvent) -> Optional[str]:
        """Get the resource ID from an event.
        
        Args:
            event: The event
            
        Returns:
            Resource ID or None
        """
        if event.event_type in [SyncEventType.TICKET_CREATED, SyncEventType.TICKET_UPDATED, SyncEventType.TICKET_CLOSED]:
            return event.data.get("id") or event.data.get("discord_channel_id")
        elif event.event_type in [SyncEventType.MESSAGE_CREATED, SyncEventType.MESSAGE_UPDATED, SyncEventType.MESSAGE_DELETED]:
            return event.data.get("id") or event.data.get("discord_message_id")
        
        return None
    
    async def _sync_worker(self) -> None:
        """Background worker for processing sync events."""
        while self.running:
            try:
                # Process pending events
                if self.pending_events:
                    async with self.sync_lock:
                        events_to_process = self.pending_events.copy()
                        self.pending_events.clear()
                    
                    for event in events_to_process:
                        await self._process_event(event)
                
                # Clean up old events
                await self._cleanup_old_events()
                
                # Wait before next iteration
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in sync worker: {e}")
                await asyncio.sleep(1.0)
    
    async def _process_event(self, event: SyncEvent) -> None:
        """Process a synchronization event.
        
        Args:
            event: The event to process
        """
        try:
            # Get handlers for this event type
            handlers = self.event_handlers.get(event.event_type, [])
            
            # Execute handlers
            for handler in handlers:
                try:
                    await handler(event)
                except Exception as e:
                    logger.error(f"Error in event handler {handler.__name__}: {e}")
                    
                    # Retry logic
                    if event.retry_count < event.max_retries:
                        event.retry_count += 1
                        await asyncio.sleep(2 ** event.retry_count)  # Exponential backoff
                        self.pending_events.append(event)
                    else:
                        logger.error(f"Max retries exceeded for event {event.event_type}")
        
        except Exception as e:
            logger.error(f"Error processing event {event.event_type}: {e}")
    
    async def _cleanup_old_events(self) -> None:
        """Clean up old events from recent events cache."""
        current_time = time.time()
        expired_keys = []
        
        for resource_id, event in self.recent_events.items():
            if current_time - event.timestamp > self.event_timeout:
                expired_keys.append(resource_id)
        
        for key in expired_keys:
            del self.recent_events[key]
    
    # Backend-to-Discord event handlers
    
    async def _handle_backend_ticket_created(self, event: SyncEvent) -> None:
        """Handle ticket created event from backend.
        
        Args:
            event: The sync event
        """
        if event.source == "discord":
            return  # Skip Discord-originated events
        
        ticket_data = event.data
        logger.info(f"Handling backend ticket created: {ticket_data.get('id')}")
        
        # Update bot's ticket cache
        channel_id = ticket_data.get("discord_channel_id")
        if channel_id and hasattr(self.bot, 'ticket_manager'):
            self.bot.ticket_manager.active_tickets[channel_id] = ticket_data
    
    async def _handle_backend_ticket_updated(self, event: SyncEvent) -> None:
        """Handle ticket updated event from backend.
        
        Args:
            event: The sync event
        """
        if event.source == "discord":
            return  # Skip Discord-originated events
        
        ticket_data = event.data
        logger.info(f"Handling backend ticket updated: {ticket_data.get('id')}")
        
        # Update bot's ticket cache
        channel_id = ticket_data.get("discord_channel_id")
        if channel_id and hasattr(self.bot, 'ticket_manager'):
            self.bot.ticket_manager.active_tickets[channel_id] = ticket_data
        
        # Update Discord channel if needed (e.g., topic, permissions)
        channel = self.bot.get_channel(channel_id)
        if channel:
            # Update channel topic with ticket status
            new_topic = f"Ticket #{ticket_data.get('id')} - Status: {ticket_data.get('status', 'open')}"
            if channel.topic != new_topic:
                try:
                    await channel.edit(topic=new_topic)
                except discord.Forbidden:
                    logger.warning(f"No permission to update channel topic for {channel_id}")
    
    async def _handle_backend_ticket_closed(self, event: SyncEvent) -> None:
        """Handle ticket closed event from backend.
        
        Args:
            event: The sync event
        """
        if event.source == "discord":
            return  # Skip Discord-originated events
        
        ticket_data = event.data
        logger.info(f"Handling backend ticket closed: {ticket_data.get('id')}")
        
        # Remove from bot's ticket cache
        channel_id = ticket_data.get("discord_channel_id")
        if channel_id and hasattr(self.bot, 'ticket_manager'):
            if channel_id in self.bot.ticket_manager.active_tickets:
                del self.bot.ticket_manager.active_tickets[channel_id]
        
        # Archive Discord channel
        channel = self.bot.get_channel(channel_id)
        if channel:
            try:
                # Move to archive category or delete
                await channel.send("🔒 This ticket has been closed.")
                # Could implement archiving logic here
            except discord.Forbidden:
                logger.warning(f"No permission to update closed channel {channel_id}")
    
    async def _handle_backend_message_created(self, event: SyncEvent) -> None:
        """Handle message created event from backend.
        
        Args:
            event: The sync event
        """
        if event.source == "discord":
            return  # Skip Discord-originated events
        
        message_data = event.data
        logger.info(f"Handling backend message created: {message_data.get('id')}")
        
        # Find the Discord channel
        ticket_id = message_data.get("ticket_id")
        if not ticket_id:
            return
        
        # Get ticket data to find channel
        channel_id = None
        if hasattr(self.bot, 'ticket_manager'):
            for cid, ticket in self.bot.ticket_manager.active_tickets.items():
                if ticket.get("id") == ticket_id:
                    channel_id = cid
                    break
        
        if not channel_id:
            logger.warning(f"Could not find Discord channel for ticket {ticket_id}")
            return
        
        # Send message to Discord channel
        channel = self.bot.get_channel(channel_id)
        if channel:
            try:
                # Format the message
                if hasattr(self.bot, 'message_processor'):
                    formatted_message = await self.bot.message_processor.format_message(message_data)
                else:
                    formatted_message = f"**Web Dashboard:** {message_data.get('content', '')}"
                
                await channel.send(formatted_message)
            except discord.Forbidden:
                logger.warning(f"No permission to send message to channel {channel_id}")
    
    # Discord-to-Backend event handlers
    
    async def _handle_discord_message_created(self, event: SyncEvent) -> None:
        """Handle message created event from Discord.
        
        Args:
            event: The sync event
        """
        if event.source == "backend":
            return  # Skip backend-originated events
        
        message_data = event.data
        logger.info(f"Handling Discord message created: {message_data.get('discord_message_id')}")
        
        # Forward to backend API
        if self.api_client and self.api_client.connected:
            try:
                ticket_id = message_data.get("ticket_id")
                await self.api_client.add_message(ticket_id, message_data)
            except (APIError, ConnectionError) as e:
                logger.error(f"Failed to forward Discord message to backend: {e}")
                # Re-queue for retry
                if event.retry_count < event.max_retries:
                    event.retry_count += 1
                    await asyncio.sleep(2 ** event.retry_count)
                    self.pending_events.append(event)


# Global sync service instance
sync_service = None


async def get_sync_service(bot) -> SynchronizationService:
    """Get or create the synchronization service instance.
    
    Args:
        bot: The Discord bot instance
        
    Returns:
        SynchronizationService instance
    """
    global sync_service
    if sync_service is None:
        sync_service = SynchronizationService(bot)
        await sync_service.initialize()
    return sync_service


async def reset_sync_service() -> None:
    """Reset the global synchronization service instance."""
    global sync_service
    if sync_service:
        await sync_service.shutdown()
        sync_service = None