"""Main Discord bot class for ticket management."""

import logging
import asyncio
import sys
import os
import discord
from discord.ext import commands
from typing import Optional, List, Dict, Any, Union

from discord_bot.config.settings import config, logger
from discord_bot.bot.ticket_manager import TicketManager
from discord_bot.bot.permission_manager import PermissionManager
from discord_bot.bot.message_processor import MessageProcessor

class TicketBot(commands.Bot):
    """Main Discord bot class for ticket management."""
    
    def __init__(self):
        """Initialize the Discord bot with required intents and settings."""
        # Set up intents
        intents = discord.Intents.default()
        intents.message_content = True  # Required for reading message content
        intents.members = True  # Required for accessing member information
        intents.guilds = True  # Required for accessing guild information
        
        # Initialize the bot with settings from config
        super().__init__(
            command_prefix=config.command_prefix,
            intents=intents,
            description="Discord Ticket Bot for support ticket management",
            help_command=None  # Disable default help command
        )
        
        # Bot state
        self.is_ready = False
        self.synced = False
        self.startup_time = None
        self.health_status = {
            "status": "starting",
            "discord_connected": False,
            "commands_synced": False,
            "backend_connected": False,
            "redis_connected": False,
            "uptime": 0,
            "version": "0.1.0",
            "python_version": sys.version.split()[0],
            "discord_version": discord.__version__,
        }
        
        # Initialize managers
        self.ticket_manager = TicketManager(self)
        self.permission_manager = PermissionManager(self)
        self.message_processor = MessageProcessor(self)
        
        # Register error handlers
        self.tree.on_error = self.on_app_command_error
    
    async def setup_hook(self) -> None:
        """Set up hook called before the bot starts running."""
        try:
            # Initialize managers
            logger.info("Initializing message processor...")
            await self.message_processor.initialize()
            
            logger.info("Initializing ticket manager...")
            await self.ticket_manager.initialize()
            
            # Load extensions (cogs)
            logger.info("Loading extensions...")
            await self.load_extensions()
            
            # Register message handler
            self.add_listener(self.on_message, "on_message")
            
            # Record startup time
            self.startup_time = discord.utils.utcnow()
            logger.info("Bot setup completed successfully")
        except Exception as e:
            logger.error(f"Error during bot setup: {e}")
            # Log the full traceback
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    async def load_extensions(self) -> None:
        """Load all bot extensions (cogs)."""
        # Load ticket commands cog
        try:
            await self.load_extension("discord_bot.bot.cogs.ticket_commands")
            logger.info("Loaded ticket_commands extension")
        except Exception as e:
            logger.error(f"Failed to load ticket_commands extension: {e}")
            # Log the full traceback
            import traceback
            logger.error(traceback.format_exc())
    
    async def on_app_command_error(
        self, 
        interaction: discord.Interaction, 
        error: discord.app_commands.AppCommandError
    ) -> None:
        """Handle errors in application commands."""
        if isinstance(error, discord.app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"This command is on cooldown. Try again in {error.retry_after:.2f} seconds.",
                ephemeral=True
            )
        elif isinstance(error, discord.app_commands.MissingPermissions):
            await interaction.response.send_message(
                "You don't have permission to use this command.",
                ephemeral=True
            )
        else:
            # Log the error
            logger.error(f"Error in command {interaction.command.name}: {error}")
            
            # Send a generic error message
            if interaction.response.is_done():
                await interaction.followup.send(
                    "An error occurred while processing this command. Please try again later.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "An error occurred while processing this command. Please try again later.",
                    ephemeral=True
                )
    
    async def sync_commands(self) -> None:
        """Sync application commands with Discord."""
        try:
            if config.guild_id:
                # Sync commands to a specific guild (faster for development)
                guild = discord.Object(id=config.guild_id)
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
                logger.info(f"Synced commands to guild ID: {config.guild_id}")
            else:
                # Sync commands globally (can take up to an hour to propagate)
                await self.tree.sync()
                logger.info("Synced commands globally")
            
            self.synced = True
            self.health_status["commands_synced"] = True
        except discord.HTTPException as e:
            logger.error(f"HTTP error syncing commands: {e}")
            self.health_status["commands_synced"] = False
        except discord.Forbidden as e:
            logger.error(f"Permission error syncing commands: {e}")
            self.health_status["commands_synced"] = False
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
            # Log the full traceback
            import traceback
            logger.error(traceback.format_exc())
            self.health_status["commands_synced"] = False
    
    async def on_ready(self) -> None:
        """Event triggered when the bot is ready."""
        if self.is_ready:
            logger.info("Bot reconnected")
            self.health_status["discord_connected"] = True
            self.health_status["status"] = "running"
            return
        
        self.is_ready = True
        self.health_status["discord_connected"] = True
        self.health_status["status"] = "running"
        
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        
        # Log guild information
        for guild in self.guilds:
            logger.info(f"Connected to guild: {guild.name} (ID: {guild.id})")
        
        # Sync commands with Discord
        await self.sync_commands()
        
        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching, 
                name="for support tickets"
            ),
            status=discord.Status.online
        )
        
        # Register basic commands
        await self.register_basic_commands()
    
    async def on_disconnect(self) -> None:
        """Event triggered when the bot disconnects from Discord."""
        logger.warning("Bot disconnected from Discord")
        self.health_status["discord_connected"] = False
        self.health_status["status"] = "disconnected"
    
    async def on_resumed(self) -> None:
        """Event triggered when the bot resumes connection to Discord."""
        logger.info("Bot resumed connection to Discord")
        self.health_status["discord_connected"] = True
        self.health_status["status"] = "running"
    
    async def on_message(self, message: discord.Message) -> None:
        """Event triggered when a message is sent in a channel the bot can see.
        
        Args:
            message: The Discord message
        """
        # Ignore messages from bots (including self)
        if message.author.bot:
            return
        
        # Ignore DMs for now
        if not message.guild:
            return
        
        # Check if the message is in a ticket channel
        ticket = await self.ticket_manager.get_ticket_by_channel(message.channel.id)
        if ticket:
            # Process the message
            await self.message_processor.process_message(message, ticket["id"])
    
    async def on_error(self, event_method: str, *args, **kwargs) -> None:
        """Handle errors that occur in event handlers."""
        logger.error(f"Error in {event_method}: {args} {kwargs}")
        # Log the full traceback
        import traceback
        logger.error(traceback.format_exc())
    
    async def register_basic_commands(self) -> None:
        """Register basic bot commands."""
        # Health command
        @self.tree.command(name="health", description="Check the bot's health status")
        async def health(interaction: discord.Interaction):
            """Check the bot's health status."""
            health_status = await self.check_health()
            
            # Format the health status as a message
            status_emoji = "🟢" if health_status["status"] == "healthy" else "🟠" if health_status["status"] == "degraded" else "🔴"
            
            embed = discord.Embed(
                title="Bot Health Status",
                description=f"{status_emoji} **Status:** {health_status['status'].upper()}",
                color=discord.Color.green() if health_status["status"] == "healthy" else 
                      discord.Color.orange() if health_status["status"] == "degraded" else 
                      discord.Color.red()
            )
            
            # Add connection status fields
            embed.add_field(name="Discord Connected", value="✅" if health_status["discord_connected"] else "❌", inline=True)
            embed.add_field(name="Commands Synced", value="✅" if health_status["commands_synced"] else "❌", inline=True)
            embed.add_field(name="Backend Connected", value="✅" if health_status["backend_connected"] else "❌", inline=True)
            embed.add_field(name="Redis Connected", value="✅" if health_status["redis_connected"] else "❌", inline=True)
            
            # Add version information
            embed.add_field(name="Bot Version", value=health_status["version"], inline=True)
            embed.add_field(name="Uptime", value=f"{health_status['uptime']} seconds", inline=True)
            
            # Add footer with timestamp
            embed.set_footer(text=f"Discord.py {health_status['discord_version']} | Python {health_status['python_version']}")
            embed.timestamp = discord.utils.utcnow()
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Ping command
        @self.tree.command(name="ping", description="Check if the bot is responsive")
        async def ping(interaction: discord.Interaction):
            """Simple command to check if the bot is responsive."""
            latency = round(self.latency * 1000)
            color = discord.Color.green() if latency < 100 else discord.Color.orange() if latency < 300 else discord.Color.red()
            
            embed = discord.Embed(
                title="Pong! 🏓",
                description=f"Bot latency: **{latency}ms**",
                color=color
            )
            embed.timestamp = discord.utils.utcnow()
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Version command
        @self.tree.command(name="version", description="Show bot version information")
        async def version(interaction: discord.Interaction):
            """Show bot version information."""
            embed = discord.Embed(
                title="Discord Ticket Bot",
                description="Support ticket management system",
                color=discord.Color.blue()
            )
            
            embed.add_field(name="Version", value=self.health_status["version"], inline=True)
            embed.add_field(name="Framework", value=f"py-cord {discord.__version__}", inline=True)
            embed.add_field(name="Python", value=self.health_status["python_version"], inline=True)
            
            if self.startup_time:
                embed.add_field(
                    name="Uptime", 
                    value=str(discord.utils.utcnow() - self.startup_time).split(".")[0],
                    inline=True
                )
            
            embed.set_footer(text=f"Connected to {len(self.guilds)} guilds")
            embed.timestamp = discord.utils.utcnow()
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        logger.info("Registered basic commands")
    
    async def check_health(self) -> Dict[str, Any]:
        """Check the health status of the bot."""
        # Update health status
        self.health_status["discord_connected"] = self.is_ready and not self.is_closed()
        
        # Check backend connection
        if hasattr(self.ticket_manager, "api_client") and self.ticket_manager.api_client:
            self.health_status["backend_connected"] = self.ticket_manager.api_client.connected
        
        # Calculate uptime
        if self.startup_time:
            self.health_status["uptime"] = (discord.utils.utcnow() - self.startup_time).total_seconds()
        
        # Determine overall status
        if all([
            self.health_status["discord_connected"],
            self.health_status["commands_synced"],
            self.health_status["backend_connected"],
            self.health_status["redis_connected"],
        ]):
            self.health_status["status"] = "healthy"
        elif self.health_status["discord_connected"]:
            self.health_status["status"] = "degraded"
        else:
            self.health_status["status"] = "unhealthy"
        
        return self.health_status