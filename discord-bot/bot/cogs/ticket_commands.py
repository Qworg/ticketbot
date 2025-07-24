"""Discord ticket commands cog."""

import logging
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, Dict, Any, List

# Use relative imports that work both when installed and in development
import sys
import os

# Try the installed package path first, then fall back to relative path
try:
    from discord_bot.config.settings import config, logger
    from discord_bot.utils.http_client import get_api_client
except ImportError:
    # Fall back to relative imports
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
    from config.settings import config, logger
    from utils.http_client import get_api_client


class TicketCommands(commands.Cog):
    """Cog for ticket-related commands."""
    
    def __init__(self, bot):
        """Initialize the ticket commands cog.
        
        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
        self.ticket_manager = bot.ticket_manager
        self.permission_manager = bot.permission_manager
        self.message_processor = bot.message_processor
    
    @app_commands.command(name="ticket", description="Manage support tickets")
    @app_commands.describe(
        action="The action to perform (create, close, assign)",
        subject="Subject of the ticket (for create action)",
        user="User to assign the ticket to (for assign action)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="create", value="create"),
        app_commands.Choice(name="close", value="close"),
        app_commands.Choice(name="assign", value="assign"),
    ])
    async def ticket_command(
        self,
        interaction: discord.Interaction,
        action: str,
        subject: Optional[str] = None,
        user: Optional[discord.Member] = None
    ) -> None:
        """Manage support tickets.
        
        Args:
            interaction: The Discord interaction
            action: The action to perform (create, close, assign)
            subject: Subject of the ticket (for create action)
            user: User to assign the ticket to (for assign action)
        """
        # Defer the response to give us time to process
        await interaction.response.defer(ephemeral=True)
        
        if action == "create":
            await self.create_ticket(interaction, subject)
        elif action == "close":
            await self.close_ticket(interaction)
        elif action == "assign":
            await self.assign_ticket(interaction, user)
        else:
            await interaction.followup.send(
                "Invalid action. Use `/ticket create`, `/ticket close`, or `/ticket assign`.",
                ephemeral=True
            )
    
    async def create_ticket(
        self,
        interaction: discord.Interaction,
        subject: Optional[str]
    ) -> None:
        """Create a new support ticket.
        
        Args:
            interaction: The Discord interaction
            subject: Subject of the ticket
        """
        if not subject:
            await interaction.followup.send(
                "Please provide a subject for your ticket.",
                ephemeral=True
            )
            return
        
        # Get API client
        api_client = await get_api_client()
        if not api_client or not api_client.connected:
            await interaction.followup.send(
                "Unable to connect to the ticket system. Please try again later.",
                ephemeral=True
            )
            return
        
        # Get ticket category
        category = await self.ticket_manager.get_ticket_category()
        if not category:
            await interaction.followup.send(
                "Ticket category not configured. Please contact an administrator.",
                ephemeral=True
            )
            return
        
        try:
            # Create ticket in the backend
            ticket_data = {
                "title": subject,
                "description": f"Ticket created by {interaction.user.display_name}",
                "creator_discord_id": interaction.user.id,
            }
            
            # Send request to create ticket
            response = await api_client.post("/api/tickets", data=ticket_data)
            ticket_id = response.get("id")
            
            if not ticket_id:
                await interaction.followup.send(
                    "Failed to create ticket. Please try again later.",
                    ephemeral=True
                )
                return
            
            # Create Discord channel
            channel_name = f"ticket-{ticket_id[:8]}"
            channel = await interaction.guild.create_text_channel(
                name=channel_name,
                category=category,
                topic=f"Support ticket: {subject} | ID: {ticket_id}"
            )
            
            # Update ticket with channel ID
            await api_client.put(
                f"/api/tickets/{ticket_id}",
                data={"discord_channel_id": channel.id}
            )
            
            # Set up channel permissions
            await self.permission_manager.setup_ticket_permissions(
                channel=channel,
                user_id=interaction.user.id
            )
            
            # Add ticket to local cache
            self.ticket_manager.active_tickets[channel.id] = response
            
            # Send welcome message
            embed = discord.Embed(
                title=f"Ticket: {subject}",
                description="Thank you for creating a support ticket. A staff member will assist you shortly.",
                color=discord.Color.blue()
            )
            embed.add_field(name="Ticket ID", value=ticket_id, inline=True)
            embed.add_field(name="Created by", value=interaction.user.mention, inline=True)
            embed.set_footer(text="Use /ticket close to close this ticket when resolved")
            
            await channel.send(embed=embed)
            
            # Send confirmation to user
            await interaction.followup.send(
                f"Ticket created successfully! Please check {channel.mention}",
                ephemeral=True
            )
            
            # Log the action
            logger.info(f"Ticket created by {interaction.user.id} with ID {ticket_id}")
            
        except Exception as e:
            logger.error(f"Error creating ticket: {e}")
            await interaction.followup.send(
                "An error occurred while creating your ticket. Please try again later.",
                ephemeral=True
            )
    
    async def close_ticket(self, interaction: discord.Interaction) -> None:
        """Close a support ticket.
        
        Args:
            interaction: The Discord interaction
        """
        # Check if the command is used in a ticket channel
        ticket = await self.ticket_manager.get_ticket_by_channel(interaction.channel_id)
        if not ticket:
            await interaction.followup.send(
                "This command can only be used in a ticket channel.",
                ephemeral=True
            )
            return
        
        # Check permissions
        if not interaction.user.guild_permissions.manage_channels:
            staff_role = await self.ticket_manager.get_staff_role(interaction.guild)
            if not staff_role or staff_role not in interaction.user.roles:
                # Check if user is the ticket creator
                if interaction.user.id != ticket.get("creator_discord_id"):
                    await interaction.followup.send(
                        "You don't have permission to close this ticket.",
                        ephemeral=True
                    )
                    return
        
        # Get API client
        api_client = await get_api_client()
        if not api_client or not api_client.connected:
            await interaction.followup.send(
                "Unable to connect to the ticket system. Please try again later.",
                ephemeral=True
            )
            return
        
        try:
            # Update ticket status in the backend
            ticket_id = ticket.get("id")
            await api_client.put(
                f"/api/tickets/{ticket_id}",
                data={"status": "closed"}
            )
            
            # Update permissions
            await self.permission_manager.update_ticket_permissions(
                channel=interaction.channel,
                user_id=ticket.get("creator_discord_id"),
                is_closed=True
            )
            
            # Remove from active tickets
            if interaction.channel_id in self.ticket_manager.active_tickets:
                del self.ticket_manager.active_tickets[interaction.channel_id]
            
            # Send closure message
            embed = discord.Embed(
                title="Ticket Closed",
                description=f"This ticket has been closed by {interaction.user.mention}.",
                color=discord.Color.red()
            )
            embed.add_field(name="Ticket ID", value=ticket_id, inline=True)
            embed.set_footer(text="This channel will be archived")
            
            await interaction.channel.send(embed=embed)
            
            # Send confirmation to user
            await interaction.followup.send(
                "Ticket closed successfully!",
                ephemeral=True
            )
            
            # Archive the channel
            try:
                await interaction.channel.edit(archived=True)
            except discord.HTTPException:
                # If archiving fails, just lock the channel
                await interaction.channel.set_permissions(
                    interaction.guild.default_role,
                    send_messages=False
                )
            
            # Log the action
            logger.info(f"Ticket {ticket_id} closed by {interaction.user.id}")
            
        except Exception as e:
            logger.error(f"Error closing ticket: {e}")
            await interaction.followup.send(
                "An error occurred while closing the ticket. Please try again later.",
                ephemeral=True
            )
    
    async def assign_ticket(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.Member]
    ) -> None:
        """Assign a ticket to a staff member.
        
        Args:
            interaction: The Discord interaction
            user: The user to assign the ticket to
        """
        # Check if the command is used in a ticket channel
        ticket = await self.ticket_manager.get_ticket_by_channel(interaction.channel_id)
        if not ticket:
            await interaction.followup.send(
                "This command can only be used in a ticket channel.",
                ephemeral=True
            )
            return
        
        # Check permissions
        if not interaction.user.guild_permissions.manage_channels:
            staff_role = await self.ticket_manager.get_staff_role(interaction.guild)
            if not staff_role or staff_role not in interaction.user.roles:
                await interaction.followup.send(
                    "You don't have permission to assign this ticket.",
                    ephemeral=True
                )
                return
        
        # Check if a user was provided
        if not user:
            await interaction.followup.send(
                "Please specify a user to assign this ticket to.",
                ephemeral=True
            )
            return
        
        # Check if the user is a staff member
        staff_role = await self.ticket_manager.get_staff_role(interaction.guild)
        if staff_role and staff_role not in user.roles:
            await interaction.followup.send(
                f"{user.mention} is not a staff member and cannot be assigned to tickets.",
                ephemeral=True
            )
            return
        
        # Get API client
        api_client = await get_api_client()
        if not api_client or not api_client.connected:
            await interaction.followup.send(
                "Unable to connect to the ticket system. Please try again later.",
                ephemeral=True
            )
            return
        
        try:
            # Update ticket in the backend
            ticket_id = ticket.get("id")
            await api_client.put(
                f"/api/tickets/{ticket_id}",
                data={"assigned_staff_id": user.id}
            )
            
            # Update permissions
            await self.permission_manager.update_ticket_permissions(
                channel=interaction.channel,
                staff_id=user.id
            )
            
            # Update local cache
            if interaction.channel_id in self.ticket_manager.active_tickets:
                self.ticket_manager.active_tickets[interaction.channel_id]["assigned_staff_id"] = user.id
            
            # Send assignment message
            embed = discord.Embed(
                title="Ticket Assigned",
                description=f"This ticket has been assigned to {user.mention}.",
                color=discord.Color.green()
            )
            embed.add_field(name="Ticket ID", value=ticket_id, inline=True)
            embed.add_field(name="Assigned by", value=interaction.user.mention, inline=True)
            
            await interaction.channel.send(embed=embed)
            
            # Send confirmation to user
            await interaction.followup.send(
                f"Ticket assigned to {user.mention} successfully!",
                ephemeral=True
            )
            
            # Log the action
            logger.info(f"Ticket {ticket_id} assigned to {user.id} by {interaction.user.id}")
            
        except Exception as e:
            logger.error(f"Error assigning ticket: {e}")
            await interaction.followup.send(
                "An error occurred while assigning the ticket. Please try again later.",
                ephemeral=True
            )


async def setup(bot):
    """Add the cog to the bot."""
    await bot.add_cog(TicketCommands(bot))