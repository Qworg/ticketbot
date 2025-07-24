"""Discord Bot for Ticket Management System."""

import asyncio
import sys
import os
import signal
import traceback

# Add the parent directory to sys.path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from discord_bot.bot.ticket_bot import TicketBot
from discord_bot.config.settings import config, logger
from discord_bot.utils.http_client import get_api_client
from discord_bot.utils.redis_client import get_redis_client


# Register Redis event handlers
async def register_redis_handlers(bot, redis_client):
    """Register handlers for Redis events."""
    
    # Handler for ticket events
    async def handle_ticket_event(data):
        """Handle ticket events from Redis."""
        event_type = data.get("event_type")
        ticket_data = data.get("ticket")
        
        if not ticket_data:
            return
        
        logger.info(f"Received ticket event: {event_type}")
        
        # Update bot's ticket cache
        if event_type == "ticket_created":
            channel_id = ticket_data.get("discord_channel_id")
            if channel_id:
                bot.ticket_manager.active_tickets[channel_id] = ticket_data
        
        elif event_type == "ticket_updated":
            channel_id = ticket_data.get("discord_channel_id")
            if channel_id:
                bot.ticket_manager.active_tickets[channel_id] = ticket_data
        
        elif event_type == "ticket_closed":
            channel_id = ticket_data.get("discord_channel_id")
            if channel_id and channel_id in bot.ticket_manager.active_tickets:
                del bot.ticket_manager.active_tickets[channel_id]
    
    # Handler for message events
    async def handle_message_event(data):
        """Handle message events from Redis."""
        event_type = data.get("event_type")
        message_data = data.get("message")
        
        if not message_data:
            return
        
        logger.info(f"Received message event: {event_type}")
        
        # Process the message if it's from the web dashboard
        if event_type == "message_created" and message_data.get("source") == "dashboard":
            ticket_id = message_data.get("ticket_id")
            
            # Find the ticket channel
            channel_id = None
            for cid, ticket in bot.ticket_manager.active_tickets.items():
                if ticket.get("id") == ticket_id:
                    channel_id = cid
                    break
            
            if channel_id:
                channel = bot.get_channel(channel_id)
                if channel:
                    # Format and send the message
                    formatted_message = await bot.message_processor.format_message(message_data)
                    await channel.send(formatted_message)
    
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