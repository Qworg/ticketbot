"""Discord Bot for Ticket Management System."""

import asyncio
import sys
import os
import signal
import traceback

# Add the parent directory to sys.path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot.ticket_bot import TicketBot
from config.settings import config, logger
from utils.http_client import get_api_client
from utils.redis_client import get_redis_client


# Register Redis event handlers
async def register_redis_handlers(bot, redis_client):
    """Register handlers for Redis events."""
    from utils.sync_service import get_sync_service, SyncEvent, SyncEventType
    
    # Get sync service
    sync_service = await get_sync_service(bot)
    
    # Handler for ticket events
    async def handle_ticket_event(data):
        """Handle ticket events from Redis."""
        event_type = data.get("event_type")
        ticket_data = data.get("ticket")
        
        if not ticket_data:
            return
        
        logger.info(f"Received ticket event: {event_type}")
        
        # Convert to sync event and emit
        sync_event_type = None
        if event_type == "ticket_created":
            sync_event_type = SyncEventType.TICKET_CREATED
        elif event_type == "ticket_updated":
            sync_event_type = SyncEventType.TICKET_UPDATED
        elif event_type == "ticket_closed":
            sync_event_type = SyncEventType.TICKET_CLOSED
        
        if sync_event_type:
            sync_event = SyncEvent(
                event_type=sync_event_type,
                data=ticket_data,
                source="backend"
            )
            await sync_service.emit_event(sync_event)
    
    # Handler for message events
    async def handle_message_event(data):
        """Handle message events from Redis."""
        event_type = data.get("event_type")
        message_data = data.get("message")
        
        if not message_data:
            return
        
        logger.info(f"Received message event: {event_type}")
        
        # Convert to sync event and emit
        if event_type == "message_created":
            sync_event = SyncEvent(
                event_type=SyncEventType.MESSAGE_CREATED,
                data=message_data,
                source="backend"
            )
            await sync_service.emit_event(sync_event)
    
    # Register the handlers
    redis_client.register_handler("ticket_events", handle_ticket_event)
    redis_client.register_handler("message_events", handle_message_event)


async def main():
    """Main entry point for the Discord bot."""
    # Create resources
    bot = None
    api_client = None
    redis_client = None
    
    try:
        # Create the bot instance
        logger.info("Creating Discord bot instance...")
        bot = TicketBot()
        
        # Initialize API client
        logger.info("Initializing API client...")
        api_client = await get_api_client()
        if api_client.connected:
            logger.info("Connected to backend API")
            bot.health_status["backend_connected"] = True
        else:
            logger.warning("Failed to connect to backend API")
            bot.health_status["backend_connected"] = False
        
        # Initialize Redis client
        logger.info("Initializing Redis client...")
        redis_client = await get_redis_client()
        if redis_client.connected:
            logger.info("Connected to Redis")
            bot.health_status["redis_connected"] = True
            
            # Subscribe to channels
            await redis_client.subscribe([
                "ticket_events",
                "message_events",
                "system_events"
            ])
            
            # Register Redis event handlers
            await register_redis_handlers(bot, redis_client)
            
            # Start listener
            await redis_client.start_listener()
        else:
            logger.warning("Failed to connect to Redis")
            bot.health_status["redis_connected"] = False
        
        # Set up signal handlers for graceful shutdown
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(bot, api_client, redis_client)))
            except NotImplementedError:
                # Windows doesn't support SIGINT/SIGTERM properly
                pass
        
        # Start the bot
        logger.info("Starting Discord bot...")
        await bot.start(config.token)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        logger.error(traceback.format_exc())
    finally:
        # Clean up resources if not already done by signal handler
        await cleanup(bot, api_client, redis_client)


async def shutdown(bot, api_client, redis_client):
    """Handle graceful shutdown."""
    logger.info("Shutdown signal received, cleaning up...")
    await cleanup(bot, api_client, redis_client)
    # Force exit after cleanup
    os._exit(0)


async def cleanup(bot, api_client, redis_client):
    """Clean up resources."""
    # Close Redis client
    if redis_client:
        logger.info("Closing Redis client...")
        await redis_client.close()
    
    # Close API client
    if api_client:
        logger.info("Closing API client...")
        await api_client.close()
    
    # Close the bot
    if bot and not (hasattr(bot, "is_closed") and bot.is_closed()):
        logger.info("Closing Discord bot...")
        await bot.close()


if __name__ == "__main__":
    import discord
    asyncio.run(main())