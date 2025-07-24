"""Ticket manager for handling ticket operations."""

import logging
import asyncio
import discord
from typing import Dict, List, Optional, Any

from discord_bot.config.settings import config, logger
from discord_bot.utils.http_client import get_api_client


class TicketManager:
    """Manager for ticket operations."""
    
    def __init__(self, bot):
        """Initialize the ticket manager.
        
        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
        self.api_client = None
        self.ticket_category_id = config.ticket_category_id
        self.staff_role_id = config.staff_role_id
        self.active_tickets = {}  # Map of channel_id to ticket data
    
    async def initialize(self) -> None:
        """Initialize the ticket manager."""
        # Get API client
        self.api_client = await get_api_client()
        
        # Load active tickets from the database
        await self.load_active_tickets()
    
    async def load_active_tickets(self) -> None:
        """Load active tickets from the database."""
        if not self.api_client or not self.api_client.connected:
            logger.warning("Cannot load active tickets: API client not connected")
            return
        
        try:
            # Get active tickets from the API
            tickets = await self.api_client.get("/api/tickets", params={"status": "open"})
            
            # Store active tickets
            for ticket in tickets.get("items", []):
                channel_id = ticket.get("discord_channel_id")
                if channel_id:
                    self.active_tickets[channel_id] = ticket
            
            logger.info(f"Loaded {len(self.active_tickets)} active tickets")
        except Exception as e:
            logger.error(f"Failed to load active tickets: {e}")
    
    async def get_ticket_category(self) -> Optional[discord.CategoryChannel]:
        """Get the ticket category channel.
        
        Returns:
            The ticket category channel or None if not found
        """
        if not self.ticket_category_id:
            logger.warning("Ticket category ID not configured")
            return None
        
        # Get the category channel
        category = self.bot.get_channel(self.ticket_category_id)
        if not category:
            logger.warning(f"Ticket category not found: {self.ticket_category_id}")
            return None
        
        return category
    
    async def get_staff_role(self, guild: discord.Guild) -> Optional[discord.Role]:
        """Get the staff role.
        
        Args:
            guild: The Discord guild
            
        Returns:
            The staff role or None if not found
        """
        if not self.staff_role_id:
            logger.warning("Staff role ID not configured")
            return None
        
        # Get the staff role
        role = guild.get_role(self.staff_role_id)
        if not role:
            logger.warning(f"Staff role not found: {self.staff_role_id}")
            return None
        
        return role
    
    async def get_ticket_by_channel(self, channel_id: int) -> Optional[Dict[str, Any]]:
        """Get ticket data by channel ID.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            Ticket data or None if not found
        """
        # Check local cache first
        if channel_id in self.active_tickets:
            return self.active_tickets[channel_id]
        
        # If not in cache, try to get from API
        if self.api_client and self.api_client.connected:
            try:
                tickets = await self.api_client.get(
                    "/api/tickets", 
                    params={"discord_channel_id": channel_id}
                )
                
                if tickets.get("items") and len(tickets["items"]) > 0:
                    ticket = tickets["items"][0]
                    self.active_tickets[channel_id] = ticket
                    return ticket
            except Exception as e:
                logger.error(f"Failed to get ticket by channel ID: {e}")
        
        return None