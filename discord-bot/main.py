"""Discord Bot for Ticket Management System."""

import asyncio
import sys
import os
import signal
import traceback
import threading
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

# Add the parent directory to sys.path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot.ticket_bot import TicketBot
from config.settings import config
from utils.http_client import get_api_client
from utils.redis_client import get_redis_client
from logging_config import setup_logging, get_logger, bot_metrics_collector

# Set up logging
setup_logging()
logger = get_logger(__name__)


# Global health status
health_status = {
    "status": "starting",
    "discord_connected": False,
    "backend_connected": False,
    "redis_connected": False,
    "start_time": datetime.utcnow(),
    "last_heartbeat": datetime.utcnow(),
}


class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP handler for health check endpoint."""
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/health":
            self.send_health_response()
        elif self.path == "/metrics":
            self.send_metrics_response()
        else:
            self.send_response(404)
            self.end_headers()
    
    def send_health_response(self):
        """Send health check response."""
        global health_status
        
        # Update last heartbeat
        health_status["last_heartbeat"] = datetime.utcnow()
        
        # Determine overall status
        is_healthy = (
            health_status["discord_connected"] and
            health_status["backend_connected"] and
            health_status["redis_connected"]
        )
        
        health_status["status"] = "healthy" if is_healthy else "unhealthy"
        
        # Calculate uptime
        uptime = datetime.utcnow() - health_status["start_time"]
        health_status["uptime_seconds"] = uptime.total_seconds()
        
        # Prepare response
        response_data = {
            **health_status,
            "service": "discord-ticket-bot",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "start_time": health_status["start_time"].isoformat() + "Z",
            "last_heartbeat": health_status["last_heartbeat"].isoformat() + "Z",
        }
        
        # Send response
        self.send_response(200 if is_healthy else 503)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response_data).encode())
    
    def send_metrics_response(self):
        """Send metrics response."""
        metrics = bot_metrics_collector.get_metrics()
        
        response_data = {
            "service": "discord-ticket-bot",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metrics": metrics
        }
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response_data).encode())
    
    def log_message(self, format, *args):
        """Override to suppress HTTP server logs."""
        pass


def start_health_server():
    """Start health check HTTP server in a separate thread."""
    server = HTTPServer(("0.0.0.0", 8080), HealthCheckHandler)
    logger.info("Health check server started on port 8080")
    server.serve_forever()


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
    global health_status
    
    # Start health check server in background thread
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    
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
            health_status["backend_connected"] = True
            bot_metrics_collector.increment_api_calls()
        else:
            logger.warning("Failed to connect to backend API")
            health_status["backend_connected"] = False
            bot_metrics_collector.increment_errors()
        
        # Initialize Redis client
        logger.info("Initializing Redis client...")
        redis_client = await get_redis_client()
        if redis_client.connected:
            logger.info("Connected to Redis")
            health_status["redis_connected"] = True
            
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
            health_status["redis_connected"] = False
            bot_metrics_collector.increment_errors()
        
        # Set up signal handlers for graceful shutdown
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(bot, api_client, redis_client)))
            except NotImplementedError:
                # Windows doesn't support SIGINT/SIGTERM properly
                pass
        
        # Update health status
        health_status["status"] = "running"
        
        # Start the bot
        logger.info("Starting Discord bot...")
        await bot.start(config.token)
        
        # Update health status when connected
        health_status["discord_connected"] = True
        bot_metrics_collector.set_guild_count(len(bot.guilds))
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Error starting bot: {e}", exc_info=True)
        bot_metrics_collector.increment_errors()
        health_status["status"] = "error"
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