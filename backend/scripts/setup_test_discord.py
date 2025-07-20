"""
Setup script for creating a test Discord server and users for local development.
This script uses the Discord API to create a server, channels, and test users.

Note: This script requires a Discord bot token with the appropriate permissions.
"""

import os
import sys
import asyncio
import json
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Discord API endpoints
DISCORD_API_BASE = "https://discord.com/api/v10"
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Test server configuration
TEST_SERVER_CONFIG = {
    "name": "Ticket Bot Test Server",
    "channels": [
        {"name": "general", "type": 0},  # Text channel
        {"name": "tickets", "type": 0},  # Text channel for ticket commands
        {"name": "staff-only", "type": 0},  # Staff-only channel
    ],
    "roles": [
        {"name": "Admin", "color": 0xFF0000, "permissions": 8},  # Administrator
        {"name": "Moderator", "color": 0x00FF00, "permissions": 0x0000000000000020},  # Manage Messages
        {"name": "Support", "color": 0x0000FF, "permissions": 0x0000000000000400},  # Read Messages
        {"name": "User", "color": 0x808080, "permissions": 0x0000000000000400},  # Read Messages
    ]
}


class DiscordSetup:
    """Discord server setup utility."""
    
    def __init__(self, token):
        """Initialize with Discord bot token."""
        self.token = token
        self.headers = {
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json"
        }
        self.client = httpx.AsyncClient(headers=self.headers, timeout=30.0)
        self.guild_id = None
        self.channels = {}
        self.roles = {}
    
    async def create_guild(self):
        """Create a new Discord guild (server)."""
        print("Creating Discord test server...")
        response = await self.client.post(
            f"{DISCORD_API_BASE}/guilds",
            json={"name": TEST_SERVER_CONFIG["name"]}
        )
        
        if response.status_code == 201:
            guild_data = response.json()
            self.guild_id = guild_data["id"]
            print(f"Created server: {guild_data['name']} (ID: {self.guild_id})")
            return guild_data
        else:
            print(f"Failed to create server: {response.status_code} {response.text}")
            return None
    
    async def create_channels(self):
        """Create channels in the Discord server."""
        print("Creating channels...")
        for channel_config in TEST_SERVER_CONFIG["channels"]:
            response = await self.client.post(
                f"{DISCORD_API_BASE}/guilds/{self.guild_id}/channels",
                json=channel_config
            )
            
            if response.status_code == 201:
                channel_data = response.json()
                self.channels[channel_data["name"]] = channel_data["id"]
                print(f"Created channel: {channel_data['name']} (ID: {channel_data['id']})")
            else:
                print(f"Failed to create channel {channel_config['name']}: {response.status_code} {response.text}")
    
    async def create_roles(self):
        """Create roles in the Discord server."""
        print("Creating roles...")
        for role_config in TEST_SERVER_CONFIG["roles"]:
            response = await self.client.post(
                f"{DISCORD_API_BASE}/guilds/{self.guild_id}/roles",
                json=role_config
            )
            
            if response.status_code == 200:
                role_data = response.json()
                self.roles[role_data["name"]] = role_data["id"]
                print(f"Created role: {role_data['name']} (ID: {role_data['id']})")
            else:
                print(f"Failed to create role {role_config['name']}: {response.status_code} {response.text}")
    
    async def save_config(self):
        """Save the server configuration to a file."""
        config = {
            "guild_id": self.guild_id,
            "channels": self.channels,
            "roles": self.roles
        }
        
        config_path = Path(__file__).parent / "discord_test_config.json"
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        
        print(f"Saved Discord test server configuration to {config_path}")
    
    async def setup(self):
        """Set up the Discord test server."""
        if not self.token:
            print("Error: DISCORD_BOT_TOKEN environment variable not set.")
            print("Please set it in your .env file or environment variables.")
            return False
        
        try:
            # Create guild
            guild = await self.create_guild()
            if not guild:
                return False
            
            # Create channels and roles
            await self.create_channels()
            await self.create_roles()
            
            # Save configuration
            await self.save_config()
            
            print("\nDiscord test server setup complete!")
            print(f"Server ID: {self.guild_id}")
            print("\nImportant: Add this server ID to your .env file as DISCORD_GUILD_ID")
            print("You can now use this server for testing the Discord Ticket Bot.")
            
            return True
        
        except Exception as e:
            print(f"Error setting up Discord test server: {e}")
            return False
        
        finally:
            await self.client.aclose()


async def main():
    """Main function to set up the Discord test server."""
    setup = DiscordSetup(DISCORD_BOT_TOKEN)
    await setup.setup()


if __name__ == "__main__":
    # Create directory if it doesn't exist
    os.makedirs(Path(__file__).parent, exist_ok=True)
    
    # Run the setup
    asyncio.run(main())