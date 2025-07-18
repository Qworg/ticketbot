"""Discord Bot for Ticket Management System."""

import os
import logging
import asyncio
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("discord-bot")

# Load environment variables
load_dotenv()

# Bot configuration
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID")

if not DISCORD_BOT_TOKEN:
    logger.error("DISCORD_BOT_TOKEN not found in environment variables")
    exit(1)

if not DISCORD_GUILD_ID:
    logger.warning("DISCORD_GUILD_ID not found in environment variables, bot will not auto-sync commands")


# Initialize bot with all intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    """Event triggered when the bot is ready."""
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    logger.info(f"Connected to {len(bot.guilds)} guilds")
    
    # Sync commands with Discord
    if DISCORD_GUILD_ID:
        guild = discord.Object(id=int(DISCORD_GUILD_ID))
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
        logger.info(f"Synced commands to guild ID: {DISCORD_GUILD_ID}")
    
    # Set bot status
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching, 
            name="for support tickets"
        )
    )


@bot.tree.command(name="ping", description="Check if the bot is responsive")
async def ping(interaction: discord.Interaction):
    """Simple command to check if the bot is responsive."""
    await interaction.response.send_message(
        f"Pong! Bot latency: {round(bot.latency * 1000)}ms"
    )


@bot.tree.command(name="ticket", description="Manage support tickets")
@app_commands.describe(
    action="The action to perform (create, close, assign)",
    subject="Subject of the ticket (for create action)",
    user="User to assign the ticket to (for assign action)"
)
async def ticket(
    interaction: discord.Interaction, 
    action: str,
    subject: Optional[str] = None,
    user: Optional[discord.Member] = None
):
    """Command group for ticket management."""
    if action == "create":
        if not subject:
            await interaction.response.send_message(
                "Please provide a subject for your ticket.", 
                ephemeral=True
            )
            return
            
        await interaction.response.send_message(
            f"Creating ticket: {subject}... (This is a placeholder, actual implementation coming soon)",
            ephemeral=True
        )
    
    elif action == "close":
        await interaction.response.send_message(
            "Closing this ticket... (This is a placeholder, actual implementation coming soon)",
            ephemeral=True
        )
    
    elif action == "assign":
        if not user:
            await interaction.response.send_message(
                "Please specify a user to assign this ticket to.",
                ephemeral=True
            )
            return
            
        await interaction.response.send_message(
            f"Assigning ticket to {user.mention}... (This is a placeholder, actual implementation coming soon)",
            ephemeral=True
        )
    
    else:
        await interaction.response.send_message(
            "Invalid action. Available actions: create, close, assign",
            ephemeral=True
        )


@bot.event
async def on_message(message):
    """Event triggered when a message is sent."""
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    
    # Process commands
    await bot.process_commands(message)


async def main():
    """Main entry point for the Discord bot."""
    async with bot:
        await bot.start(DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())