"""Message processor for handling Discord messages."""

import logging
import discord
from typing import Dict, Optional, Any

from config.settings import config, logger
from utils.http_client import get_api_client
from utils.sync_service import get_sync_service, SyncEvent, SyncEventType


class MessageProcessor:
    """Processor for Discord messages."""
    
    def __init__(self, bot):
        """Initialize the message processor.
        
        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
        self.api_client = None
        self.sync_service = None
    
    async def initialize(self) -> None:
        """Initialize the message processor."""
        # Get API client
        self.api_client = await get_api_client()
        
        # Get sync service
        self.sync_service = await get_sync_service(self.bot)
    
    async def process_message(
        self, 
        message: discord.Message, 
        ticket_id: str
    ) -> Optional[Dict[str, Any]]:
        """Process a message from a ticket channel.
        
        Args:
            message: The Discord message
            ticket_id: The ticket ID
            
        Returns:
            The processed message data or None if processing failed
        """
        # Skip bot messages
        if message.author.bot:
            return None
        
        # Skip system messages
        if message.type != discord.MessageType.default:
            return None
        
        # Skip commands
        if message.content.startswith(config.command_prefix):
            return None
        
        # Format the message data
        message_data = {
            "ticket_id": ticket_id,
            "discord_message_id": message.id,
            "author_discord_id": message.author.id,
            "content": message.content,
            "message_type": "user_message"
        }
        
        # Add attachments if any
        if message.attachments:
            attachments = []
            for attachment in message.attachments:
                attachments.append({
                    "url": attachment.url,
                    "filename": attachment.filename,
                    "content_type": attachment.content_type,
                    "size": attachment.size
                })
            message_data["attachments"] = attachments
        
        # Emit sync event for Discord-to-backend synchronization
        if self.sync_service:
            sync_event = SyncEvent(
                event_type=SyncEventType.MESSAGE_CREATED,
                data=message_data,
                source="discord"
            )
            await self.sync_service.emit_event(sync_event)
            logger.info(f"Emitted sync event for message {message.id}")
        
        return message_data
    
    async def format_message(self, message_data: Dict[str, Any]) -> str:
        """Format a message for display.
        
        Args:
            message_data: The message data
            
        Returns:
            The formatted message
        """
        content = message_data.get("content", "")
        author_id = message_data.get("author_discord_id")
        
        # Try to get the author's name
        author_name = f"<@{author_id}>"
        if author_id:
            for guild in self.bot.guilds:
                member = guild.get_member(author_id)
                if member:
                    author_name = member.display_name
                    break
        
        # Format the message
        formatted = f"**{author_name}:** {content}"
        
        # Add attachments if any
        attachments = message_data.get("attachments", [])
        if attachments:
            formatted += "\n**Attachments:**"
            for attachment in attachments:
                formatted += f"\n- [{attachment.get('filename')}]({attachment.get('url')})"
        
        return formatted