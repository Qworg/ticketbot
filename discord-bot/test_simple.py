"""Simple test to verify the ticket commands implementation."""

import sys
import os

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Try importing the modules
try:
    from discord_bot.bot.cogs.ticket_commands import TicketCommands
    print("Successfully imported TicketCommands")
except ImportError as e:
    print(f"Import error: {e}")

# Print the current sys.path
print("\nPython path:")
for path in sys.path:
    print(f"- {path}")

# Try importing with a different approach
print("\nTrying alternative import approach:")
try:
    import discord_bot
    print(f"discord_bot package found at: {discord_bot.__file__}")
    
    from bot.cogs.ticket_commands import TicketCommands
    print("Successfully imported TicketCommands with alternative approach")
except ImportError as e:
    print(f"Alternative import error: {e}")