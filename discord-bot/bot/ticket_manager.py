"""Ticket manager for handling ticket operations."""

import logging
import asyncio
import discord
from typing import Dict, List, Optional, Any

from config.settings import config, logger
from utils.http_client import get_api_client
from utils.sync_service import get_sync_service, SyncEvent, SyncEventType


class TicketManager:
    """Manager for ticket operations."""
    
    def __init__(self, bot):
        """Initialize the ticket manager.
        
        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
        self.api_client = None
        self.sync_service = None
        self.ticket_category_id = config.ticket_category_id
        self.staff_role_id = config.staff_role_id
        self.active_tickets = {}  # Map of channel_id to ticket data
    
    async def initialize(self) -> None:
        """Initialize the ticket manager."""
        # Get API client
        self.api_client = await get_api_client()
        
        # Get sync service
        self.sync_service = await get_sync_service(self.bot)
        
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
    
    async def create_ticket(self, 
                           guild: discord.Guild,
                           user: discord.Member,
                           title: str,
                           description: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Create a new ticket.
        
        Args:
            guild: Discord guild
            user: User creating the ticket
            title: Ticket title
            description: Ticket description
            
        Returns:
            Created ticket data or None if creation failed
        """
        try:
            # Get ticket category
            category = await self.get_ticket_category()
            if not category:
                logger.error("Cannot create ticket: no ticket category configured")
                return None
            
            # Create Discord channel
            channel_name = f"ticket-{user.name}-{len(self.active_tickets) + 1}"
            channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                topic=f"Ticket: {title}"
            )
            
            # Set channel permissions
            await self._set_ticket_permissions(channel, user)
            
            # Prepare ticket data
            ticket_data = {
                "title": title,
                "description": description,
                "discord_channel_id": channel.id,
                "creator_discord_id": user.id,
                "status": "open"
            }
            
            # Create ticket via API
            if self.api_client and self.api_client.connected:
                try:
                    created_ticket = await self.api_client.create_ticket(ticket_data)
                    
                    # Update local cache
                    self.active_tickets[channel.id] = created_ticket
                    
                    # Emit sync event
                    if self.sync_service:
                        sync_event = SyncEvent(
                            event_type=SyncEventType.TICKET_CREATED,
                            data=created_ticket,
                            source="discord"
                        )
                        await self.sync_service.emit_event(sync_event)
                    
                    # Send welcome message
                    await channel.send(
                        f"🎫 **Ticket Created**\n"
                        f"**Title:** {title}\n"
                        f"**Created by:** {user.mention}\n"
                        f"**Ticket ID:** {created_ticket.get('id')}\n\n"
                        f"Please describe your issue and a staff member will assist you shortly."
                    )
                    
                    logger.info(f"Created ticket {created_ticket.get('id')} in channel {channel.id}")
                    return created_ticket
                    
                except Exception as e:
                    logger.error(f"Failed to create ticket via API: {e}")
                    # Clean up Discord channel
                    await channel.delete()
                    return None
            else:
                logger.error("Cannot create ticket: API client not connected")
                await channel.delete()
                return None
                
        except Exception as e:
            logger.error(f"Failed to create ticket: {e}")
            return None
    
    async def update_ticket(self, 
                           channel_id: int,
                           update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a ticket.
        
        Args:
            channel_id: Discord channel ID
            update_data: Update data
            
        Returns:
            Updated ticket data or None if update failed
        """
        # Get current ticket data
        ticket = await self.get_ticket_by_channel(channel_id)
        if not ticket:
            logger.error(f"Cannot update ticket: ticket not found for channel {channel_id}")
            return None
        
        ticket_id = ticket.get("id")
        if not ticket_id:
            logger.error("Cannot update ticket: no ticket ID")
            return None
        
        try:
            # Update via API
            if self.api_client and self.api_client.connected:
                updated_ticket = await self.api_client.update_ticket(ticket_id, update_data)
                
                # Update local cache
                self.active_tickets[channel_id] = updated_ticket
                
                # Emit sync event
                if self.sync_service:
                    sync_event = SyncEvent(
                        event_type=SyncEventType.TICKET_UPDATED,
                        data=updated_ticket,
                        source="discord"
                    )
                    await self.sync_service.emit_event(sync_event)
                
                logger.info(f"Updated ticket {ticket_id}")
                return updated_ticket
            else:
                logger.error("Cannot update ticket: API client not connected")
                return None
                
        except Exception as e:
            logger.error(f"Failed to update ticket {ticket_id}: {e}")
            return None
    
    async def close_ticket(self, channel_id: int) -> bool:
        """Close a ticket.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            True if ticket was closed successfully
        """
        # Get current ticket data
        ticket = await self.get_ticket_by_channel(channel_id)
        if not ticket:
            logger.error(f"Cannot close ticket: ticket not found for channel {channel_id}")
            return False
        
        ticket_id = ticket.get("id")
        if not ticket_id:
            logger.error("Cannot close ticket: no ticket ID")
            return False
        
        try:
            # Close via API
            if self.api_client and self.api_client.connected:
                closed_ticket = await self.api_client.close_ticket(ticket_id)
                
                # Remove from local cache
                if channel_id in self.active_tickets:
                    del self.active_tickets[channel_id]
                
                # Emit sync event
                if self.sync_service:
                    sync_event = SyncEvent(
                        event_type=SyncEventType.TICKET_CLOSED,
                        data=closed_ticket,
                        source="discord"
                    )
                    await self.sync_service.emit_event(sync_event)
                
                # Update Discord channel
                channel = self.bot.get_channel(channel_id)
                if channel:
                    await channel.send("🔒 This ticket has been closed.")
                    # Could implement archiving logic here
                
                logger.info(f"Closed ticket {ticket_id}")
                return True
            else:
                logger.error("Cannot close ticket: API client not connected")
                return False
                
        except Exception as e:
            logger.error(f"Failed to close ticket {ticket_id}: {e}")
            return False
    
    async def _set_ticket_permissions(self, 
                                     channel: discord.TextChannel,
                                     user: discord.Member) -> None:
        """Set permissions for a ticket channel.
        
        Args:
            channel: The ticket channel
            user: The user who created the ticket
        """
        try:
            # Deny @everyone
            await channel.set_permissions(
                channel.guild.default_role,
                read_messages=False,
                send_messages=False
            )
            
            # Allow ticket creator
            await channel.set_permissions(
                user,
                read_messages=True,
                send_messages=True,
                read_message_history=True
            )
            
            # Allow staff role if configured
            staff_role = await self.get_staff_role(channel.guild)
            if staff_role:
                await channel.set_permissions(
                    staff_role,
                    read_messages=True,
                    send_messages=True,
                    read_message_history=True,
                    manage_messages=True
                )
            
        except discord.Forbidden:
            logger.warning(f"No permission to set channel permissions for {channel.id}")
        except Exception as e:
            logger.error(f"Failed to set channel permissions: {e}")